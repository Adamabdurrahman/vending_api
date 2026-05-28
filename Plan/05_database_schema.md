# 05 — Database Schema

> Dokumen ini mendaftar semua tabel SQL Server yang digunakan project.
> Prasyarat: Sudah membaca `01_arsitektur_overview.md`.

---

## Koneksi Database

| Parameter   | Nilai                          |
|-------------|--------------------------------|
| Server      | `ADAM123\SQLEXPRESS`            |
| Database    | `db_vending_machine`           |
| Username    | `sa`                           |
| Driver      | ODBC Driver 17 for SQL Server  |
| ORM         | SQLAlchemy (via PyODBC)        |

File konfigurasi: [`database.py`](file:///c:/Users/isyaa/OneDrive/Documents/Web%20and%20Code/vending_api/database.py)

---

## Tabel-Tabel Utama

### 1. `dbo.master_user`
**Fungsi:** Data pengguna aplikasi Android.

| Kolom            | Tipe           | Keterangan                  |
|------------------|----------------|-----------------------------|
| `id_recnum_mur`  | BIGINT (PK)    | ID numerik unik             |
| `Id`             | VARCHAR(100)   | ID alfanumerik              |
| `UserName`       | VARCHAR(100)   | Nama pengguna               |
| `Password`       | VARCHAR(200)   | Password (plain text!)      |
| `level_user`     | INT            | Level akses                 |
| `email_primary`  | VARCHAR(200)   | Email utama                 |
| `email_secondary`| VARCHAR(200)   | Email cadangan (nullable)   |
| `nohp`           | VARCHAR(20)    | Nomor HP                    |
| `register_time`  | DATETIME       | Waktu pendaftaran           |
| `update_time`    | DATETIME       | Waktu update terakhir       |
| `approve_by`     | VARCHAR(10)    | Siapa yang approve          |
| `status_active`  | VARCHAR(1)     | 'Y' = aktif, 'N' = nonaktif|
| `photo_url`      | VARCHAR(255)   | Path foto profil            |

---

### 2. `dbo.monitor_log_datatransaksi`
**Fungsi:** Log transaksi mentah dari vending machine. **Sumber data utama ETL.**

| Kolom              | Keterangan                              |
|--------------------|-----------------------------------------|
| `update_time`      | Timestamp transaksi                     |
| `keterangan`       | Nama shift (misal: "SHIFT1 06:00-14:00")|
| `id_recnum_mav`    | ID alat vending machine                 |
| `slot_number`      | Nomor slot                              |
| `qty`              | Jumlah                                  |
| `status_transaksi` | '1' = valid                             |

---

### 3. `dbo.Vending_Aggregrated`
**Fungsi:** Data harian yang sudah diolah ETL. Sumber aktual untuk evaluasi.

| Kolom              | Tipe    | Keterangan                             |
|--------------------|---------|----------------------------------------|
| `tanggal`          | DATE    | Tanggal                                |
| `keterangan`       | VARCHAR | Shift                                  |
| `nama_variant`     | VARCHAR | Nama varian (Coklat, Moca, dll)        |
| `demand`           | INT     | Jumlah demand                          |
| `is_holiday`       | INT     | 1 = hari libur nasional                |
| `is_ramadan`       | INT     | 1 = bulan Ramadan                      |
| `is_weekend`       | INT     | 1 = Sabtu/Minggu                       |
| `is_manual_insert` | INT     | 0 = dari ETL, 1 = input manual admin   |

---

### 4. `dbo.vending_training_ml`
**Fungsi:** Data dengan fitur ML yang sudah dihitung. Input untuk training model.

| Kolom (utama)       | Keterangan                              |
|---------------------|-----------------------------------------|
| `period`            | Bulan dalam format date                 |
| `variant`           | Nama varian                             |
| `demand`            | Total demand bulan tersebut             |
| `working_days`      | Jumlah hari kerja                       |
| `n_days`            | Jumlah hari dalam bulan                 |
| `ramadan_days`      | Jumlah hari Ramadan                     |
| `holiday_days`      | Jumlah hari libur                       |
| `share_pct`         | Market share varian (%)                 |
| `lag_1m` - `lag_12m`| Lag demand bulan sebelumnya             |
| `rolling_avg_3m`    | Rata-rata 3 bulan                       |
| `growth_rate`       | Tingkat pertumbuhan                     |
| `share_lag_1m`      | Share bulan lalu                        |
| `share_change`      | Perubahan share                         |
| `month_sin/cos`     | Sinusoidal encoding bulan               |
| `month_idx`         | Index linear bulan                      |

---

### 5. `dbo.ForecastResults_Layer1`
**Fungsi:** Hasil prediksi bulanan (output Layer 1).

| Kolom               | Tipe        | Keterangan                           |
|----------------------|-------------|--------------------------------------|
| `Id`                 | INT (PK)    | Auto-increment                       |
| `PredictedMonth`     | VARCHAR(7)  | "YYYY-MM"                            |
| `RunTimestamp`       | DATETIME    | Kapan prediksi dijalankan            |
| `ModelVersion`       | VARCHAR(20) | Versi model                          |
| `TotalDemand`        | INT         | Total prediksi                       |
| `DemandCoklat`       | INT         | Prediksi Coklat                      |
| `DemandMoca`         | INT         | Prediksi Moca                        |
| `DemandOriginal`     | INT         | Prediksi Original                    |
| `DemandStrawberry`   | INT         | Prediksi Strawberry                  |
| `IsBusinessLogic`    | BIT         | 1 = pakai fallback, bukan XGBoost    |
| `ProductiveDays`     | FLOAT       | Hari produktif                       |
| `SmootherEnabled`    | BIT         | 1 = Share Smoother aktif             |
| `MAPE_Total`         | FLOAT       | Error model keseluruhan              |
| `MAE_Total`          | FLOAT       | Mean Absolute Error                  |
| `RMSE_Total`         | FLOAT       | Root Mean Square Error               |
| `MAPE_Coklat`        | FLOAT       | MAPE per varian                      |
| `MAPE_Moca`          | FLOAT       | MAPE per varian                      |
| `MAPE_Original`      | FLOAT       | MAPE per varian                      |
| `MAPE_Strawberry`    | FLOAT       | MAPE per varian                      |
| `ActualDemand`       | INT (NULL)  | Demand aktual (diisi oleh Update Actuals) |
| `ErrorPercent`       | FLOAT (NULL)| Error vs aktual (%)                  |
| `ActualUpdatedAt`    | DATETIME    | Kapan aktual di-sync                 |
| `is_data_gap`        | BIT         | 1 = prediksi dipaksa (timeout 45 hari)|
| `is_retrained`       | BIT         | 1 = model di-retrain sebelum prediksi|

---

### 6. `dbo.ForecastResults_Layer2`
**Fungsi:** Hasil distribusi harian (output Layer 2).

| Kolom              | Tipe        | Keterangan                     |
|--------------------|-------------|--------------------------------|
| `Id`               | INT (PK)    | Auto-increment                 |
| `RunTimestamp`      | DATETIME    | Kapan prediksi dijalankan      |
| `PredictedMonth`   | VARCHAR(7)  | "YYYY-MM"                      |
| `Date`             | DATE        | Tanggal spesifik               |
| `DayName`          | VARCHAR(10) | Nama hari (Monday, dll)        |
| `Shift`            | VARCHAR(30) | Nama shift                     |
| `Variant`          | VARCHAR(30) | Nama varian                    |
| `PredictedDemand`  | INT         | Prediksi demand                |
| `IsHoliday`        | BIT         | Flag hari libur                |
| `IsRamadan`        | BIT         | Flag Ramadan                   |
| `IsWeekend`        | BIT         | Flag weekend                   |
| `ActualDemand`     | INT (NULL)  | Demand aktual                  |
| `ErrorPercent`     | FLOAT (NULL)| Error vs aktual (%)            |

**Index:** `IX_Layer2_DateShiftVariant ON (Date, Shift, Variant)`

---

### 7. `dbo.OperationalCalendar`
**Fungsi:** Kalender operasional pabrik. Sumber kebenaran (source of truth) untuk
hari kerja, shift aktif, Ramadan, dan shutdown.

| Kolom            | Tipe    | Keterangan                    |
|------------------|---------|-------------------------------|
| `Date`           | DATE    | Tanggal                       |
| `IsWorkingDay`   | BIT     | 1 = hari kerja                |
| `Shift1_Active`  | BIT     | 1 = Shift 1 berjalan          |
| `Shift2_Active`  | BIT     | 1 = Shift 2 berjalan          |
| `Shift3_Active`  | BIT     | 1 = Shift 3 berjalan          |
| `IsRamadan`      | BIT     | 1 = hari Ramadan              |
| `IsShutdown`     | BIT     | 1 = pabrik tutup total        |

---

### 8. `dbo.RetrainLog`
**Fungsi:** Log setiap kali model di-retrain.

| Kolom               | Tipe         | Keterangan              |
|----------------------|--------------|-------------------------|
| `Id`                 | INT (PK)     | Auto-increment          |
| `RunTimestamp`       | DATETIME     | Kapan retrain dijalankan|
| `ModelVersion`       | VARCHAR(50)  | Versi model             |
| `MAPE`               | FLOAT        | Backtest MAPE           |
| `MAE`                | FLOAT        | Backtest MAE            |
| `RMSE`               | FLOAT        | Backtest RMSE           |
| `TrainingRows`       | INT          | Jumlah baris training   |
| `TrainingPeriodEnd`  | VARCHAR(7)   | Bulan terakhir training |
| `BestParams`         | NVARCHAR(500)| JSON hyperparameter     |
| `Status`             | VARCHAR(20)  | "success" atau "error"  |

---

### 9. `dbo.SystemNotifications`
**Fungsi:** Notifikasi sistem untuk dashboard.

| Kolom             | Tipe          | Keterangan                 |
|-------------------|---------------|----------------------------|
| `Id`              | INT (PK)      | Auto-increment             |
| `CreatedAt`       | DATETIME      | Waktu dibuat               |
| `NotifType`       | VARCHAR(30)   | ETL / QUARTERLY / RETRAIN  |
| `Severity`        | VARCHAR(10)   | SUCCESS / INFO / WARNING / ERROR |
| `Title`           | VARCHAR(200)  | Judul notifikasi           |
| `Message`         | NVARCHAR(MAX) | Pesan detail               |
| `IsRead`          | BIT           | 0 = belum dibaca           |
| `RelatedMonth`    | VARCHAR(7)    | Bulan terkait (opsional)   |
| `RelatedQuarter`  | VARCHAR(10)   | Kuartal terkait (opsional) |

---

### Tabel Referensi Lainnya

| Tabel                       | Fungsi                                    |
|-----------------------------|-------------------------------------------|
| `dbo.manage_map_new_slot`   | Mapping ID slot baru → slot number        |
| `dbo.manage_map_slot_number`| Mapping slot → varian                     |
| `dbo.master_variant`        | Master data varian (Coklat, Moca, dll)    |
| `dbo.master_alat_vm`        | Master data mesin vending (nama, status)  |

---

> **Lanjut baca:** `06_mekanisme_khusus.md` untuk penjelasan fitur khusus (Satpam, Smoother, dll).
