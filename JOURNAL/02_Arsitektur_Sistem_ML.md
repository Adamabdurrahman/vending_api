# 02 — Arsitektur Sistem Machine Learning

## 1. Gambaran Arsitektur Keseluruhan

Sistem peramalan permintaan yang dibangun mengadopsi pola arsitektur **dua lapis kaskade** (*two-layer cascaded prediction*). Filosofi dasarnya adalah memisahkan dua permasalahan yang secara fundamental berbeda:

- **Lapis 1 (Layer 1)**: *Berapa banyak?* — Menjawab pertanyaan berapa total permintaan dalam satu bulan, per varian produk.
- **Lapis 2 (Layer 2)**: *Kapan tepatnya?* — Menjawab pertanyaan bagaimana distribusi permintaan bulanan tersebut tersebar ke hari-hari dan shift-shift dalam bulan tersebut.

Pemisahan ini dipilih karena kedua permasalahan memiliki karakteristik yang berbeda dan memerlukan pendekatan yang berbeda pula. Layer 1 adalah masalah regresi time-series multi-varian yang cocok untuk model ML, sementara Layer 2 adalah masalah distribusi berbasis pola historis dan aturan domain yang lebih cocok untuk pendekatan *rule-based*.

---

## 2. Diagram Alur Sistem

