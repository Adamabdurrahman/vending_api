# 03 — Pipeline Data dan Feature Engineering

## 1. Alur Data End-to-End

Data mengalir dari transaksi mentah vending machine hingga menjadi dataset siap latih melalui serangkaian tahapan yang terotomasi. Secara keseluruhan, alur ini terbagi menjadi lima tahap utama:

```
[1] Raw Transactions       → dbo.monitor_log_datatransaksi
         ↓ ETL (slot mapping, agregasi harian)
[2] Daily Aggregated Data  → dbo.Vending_Aggregrated
         ↓ build_v3_exact_features() — 6 langkah transformasi
[3] ML Training Dataset    → dbo.vending_training_ml
         ↓ retrain_service.py (feature engineering tambahan)
[4] Final Training Matrix  → DataFrame 22 fitur × N baris
         ↓ SimpleImputer + StandardScaler + XGBRegressor
[5] Model Artifact         → Layer1_XGBoost_V6_Artifact.joblib
```

---

## 2. Tahap ETL: Transaksi → Demand Harian

### 2.1 Proses Extract dan Transform

Data pada tabel `dbo.monitor_log_datatransaksi` mengandung log catatan distribusi susu mentah — setiap baris merepresentasikan satu unit susu yang diambil oleh karyawan. Kolom `slot_number` berupa kode alfanumerik (misalnya "A1", "B3") atau kode numerik lama yang perlu dipetakan ke kode baru.

- `dbo.manage_map_new_slot`: memetakan kode numerik lama ke kode slot baru
- `dbo.manage_map_slot_number`: memetakan slot ke ID varian produk
- `dbo.master_variant`: master data nama varian produk

Setelah pemetaan, catatan pengambilan susu diagregasi per hari per shift per varian untuk menghasilkan kolom `demand` (jumlah unit susu yang diambil karyawan).

### 2.2 Penambahan Flag Kalender

Pada tahap ETL, setiap baris data dilengkapi tiga flag kalender yang konsisten dengan yang digunakan oleh pipeline ML:

```python
# is_holiday: menggunakan library pyholidays.Indonesia()
id_holidays = pyholidays.Indonesia(years=_years, categories=(pyholidays.PUBLIC,))
EXTRA_HOLIDAYS = {datetime.date(2025, 12, 25)}  # Natal 2025 — tidak selalu terdeteksi
holidays_set = set(id_holidays.keys()) | EXTRA_HOLIDAYS

# is_weekend: Sabtu (5) dan Minggu (6)
df["is_weekend"] = (df["tanggal"].dt.dayofweek >= 5).astype(int)

# is_ramadan: berdasarkan rentang Ramadan yang dikonfirmasi
RAMADAN_PERIODS = [
    ("2023-03-22", "2023-04-21"),
    ("2024-03-11", "2024-04-09"),
    ("2025-02-28", "2025-03-30"),
    ("2026-02-17", "2026-03-18"),
]
```

Penting untuk dicatat bahwa definisi `is_holiday` menggunakan kalender resmi nasional Indonesia (bukan "hari tanpa catatan pengambilan susu"), sehingga konsisten antara pipeline ETL, pipeline feature engineering, dan Layer 2 distributer. Ketidakkonsistenan definisi ini pernah menjadi sumber bug yang menyebabkan mismatch data antar komponen sistem.

### 2.3 Perlindungan Data Manual

Sistem membedakan antara data yang masuk melalui pipeline otomatis (`is_manual_insert = 0`) dan data yang diinput manual oleh administrator (`is_manual_insert = 1`). Pada setiap eksekusi ETL, hanya baris dengan `is_manual_insert = 0` yang dihapus dan diganti, sehingga data koreksi manual oleh admin tetap aman.

---

## 3. Feature Engineering: Demand Harian → Dataset ML

Fungsi `build_v3_exact_features()` di `PYTHONEnginering/Script_Pipeline_Databuilder.py` mengubah data harian menjadi dataset bulanan per varian dengan 38+ fitur. Fungsi ini **dipanggil oleh ETL melalui file CSV sementara** (`temp_etl_input.csv` → `temp_etl_output.csv`) sebagai jembatan antara hasil agregasi SQL dan pipeline feature engineering Python. Proses ini terdiri dari enam langkah:

