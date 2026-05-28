# 04 — API Endpoints

> Dokumen ini mendaftar semua endpoint REST API yang tersedia di `main.py`.
> Prasyarat: Sudah membaca `01_arsitektur_overview.md`.

---

## Info Umum

- **Framework:** FastAPI
- **Base URL:** `http://localhost:8000` (default uvicorn)
- **Docs:** `http://localhost:8000/docs` (Swagger UI otomatis dari FastAPI)
- **Static Files:** `/uploads/` → folder `uploads/` di root project

---

## 1. Autentikasi

### `POST /login`
**Tag:** Autentikasi

Login user. Password disimpan **plain text** di database (tanpa hash).

| Field      | Tipe   | Keterangan           |
|------------|--------|----------------------|
| `username` | string | Username untuk login  |
| `password` | string | Password plain text   |

**Response:** `LoginResponse` (id, username, email, level, status, photo)

---

## 2. Pengaturan Akun

### `GET /account/{id_recnum_mur}`
Ambil detail akun berdasarkan ID numerik.

### `PUT /account/{id_recnum_mur}/update`
Update nama dan email (tombol Save Changes).

### `PUT /account/{id_recnum_mur}/change-password`
Ganti password (hanya kirim `new_password`).

### `POST /account/{id_recnum_mur}/upload-photo`
Upload foto profil. Disimpan di `/uploads/profiles/user_{id}.{ext}`.

### `DELETE /account/{id_recnum_mur}/delete`
Soft delete — set `status_active = 'N'`.

---

## 3. Forecasting

### `POST /api/v1/forecast/generate`
**Tag:** Forecasting

Generate prediksi demand untuk range bulan.

| Field         | Tipe | Keterangan                |
|---------------|------|---------------------------|
| `start_year`  | int  | Tahun awal (contoh: 2026) |
| `start_month` | int  | Bulan awal (contoh: 1)    |
| `end_year`    | int  | Tahun akhir               |
| `end_month`   | int  | Bulan akhir               |

**Proses:** Chain Prediction Layer 1 → Layer 2 → Simpan ke SQL.

**Response:** Status, results per bulan, smart_insight.

### `POST /api/v1/forecast/update-actuals`
**Tag:** Forecasting

Sinkronisasi data aktual untuk bulan tertentu.

| Field   | Tipe   | Keterangan               |
|---------|--------|---------------------------|
| `month` | string | Format "YYYY-MM" (contoh: "2026-01") |

**Proses:** Ambil aktual dari `Vending_Aggregrated` → Update `ForecastResults_Layer1` & `Layer2`.

### `GET /api/v1/forecast/history`
**Tag:** Forecasting

Ambil riwayat prediksi dari `ForecastResults_Layer1`.

| Query Param | Tipe   | Opsional | Keterangan          |
|-------------|--------|----------|---------------------|
| `month`     | string | Ya       | Filter bulan spesifik|

---

## 4. Machine Learning

### `POST /api/v1/model/retrain`
**Tag:** Machine Learning

Mulai retraining model di background. Response langsung dikembalikan,
proses retrain berjalan async.

**Response:** `{"status": "success", "message": "Retraining started in background"}`

### `GET /api/v1/model/retrain-status`
**Tag:** Machine Learning

Ambil 5 riwayat retrain terakhir dari `dbo.RetrainLog`.

**Response:** Latest retrain detail (MAPE, MAE, RMSE, params) + history list.

---

## 5. Data Pipeline

### `POST /etl/run-pipeline`
**Tag:** Data Pipeline

Jalankan ETL pipeline di background.

**Proses:** Extract dari `monitor_log_datatransaksi` → Transform → Load ke
`Vending_Aggregrated` → Feature Engineering → Load ke `vending_training_ml`.

---

## 6. Notifikasi

### `GET /api/v1/notifications`
**Tag:** Notifikasi

Ambil daftar notifikasi sistem.

| Query Param   | Tipe   | Default | Keterangan                                  |
|---------------|--------|---------|---------------------------------------------|
| `unread_only` | bool   | false   | Hanya notifikasi yang belum dibaca          |
| `limit`       | int    | 50      | Maksimal baris                              |
| `notif_type`  | string | null    | Filter tipe: ETL, QUARTERLY, RETRAIN, dll   |

**Response:** `unread_count` + array notifikasi.

### `PUT /api/v1/notifications/{notif_id}/read`
Tandai 1 notifikasi sebagai sudah dibaca.

### `PUT /api/v1/notifications/read-all`
Tandai semua notifikasi sebagai sudah dibaca.

---

## Tabel SQL yang Dipakai Langsung oleh Endpoint

| Endpoint               | Tabel SQL                    | Operasi    |
|-------------------------|------------------------------|------------|
| `/login`                | `master_user`                | READ       |
| `/account/*`            | `master_user`                | READ/WRITE |
| `/forecast/generate`    | `Vending_Aggregrated`, `ForecastResults_Layer1`, `ForecastResults_Layer2`, `OperationalCalendar` | READ/WRITE |
| `/forecast/update-actuals` | `Vending_Aggregrated`, `ForecastResults_Layer1`, `ForecastResults_Layer2`, `master_alat_vm` | READ/WRITE |
| `/forecast/history`     | `ForecastResults_Layer1`     | READ       |
| `/model/retrain`        | `vending_training_ml`, `Vending_Aggregrated`, `RetrainLog`, `OperationalCalendar` | READ/WRITE |
| `/model/retrain-status` | `RetrainLog`                 | READ       |
| `/etl/run-pipeline`     | Banyak (lihat ETL doc)       | READ/WRITE |
| `/notifications`        | `SystemNotifications`        | READ/WRITE |

---

> **Lanjut baca:** `05_database_schema.md` untuk detail tabel dan kolom SQL Server.
