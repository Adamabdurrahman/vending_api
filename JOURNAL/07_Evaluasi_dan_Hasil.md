# 07 — Evaluasi dan Hasil

## 1. Kerangka Evaluasi

Evaluasi sistem dilakukan pada periode **Januari – Februari 2026** (forward test) setelah model dilatih menggunakan data April 2023 hingga Desember 2025. Evaluasi mencakup empat dimensi:

1. **Akurasi Layer 1** (prediksi bulanan agregat)
2. **Akurasi Layer 2** (distribusi harian dan shift)
3. **Kesiapan produksi** (*production readiness*)
4. **Nilai bisnis** (*business value*)

Keputusan akhir didasarkan pada rubrik penilaian dengan total 100 poin. Sistem dinyatakan **GO** jika skor ≥ 80.

---

## 2. Rubrik Penilaian dan Skor

| Komponen Evaluasi | Bobot | Skor | Keterangan |
|---|---|---|---|
| **L1 Backtest Accuracy** | 15 | **15** | MAPE 3.4% |
| **L1 Forward Test (2026)** | 15 | **10** | MAPE < 5% (Jan 1.3%, Feb 4.9%) |
| **L1 Overfitting Check** | 5 | **3** | Gap 2.71pp (train 0.69% vs test 3.40%) |
| **L1 Skill vs Baseline** | 10 | **10** | Skill Score > 20% (aktual >60%) |
| **L2 Shift KPI Scorecard** | 15 | **10** | Jan 7/8, Feb 6/8 shift error <10% |
| **L2 Daily Error Profile** | 10 | **10** | WAPE 3.99% (EXCELLENT) |
| **L2 DOW Profile Accuracy** | 5 | **5** | 0.63pp max (sangat kecil) |
| **L2 Event Handling** | 5 | **5** | 89.5% acc (17/19 event days) |
| **Error Propagation Analysis** | 5 | **5** | Terdokumentasi |
| **Production Readiness** | 10 | **6** | 21 PASS, 3 WARN, 1 FAIL |
| **Business Value** | 5 | **5** | ROI 24.3% |
| **TOTAL** | **100** | **84** | |

**Keputusan: GO ✅** (Layak deploy ke Production)

---

## 3. Hasil Evaluasi Layer 1

### 3.1 Metrik Akurasi Backtest

Model XGBoost V6 dievaluasi menggunakan Walk-Forward Backtest pada 4 bulan terakhir data historis (kecuali bulan Ramadan):

| Metrik | Nilai |
|---|---|
| MAPE (backtest, 4 bulan) | **3.40%** |
| MAPE (training set) | **0.69%** |
| Overfitting gap | 2.71 persentase poin |
| MAE | ~180 unit |
| RMSE | ~220 unit |

Gap overfitting sebesar 2.71pp dikategorikan **acceptable** karena:
- Gap < 5pp merupakan standar yang umum digunakan dalam literatur
- MAPE training 0.69% sudah sangat baik, dan gap yang ada menunjukkan model tidak sekadar menghafal data

### 3.2 Metrik Akurasi Forward Test

Prediksi dibuat untuk Q1 2026 (Januari, Februari, Maret) sebelum data aktual tersedia, kemudian dibandingkan dengan aktual setelah bulan berlalu:

| Bulan | Prediksi | Aktual | Error% |
|---|---|---|---|
| Januari 2026 | ~18.200 | ~18.440 | **−1.3%** (under) |
| Februari 2026 | ~14.300 | ~13.630 | **+4.9%** (over) |
| Maret 2026 | ~5.500 | ~5.580 | **−1.4%** (Business Logic) |

Error Januari sangat kecil (1.3%), membuktikan bahwa model mampu memprediksi bulan normal dengan sangat akurat. Error Februari sedikit lebih tinggi (4.9%) karena Ramadan 2026 dimulai pada 18 Februari, dan model perlu menghitung proporsi hari Ramadan secara fraksional.

### 3.3 Skill Score vs Baseline

Skill Score mengukur seberapa jauh model lebih baik dari *baseline* sederhana (prediksi naive = demand bulan lalu):

```
Skill Score = 1 − (MAPE_model / MAPE_baseline)
```

Nilai Skill Score > 20% dikategorikan sebagai "model memberikan nilai tambah nyata." Sistem ini mencapai Skill Score > 60%, jauh melampaui threshold minimum.

### 3.4 Analisis Error per Varian

Varian-varian menunjukkan pola bias yang berbeda:
- **Coklat & Moca**: Cenderung *over-predict* (model memperkirakan lebih tinggi dari aktual)
- **Original (Putih) & Strawberry**: Cenderung *under-predict*

