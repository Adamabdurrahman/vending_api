# 03 — Machine Learning Detail

> Dokumen ini menjelaskan arsitektur model ML (Layer 1 + Layer 2).
> Prasyarat: Sudah membaca `01_arsitektur_overview.md` dan `02_alur_data_pipeline.md`.

---

## Arsitektur 2-Layer

```
┌──────────────────────────────────────────────────────────────────┐
│                        LAYER 1 (XGBoost)                          │
│  Input:  Fitur bulanan (lag, share, kalender, trend, dll)        │
│  Output: Budget bulanan per varian (Coklat, Moca, Original,      │
│          Strawberry)                                              │
│  Contoh: "Januari 2026 → 52,000 kotak total"                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼ budget_dict
┌──────────────────────────────────────────────────────────────────┐
│                   LAYER 2 (Distribusi Harian)                     │
│  Input:  Budget dari Layer 1 + Kalender + Profil Shift/DOW       │
│  Output: Prediksi per hari × per shift × per varian              │
│  Contoh: "1 Jan 2026, SHIFT1, Coklat → 210 kotak"               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Model XGBoost (`ProductionML/Layer1_Core.py`)

### Model Wrapper: `Layer1Model`

Ini adalah class yang membungkus semuanya menjadi 1 artifact `.joblib`:

| Komponen          | Tipe            | Fungsi                                  |
|-------------------|-----------------|-----------------------------------------|
| `model`           | XGBRegressor    | Model XGBoost yang sudah dilatih        |
| `scaler`          | StandardScaler  | Normalisasi fitur                       |
| `imputer`         | SimpleImputer   | Mengisi nilai NaN dengan median         |
| `feature_cols`    | list[str]       | Daftar 22 fitur yang dipakai            |
| `historical_df`   | DataFrame       | Data historis (untuk menghitung lag)    |
| `metadata`        | dict            | Versi, metrik, config Ramadan, dll      |

### Daftar 22 Fitur

| #  | Nama Fitur            | Arti                                                |
|----|-----------------------|-----------------------------------------------------|
| 1  | `working_days`        | Jumlah hari kerja (fractional weight dari 3 shift)  |
| 2  | `ramadan_pct`         | Persentase hari Ramadan di bulan tersebut            |
| 3  | `holiday_pct`         | Persentase hari libur                                |
| 4  | `month_sin`           | Sinusoidal encoding bulan (seasonality)              |
| 5  | `month_cos`           | Cosine encoding bulan (seasonality)                  |
| 6  | `month_idx`           | Index bulan secara linear (untuk trend)              |
| 7  | `var_Coklat`          | One-hot: varian Coklat                               |
| 8  | `var_Moca`            | One-hot: varian Moca                                 |
| 9  | `var_Original (Putih)`| One-hot: varian Original                             |
| 10 | `var_Strawberry`      | One-hot: varian Strawberry                           |
| 11 | `lag_1m`              | Demand 1 bulan lalu (skip Ramadan!)                  |
| 12 | `lag_2m`              | Demand 2 bulan lalu (skip Ramadan!)                  |
| 13 | `rolling_avg_3m`      | Rata-rata demand 3 bulan terakhir                    |
| 14 | `growth_rate`         | Pertumbuhan lag_1m → lag_2m                          |
| 15 | `trend_slope_3m`      | Kemiringan trend 3 bulan (lag_1m - lag_3m) / 2       |
| 16 | `yoy_change`          | Perubahan Year-over-Year (12 bulan lalu)             |
| 17 | `share_lag_1m`        | Market share varian ini bulan lalu (%)               |
| 18 | `total_demand_lag_1m` | Total demand semua varian bulan lalu                 |
| 19 | `lag_12m`             | Demand 12 bulan lalu (absolut, tidak skip Ramadan)   |
| 20 | `share_change`        | Perubahan market share                               |
| 21 | `demand_acceleration` | Percepatan pertumbuhan (diff of growth_rate)         |
| 22 | `share_trend_3m`      | Trend share 3 bulan                                  |

### Mekanisme Khusus: Lag Skipper

**Masalah:** Bulan Ramadan memiliki demand yang sangat rendah (anomali). Jika bulan
Ramadan dijadikan referensi lag, prediksi bulan berikutnya akan sangat rendah.

**Solusi:** Saat menghitung `lag_1m`, `lag_2m`, `lag_3m`, sistem **melompati** bulan
Ramadan dan mengambil bulan normal sebelumnya.

```
Contoh: Prediksi April 2026
  Normal:  lag_1m = Mar 2026 (RAMADAN → demand sangat rendah!)
  Skipper: lag_1m = Jan 2026 (skip Feb + Mar yang Ramadan)
```

> **PENTING**: `lag_12m` (Year-over-Year) TIDAK skip Ramadan karena digunakan untuk
> perbandingan tahunan yang memang harus absolut.

### Step 9: Business Logic Fallback

Untuk bulan dengan **hari produktif ≤ 10** (biasanya puncak Ramadan):

```
XGBoost TIDAK dipakai → diganti rumus sederhana:
  demand_varian = (rata-rata 3 bulan / 25) × jumlah_hari_produktif
