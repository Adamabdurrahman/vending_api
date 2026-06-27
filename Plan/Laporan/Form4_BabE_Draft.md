# PART E: MANUAL GUIDE

This section provides the complete deployment, installation, and user manuals for the Capstone Design Project. It covers developer compilation instructions, end-user network setup, mobile application installation, and role-based step-by-step guides for Superadmins and Normal Users.

---

## 1. SYSTEM BUILD DOCUMENTATION FROM THE SOURCE (Developer Perspective)

This chapter outlines the setup process required for developers to run, compile, and manage the system components using raw source files. The backend service editor utilized is Visual Studio Code, and the mobile application build environment is Android Studio.

### 1.1. Development Tools & Prerequisites
Ensure the following software packages are installed on the development machine:
1. **Python 3.12**: Runtime engine for the backend FastAPI and Machine Learning scripts.
2. **Visual Studio Code**: Recommended source code editor for backend modifications. Add the official "Python" extension by Microsoft.
3. **Microsoft SQL Server (Express Edition)**: Local database engine.
4. **SQL Server Management Studio (SSMS)**: Database GUI client tool.
5. **Android Studio (Koala / Jellyfish)**: Mobile development environment.
6. **Java Development Kit (JDK 17)**: Target runtime for Android compilation.

### 1.2. Database Restoration
The database must be restored from the provided backup archive (`.bak`) in SQL Server:
1. Open **SQL Server Management Studio (SSMS)** and connect to your SQL Server instance (e.g., `ADAM123\SQLEXPRESS`).
2. Right-click the **Databases** node in Object Explorer and select **Restore Database...**.
3. Choose **Device** as the source, click the ellipsis (`...`) button, click **Add**, and locate your database backup file (e.g., `db_vending_machine.bak`).
4. Enter the Destination Database name: `db_vending_machine`.
5. Click **OK** to restore.
6. Verify the database tables (such as `dbo.master_user`, `dbo.monitor_log_datatransaksi`, and `dbo.OperationalCalendar`) have successfully populated.
7. Open `database.py` in Visual Studio Code and modify the server connection details to match your system instance:
   ```python
   # database.py
   server = r'ADAM123\SQLEXPRESS'  # Replace with your local SQL Server instance name
   database = 'db_vending_machine'
   ```

### 1.3. Backend Setup & Running FastAPI
1. Open the project root directory `vending_api` in **Visual Studio Code**.
2. Open a new terminal inside VS Code and create a Python virtual environment:
   ```powershell
   python -m venv venv
   ```
