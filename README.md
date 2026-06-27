# vending_api — Smart Vending Machine Management System

Backend REST API untuk sistem monitoring distribusi hak susu karyawan berbasis Machine Learning (XGBoost).
Dibangun menggunakan FastAPI + SQL Server, dengan prediksi demand menggunakan model XGBoost 2-layer.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Database | Microsoft SQL Server (via PyODBC + SQLAlchemy) |
| ML Model | XGBoost + scikit-learn |
| Data Processing | Pandas + NumPy |
| Email (OTP) | Gmail SMTP via smtplib |
| Visualization | Matplotlib |

---

## Prerequisites

Pastikan tools berikut sudah terinstall sebelum menjalankan project:

1. **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
2. **Microsoft SQL Server** (Express atau full) — [microsoft.com/sql-server](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
3. **ODBC Driver 17 for SQL Server** — [Download di sini](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
4. **Git** (untuk clone repository)

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/vending_api.git
cd vending_api
```

### 2. Buat Virtual Environment

```bash
python -m venv venv
```

Aktifkan virtual environment:

- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **Mac/Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables

Salin file `.env.example` menjadi `.env`:

```bash
copy .env.example .env
```

Buka `.env` dan isi dengan konfigurasi sesuai environment kamu:

```env
DB_SERVER=YOURPC\SQLEXPRESS
DB_NAME=db_vending_machine
DB_USERNAME=sa
DB_PASSWORD=your_password

EMAIL_SENDER=youraddress@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
```

> **Catatan Gmail App Password:** Gunakan App Password, bukan password Gmail biasa.
> Buat di: [myaccount.google.com](https://myaccount.google.com) → Security → 2-Step Verification → App passwords

### 5. Persiapkan Database

Pastikan SQL Server sudah berjalan dan database `db_vending_machine` sudah dibuat.
Semua tabel yang dibutuhkan harus tersedia (lihat daftar tabel di bawah).

### 6. Persiapkan ML Model Artifact

Model XGBoost (`.joblib`) harus ada di path berikut:

```
ProductionML/Layer1_XGBoost_V6_Artifact.joblib
```

Jika belum ada, jalankan retrain melalui endpoint setelah server berjalan:

```
POST http://localhost:8000/api/v1/model/retrain
```

---

## Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Setelah server berjalan, buka Swagger UI di browser:

```
http://localhost:8000/docs
```

---

## Database Tables

Tabel SQL Server yang dibutuhkan oleh sistem:

| Table | Deskripsi |
|---|---|
| `dbo.master_user` | Data akun pengguna |
| `dbo.master_variant` | Varian produk susu |
| `dbo.master_alat_vm` | Unit vending machine |
| `dbo.master_settime` | Jadwal shift kerja |
| `dbo.manage_map_slot_number` | Konfigurasi slot per mesin |
| `dbo.manage_restok` | Stok dan restock per slot |
| `dbo.OperationalCalendar` | Kalender operasional harian |
| `dbo.monitor_log_datatransaksi` | Log transaksi dari vending machine |
| `dbo.Vending_Aggregrated` | Data transaksi teragregasi |
| `dbo.vending_training_ml` | Dataset training ML |
| `dbo.ForecastResults_Layer1` | Hasil prediksi bulanan (Layer 1) |
| `dbo.ForecastResults_Layer2` | Hasil distribusi harian (Layer 2) |
| `dbo.RetrainLog` | Log history model retraining |
| `dbo.SystemNotifications` | Notifikasi sistem |

---

## API Documentation

Setelah server berjalan, dokumentasi API lengkap tersedia di:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Total: **18 API tag group**, **71 endpoint**.

---

## Project Structure

```
vending_api/
├── main.py                    # Entry point, semua router terdaftar di sini
├── database.py                # Konfigurasi koneksi SQL Server
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic request/response schemas
├── requirements.txt           # Python dependencies
├── .env.example               # Template konfigurasi (salin ke .env)
│
├── *_service.py               # Service layer per fitur
│   ├── user_auth_service.py
│   ├── calendar_service.py
│   ├── dashboard_service.py
│   ├── forecast_service.py
│   ├── inventory_service.py
│   ├── manual_insert_service.py
│   ├── restock_service.py
│   ├── scheduler_service.py
│   └── ...
│
├── ProductionML/              # ML model core (XGBoost Layer 1 & Layer 2)
│   ├── Layer1_Core.py
│   └── Script_production_daily_2_prod_v2.py
│
├── PYTHONEnginering/          # Feature engineering scripts
│   └── Script_Pipeline_Databuilder.py
│
└── Plan/                      # Dokumentasi desain dan rencana
```

---

## License

Capstone Design Project — President University, 2026.