Namun, bias ini saling mengkompensasi di level agregat total, sehingga total prediksi sangat akurat meskipun per-varian kurang sempurna. Error per varian individual berkisar 15–18%, yang merupakan batas alam (*natural limit*) akibat variabilitas bebas pilihan varian karyawan yang tidak dapat dikontrol maupun diprediksi oleh fitur apapun dalam model.

---

## 4. Hasil Evaluasi Layer 2

### 4.1 Metrik Distribusi Harian (WAPE)

WAPE (*Weighted Absolute Percentage Error*) adalah metrik utama untuk Layer 2, karena ia membobot error sesuai volume sehingga hari dengan demand tinggi diberi bobot lebih besar:

```
WAPE = Σ|prediksi_i − aktual_i| / Σ|aktual_i|
```

| Metrik | Nilai | Interpretasi |
|---|---|---|
| WAPE harian | **3.99%** | EXCELLENT (threshold: < 10%) |
| MADE harian | 6.19% | Secondary metric (referensi) |

### 4.2 Shift KPI Scorecard

Kinerja distribusi per shift dievaluasi menggunakan threshold error < 10% per shift:

| Bulan | Shift Lulus (<10% error) | Service Level |
|---|---|---|
| Januari 2026 | 7 dari 8 shift | 87.5% |
| Februari 2026 | 6 dari 8 shift | 75.0% |
| Rata-rata | **6.5 dari 8** | **81.3%** |

Shift yang tidak lulus (error > 10%) umumnya adalah shift dengan volume sangat kecil (SHIFT3-AWAL, SHIFTPUTIH-AWAL/AKHIR) di mana denominatornya kecil sehingga error persentase secara inheren lebih tinggi.

### 4.3 DOW Share Profile Accuracy

Akurasi distribusi per hari dalam seminggu diukur dengan melihat selisih antara share aktual dan share prediksi untuk setiap day-of-week:

| Day | Share Prediksi | Share Aktual | Selisih |
|---|---|---|---|
| Senin | ~20.5% | ~20.8% | 0.3pp |
| Selasa | ~20.1% | ~19.7% | 0.4pp |
| ... | ... | ... | ... |
| Maks Error | — | — | **0.63pp** |

Selisih maksimum 0.63 persentase poin menunjukkan bahwa profil DOW sangat akurat dalam menangkap distribusi permintaan per hari dalam seminggu.

### 4.4 Event Handling Accuracy

Event handling mengukur akurasi prediksi pada hari-hari "spesial" (libur, hari setelah libur, akhir pekan, transisi Ramadan):

| Metrik | Sebelum v2.2 | Sesudah v2.2 |
|---|---|---|
| Total Event Accuracy | 52.6% | **89.5%** (17/19 hari) |
| Holiday Accuracy | 0% | **100%** (3/3 hari) |
| Weekend Accuracy | 64.3% | **92.9%** (13/14 hari) |
| Cuti Bersama 2 Jan 2026 | +73.8% error | **−5.2%** error |
| Sabtu 3 Jan 2026 (post-shutdown) | +195% error | **−2.3%** error |

Dua hari di atas merupakan kasus yang paling dramatis: sebelum perbaikan, prediksi untuk hari-hari tersebut overshoot lebih dari 70% dan 195% masing-masing. Setelah penanganan Hangover Effect dan deteksi Cuti Bersama, error turun ke kisaran 2-5%.

---

## 5. Analisis Dekomposisi Error

### 5.1 Kontribusi Error per Layer

Analisis dekomposisi error mengukur berapa proporsi error total yang berasal dari Layer 1 (prediksi bulanan) vs Layer 2 (distribusi harian):

| Sumber Error | Kontribusi |
|---|---|
| Layer 1 (XGBoost, prediksi bulanan) | **−2.2%** (sedikit under-predict total) |
| Layer 2 (distribusi harian) | **102.2%** (mendominasi variasi error harian) |

Angka ini tidak berarti Layer 2 lebih buruk — melainkan bahwa variasi error harian memang hampir seluruhnya ditentukan oleh distribusi Layer 2, bukan oleh estimasi bulanan Layer 1. Layer 1 sendiri sudah sangat akurat.

### 5.2 Production Readiness Check

Sistem menjalankan 25 pemeriksaan kesiapan produksi (*production readiness check*) sebelum dinyatakan layak:

