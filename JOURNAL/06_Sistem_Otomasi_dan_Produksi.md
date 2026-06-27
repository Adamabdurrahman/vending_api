# 06 — Sistem Otomasi dan Produksi

## 1. Filosofi Desain Sistem Produksi

Sistem ini dirancang untuk berjalan **tanpa intervensi manusia** dalam kondisi normal. Seluruh siklus hidup prediksi — mulai dari pengambilan data mentah, preprocessing, prediksi, validasi, hingga penyimpanan hasil — berjalan secara otomatis melalui satu skrip daily yang dijalankan setiap hari.

Namun, otomasi penuh membawa risiko: jika data belum lengkap dan prediksi tetap dijalankan, model akan menghasilkan angka yang tidak akurat. Untuk mencegah ini, sistem dilengkapi mekanisme **SATPAM** (*Sistem Antifail Tingkat Paling Aman*) — sebuah lapisan validasi data yang aktif sebelum setiap operasi kritis.

---

## 2. Daily Pipeline: Titik Masuk Harian

File `daily_pipeline.py` adalah orchestrator utama yang dijalankan setiap hari. Tiga tahap berjalan berurutan:

```
[Tahap 1] ETL Pipeline
    ↓ Jika gagal → STOP (cegah prediksi dari data basi)
[Tahap 2] Sinkronisasi Aktual vs Prediksi
    ↓ Untuk semua bulan yang belum tersinkron
[Tahap 3] Quarterly Check
    ↓ Trigger retrain + forecast jika saatnya
```

### 2.1 Tahap 1: ETL

Setiap hari, seluruh data transaksi ditarik ulang dari source (`dbo.monitor_log_datatransaksi`) dan ditulis ke tabel staging (`dbo.Vending_Aggregrated`). Pendekatan "refresh penuh" (bukan incremental) ini dipilih untuk memastikan:
- Koreksi transaksi yang dilakukan retroaktif oleh admin tetap terrefleksi
- Tidak ada risiko duplikasi atau data hilang akibat boundary condition incremental

Setelah ETL selesai, feature engineering ML dijalankan otomatis, menghasilkan dataset training terbaru di `dbo.vending_training_ml`.

### 2.2 Tahap 2: Sinkronisasi Aktual

Setelah prediksi dibuat, sistem terus memperbarui kolom `ActualDemand` di `ForecastResults_Layer1` seiring dengan masuknya data aktual. Logika sinkronisasi:

```python
# Ambil semua bulan yang punya prediksi tapi aktual belum tersinkron
pending_months = conn.execute("""
    SELECT DISTINCT PredictedMonth FROM dbo.ForecastResults_Layer1
    WHERE ActualDemand IS NULL ORDER BY PredictedMonth
""").fetchall()

# Update aktual untuk tiap bulan pending
for m_str in pending_months:
    res_act = update_actuals(m_str)
    # update_actuals() membandingkan SUM(demand) dari Vending_Aggregrated
    # vs TotalDemand di ForecastResults_Layer1 untuk menghitung error%
```

Desain ini menggantikan pendekatan lama yang hanya memperbarui 3 bulan terakhir, yang menyebabkan bulan-bulan awal kuartal tidak pernah mendapatkan data aktual.

---

## 3. Scheduler: Logika Kuartalan

Fungsi `check_and_run_quarterly()` di `scheduler_service.py` adalah otak dari otomasi kuartalan. Alur kerjanya:

```
[1] Smart Backfill: Cari kuartal tertua yang belum diprediksi (mulai Q1 2026)
         ↓
[2] Cek kelengkapan data kuartal sebelumnya
    (target: ≥ 80% hari produktif harus tercatat di Vending_Aggregrated)
         ↓
[3a] Jika ≥ 80% → NORMAL RUN
    - Jalankan retrain (jika histori ≥ 6 bulan)
    - Jalankan chain prediction untuk kuartal ini
         ↓
[3b] Jika < 80% dan belum 45 hari → TUNGGU
    - Kirim notifikasi
    - Besok coba lagi
         ↓
[3c] Jika < 80% dan sudah ≥ 45 hari → FORCE RUN (timeout)
    - Jalankan tanpa retrain
    - Tandai is_data_gap=True di hasil prediksi
```

### 3.1 Smart Backfill

Fitur Smart Backfill memastikan tidak ada kuartal yang "terlewat" jika sistem sempat offline atau gagal. Daripada hanya memproses kuartal saat ini, sistem mencari dari Q1 2026 ke depan dan menemukan kuartal pertama yang belum memiliki data prediksi di `ForecastResults_Layer1`.

```python
target_y = 2026
target_q = 1

while True:
    first_month_str = f"{target_y}-{get_quarter_months(target_q, target_y)[0][1]:02d}"
    exists = conn.execute(
        "SELECT COUNT(*) FROM ForecastResults_Layer1 WHERE PredictedMonth = :m",
        {"m": first_month_str}
    ).scalar()

    if exists == 0:
        break  # Kuartal ini belum diprediksi → proses ini
    # Lanjut ke kuartal berikutnya
    ...
```

