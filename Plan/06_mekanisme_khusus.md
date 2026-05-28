# 06 — Mekanisme Khusus & Safety Net

> Dokumen ini menjelaskan fitur-fitur unik dan "pagar pengaman" yang dibangun
> di dalam sistem. Penting dibaca agar paham MENGAPA sistem berperilaku tertentu.
> Prasyarat: Sudah membaca `03_machine_learning_detail.md`.

---

## 1. SATPAM Data Completeness

**Lokasi:** `forecast_service.py` (awal fungsi `generate_forecast`)

**Tujuan:** Mencegah prediksi dijalankan jika data historis bulan lalu tidak lengkap.

### Logika
```
1. Hitung jumlah hari data yang ada di Vending_Aggregrated (bulan lalu)
2. Hitung jumlah hari produktif dari OperationalCalendar (non-Ramadan, hari kerja)
3. Jika data < 80% dari target → TOLAK prediksi (raise ValueError)
4. PENGECUALIAN: Jika target hari ≤ 10 (bulan Ramadan penuh) → lewati pengecekan
5. PENGECUALIAN: Jika is_data_gap=True (timeout 45 hari) → izinkan dengan warning
```

### Kenapa Ada?
Lag XGBoost butuh data bulan lalu yang akurat. Jika data tidak lengkap,
lag yang terhitung akan lebih rendah dari seharusnya → prediksi meleset.

---

## 2. SATPAM VM Mati

**Lokasi:** `forecast_service.py` (fungsi `update_actuals`)

**Tujuan:** Peringatan jika ada mesin vending yang belum sinkron datanya.

### Logika
```
1. Baca master_alat_vm
2. Cek mesin dengan update_time = NULL
3. Jika ada → tambahkan warning di response
```

### Kenapa Ada?
Jika VM mati, data aktual tidak lengkap → ErrorPercent bisa menyesatkan.

---

## 3. SATPAM Retrain (Target Leakage Prevention)

**Lokasi:** `retrain_service.py` (parameter `exclude_month_and_beyond`)

**Tujuan:** Mencegah kebocoran data saat retrain.

### Logika
```
Saat retrain untuk Q2 (Apr-Jun):
  - Buang semua data bulan April ke atas dari training set
  - Karena bulan April adalah "masa depan" yang belum selesai
  - Jika datanya parsial masuk training → model "mengintip" jawaban
```

---

## 4. Lag Skipper (Ramadan)

**Lokasi:** `ProductionML/Layer1_Core.py` (fungsi `_get_normal_lag_month`)

**Tujuan:** Memastikan lag referensi selalu dari bulan "normal" (non-Ramadan).

### Contoh
```
Prediksi: April 2026
  lag_1m (tanpa skipper): Maret 2026 → demand 5,500 (RAMADAN!)
  lag_1m (dengan skipper): Januari 2026 → demand 52,000 (NORMAL)
```

### Aturan
- `lag_1m`, `lag_2m`, `lag_3m` → SKIP bulan Ramadan
- `lag_12m` → TIDAK skip (karena untuk Year-over-Year, harus absolut)

---

## 5. YoY Guard

**Lokasi:** `ProductionML/Layer1_Core.py` (fungsi `build_features`)

**Tujuan:** Mencegah YoY change yang menyesatkan.

### Logika
```
Jika lag_12m < 100 (demand sangat rendah) ATAU bulan 12 lalu adalah Ramadan:
  yoy_change = 0.0 (netralkan)
Alasan: Membandingkan bulan normal sekarang vs Ramadan setahun lalu tidak bermakna.
```

---

## 6. Share Smoother

**Lokasi:** `retrain_service.py` (Step 2B)

**Tujuan:** Memperbaiki distribusi share varian yang terdistorsi oleh Ramadan.

### Kondisi Deteksi Distorsi
```
total_demand_bulan < 500          → anomali rendah
ATAU share_varian > 85%           → satu varian mendominasi
ATAU share_varian < 2% (dan median > 5%) → varian menghilang
```

### Perbaikan
```
share_baru = (share_bulan_sebelum + share_bulan_sesudah) / 2
```

Setelah patch, fitur downstream (`share_lag_1m`, `share_change`, `share_trend_3m`)
dihitung ulang.

---

## 7. Step 9 Business Logic Override

**Lokasi:** `ProductionML/Layer1_Core.py` (fungsi `predict`)

**Tujuan:** Mengganti XGBoost dengan rumus sederhana untuk bulan Ramadan ekstrem.

### Kondisi Aktivasi
```
productive_milk_days ≤ 10
```

### Rumus Pengganti
```
demand_varian = (rolling_avg_3m / 25) × jumlah_hari_produktif
```