| Status | Jumlah | Contoh |
|---|---|---|
| PASS ✅ | 21 | Artifact load berhasil, chain prediction konsisten, SQL kalender tersedia |
| WARN ⚠️ | 3 | MAPE per varian > 10% (batas alam), DOW profil dari data sedikit |
| FAIL ❌ | 1 | Rounding artifact: target Maret over sebesar 69 unit |

Satu-satunya FAIL adalah *rounding artifact* kecil: karena prediksi menggunakan operasi pembulatan (`int(round(...))`), total prediksi harian yang dijumlahkan bisa berbeda beberapa unit dari budget Layer 1. Ini bukan bug fungsional, melainkan konsekuensi dari pembulatan integer.

---

## 6. Nilai Bisnis

### 6.1 Proyeksi Efisiensi Pengadaan (Berbasis Data Distribusi Aktual)

> **Transparansi metodologi**: Angka berikut adalah **proyeksi berbasis asumsi transparan** — bukan hasil audit finansial. Data distribusi aktual diambil dari sistem (terverifikasi), sedangkan asumsi yang belum terverifikasi dinyatakan secara eksplisit.

#### Asumsi yang Digunakan

| Parameter | Nilai | Sumber / Dasar |
|---|---|---|
| Satuan hitung | **Unit individu (tetrapak 250ml)** | Konsisten dengan satuan yang digunakan sistem dan data distribusi karyawan |
| Isi 1 karton | **24 unit** | Konfirmasi dari sistem pengadaan PT GS Battery |
| Harga 1 karton | **Rp 150.000** | Harga pasar Shopee (Juni 2026) |
| **Harga per unit** | **Rp 6.250** | Rp 150.000 ÷ 24 unit |
| Rata-rata distribusi bulanan (bulan normal) | **83.141 unit/bulan** | Data historis sistem, Apr 2023–Des 2025, exclude Ramadan (n = 29 bulan) |
| Tingkat error estimasi manual (asumsi) | **~25%** | Asumsi konservatif — tidak ada catatan pengadaan manual yang terdokumentasi |
| Tingkat error sistem (MAPE Layer 1, terukur) | **~5%** | Walk-forward backtest Nov 2025–Feb 2026 |
| Selisih error = potensi pengurangan overstock | **~20%** | 25% − 5% |

#### Kerangka Perhitungan

```
Rata-rata distribusi bulanan (bulan normal)  = 83.141 unit
Overstock yang berpotensi berkurang (20%)    = 83.141 × 0,20 = 16.628 unit/bulan
Nilai penghematan per bulan                  = 16.628 × Rp 6.250 = Rp 103.925.000
```

#### Data Distribusi Aktual per Bulan (Bulan Normal)

Data berikut diambil langsung dari dataset pelatihan sistem — volume distribusi aktual yang tercatat, bukan estimasi:

| Periode | Unit Terdistribusi | Setara Karton (÷24) |
|---|---|---|
| 2023-05 | 93.525 | 3.897 |
| 2023-08 | 97.012 | 4.042 (tertinggi) |
| 2024-01 | 89.266 | 3.719 |
| 2024-10 | 91.836 | 3.827 |
| 2025-07 | 82.815 | 3.451 |
| 2025-10 | 84.188 | 3.508 |
| 2025-12 | 77.823 | 3.243 |
| **Rata-rata (29 bulan normal)** | **83.141** | **3.464** |

> **Catatan tren**: Terdapat tren penurunan demand antar tahun — rata-rata 2023 sekitar 3.785 karton/bulan, 2024 sekitar 3.542 karton/bulan, dan 2025 sekitar 3.161 karton/bulan. Ini kemungkinan mencerminkan perubahan jumlah karyawan aktif atau kebijakan distribusi. Untuk proyeksi ke depan, skenario berbasis data 2025 lebih konservatif dan representatif.

#### Proyeksi Penghematan per Bulan

| Skenario | Basis Distribusi | Overstock Berkurang (20%) | Harga/Unit | Penghematan/Bulan |
|---|---|---|---|---|
| Konservatif (tren 2025) | ~75.873 unit | ~15.175 unit | Rp 6.250 | **Rp 94.844.000** |
| **Rata-rata historis** | **~83.141 unit** | **~16.628 unit** | **Rp 6.250** | **Rp 103.925.000** |
| Optimis (tren 2023) | ~90.820 unit | ~18.164 unit | Rp 6.250 | **Rp 113.525.000** |

#### Komponen Penghematan yang Diperhitungkan

Proyeksi di atas hanya menghitung **pengurangan overstock** — selisih antara volume yang dibeli berlebih secara manual vs volume yang direkomendasikan sistem. Komponen lain yang tidak dimodelkan namun relevan:

