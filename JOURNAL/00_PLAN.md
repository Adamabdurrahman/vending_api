# JOURNAL — Rencana & Progress Pembuatan Dokumentasi ML

**Judul Penelitian (Draft):**
> Sistem Peramalan Permintaan Dua Lapis untuk Vending Machine Susu Menggunakan XGBoost dan Smart Event Classifier Berbasis Aturan di PT GS Battery

**Tanggal Mulai:** Juni 2026  
**Tujuan:** Dokumentasi teknis komprehensif sistem ML yang siap diadaptasi untuk publikasi jurnal Sinta 4

---

## Daftar File & Status

| No | File | Topik Utama | Status |
|----|------|-------------|--------|
| 1 | `01_Gambaran_Umum_dan_Konteks_Bisnis.md` | Latar belakang, problem statement, tujuan penelitian | ✅ SELESAI |
| 2 | `02_Arsitektur_Sistem_ML.md` | Two-layer design, alur data, skema SQL | ✅ SELESAI |
| 3 | `03_Pipeline_Data_dan_Feature_Engineering.md` | ETL, 22 fitur, Dual-Mode Lag, Share Smoother | ✅ SELESAI |
| 4 | `04_Layer1_Model_XGBoost_V6.md` | XGBoost V6, training, Ramadan handling, inferensi | ✅ SELESAI |
| 5 | `05_Layer2_Smart_Event_Classifier.md` | Rule-based distributer, DOW Profile, Tiered Events | ✅ SELESAI |
| 6 | `06_Sistem_Otomasi_dan_Produksi.md` | Daily pipeline, scheduler, SATPAM, auto-retrain | ✅ SELESAI |
| 7 | `07_Evaluasi_dan_Hasil.md` | Evaluasi komprehensif, metrik, business value | ✅ SELESAI |

**Semua file selesai dibuat: 23 Juni 2026**

---

## Ringkasan Sistem yang Didokumentasikan

### Domain
Peramalan permintaan (*demand forecasting*) produk susu pada vending machine milik PT GS Battery.

### Input Utama
- Data transaksi harian dari vending machine (tabel `dbo.monitor_log_datatransaksi`)
- Kalender operasional pabrik (tabel `dbo.OperationalCalendar`)
- 4 varian produk: Coklat, Moca, Original (Putih), Strawberry

### Output Utama
- Prediksi bulanan per varian (Layer 1) → disimpan di `dbo.ForecastResults_Layer1`
- Prediksi harian per shift × per varian (Layer 2) → disimpan di `dbo.ForecastResults_Layer2`

### Entry Point Eksekusi Harian
```
daily_pipeline.py
   ├── etl_service.py           ← Extract-Transform-Load transaksi harian
   ├── forecast_service.py      ← Update aktual vs prediksi
   └── scheduler_service.py     ← Trigger retrain + forecast tiap kuartal
```

### Source of Truth ML (folder ProductionML/)
```
ProductionML/
   ├── Layer1_Core.py                          ← Wrapper model Layer 1
   ├── Script_Model_XGBoost_V6_Fallback.py     ← Logika training XGBoost V6
   ├── Script_Pipeline_Databuilder.py          ← Feature engineering pipeline
   ├── Script_production_daily_2_prod_v2.py    ← Layer 2 distributor (Smart Event Classifier)
   ├── Script_SqlCalendar.py                   ← SQL Calendar reader
   └── Layer1_XGBoost_V6_Artifact.joblib       ← Model artifact (self-contained)
```

---

## Metrik Kunci Sistem (Terverifikasi 11 Mei 2026)

| Metrik | Nilai | Keterangan |
|--------|-------|------------|
| L1 MAPE Backtest | **3.40%** | Train 0.69% (gap 2.71pp — acceptable) |
| L1 MAPE Forward Jan 2026 | **1.3%** | |
| L1 MAPE Forward Feb 2026 | **4.9%** | |
| L2 WAPE Harian | **3.99%** | Threshold EXCELLENT < 10% |
| L2 Event Accuracy | **89.5%** | 17/19 event days error < 20% |
| L2 DOW Error Maks | **0.63pp** | Selisih share per hari sangat kecil |
| Business Value (1.5 bln) | **Rp 87,195,500** | Cost reduction 24.3% |
| Skor Evaluasi Total | **84/100** | Keputusan: GO ✅ |

---

## Catatan untuk AI Penulis Jurnal

1. **Bahasa:** Bahasa Indonesia akademis, sesuai gaya penulisan jurnal Sinta 4
2. **Nama institusi:** PT GS Battery (dapat disebutkan)
3. **Struktur jurnal yang disarankan:** Abstrak → Pendahuluan → Tinjauan Pustaka → Metodologi → Hasil dan Pembahasan → Kesimpulan
4. **Keunikan yang perlu ditonjolkan:**
   - Arsitektur dua lapis (ML + Rule-Based) yang terbukti lebih baik dari pendekatan ML murni
   - Ramadan Lag Skipper sebagai solusi orisinal untuk menangani anomali musiman religius
   - Smart Event Classifier v2.2 yang membagi hari menjadi 7 kategori bobot dinamis
   - Sistem produksi otomatis dengan SATPAM validasi data yang mencegah kebocoran
5. **Referensi metrik benchmark:** Prophet WAPE 27% (ditolak) vs Smart Event Classifier WAPE 3.99%