### Efek Lanjutan di Layer 2
Ketika Business Logic aktif, `forecast_service.py` set `event_factors["ramadan"] = 0.0`
agar seluruh budget terkonsentrasi ke hari-hari produktif saja (tidak dibagi ke hari Ramadan).

---

## 8. Time Machine Simulation

**Lokasi:** `forecast_service.py` (generate_forecast)

**Tujuan:** Memastikan hasil prediksi konsisten meskipun dijalankan terlambat.

### Logika
```
Potong histori data HANYA sampai tepat sebelum start_month.
Contoh: Prediksi Q2 2026 dijalankan di Mei 2026
  → data dipotong hanya sampai 31 Maret 2026
  → seolah-olah dijalankan tepat 1 April 2026
```

### Kenapa Ada?
Tanpa ini, prediksi yang dijalankan bulan Mei akan memakai data April yang sudah
ada → menghasilkan angka yang berbeda dari prediksi yang dijalankan tepat awal kuartal.

---

## 9. Smart Backfill (Quarterly)

**Lokasi:** `scheduler_service.py` (check_and_run_quarterly)

**Tujuan:** Otomatis mendeteksi kuartal yang terlewat.

### Logika
```
1. Mulai dari Q1 2026
2. Cek apakah bulan pertama kuartal sudah ada di ForecastResults_Layer1
3. Jika belum → fokus eksekusi di kuartal ini
4. Jika sudah → lanjut cek kuartal berikutnya
5. Ulangi sampai kuartal sekarang
```

### Kenapa Ada?
Jika server mati 3 bulan, saat dinyalakan kembali sistem tidak bingung —
otomatis mengejar kuartal-kuartal yang terlewat secara berurutan.

---

## 10. Outlier Removal (Dynamic)

**Lokasi:** `retrain_service.py` (sebelum Step 3)

**Tujuan:** Mengeluarkan bulan Ramadan ekstrem dari set training XGBoost.

### Logika
```
Query ke OperationalCalendar:
  Cari bulan dengan hari produktif ≤ 10
  → Keluarkan dari training data

Jika query gagal → fallback ke ["2026-03"]
```

### Kenapa Ada?
Bulan dengan hanya 2 hari kerja memiliki demand yang sangat rendah.
Jika masuk training, pohon keputusan XGBoost akan "belajar" bahwa
demand rendah itu normal → merusak prediksi bulan-bulan lain.

---

## 11. Backtest Filter (Ramadan)

**Lokasi:** `retrain_service.py` (Step 3)

**Tujuan:** Mengeluarkan bulan Ramadan dari pool backtest.

### Alasan
Sistem sendiri sudah memperlakukan Ramadan sebagai anomali:
- Lag Skipper: skip bulan Ramadan
- Step 9: Business Logic override
- Share Smoother: interpolasi

Maka tidak konsisten untuk mengevaluasi akurasi model TERHADAP bulan Ramadan.

---

## 12. Adaptive Pre-Ramadan Weekend

**Lokasi:** `Script_production_daily_2_prod_v2.py` (fungsi `_get_adaptive_weekend_ratios`)

**Tujuan:** Boost demand weekend di bulan sebelum Ramadan.

### Alasan
Pola historis menunjukkan bahwa weekend sebelum Ramadan lebih ramai dari biasanya
(orang belanja stok). Sistem menghitung rasio Sabtu/Minggu vs weekday dari data
tahun-tahun sebelumnya, lalu override profil DOW normal.

---

## Ringkasan Safety Net

| #  | Nama                    | Melindungi Dari                        |
|----|-------------------------|----------------------------------------|
| 1  | SATPAM Data             | Prediksi dengan data tidak lengkap     |
| 2  | SATPAM VM Mati          | Evaluasi dengan aktual tidak lengkap   |
| 3  | SATPAM Retrain          | Target leakage saat retrain            |
| 4  | Lag Skipper             | Lag terkontaminasi Ramadan             |
| 5  | YoY Guard               | YoY menyesatkan (bulan Ramadan)        |
| 6  | Share Smoother          | Share terdistorsi oleh demand rendah   |
| 7  | Step 9 Business Logic   | XGBoost tidak reliable pada < 10 hari  |
| 8  | Time Machine            | Hasil berubah tergantung waktu run     |
| 9  | Smart Backfill          | Kuartal terlewat saat server mati      |
| 10 | Outlier Removal         | Training data terkontaminasi outlier   |
| 11 | Backtest Filter         | Metrik MAPE terdistorsi bulan Ramadan  |
| 12 | Adaptive Weekend        | Weekend pre-Ramadan lebih ramai        |

---

> Ini dokumen terakhir dari seri gradual. Untuk referensi cepat, kembali ke
> `01_arsitektur_overview.md`.