### 3.2 Mekanisme Timeout 45 Hari

Jika data kuartal sebelumnya tidak kunjung mencapai 80% setelah 45 hari kuartal baru dimulai, sistem mengaktifkan **Force Run**. Ini mencegah sistem "terjebak" selamanya menunggu data yang mungkin memang tidak akan datang (misalnya periode shutdown panjang).

Prediksi yang dihasilkan dalam mode Force Run ditandai dengan `is_data_gap = 1` di tabel `ForecastResults_Layer1`, sehingga pengguna dapat mengetahui bahwa prediksi tersebut dibuat dalam kondisi data tidak lengkap.

### 3.3 Gate Retrain: Minimal 6 Bulan Histori

Retrain hanya dilakukan jika data historis cukup (minimal 6 bulan sebelum kuartal yang diprediksi). Ini mencegah model dilatih pada data yang terlalu sedikit:

```python
hist_count = conn.execute(
    "SELECT COUNT(DISTINCT CAST(period AS VARCHAR(7))) FROM dbo.vending_training_ml "
    "WHERE CAST(period AS VARCHAR(7)) < :m",
    {"m": first_month_str}
).scalar()

if hist_count < 6:
    is_retrained = False  # Terlalu sedikit data — skip retrain
```

---

## 4. SATPAM: Mekanisme Validasi Data Berlapis

SATPAM adalah nama internal untuk **tiga** mekanisme validasi data kritis yang mencegah tiga jenis kegagalan yang berbeda.

### 4.1 SATPAM DATA COMPLETENESS (sebelum prediksi)

Sebelum menjalankan prediksi, sistem memeriksa apakah data bulan sebelumnya sudah masuk dengan cukup lengkap:

```python
# Hitung berapa hari produktif yang sudah tercatat
total_hari_ada = conn.execute("""
    SELECT COUNT(DISTINCT CAST(tanggal AS DATE))
    FROM dbo.Vending_Aggregrated
    WHERE YEAR(tanggal) = :y AND MONTH(tanggal) = :m
""", {"y": prev_year, "m": prev_month}).scalar()

# Hitung berapa hari produktif yang seharusnya ada (dari kalender SQL)
target_hari = conn.execute("""
    SELECT COUNT(Date) FROM dbo.OperationalCalendar
    WHERE YEAR(Date) = :y AND MONTH(Date) = :m
    AND IsRamadan = 0 AND IsWorkingDay = 1
""", {"y": prev_year, "m": prev_month}).scalar()

# Tolak prediksi jika kurang dari 80%
if target_hari > 10 and total_hari_ada < (target_hari * 0.8):
    raise ValueError("Data TIDAK LENGKAP! Prediksi ditolak.")
```

Pengecualian khusus berlaku untuk bulan Ramadan ekstrem (`target_hari ≤ 10`): gate ini dinonaktifkan karena Ramadan Lag Skipper sudah mengabaikan data bulan tersebut saat prediksi.

### 4.2 SATPAM RETRAIN (sebelum training)

Sebelum melatih ulang model, sistem membuang baris data yang berasal dari bulan yang belum selesai (parsial):

```python
def run_retrain(exclude_month_and_beyond: str = None):
    if exclude_month_and_beyond:
        df = df[df["period_str"] < exclude_month_and_beyond]
        # Contoh: exclude "2026-04" saat melatih untuk prediksi Q2 2026
        # → data April ke atas dibuang, mencegah model "melihat" masa depan
```

Tanpa mekanisme ini, jika training dijalankan di pertengahan April, data April yang sudah masuk (tapi belum lengkap) akan ikut dilatih, menyebabkan model belajar dari data yang terpotong — sebuah bentuk target leakage.

### 4.3 SATPAM VM MATI (saat sinkronisasi aktual)

Saat proses `update_actuals()` dijalankan, sistem juga memeriksa apakah semua unit vending machine yang terdaftar di `dbo.master_alat_vm` masih aktif sinkronisasi:

```python
df_vm = pd.read_sql("SELECT nama_vm, update_time FROM dbo.master_alat_vm", conn)
for _, row in df_vm.iterrows():
    if pd.isna(row["update_time"]):
        dead_vms.append(row["nama_vm"])

if dead_vms:
    warning_msg = f"SATPAM WARNING: {len(dead_vms)} mesin belum sinkron/mati. "\
                  f"Akurasi mungkin tidak valid 100%."
```

Jika terdeteksi ada mesin yang tidak sinkron, peringatan (`vm_status_warning`) ditambahkan ke dalam respons API tanpa membatalkan proses sinkronisasi. Ini memberikan visibilitas kepada pengguna bahwa data aktual yang tersinkron mungkin tidak mencerminkan seluruh aktivitas distribusi.

---

## 5. Layanan Notifikasi