- **Pengurangan stockout**: distribusi berjalan penuh setiap shift, kewajiban perusahaan terpenuhi
- **Efisiensi waktu staf**: eliminasi proses estimasi manual mingguan oleh operator

### 6.2 Proyeksi Tahunan

Bulan aktif dalam setahun: **10 bulan** (12 bulan dikurangi ±2 bulan Ramadan dengan volume mendekati nol).

| Skenario | Penghematan/Bulan | Proyeksi/Tahun (× 10 bulan) |
|---|---|---|
| Konservatif (tren 2025) | Rp 94.844.000 | **Rp 948.440.000** |
| **Rata-rata historis** | **Rp 103.925.000** | **Rp 1.039.250.000** |
| Optimis (tren 2023) | Rp 113.525.000 | **Rp 1.135.250.000** |

> **Keterbatasan proyeksi ini**: Volume distribusi karyawan (data sistem) diasumsikan mendekati volume pengadaan perusahaan. Dalam praktik, perusahaan mungkin membeli sedikit lebih banyak dari distribusi aktual sebagai safety stock — yang justru memperbesar potensi penghematan dari pengurangan overstock.


---

## 7. Risiko dan Limitasi

### 7.1 Risiko yang Diidentifikasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Pergeseran jadwal Ramadan | Lag Skipper tidak update | Rutin memperbarui `RAMADAN_START_MONTHS` dan metadata artifact setiap tahun |
| Pola kehadiran/konsumsi karyawan berubah | Model stale | Retrain otomatis tiap kuartal dengan data terbaru |
| Hari libur baru tidak tercatat di SQL | Layer 2 over-predict | Prosedur maintenance rutin kalender SQL |
| Shutdown pabrik tak terduga | Prediksi tidak akurat | Kolom `IsShutdown` dapat di-update secara retroaktif |
| Degradasi kualitas catatan distribusi | MAPE naik | SATPAM deteksi kelengkapan data <80% |

### 7.2 Limitasi Inheren

1. **Single machine scope**: Sistem hanya divalidasi untuk 1 unit vending machine. Pola konsumsi karyawan di lokasi atau departemen lain mungkin berbeda secara signifikan.

2. **Minimum data requirement**: Model membutuhkan minimal 6 bulan data historis untuk retrain yang reliable. Untuk deployment di lokasi baru, periode *cold start* tanpa retrain diperlukan.

3. **Sunday pre-Ramadan under-prediction**: Minggu menjelang Ramadan masih under-predict sekitar 15% karena hanya ada 3 titik data historis. Akurasi akan meningkat otomatis seiring bertambahnya data (sistem *self-correcting*).

4. **Variabilitas preferensi varian**: Pilihan varian susu karyawan (apakah hari ini memilih Coklat atau Strawberry) bersifat stokastik dan tidak dapat diprediksi secara deterministik. Error 15–18% per varian adalah batas bawah yang tidak dapat ditekan lebih jauh dengan pendekatan ML konvensional, karena ini merupakan perilaku bebas individual yang tidak berkorelasi langsung dengan faktor kalender apapun.

---

## 8. Rekomendasi Pengembangan Lanjutan

Berdasarkan hasil evaluasi, tim merekomendasikan:

1. **Pemantauan parameter Ramadan rutin**: Setiap akhir tahun, parameter `RAMADAN_START_MONTHS` dan daftar `RAMADAN_MONTHS` di metadata artifact perlu diperbarui untuk mengantisipasi pergerakan maju jadwal Ramadan.

2. **Retraining pasca-Ramadan**: Setelah data 2026 penuh tersedia (khususnya pola pemulihan pasca-Ramadan), lakukan retraining Layer 1 untuk menangkap pola pasca-Ramadan yang lebih baru dan akurat.

3. **Ekspansi ke multi-machine**: Jika perusahaan menambah unit vending machine, pertimbangkan untuk membuat model per-mesin dengan infrastruktur yang sama, menggunakan tabel SQL terpisah per mesin.

4. **Monitoring WAPE berkelanjutan**: Pantau WAPE dan Event Accuracy setiap kuartal. Jika WAPE kembali naik di atas 10%, periksa apakah ada pola baru (event baru, perubahan jam operasi shift) yang belum ditangani.

5. **Eksperimen Layer 1 alternatif**: Meskipun XGBoost saat ini sangat baik, pertimbangkan eksperimen dengan LightGBM atau CatBoost saat data historis mencapai 3+ tahun penuh, karena jumlah data yang lebih besar mungkin memungkinkan model berbasis tree yang lebih dalam.