3. Activate the virtual environment:
   * **PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Command Prompt (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
4. Install backend dependencies and Machine Learning libraries from the package manifest:
   ```powershell
   pip install -r requirements.txt
   pip install xgboost scikit-learn pandas numpy joblib
   ```
5. Launch the FastAPI server locally:
   ```powershell
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   > [!IMPORTANT]
   > Parameter `--host 0.0.0.0` is critical in production/local networks. It configures Uvicorn to bind to all active network interfaces rather than only localhost (`127.0.0.1`), enabling local network devices (like mobile phones) to reach the API server.

### 1.4. Running the Machine Learning Engine
To execute machine learning processes manually, developers can utilize the interactive Swagger UI:
1. Open your browser and navigate to `http://localhost:8000/docs`.
2. **Model Retraining:**
   * Expand the `POST /api/v1/model/retrain` endpoint block.
   * Click **Try it out** and then **Execute**.
   * The backend will fetch features, perform `GridSearchCV` hyperparameter tuning, update accuracy scores in `dbo.RetrainLog`, and overwrite the active XGBoost pipeline model file (`ProductionML/Layer1_XGBoost_V6_Artifact.joblib`).
3. **Forecast Generation:**
   * Expand the `POST /api/v1/forecast/generate` endpoint.
   * Click **Try it out** and input the target month bounds in JSON format:
     ```json
     {
       "start_month": "2026-07",
       "end_month": "2026-09",
       "force_run": false
     }
     ```
   * Click **Execute**. The backend runs the forecast and populates `ForecastResults_Layer1` and `ForecastResults_Layer2` tables.

### 1.5. Automated Background Jobs Setup on Windows
To run the automated ETL pipeline, actuals evaluations, and quarterly predictions daily, configure the script to run as a background task:
1. Create a batch script file named `run_daily_pipeline.bat` inside your project root directory (`C:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api`):
   ```bat
   @echo off
   cd /d "C:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api"
   call .\venv\Scripts\activate.bat
   python daily_pipeline.py >> daily_pipeline_log.txt 2>&1
   exit
   ```
2. Open the **Windows Task Scheduler** (type `Task Scheduler` in the Windows Start search).
3. Click **Create Basic Task...** in the right Actions sidebar.
4. Input a Name (e.g., `Vending Daily Pipeline Job`) and click **Next**.
5. Choose **Daily** under task trigger, click **Next**, and set the execution time (e.g., `01:00 AM`), click **Next**.
6. Select **Start a program** as the action, click **Next**.
7. In the **Program/script** field, browse and select your `run_daily_pipeline.bat` file.
8. In the **Start in (optional)** field, input your project directory path: `C:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api`.
9. Click **Next**, tick the checkbox *"Open the Properties dialog for this task when I click Finish"*, and click **Finish**.
10. In the Properties window, select **"Run whether user is logged on or not"** and tick **"Run with highest privileges"**. Click **OK** to save.

### 1.6. Android Application Setup & Running
1. Open **Android Studio**.
2. Click **Open** and select the folder `CapstoneProject` located on your machine (e.g. `C:\Users\isyaa\AndroidStudioProjects\CapstoneProject`).
3. Allow Gradle to synchronize dependencies and build project indices.
4. In the Project pane, open the Java class defining API endpoint URLs (e.g., `ApiClient.java` or `RetrofitInstance.java`).
5. Replace the local emulator endpoint address (`http://10.0.2.2:8000/`) with the active local IP address of your Office Server:
   ```java
   public static final String BASE_URL = "http://192.168.1.10:8000/"; // Replace with your Office Server IP
   ```
6. To build the application package, click **Build** -> **Build Bundle(s) / APK(s)** -> **Build APK(s)** in the top toolbar.
7. Locate the generated application file `app-debug.apk` in the folder path displayed in the bottom right pop-up notification.

---

## 2. END-USER SYSTEM INSTALLATION (User Perspective)

This chapter describes how the system is deployed and accessed from the perspective of the office workers and General Affairs staff.

### 2.1. System Hardware Requirements
* **Office Server PC**: A computer on the office network hosting the SQL Server database and running the FastAPI backend.
* **End-User Device**: Standard Android Smartphone with:
  * Minimum 2 GB of RAM.
  * OS Version: Android 9.0 (Pie) or above.
  * Active Wi-Fi network capability.

### 2.2. Network Configuration
* Both the Office Server PC and the Android Smartphone must be connected to the **same office Wi-Fi network**.
* Identify the IP address of the Office Server PC (e.g., open command prompt on the server, type `ipconfig`, and locate the IPv4 Address line, such as `192.168.1.10`).

### 2.3. Mobile App Installation
1. Transfer the compiled `app-debug.apk` file to the storage of the Android Smartphone (via USB cable, local sharing, or Google Drive download).
2. Open the **Files / File Manager** application on the Android device and select the `.apk` file.
3. If prompted by a security dialog regarding installing apps from unknown developers:
   * Click **Settings** on the prompt.
   * Enable the toggle for **"Allow from this source"** (or *Izinkan instalasi dari sumber tidak dikenal*).
   * Click the back button.
4. Click **Install** (or *Pasang*).
5. Open the application.

---

## 3. USER GUIDE PER USER ROLE

The table below presents step-by-step instructions on how users interact with the system based on their assigned roles (**Superadmin** vs. **Normal User / GA Staff**).

| Role | Feature Module | Langkah Penggunaan (Langkah-demi-Langkah) | Output/Hasil yang Dilihat |
|:---|:---|:---|:---|
| **Superadmin** | User Management | 1. Buka sidebar menu lalu ketuk **Master Data User**.<br>2. Cari nama user baru berstatus `PENDING` (warna merah).<br>3. Klik tombol **Setujui**.<br>4. Berikan kode OTP aktivasi debug yang tampil di dialog kepada pengguna baru. | Akun pengguna baru beralih status ke `VERIFICATION` (warna oranye) dan siap diaktivasi. |
| **Superadmin** | Edit User Profile | 1. Masuk ke **Master Data User**.<br>2. Klik tombol **Edit** pada salah satu baris pengguna.<br>3. Ubah level pengguna (misal dari Level 1 ke Level 9) atau ubah kata sandi.<br>4. Klik tombol **Simpan**. | Peran pengguna diperbarui langsung di database, dan sandi baru aktif. |
| **Superadmin** | Deactive User | 1. Masuk ke **Master Data User**.<br>2. Klik tombol **Hapus** pada kartu user.<br>3. Konfirmasi penghapusan pada dialog pop-up. | Akun pengguna dinonaktifkan (`status_active = '0'`) dan dihapus dari daftar aktif. |
| **Superadmin** | Operational Calendar | 1. Buka sidebar menu lalu pilih **Operational Calendar**.<br>2. Klik tombol **Add Year** di bagian bawah, masukkan tahun target (misal `2027`), klik Confirm.<br>3. Untuk menghapus, pilih tahun lalu klik **Delete Year**. | Database otomatis membuat 365 baris kalender beserta data hari libur nasional Indonesia. |
| **Superadmin** | Day Customization | 1. Pada kalender bulanan, klik tanggal yang ingin diubah.<br>2. Di Bottom Sheet yang muncul, atur toggle **Working Day** atau **Shutdown**.<br>3. Aktifkan/nonaktifkan shift kerja (Shift 1, 2, 3).<br>4. Tulis catatan libur (misal: "Cuti Bersama"), klik **Simpan**. | Sel kalender berubah warna (merah untuk libur/shutdown), dan data kalender operasional ter-update. |
| **Superadmin** | Model Retraining | 1. Buka sidebar menu lalu ketuk **Prediction Dashboard**.<br>2. Klik ikon/tombol **Retrain Logs**.<br>3. Klik tombol **Retrain Model** untuk memicu training model XGBoost.<br>4. Tunggu progress overlay selesai. | Log retraining baru muncul di paling atas daftar beserta status `Success` dan metrik akurasi (MAPE). |
| **User & Superadmin** | Registration & Login | 1. Buka aplikasi, klik link **Daftar Akun Baru**.<br>2. Isi nama, email, no HP, dan sandi, lalu klik **Daftar**.<br>3. Setelah disetujui Admin, login di halaman utama, masukkan kode OTP verifikasi 6 digit.<br>4. Setelah aktif, masukkan email dan password di halaman login, klik **Login**. | Pengguna masuk ke halaman dashboard utama sistem vending monitoring. |
| **User & Superadmin** | Sales & Stock Dashboard | 1. Masuk ke halaman **Dashboard Summary**.<br>2. Klik **Date Filter** untuk memilih rentang waktu.<br>3. Pilih filter shift kerja pada dropdown jika dibutuhkan.<br>4. Geser layar ke bawah untuk melihat grafik MPAndroidChart. | Metrik kartu (Orders, Revenue, Average Price, Products Sold), Pie chart varian rasa, dan Line chart tren diperbarui. |
| **User & Superadmin** | Manual Excel Upload | 1. Buka sidebar menu lalu pilih **Insert Manual Excel**.<br>2. Klik tombol **Download Template** untuk mengunduh template Excel.<br>3. Isi data transaksi vending pada file Excel tersebut.<br>4. Klik area **Drop Zone** di aplikasi untuk memilih file Excel, klik **Process Upload**. | Muncul dialog popup hasil ringkasan berisi info baris yang sukses di-import, dilewati (duplikat), dan gagal. |
| **User & Superadmin** | Forecast Viewing | 1. Buka sidebar menu lalu ketuk **Prediction Dashboard**.<br>2. Lihat ringkasan MAPE dan total prediksi 3 bulan mendatang.<br>3. Ubah dropdown filter chart (Total, Per Variant, Per Shift).<br>4. Klik tombol navigasi bulan di tabel bawah untuk menyaring log harian. | Grafik visual tren garis prediksi vs aktual diperbarui beserta detail error per hari. |
