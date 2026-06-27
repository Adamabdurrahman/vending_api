# Hasil dan Pembahasan — Tabel Data Jurnal Ilmiah
# Sistem Prediksi Demand Distribusi Susu UHT Karyawan PT GS Battery

---

## Tabel 1. Walk-Forward Backtest Layer 1 (XGBoost V6)

Evaluasi dilakukan dengan metode *walk-forward backtest* menggunakan **4 bulan non-Ramadan terbaru** yang dipilih secara dinamis dari dataset pelatihan (Apr 2023–Des 2025). Bulan-bulan Ramadan dikecualikan dari pool evaluasi secara eksplisit karena sistem menggunakan mekanisme *Business Logic Fallback* (Step 9) untuk periode tersebut, sehingga tidak relevan untuk mengevaluasi kemampuan generalisasi raw XGBoost.

| Iterasi | Period Train | Bulan Test | Prediksi (unit) | Aktual (unit) | Error (%) |
|:---:|---|:---:|---:|---:|:---:|
| 1 | Apr 2023 – Agu 2025 | Sep 2025 | 78.745 | 79.442 | −0,88% |
| 2 | Apr 2023 – Sep 2025 | Okt 2025 | 83.076 | 84.188 | −1,32% |
| 3 | Apr 2023 – Okt 2025 | Nov 2025 | 79.712 | 74.432 | +7,09% |
| 4 | Apr 2023 – Nov 2025 | Des 2025 | 81.723 | 78.531 | +4,06% |
| **Rata-rata** | | | | | **3,34%** |

**Konfigurasi hiperparameter terbaik** (GridSearchCV):
`colsample_bytree=0.8`, `learning_rate=0.1`, `max_depth=4`, `n_estimators=100`, `subsample=0.8`

**Metrik evaluasi keseluruhan**: MAPE = **3,34%** | MAE = 2.570 unit | RMSE = 3.154 unit

*Sumber: retrain_log.txt — Run timestamp: 2026-05-16 19:53:26*

---

## Tabel 2. Forward Test Q1 2026 — Layer 1 (Out-of-Sample)

Data aktual Q1 2026 diambil dari `dbo.Vending_Aggregrated`. Maret 2026 merupakan bulan Ramadan ekstrem (hari produktif ≤ 10 hari) sehingga prediksi Layer 1 di-override oleh *Business Logic Fallback* berbasis rata-rata konsumsi harian historis.

| Bulan | Prediksi Layer 1 (unit) | Aktual (unit) | Selisih Error | Keterangan |
|---|---:|---:|:---:|---|
| Januari 2026 | 78.869 | 78.332 | +0,68% | Normal — *under 1%* |
| Februari 2026 | 52.299 | 48.515 | +7,80% | Ramadan parsial (mulai 17 Feb) |
| Maret 2026 | 6.180 | 6.074 | +1,75% | **Business Logic** (Ramadan penuh, 2 hari produktif) |

**Catatan Februari 2026**: Aktual hanya mencakup 18 hari (1–18 Feb) karena data Ramadan setelah 17 Feb tidak masuk dataset evaluasi. Layer 1 memprediksi total 28 hari termasuk ~11 hari Ramadan parsial dengan `factor_ramadan` yang dikalibrasi, menghasilkan selisih 7,80% — masih dalam batas acceptable untuk kondisi transisi Ramadan.

**Catatan Maret 2026**: Sistem mendeteksi `working_days ≤ 10` (hanya 2 hari produktif) dan secara otomatis mengaktifkan *Step 9 Business Logic Fallback*, menghasilkan akurasi sangat tinggi (error 1,75%) meski kondisi ekstrem.

*Sumber: `dbo.ForecastResults_Layer1` — Run timestamp: 2026-05-17 17:11:48*

---

## Tabel 3. Pembuktian Smart Event Classifier v2.2 — Akurasi Event Handling

Perbandingan error prediksi distribusi harian untuk kejadian ekstrem sebelum implementasi v2.2 (baseline: distribusi proporsional seragam) dan sesudah implementasi v2.2 (Smart Event Classifier dengan 8 kategori bobot hari).

| Tanggal | Kategori Hari | Error Sebelum v2.2 (%) | Error Sesudah v2.2 (%) | Penurunan Absolut |
|---|---|:---:|:---:|:---:|
| 1 Jan 2026 | Factory Shutdown (Tahun Baru) | N/A¹ | **0,0%** | — |
| 2 Jan 2026 | Cuti Bersama (post-shutdown) | +73,8% | **−5,2%** | 79,0 pp |
| 3 Jan 2026 | Sabtu post-shutdown (Hangover) | +195,0% | **−2,3%** | 197,3 pp |
| Weekend rata-rata (n=14) | Akhir pekan reguler | +35,7% | **+3,5%** | 32,2 pp |
| Holiday rata-rata (n=3) | Hari libur nasional | +80,0% | **+5,5%** | 74,5 pp |

**Ringkasan dampak v2.2**:
- WAPE harian: **10,6%** → **3,99%** (turun 62,4%)
- Event Accuracy (|error| < 20%): **52,6%** → **89,5%** (naik 36,9 pp)
- Akurasi hari libur khusus: **0%** → **100%** (3/3 hari)
- Akurasi hari akhir pekan: **64,3%** → **92,9%** (13/14 hari)

¹ *Tanggal 1 Jan dikategorikan Factory Shutdown sejak awal — demand = 0 sudah ditangani benar oleh v1 (tidak ada error). Kasus v2.2 adalah akurasi kategori Hangover di H+1 dan H+2 pasca-shutdown.*

*Sumber: Final_Evaluation_Report.txt — Evaluasi: 10–11 Mei 2026*

---

## Referensi Gambar

| No. | Nama File | Deskripsi |
|:---:|---|---|
| Gambar 1 | `plot_01_prediksi_vs_aktual_jan2026.png` | Grafik harian Prediksi vs Aktual — Januari 2026 |
| Gambar 2 | `plot_02_prediksi_vs_aktual_feb2026.png` | Grafik harian Prediksi vs Aktual — Februari 2026 (Ramadan parsial) |
| Gambar 3 | `plot_03_walkforward_backtest_layer1.png` | Bar chart Walk-Forward Backtest Layer 1 (4 iterasi) |
| Gambar 4 | `plot_04_smart_event_classifier_impact.png` | Perbandingan error sebelum/sesudah Smart Event Classifier v2.2 |

Semua file tersimpan di: `vending_api/Asset/`