### Langkah 1: Injeksi Hari yang Hilang

Beberapa hari libur tidak memiliki transaksi sama sekali karena vending machine tidak beroperasi, sehingga tidak ada baris di database. Jika tidak ditangani, hitungan `n_days` menjadi kurang dari jumlah hari sebenarnya dalam bulan tersebut. Sistem menginject baris dengan `demand = 0` untuk tanggal-tanggal ini:

```python
MISSING_HOLIDAY_DATES = [
    ('2025-12-25', 'Hari Natal'),  # Natal 2025 tidak ada di database
]
# Inject baris demand=0 untuk setiap varian pada tanggal yang hilang
```

### Langkah 2: Agregasi Bulanan dan Fitur Kalender

Data harian diagregasi ke level bulanan per varian. Sekaligus dihitung empat dimensi kalender per bulan:

| Fitur | Formula |
|---|---|
| `n_days` | Jumlah hari unik dalam bulan |
| `ramadan_days` | Jumlah hari yang masuk periode Ramadan |
| `holiday_days` | Jumlah hari libur nasional pada hari kerja (*holiday weekday*) |
| `weekend_days` | Jumlah hari Sabtu dan Minggu |
| `working_days` | n_days − weekend_days − holiday_weekday_days |
| `ramadan_pct` | ramadan_days / n_days |
| `holiday_pct` | holiday_days / n_days |

### Langkah 3: Fitur Temporal

Fitur temporal dikodekan untuk membantu model memahami siklus musiman:

| Fitur | Formula | Tujuan |
|---|---|---|
| `month_sin` | sin(2π × bulan / 12) | Mengkodekan siklus bulanan (komponen sinus) |
| `month_cos` | cos(2π × bulan / 12) | Mengkodekan siklus bulanan (komponen cosinus) |
| `month_idx` | Indeks urutan bulan sejak awal dataset | Menangkap tren jangka panjang |

Penggunaan encoding sinus dan cosinus memungkinkan model memahami bahwa Desember (bulan 12) dan Januari (bulan 1) berdekatan secara musiman, sesuatu yang tidak dapat ditangkap oleh representasi integer biasa.

### Langkah 4: Lag Features dan Dual-Mode Lag Skipper

Ini adalah tahap paling kritis dalam pipeline. Sistem menghitung lag 1, 2, 3, dan 12 bulan dari data demand historis. Namun, perhitungan lag ini menggunakan mekanisme **Dual-Mode** yang berbeda perilakunya tergantung periode:

**Mode Historis (data sebelum 2026-01)**:
Lag dihitung secara natural — lag_1m adalah bulan sebelumnya tanpa pengecualian. Ini mempertahankan perilaku training data yang konsisten dengan versi model sebelumnya.

**Mode Skip Ramadan (data mulai 2026-01 ke atas)**:
Lag dihitung dengan melewati bulan-bulan Ramadan. Algoritma ini beroperasi seperti berikut:

```python
def compute_dual_mode_lag(row, grp, lag_n):
    p_str = row['period_str']
    if p_str >= "2026-01":  # Mode Skip Ramadan aktif
        curr = p_str
        count = 0
        while count < lag_n:
            curr = get_prev_month(curr)
            if curr not in RAMADAN_MONTHS_LIST:  # Lewati bulan Ramadan
                count += 1
        return get_demand_for_period(grp, curr)
    else:
        # Mode natural: mundur n bulan langsung
        curr = p_str
        for _ in range(lag_n):
            curr = get_prev_month(curr)
        return get_demand_for_period(grp, curr)
```

**Contoh konkret**: Untuk April 2026 (bulan normal setelah Ramadan 2026), lag_1m dalam Mode Historis akan mengambil Maret 2026 yang merupakan bulan Ramadan dengan demand ~0. Ini akan menghasilkan `growth_rate` yang sangat ekstrem dan menyesatkan model. Dengan Mode Skip Ramadan, lag_1m April 2026 mengambil Januari 2026 (bulan normal terdekat), menghasilkan fitur yang lebih representatif.

