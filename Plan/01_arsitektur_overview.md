# 01 — Arsitektur Overview

> Dokumen ini menjelaskan gambaran besar project `vending_api`.
> Baca ini dulu sebelum membaca dokumen lainnya.

---

## Apa Project Ini?

Project ini adalah **backend inti** untuk sistem prediksi demand vending machine susu.
Tugasnya ada 2 hal utama:

1. **Machine Learning Pipeline** — Mengambil data penjualan dari SQL Server, memprosesnya,
   menjalankan model XGBoost untuk memprediksi demand masa depan, lalu menyimpan hasilnya
   kembali ke SQL Server.
2. **API Endpoint** — Menyediakan REST API (FastAPI) agar aplikasi Android dan website
   bisa mengakses data (login, akun, notifikasi, hasil forecast, dll).

---

## Stack Teknologi

| Komponen       | Teknologi                          |
|----------------|------------------------------------|
| Framework API  | FastAPI + Uvicorn                  |
| Database       | SQL Server (ADAM123\SQLEXPRESS)     |
| ORM            | SQLAlchemy + PyODBC                |
| ML Model       | XGBoost (scikit-learn wrapper)     |
| Data Processing| Pandas + NumPy                     |
| Serialisasi ML | Joblib (.joblib artifact)          |
| Kalender       | `holidays` (Indonesia)             |

---

## Alur Data Utama (Big Picture)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          SQL SERVER                                  │
│  ┌─────────────────────┐    ┌──────────────────────┐                │
│  │ monitor_log_         │    │ Vending_Aggregrated  │                │
│  │ datatransaksi        │    │ (data harian bersih) │                │
│  │ (data mentah)        │    └──────────┬───────────┘                │
│  └──────────┬───────────┘               │                            │
│             │                           │                            │
│             │  ETL Service              │  Feature Engineering       │
│             ▼                           ▼                            │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │ Vending_Aggregrated  │───▶│ vending_training_ml  │               │
│  │                      │    │ (fitur ML siap pakai)│               │
│  └──────────────────────┘    └──────────┬───────────┘               │
│                                         │                            │
│                                         │  Retrain / Forecast        │
│                                         ▼                            │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │ ForecastResults_     │    │ ForecastResults_     │               │
│  │ Layer1 (bulanan)     │    │ Layer2 (harian)      │               │
│  └──────────────────────┘    └──────────────────────┘               │
│                                                                      │
│  ┌──────────────┐  ┌────────────────────┐  ┌───────────────┐       │
│  │ RetrainLog   │  │ SystemNotifications │  │ master_user   │       │
│  └──────────────┘  └────────────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────────┘

                    ▲                    ▲
                    │ Baca/Tulis         │ Baca/Tulis
                    │                    │
         ┌──────────┴──────────┐  ┌──────┴───────┐
         │  Python Backend     │  │  Website /   │
         │  (project ini)      │  │  App Android │
         │  - FastAPI          │  │  (consumer)  │
         │  - ML Pipeline      │  │              │
         │  - Daily Scheduler  │  │              │
         └─────────────────────┘  └──────────────┘
```

---

## Daftar File Utama

| File                    | Peran                                                         |
|-------------------------|---------------------------------------------------------------|
| `main.py`               | Entry point FastAPI — semua endpoint didefinisikan di sini    |
| `database.py`           | Konfigurasi koneksi SQL Server (SQLAlchemy engine)            |
| `models.py`             | SQLAlchemy ORM model (hanya tabel `master_user`)              |
| `schemas.py`            | Pydantic schema untuk request/response API                    |
| `etl_service.py`        | ETL Pipeline — extract data mentah, transform, load ke SQL    |
| `forecast_service.py`   | Orchestrator prediksi Layer 1 + Layer 2                       |
| `retrain_service.py`    | Retraining model XGBoost (GridSearchCV + Backtest)            |
| `scheduler_service.py`  | Logika quarterly check (kapan harus prediksi/retrain)         |
| `daily_pipeline.py`     | Entry point pipeline harian (ETL → Update Actuals → Quarterly)|
| `notif_service.py`      | Penyimpan notifikasi ke tabel SystemNotifications             |
| `setup_forecast_tables.py` | Script setup tabel-tabel forecast di SQL Server            |

### Folder

| Folder            | Isi                                                              |
|-------------------|------------------------------------------------------------------|
| `ProductionML/`   | Source of truth ML — Layer1_Core.py, Layer2 script, artifact     |
| `PYTHONEnginering/` | Script feature engineering (Databuilder)                       |
| `Plan/`           | Dokumentasi (file yang kamu baca sekarang)                       |
| `uploads/`        | Folder upload foto profil user                                   |

---

## Konsep Kunci yang Perlu Dipahami

1. **Layer 1** = Prediksi **bulanan** total demand (per varian). Menggunakan XGBoost.
2. **Layer 2** = **Distribusi harian** dari budget Layer 1 ke per-hari × per-shift × per-varian.
3. **Chain Prediction** = Prediksi bulan ini jadi input (lag) untuk prediksi bulan depan.
4. **Quarterly Run** = Prediksi dilakukan per kuartal (3 bulan sekaligus).
5. **Artifact** = File `.joblib` yang berisi model terlatih + metadata, siap dipakai inferensi.

---

> **Lanjut baca:** `02_alur_data_pipeline.md` untuk detail alur ETL dan pipeline harian.