Sistem mengirimkan notifikasi untuk tiga jenis kejadian: `success`, `warning`, dan `error`. Setiap operasi kritis (retrain berhasil, prediksi berhasil, timeout force run, kegagalan ETL) menghasilkan notifikasi yang dicatat oleh `notif_service.py`.

| Event | Level | Contoh |
|---|---|---|
| Retrain berhasil | SUCCESS | "Retrain Q2 Berhasil, MAPE: 3.4%" |
| Prediksi kuartal berhasil | SUCCESS | "Prediksi Q1 2026 Normal: 3 bulan selesai" |
| Data kuartal belum 80% | WARNING | "Data 65.3%. Menunggu hingga 80% atau timeout." |
| Force Run karena timeout | WARNING | "Prediksi Q2 2026 DENGAN GAP (force run)" |
| ETL gagal | ERROR | Exception traceback lengkap |

---

## 6. Smart Insight

Setiap kali `generate_forecast()` selesai, sistem menghasilkan ringkasan otomatis (*smart insight*) yang merangkum hasil prediksi secara naratif melalui fungsi `generate_smart_insight()`. Fungsi ini mendeteksi **5 kondisi kontekstual secara dinamis** tanpa hardcode bulan atau tahun tertentu:

| Trigger | Kondisi | Contoh output |
|---|---|---|
| **Business Logic** | `is_business_logic = True` (Ramadan penuh) | `"via Business Logic (2 hari produktif, Ramadan penuh)"` |
| **Ramadan Parsial** | Ada hari Ramadan tapi bukan ekstrem | `"Ramadan parsial (11 hari, 35% bulan)"` |
| **Recovery Pasca-Ramadan** | Demand bulan ini > 2.5x bulan sebelumnya | `"recovery pasca-Ramadan (+240% vs bulan lalu)"` |
| **Demand Drop >20%** | Turun signifikan vs bulan sebelumnya yang normal | `"turun 23% vs bulan lalu"` |
| **Seasonality Historis** | Pola berulang >2 tahun dari data SQL | `"pola historis 2 tahun berturut-turut, bukan anomali"` |

Setiap insight dikompilasi menjadi satu kalimat ringkasan (*summary*) yang digunakan sebagai isi pesan notifikasi:

```
"Jan 2026=18,200 (normal) | Feb 2026=5,544 (Ramadan parsial, 11 hari, 35% bulan) |
Mar 2026=18,900 (recovery pasca-Ramadan +240%) | Total=42,644"
```

Karena analisis dilakukan secara dinamis dari SQL, Smart Insight akan selalu relevan tanpa perubahan kode apapun saat ada retrain atau perubahan tahun.

---

## 7. Integrasi dengan FastAPI

Seluruh fungsionalitas sistem ML dapat diakses melalui REST API yang dibangun menggunakan **FastAPI**. Endpoint utama ML:

| Method | Endpoint | Fungsi |
|---|---|---|
| `POST` | `/api/v1/forecast/generate` | Generate prediksi untuk range bulan tertentu |
| `POST` | `/api/v1/model/retrain` | Trigger retraining model (async BackgroundTasks) |
| `GET` | `/api/v1/forecast/results` | Ambil hasil prediksi Layer 1 dari database |
| `GET` | `/api/v1/forecast/daily` | Ambil hasil prediksi Layer 2 (harian per shift) |
| `GET` | `/api/v1/model/retrain-logs` | Lihat log riwayat retraining |

Endpoint retrain menggunakan `BackgroundTasks` FastAPI agar proses training yang memakan waktu (beberapa menit untuk GridSearchCV) tidak memblokir HTTP response. Client menerima respons segera dengan status "running", dan dapat mengecek hasilnya melalui endpoint retrain-logs.

---

## 8. Alur Otomasi Tahunan yang Diharapkan

Berikut adalah siklus otomasi yang dirancang untuk berjalan mandiri sepanjang tahun:

```
Q4 tahun sebelumnya selesai
    ↓ Daily pipeline berjalan
    ↓ Data Q4 mencapai 80% kelengkapan
    ↓ Scheduler mendeteksi Q1 tahun baru belum diprediksi
    ↓ SATPAM COMPLETENESS lolos
    ↓ Run retrain (data Q4 baru sudah masuk)
    ↓ Chain predict Q1 (Jan, Feb, Mar)
    ↓ Hasil tersimpan di ForecastResults
    ↓ Daily pipeline update aktual setiap hari
    ↓ Di Q2: proses berulang dengan data Q1 sebagai referensi
    ...
```

Untuk bulan-bulan Ramadan, alur sedikit berbeda:
- Bulan Ramadan dideteksi otomatis dari `OperationalCalendar`
- SATPAM menonaktifkan gate jika bulan tersebut memiliki ≤ 10 hari produktif
- Step 9 Business Logic aktif secara otomatis
- Layer 2 menerima sinyal Step 9 dan mengkonsentrasikan budget ke hari produktif