Pengecualian penting: **lag_12m tetap absolut** (tidak menggunakan Skip). Ini disengaja karena lag_12m digunakan untuk Year-over-Year comparison. Membandingkan bulan ini dengan bulan yang sama setahun lalu tetap relevan secara semantik.

> **Catatan tentang `lag_3m`**: Selain `lag_1m`, `lag_2m`, dan `lag_12m`, pipeline juga menghitung `lag_3m` sebagai **fitur perantara (*intermediate feature*)**. Nilai `lag_3m` tidak masuk langsung sebagai input ke model XGBoost, melainkan digunakan untuk menghitung dua fitur turunan: `rolling_avg_3m = mean(lag_1m, lag_2m, lag_3m)` dan `trend_slope_3m = (lag_1m − lag_3m) / 2.0`. Dengan demikian, `lag_3m` ada di dataset pelatihan tetapi tidak ada dalam daftar `FEATURE_COLS` yang diteruskan ke `XGBRegressor`.

### Langkah 5: Fitur Market Share

Untuk setiap varian, sistem menghitung pangsa pasar (*market share*) terhadap total demand semua varian dalam bulan yang sama:

| Fitur | Keterangan |
|---|---|
| `share_pct` | Persentase demand varian terhadap total demand bulan ini |
| `share_lag_1m` | `share_pct` bulan lalu |
| `share_change` | `share_pct` − `share_lag_1m` (perubahan pangsa pasar) |
| `total_demand_lag_1m` | Total demand semua varian bulan lalu |

Fitur market share ini penting karena permintaan antar varian tidak independen — jika permintaan Coklat naik, kemungkinan besar karena ada perpindahan dari varian lain.

### Langkah 6: Same-Month Historical Statistics

Untuk setiap baris (variant × bulan), sistem menghitung statistik dari data bulan yang sama di tahun-tahun sebelumnya:

| Fitur | Keterangan |
|---|---|
| `share_peak_sm` | Nilai share tertinggi yang pernah tercatat di bulan yang sama |
| `share_min_sm` | Nilai share terendah di bulan yang sama |
| `share_mean_sm` | Rata-rata share di bulan yang sama |
| `share_range_sm` | Rentang (max − min) share di bulan yang sama |
| `demand_peak_sm` | Demand tertinggi di bulan yang sama |
| `demand_mean_sm` | Rata-rata demand di bulan yang sama |

---

## 4. Feature Engineering Tambahan di Retrain Service

Selain fitur yang dihitung oleh pipeline databuilder, `retrain_service.py` menghitung empat fitur tambahan saat proses training:

| Fitur | Formula | Makna |
|---|---|---|
| `trend_slope_3m` | (lag_1m − lag_3m) / 2.0 | Kecepatan perubahan demand dalam 3 bulan terakhir |
| `yoy_change` | lag_1m / lag_12m − 1 | Perubahan demand Year-over-Year |
| `demand_acceleration` | growth_rate − growth_rate_bulan_lalu | Percepatan/perlambatan pertumbuhan demand |
| `share_trend_3m` | share_lag_1m − share_lag_3m | Tren perubahan pangsa pasar dalam 3 bulan |

Fitur `yoy_change` memiliki perlakuan khusus: jika referensi 12 bulan lalu adalah bulan Ramadan (`lag_12m < 100` unit atau periode tersebut teridentifikasi sebagai Ramadan), maka `yoy_change` diset 0.0. Ini mencegah perbandingan "bulan normal vs bulan Ramadan setahun lalu" yang akan menghasilkan rasio yang menyesatkan.

---

## 5. Share Smoother untuk Koreksi Distorsi Ramadan

Bulan Ramadan menyebabkan anomali distribusi pangsa pasar antar varian. Ketika total demand turun drastis (misalnya dari 5.000 unit menjadi 200 unit), distribusi antar varian cenderung sangat tidak stabil — satu varian mungkin mendominasi 80%+ hanya karena denominatornya sangat kecil. Jika dibiarkan, distorsi ini akan merusak fitur `share_pct`, `share_lag_1m`, dan `share_change` yang merupakan fitur penting dalam model.

**Share Smoother** mendeteksi dan memperbaiki distorsi ini sebelum training:

