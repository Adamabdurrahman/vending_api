# FASTAPI & .NET INTEGRATION PROGRESS LOG
**Terakhir Diperbarui:** 13 Mei 2026
**Fase Saat Ini:** Backend ML (FastAPI & SQL Integration) — SELESAI

Dokumen ini mencatat pencapaian dan perbaikan (*improvements*) yang telah dilakukan berdasarkan `FastAPI_Integration_Plan.txt`. Dokumen ini bertujuan menjadi *handover* bagi AI Assistant selanjutnya agar dapat langsung melanjutkan ke fase pengembangan Frontend (.NET) tanpa mengulangi pekerjaan Backend.

---

## ✅ APA YANG SUDAH KITA SELESAIKAN (MILESTONES)

### 1. Integrasi FastAPI (API Routes)
Semua endpoint utama telah berhasil dibuat dan diregistrasikan di `main.py`:
- `POST /api/v1/forecast/generate`: Menjalankan Chain Prediction (Layer 1 & 2) dengan support rentang bulan.
- `POST /api/v1/forecast/update-actuals`: Menyinkronkan metrik error vs data aktual (termasuk fitur *INNER JOIN Bulk Update* di SQL).
- `POST /api/v1/model/retrain`: Berjalan secara *Asynchronous* via `BackgroundTasks` untuk mencegah *Timeout*.
- `POST /etl/run-pipeline`: Menjalankan pembentukan fitur ML di *background*.
- `GET /api/v1/forecast/history`: Menampilkan riwayat hasil prediksi yang telah tersimpan.

### 2. Migrasi CSV ke SQL Server (SQL-First Architecture)
- Semua fungsi prediktif sekarang mengambil data *Pure SQL* via SQLAlchemy (tidak ada lagi `pd.read_csv`).
- Layer 1 dan Layer 2 Prediction secara otomatis melakukan `INSERT` hasil prediksi puluhan ribu baris distribusi harian ke tabel `dbo.ForecastResults_Layer1` dan `dbo.ForecastResults_Layer2`.
- Bug encoding karakter (`charmap` error di Windows) pada skrip Layer 2 produksi telah dibersihkan.
- Fitur "Model Metrics": Nilai `MAPE_Total`, `MAE_Total`, `RMSE_Total`, dan `ModelVersion` ditarik secara otomatis dari *Metadata* artefak `.joblib` lalu disimpan ke dalam SQL setiap kali prediksi di-generate.

---

## 🚀 IMPROVEMENT PENTING (BUSINESS LOGIC & SAFETY)

Selama proses pengerjaan, kita menambahkan fitur-fitur **Satpam (Security Gates)** untuk menjaga integritas data operasional:

### 1. Satpam Data Completeness (Mencegah Under-Forecast)
Diimplementasikan pada endpoint `generate_forecast`. Sistem **tidak akan** menjalankan prediksi untuk bulan depan jika sinkronisasi data bulan ini belum lengkap. 
*   **Logika:** Skrip mengecek tabel `Vending_Aggregrated` (menghitung `COUNT(DISTINCT tanggal)`) dan membandingkannya dengan target hari kalender (`OperationalCalendar`). Jika rekaman terakhir berjarak lebih dari 3 hari dari akhir bulan, prediksi akan **Ditolak** (ValueError). Ini mencegah XGBoost menerima fitur Lag yang "setengah matang".

### 2. Satpam VM Offline (Mencegah Evaluasi Palsu)
Diimplementasikan pada endpoint `update-actuals`.
*   **Logika:** Saat administrator melakukan update metrik evaluasi aktual, sistem menembak *query* ke `dbo.master_alat_vm`. Jika terdapat mesin yang status sinkronisasinya (`update_time`) kosong/mati, API akan menyisipkan pesan *Warning* di JSON *Response*, memberitahu bahwa nilai akurasi (MAPE) bulan tersebut mungkin belum 100% valid karena populasi mesin belum semuanya masuk ke data sentral.

### 3. Dual-Mode Lag Computation (Conditional Ramadan Lag Skipper di ETL)
Implementasi dari instruksi spesifik di *Section 7E* dokumen *Plan*. Pada `Script_Pipeline_Databuilder.py`, kita telah menerapkan logika *skip* yang terpisah:
*   **Historis (2023 - 2025):** Natural Lag (Kotor). Tetap mempertahankan bulan puasa sebagai nilai Lag agar XGBoost bisa mempelajari fenomena *Rebound* pra/pasca-Lebaran.
*   **Masa Depan (2026+):** Skipped Lag (Bersih). Memaksa bulan seperti April 2026 untuk mengambil *Lag* dari Januari 2026 (mengabaikan Februari dan Maret yang merupakan musim puasa). Hal ini memastikan akurasi prediksi pra-produksi tidak meleset jatuh ke angka rendah.

---

## ⏭️ NEXT STEPS (UNTUK AI SELANJUTNYA)

Sistem *Backend ML* (FastAPI + SQL Server) dinyatakan stabil dan berjalan sempurna (*End-to-End Test* via `test_endpoints.py` sukses besar).

Fokus langkah selanjutnya adalah:
1. **Frontend Integration:** Hubungkan endpoint `/api/v1/forecast/generate` dan `/update-actuals` ini ke *UI Dashboard* (.NET Framework atau Web Apps).
2. **Setup Background Jobs (Production Guide):** FastAPI (Uvicorn) hanya menjalankan Endpoint API. Untuk menjalankan siklus otomatis *Pipeline* (ETL, Update Actuals, dan pengecekan Kuartal), atur **Windows Task Scheduler** di server *Production*:
   - Buat *Basic Task* harian pada pukul `02:00:00`.
   - *Action*: `Start a program` menunjuk ke Python (`venv\Scripts\python.exe`).
   - *Argument*: `daily_pipeline.py` dengan *Start In* di direktori proyek `vending_api`.
   - **Penting:** Centang *"Run task as soon as possible after a scheduled start is missed"* di tab *Settings* agar proses tetap dieksekusi walau PC server sempat mati.
3. **Observability:** Tambahkan visualisasi tabel `ForecastResults_Layer1` dan `Layer2` menjadi grafik interaktif di sisi *Frontend*.

*Sistem siap digunakan!*