```

Alasan: XGBoost tidak pernah dilatih pada kondisi "hanya 2 hari kerja", jadi hasilnya
tidak bisa dipercaya.

---

## Layer 2: Distribusi Harian (`ProductionML/Script_production_daily_2_prod_v2.py`)

### Tujuan
Membagi budget bulanan Layer 1 ke level **per-hari × per-shift × per-varian**.

### Komponen Utama

#### 1. Kalender Operasional (dari SQL)
```
OperationalCalendar → tanggal, IsWorkingDay, Shift1/2/3_Active, IsRamadan, IsShutdown
```

#### 2. Shift Profile (Hybrid Lookback)
- SHIFT1: rata-rata **3 bulan** terakhir (lebih stabil)
- SHIFT2, SHIFT3: rata-rata **1 bulan** terakhir (lebih responsif)

#### 3. DOW (Day-of-Week) Share Profile
Setiap hari dalam seminggu punya bobot berbeda:
```
Senin: 19.8%  Selasa: 20.2%  Rabu: 20.5%  Kamis: 20.1%  Jumat: 19.4%
Sabtu: ~50% dari weekday   Minggu: ~50% dari weekday
```
*(Angka contoh — dihitung dinamis dari data historis 6 bulan terakhir)*

#### 4. Tiered Event System (Smart Day-Weighting)

| Tipe Hari          | Bobot (Weight)                  |
|---------------------|---------------------------------|
| Factory Shutdown    | **0.0** (pabrik tutup total)    |
| Hangover Normal     | 0.08 (hari setelah shutdown)    |
| Standalone Holiday  | 0.24                            |
| Hangover Weekend    | 0.24                            |
| Ramadan Transition  | 0.70 × weekday + 0.30 × ramadan|
| Ramadan             | `event_factors["ramadan"]` × weekday_avg |
| Weekend             | `dow_shares[5 atau 6]` × weekday_avg |
| Hari Kerja Normal   | `dow_shares[dow]` × 5 × weekday_avg |

#### 5. Adaptive Pre-Ramadan Weekend
Untuk bulan sebelum Ramadan, weekend biasanya **lebih ramai** dari biasa (orang belanja
stok). Sistem menghitung rasio weekend/weekday dari tahun-tahun sebelumnya lalu
meng-override profil DOW.

---

## Retrain Service (`retrain_service.py`)

### Kapan Dijalankan?
- Secara otomatis oleh `scheduler_service.py` sebelum prediksi kuartal baru
- Secara manual via endpoint `POST /api/v1/model/retrain`

### Alur Retrain (8 Step)

```
Step 1:  Load data dari SQL [vending_training_ml]
Step 2:  Feature engineering tambahan (trend_slope_3m, yoy_change, dll)
Step 2B: Share Smoother (interpolasi share bulan Ramadan yang terdistorsi)
Step 3:  GridSearchCV (optimasi hyperparameter)
Step 4:  Walk-Forward Backtest (evaluasi 4 bulan terakhir non-Ramadan)
Step 5:  Final Training (semua data)
Step 6:  Backup artifact lama
Step 7:  Export artifact baru (.joblib)
Step 8:  Verifikasi round-trip (load → predict → cek output masuk akal)
```

### Share Smoother

**Masalah:** Bulan Ramadan demand rendah → share varian terdistorsi (misal Strawberry
jadi 90% karena hanya sedikit transaksi).

**Solusi:** Deteksi distorsi dan **interpolasi** menggunakan rata-rata bulan
sebelum/sesudah:
```
Kondisi distorsi: total_demand < 500 ATAU share > 85% ATAU share < 2%
Perbaikan: share_baru = (share_sebelum + share_sesudah) / 2
```

### Outlier Removal

Bulan dengan hari produktif ≤ 10 (Ramadan ekstrem) **dikeluarkan** dari training,
karena akan merusak bobot pohon keputusan XGBoost.

### Backtest Filter

Bulan Ramadan juga **dikeluarkan** dari pool backtest karena sistem sendiri tidak
mempercayai data Ramadan sebagai referensi.

---

## Smart Insight (`forecast_service.py → generate_smart_insight`)

Setelah prediksi, sistem menghasilkan pesan kontekstual otomatis:

| Trigger                    | Contoh Output                                          |
|----------------------------|--------------------------------------------------------|
| Business Logic aktif       | "via Business Logic (2 hari produktif, Ramadan penuh)" |
| Ramadan parsial            | "Ramadan parsial (15 hari, 50% bulan)"                 |
| Recovery pasca-Ramadan     | "recovery pasca-Ramadan (+180% vs bulan lalu)"         |
| Demand drop > 20%          | "turun 25% vs bulan lalu"                              |
| Pola historis berulang     | "pola historis 3 tahun berturut-turut, bukan anomali"  |

---

> **Lanjut baca:** `04_api_endpoints.md` untuk daftar semua endpoint REST API.
