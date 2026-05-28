# 02 — Alur Data Pipeline

> Dokumen ini menjelaskan bagaimana data mengalir dari mentah sampai jadi prediksi.
> Prasyarat: Sudah membaca `01_arsitektur_overview.md`.

---

## Pipeline Harian (`daily_pipeline.py`)

File `daily_pipeline.py` adalah **orkestrator utama** yang dijalankan 1x sehari.
Ia menjalankan 3 langkah berurutan:

```
┌──────────────────────────────────────────────────────────┐
│                  DAILY PIPELINE (job())                    │
│                                                           │
│  Step 1: ETL (run_etl_pipeline)                          │
│    └─ Jika gagal → BERHENTI (besok coba lagi)            │
│                                                           │
│  Step 2: Update Actuals (update_actuals)                 │
│    └─ Sinkronisasi data aktual untuk bulan-bulan          │
│       yang sudah diprediksi tapi belum punya aktual       │
│                                                           │
│  Step 3: Quarterly Check (check_and_run_quarterly)       │
│    └─ Cek apakah sudah waktunya prediksi kuartal baru    │
│    └─ Jika ya → Retrain model → Generate forecast        │
└──────────────────────────────────────────────────────────┘
```

---

## Step 1: ETL Service (`etl_service.py`)

### Tujuan
Mengubah data mentah transaksi → data harian yang bersih dan siap ML.

### Alur Detail

```
EXTRACT                    TRANSFORM                         LOAD
───────                    ─────────                         ────
monitor_log_               1. Mapping slot number            → Vending_Aggregrated
datatransaksi              2. Gabung dengan master_variant      (tabel harian)
                           3. Agregasi per hari/shift/varian
manage_map_new_slot        4. Tambah template hari kosong    → vending_training_ml
manage_map_slot_number     5. Hitung flag kalender:             (tabel fitur ML)
master_variant                - is_holiday (dari library)
                              - is_weekend (Sabtu/Minggu)
                              - is_ramadan (dari config)
                           6. Feature Engineering (Databuilder)
```

### Tabel SQL yang Terlibat

| Tabel                        | Peran                    | Operasi |
|------------------------------|--------------------------|---------|
| `monitor_log_datatransaksi`  | Data mentah transaksi    | READ    |
| `manage_map_new_slot`        | Mapping slot baru        | READ    |
| `manage_map_slot_number`     | Mapping slot → varian    | READ    |
| `master_variant`             | Master data varian       | READ    |
| `Vending_Aggregrated`        | Output ETL (harian)      | DELETE + INSERT |
| `vending_training_ml`        | Output fitur ML          | TRUNCATE + INSERT |

### Catatan Penting
- **Tidak TRUNCATE Vending_Aggregrated** — hanya hapus baris `is_manual_insert = 0`
  agar data yang diinput manual admin tetap aman.
- Feature engineering menggunakan `PYTHONEnginering/Script_Pipeline_Databuilder.py`
  melalui fungsi `build_v3_exact_features()`.

---

## Step 2: Update Actuals (`forecast_service.py → update_actuals`)

### Tujuan
Mencocokkan data prediksi yang sudah ada dengan data aktual yang baru masuk.

### Alur Detail

```
1. Query bulan-bulan yang ActualDemand masih NULL di ForecastResults_Layer1
2. Untuk setiap bulan:
   a. Hitung total aktual dari Vending_Aggregrated
   b. Update ForecastResults_Layer1:
      - SET ActualDemand = total aktual
      - SET ErrorPercent = (prediksi - aktual) / aktual × 100
   c. Update ForecastResults_Layer2:
      - JOIN dengan Vending_Aggregrated berdasarkan tanggal + shift + varian
      - SET ActualDemand dan ErrorPercent per baris
```

### Fitur Tambahan: SATPAM VM Mati
- Mengecek tabel `master_alat_vm` untuk mesin yang `update_time` NULL
- Jika ada mesin mati → tambahkan warning di response

---

## Step 3: Quarterly Check (`scheduler_service.py`)

### Tujuan
Menentukan kapan prediksi kuartal baru harus dijalankan.

### Logika Pengambilan Keputusan

```
1. SMART BACKFILL: Cari kuartal tertua yang belum diprediksi (mulai Q1 2026)
2. Cek kelengkapan data aktual kuartal sebelumnya:
   ├── ≥ 80% data masuk → NORMAL RUN (retrain dulu, lalu forecast)
   ├── < 80% tapi sudah 45 hari → FORCE RUN (skip retrain, is_data_gap=True)
   └── < 80% dan belum 45 hari → MENUNGGU (besok coba lagi)
```

### Diagram Keputusan

```
                   ┌─────────────────────┐
                   │ Ada kuartal yang     │
                   │ belum diprediksi?    │
                   └──────────┬──────────┘
                              │
                    Ya        │        Tidak
              ┌───────────────┤         └──→ ALREADY_DONE
              │               │
              ▼               │
    ┌─────────────────┐       │
    │ Data Q sebelumnya│      │
    │ ≥ 80% lengkap?  │      │
    └────────┬────────┘       │
             │                │
     Ya      │     Tidak      │
     │       │        │       │
     ▼       │        ▼       │
  ┌──────┐   │  ┌──────────┐  │
  │RETRAIN│   │  │Sudah 45  │  │
  │  ↓   │   │  │hari?     │  │
  │PREDICT│   │  └────┬─────┘  │
  └──────┘   │       │        │
             │  Ya   │  Tidak │
             │   │   │    │   │
             │   ▼   │    ▼   │
             │ FORCE  │ WAITING│
             │ RUN    │       │
             └───────┘        │
```

---

## Periode Ramadan yang Terdaftar

Ini penting karena banyak logika (Lag Skipper, Share Smoother, Backtest Filter)
bergantung pada daftar ini:

| Tahun | Mulai        | Selesai      |
|-------|--------------|--------------|
| 2023  | 22 Mar 2023  | 21 Apr 2023  |
| 2024  | 11 Mar 2024  | 09 Apr 2024  |
| 2025  | 28 Feb 2025  | 30 Mar 2025  |
| 2026  | 17 Feb 2026  | 18 Mar 2026  |

---

> **Lanjut baca:** `03_machine_learning_detail.md` untuk detail model XGBoost dan Layer 1/2.