```
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│       SUMBER DATA TRANSAKSI      │   │      SUMBER DATA KALENDER        │
│  dbo.monitor_log_datatransaksi   │   │   dbo.OperationalCalendar        │
│  (log distribusi susu harian)    │   │   (kalender operasional pabrik)  │
└──────────────┬───────────────────┘   └──────────────────┬───────────────┘
               │                                          │
               ▼                                          │ (hanya dibaca
┌──────────────────────────────────┐                      │  saat prediksi,
│        ETL SERVICE               │                      │  BUKAN saat ETL)
│   etl_service.py                 │                      │
│                                  │                      │
│  1. Extract transaksi harian     │                      │
│  2. Transform: slot mapping,     │                      │
│     variant mapping, agg.        │                      │
│  3. Load → Vending_Aggregrated   │                      │
│  4. Feature Engineering →        │                      │
│     vending_training_ml          │                      │
│     (via temp CSV bridge)        │                      │
└──────────────┬───────────────────┘                      │
               │                                          │
               ▼                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LAYER 1: XGBoost V6                            │
│  Layer1_Core.py + Script_Model_XGBoost_V6_Fallback.py          │
│                                                                 │
│  Input : 22 fitur (kalender, lag, share, trend, varian)        │
│  Output: Budget bulanan per varian (integer)                    │
│                                                                 │
│  Mekanisme Khusus:                                              │
│   • Ramadan Lag Skipper (fitur lag melewati bulan Ramadan)     │
│   • Step 9 Business Logic Fallback (bulan Ramadan ekstrem)     │
│   • Chain Prediction (prediksi bln N → lag bln N+1)            │
└───────────────────┬─────────────────────────────────────────────┘
                    │  Budget bulanan per varian
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│               LAYER 2: SMART EVENT CLASSIFIER v2.2              │
│  Script_production_daily_2_prod_v2.py                           │
│                                                                 │
│  Input : Budget Layer 1 + SQL Calendar + Data historis harian  │
│  Output: Prediksi per hari × shift × varian                     │
│                                                                 │
│  Komponen:                                                      │
│   • DOW Share Profile (bobot hari dalam seminggu)              │
│   • Shift Profile (bobot antar shift)                           │
│   • Tiered Day Weighting (7 kategori hari × faktor bobot)      │
│   • Adaptive Pre-Ramadan Weekend Override                       │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT SQL                                   │
│   dbo.ForecastResults_Layer1   ← Prediksi bulanan per varian   │
│   dbo.ForecastResults_Layer2   ← Prediksi harian per shift     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Komponen Sistem

### 3.1 Daily Pipeline (`daily_pipeline.py`)

File ini merupakan **titik masuk tunggal** (*single entry point*) eksekusi harian seluruh sistem ML. Dijalankan setiap hari oleh scheduler eksternal (misalnya Windows Task Scheduler atau cron job). Terdiri dari tiga tahap berurutan:

```python
def job():
    # 1. ETL Harian
    run_etl_pipeline()        # etl_service.py

    # 2. Sinkronisasi aktual vs prediksi (SEMUA bulan yang belum ter-update)
    pending_months = query("SELECT PredictedMonth FROM ForecastResults_Layer1
                           WHERE ActualDemand IS NULL")
    for m_str in pending_months:
        update_actuals(m_str)     # forecast_service.py

    # 3. Pengecekan & eksekusi kuartalan
    check_and_run_quarterly() # scheduler_service.py
```

> **Catatan implementasi**: Tahap 2 sebelumnya hanya memproses 3 bulan terakhir secara hardcode, yang menyebabkan bulan-bulan awal kuartal tidak pernah tersinkron. Perbaikan saat ini menggunakan query dinamis ke `ForecastResults_Layer1` untuk menemukan semua bulan dengan `ActualDemand IS NULL`.

Jika ETL gagal, pipeline berhenti dan tidak melanjutkan ke tahap berikutnya. Ini mencegah pembaruan data aktual atau pembuatan prediksi baru berdasarkan data yang belum sinkron.

### 3.2 ETL Service (`etl_service.py`)

Bertanggung jawab atas:
- Membaca seluruh transaksi dari `dbo.monitor_log_datatransaksi`
- Memetakan nomor slot ke nama varian produk melalui tabel referensi (`manage_map_new_slot`, `manage_map_slot_number`, `master_variant`)
- Mengagregasi jumlah transaksi per hari per shift per varian
- Menambahkan flag kalender (`is_holiday`, `is_weekend`, `is_ramadan`) — dihitung **secara mandiri** oleh ETL menggunakan library `holidays.Indonesia()` dan daftar `RAMADAN_PERIODS`, **bukan** dibaca dari `dbo.OperationalCalendar`
- Menulis hasil ke `dbo.Vending_Aggregrated` (hanya baris sistem yang dihapus; data input manual tetap aman)
- Menjalankan feature engineering ML melalui fungsi `build_v3_exact_features()` dari `PYTHONEnginering/Script_Pipeline_Databuilder.py` menggunakan **file CSV sementara** sebagai jembatan antara SQL dan pipeline Python
- Menulis dataset pelatihan yang telah diproses ke `dbo.vending_training_ml`

> **Penting**: `dbo.OperationalCalendar` **tidak dibaca** oleh ETL. Kalender operasional tersebut hanya digunakan oleh `forecast_service.py` dan `Script_production_daily_2_prod_v2.py` saat proses prediksi dijalankan.

### 3.3 Folder `ProductionML/` (Source of Truth ML)

Folder ini adalah inti dari sistem ML dan bersifat sebagai *source of truth* untuk semua logika prediksi. File-file di dalamnya tidak boleh dimodifikasi tanpa pertimbangan matang karena merupakan implementasi algoritma yang telah dievaluasi dan divalidasi.

> **Catatan path**: `Script_Pipeline_Databuilder.py` tersimpan dalam dua lokasi — salinan aktif yang digunakan ETL berada di folder `PYTHONEnginering/`, sementara salinan referensi ada di `ProductionML/`. ETL mengimport dari `PYTHONEnginering.Script_Pipeline_Databuilder`.

| File | Fungsi |
|---|---|
| `Layer1_Core.py` | Kelas `Layer1Model` — wrapper self-contained untuk model XGBoost |
| `Script_Model_XGBoost_V6_Fallback.py` | Skrip training XGBoost V6 lengkap (untuk eksperimen/debugging) |
| `Script_Pipeline_Databuilder.py` | Pipeline feature engineering dari raw CSV/SQL ke training dataset |
| `Script_production_daily_2_prod_v2.py` | Layer 2 distributer — implementasi Smart Event Classifier v2.2 |
| `Script_SqlCalendar.py` | Modul pembacaan kalender dari SQL Server |
| `Layer1_XGBoost_V6_Artifact.joblib` | Model artifact (self-contained, siap inference) |
| `backups/` | Direktori backup artifact lama sebelum retrain |

### 3.4 Forecast Service (`forecast_service.py`)

Orchestrator tipis yang menghubungkan Layer 1 dan Layer 2. Fungsinya adalah:
- Menerima parameter bulan awal dan akhir
- Memuat artifact Layer 1
- Menjalankan *chain prediction* (Layer 1 → Layer 2) per bulan secara berurutan
- Menyimpan hasil ke SQL Server
- Mengembalikan ringkasan prediksi (*smart insight*)

### 3.5 Retrain Service (`retrain_service.py`)

Mengelola proses retraining model secara otomatis:
- Membaca data pelatihan dari SQL
- Menjalankan feature engineering tambahan
- Menjalankan GridSearchCV
- Walk-Forward Backtest untuk validasi
- Mengekspor artifact model baru
- Menyimpan log ke `dbo.RetrainLog`

### 3.6 Scheduler Service (`scheduler_service.py`)

Mengatur logika kuartalan:
- Mencari kuartal tertua yang belum diprediksi (*Smart Backfill*)
- Memeriksa kelengkapan data kuartal sebelumnya (≥80%)
- Memutuskan apakah perlu retrain sebelum prediksi
- Menangani *timeout* 45 hari jika data tidak kunjung lengkap

---

## 4. Skema Basis Data

Sistem menggunakan **SQL Server** sebagai basis data utama. Tabel-tabel yang terlibat:

### Tabel Input (Raw Data)
| Tabel | Isi |
|---|---|
| `dbo.monitor_log_datatransaksi` | Log transaksi mentah vending machine |
| `dbo.manage_map_new_slot` | Pemetaan slot ID ke nomor slot |
| `dbo.manage_map_slot_number` | Pemetaan slot ke varian produk |
| `dbo.master_variant` | Master data nama varian |
| `dbo.OperationalCalendar` | Kalender operasional per hari (working day, shift aktif, Ramadan, shutdown) |

### Tabel Intermediate (ETL Result)
| Tabel | Isi |
|---|---|
| `dbo.Vending_Aggregrated` | Demand harian per shift per varian (hasil ETL) |
| `dbo.vending_training_ml` | Dataset pelatihan ML dengan 38+ fitur per baris |

### Tabel Output (Forecast Result)
| Tabel | Isi |
|---|---|
| `dbo.ForecastResults_Layer1` | Prediksi bulanan: total + per varian + metadata MAPE |
| `dbo.ForecastResults_Layer2` | Prediksi harian: tanggal × shift × varian × jumlah prediksi |
| `dbo.RetrainLog` | Log setiap eksekusi retrain beserta metrik hasilnya |

### Kolom Penting `dbo.OperationalCalendar`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `Date` | DATE | Tanggal |
| `DayCategory` | VARCHAR | Kategori hari (Hari Kerja, Akhir Pekan, Libur Nasional) |
| `IsWorkingDay` | BIT | 1 jika hari kerja |
| `Shift1_Active` | BIT | 1 jika Shift 1 beroperasi |
| `Shift2_Active` | BIT | 1 jika Shift 2 beroperasi |
| `Shift3_Active` | BIT | 1 jika Shift 3 beroperasi |
| `IsRamadan` | BIT | 1 jika tanggal berada dalam periode Ramadan |
| `IsShutdown` | BIT | 1 jika pabrik libur total (Idul Fitri, Natal, dll.) |

---

## 5. Prinsip Desain Kunci

### 5.1 SQL sebagai Sumber Kebenaran Kalender

Kalender operasional pabrik disimpan di `dbo.OperationalCalendar` dan diakses langsung oleh sistem saat prediksi dijalankan. Ini berarti perubahan kalender (misalnya penambahan hari libur atau hari pabrik tutup) cukup dilakukan dengan UPDATE SQL tanpa perlu mengubah kode Python apapun. Prinsip ini meningkatkan fleksibilitas dan mengurangi risiko kesalahan akibat hardcode.

### 5.2 Tidak Ada Duplikasi Logika

`forecast_service.py` dan `scheduler_service.py` tidak menduplikasi logika ML. Semua kalkulasi ML di-import dari `ProductionML/` sebagai paket Python. Ini memastikan bahwa satu perubahan di source of truth langsung berlaku di semua jalur eksekusi.

### 5.3 Backward Compatibility Artifact

Kelas `Layer1Model` dirancang dengan backward compatibility: saat dimuat (*load*) dari file `.joblib`, sistem memeriksa metadata dan menggunakan nilai default jika ada field yang hilang (misalnya artifact lama yang belum memiliki field `ramadan_months`). Ini memungkinkan artifact lama tetap berfungsi tanpa retraining ulang.

### 5.4 Chain Prediction

Saat memprediksi satu kuartal (3 bulan), sistem tidak bisa langsung memprediksi bulan Februari jika belum memprediksi Januari, karena Januari akan menjadi `lag_1m` untuk Februari. Mekanisme *chain prediction* menyelesaikan ini: prediksi bulan N disimpan di `fwd_cache` dan digunakan sebagai referensi lag untuk prediksi bulan N+1.

```
Prediksi Jan 2026
    ↓ hasil Jan masuk ke fwd_cache["2026-01"]
Prediksi Feb 2026 (lag_1m = fwd_cache["2026-01"])
    ↓ hasil Feb masuk ke fwd_cache["2026-02"]
Prediksi Mar 2026 (lag_1m = fwd_cache["2026-02"])
```

### 5.5 Time Machine Simulation

Untuk memastikan konsistensi prediksi terlepas dari kapan sistem dijalankan, data historis dipotong paksa hingga tepat sebelum bulan pertama yang diprediksi. Ini berarti prediksi Q1 2026 yang dijalankan di bulan Mei 2026 akan menghasilkan angka yang **identik** dengan prediksi yang dijalankan pada 1 Januari 2026, karena data setelah 1 Januari tidak digunakan.