```python
SMOOTHER_DEMAND_FLOOR = 500   # Bulan dengan total demand < 500 dianggap distorted
SMOOTHER_SHARE_MAX = 85.0     # Share > 85% dianggap tidak realistis
SMOOTHER_SHARE_MIN = 2.0      # Share < 2% dianggap tidak realistis (jika median > 5%)

# Jika baris terdeteksi distorted:
# Ganti share_pct dengan rata-rata antara bulan sebelum dan sesudahnya
shr_new = (shr_prev + shr_next) / 2.0
```

Setelah patching, semua fitur downstream yang bergantung pada `share_pct` (yaitu `share_lag_1m`, `share_change`, `share_trend_3m`) dihitung ulang untuk memastikan konsistensi.

---

## 6. Outlier Removal untuk Bulan Ramadan Ekstrem

Bulan-bulan di mana vending machine hampir tidak beroperasi (produktif ≤ 10 hari) dikecualikan dari dataset training XGBoost. Alasannya: untuk bulan seperti ini, Layer 1 menggunakan **Step 9 Business Logic Fallback** (bukan prediksi XGBoost). Jika data bulan-bulan ini tetap dimasukkan dalam training, bobot pohon keputusan XGBoost akan terdistorsi oleh nilai demand ekstrem yang tidak mencerminkan pola normal.

```sql
-- Identifikasi bulan ekstrem secara dinamis dari SQL
SELECT YEAR(Date) as Yr, MONTH(Date) as Mn
FROM dbo.OperationalCalendar
GROUP BY YEAR(Date), MONTH(Date)
HAVING COUNT(CASE WHEN IsRamadan = 0 AND IsWorkingDay = 1 THEN 1 END) <= 10
```

---

## 7. Ringkasan 22 Fitur Input Layer 1

| # | Nama Fitur | Kelompok | Keterangan |
|---|---|---|---|
| 1 | `working_days` | Kalender | Hari kerja (fraksional) |
| 2 | `ramadan_pct` | Kalender | Proporsi hari Ramadan |
| 3 | `holiday_pct` | Kalender | Proporsi hari libur |
| 4 | `month_sin` | Temporal | Siklus musiman (sin) |
| 5 | `month_cos` | Temporal | Siklus musiman (cos) |
| 6 | `month_idx` | Temporal | Indeks bulan absolut (tren) |
| 7 | `var_Coklat` | Varian | Dummy encoding varian Coklat |
| 8 | `var_Moca` | Varian | Dummy encoding varian Moca |
| 9 | `var_Original (Putih)` | Varian | Dummy encoding varian Original |
| 10 | `var_Strawberry` | Varian | Dummy encoding varian Strawberry |
| 11 | `lag_1m` | Lag | Demand bulan normal terdekat sebelumnya |
| 12 | `lag_2m` | Lag | Demand 2 bulan normal ke belakang |
| 13 | `rolling_avg_3m` | Lag | Rata-rata bergerak 3 bulan normal terakhir |
| 14 | `growth_rate` | Trend | Pertumbuhan demand vs bulan lalu (lag_1m) |
| 15 | `trend_slope_3m` | Trend | Kecepatan perubahan demand (lag_1m − lag_3m) / 2 |
| 16 | `yoy_change` | Trend | Perubahan Year-over-Year |
| 17 | `share_lag_1m` | Market Share | Pangsa pasar varian bulan lalu |
| 18 | `total_demand_lag_1m` | Market Share | Total demand semua varian bulan lalu |
| 19 | `lag_12m` | Lag Tahunan | Demand 12 bulan lalu (YoY reference) |
| 20 | `share_change` | Market Share | Perubahan pangsa pasar bulan ini vs lalu |
| 21 | `demand_acceleration` | Trend | Percepatan growth rate |
| 22 | `share_trend_3m` | Market Share | Tren pangsa pasar dalam 3 bulan |

> **Fitur perantara yang tidak masuk model**: `lag_3m` dihitung oleh pipeline sebagai nilai antara, digunakan untuk menghitung `rolling_avg_3m` (rata-rata lag_1m, lag_2m, lag_3m) dan `trend_slope_3m`. Namun `lag_3m` sendiri tidak termasuk dalam `FEATURE_COLS` yang diteruskan ke `XGBRegressor` — hanya 22 fitur di atas yang menjadi input model.
