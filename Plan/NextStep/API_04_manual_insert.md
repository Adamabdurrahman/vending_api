# 📥 API Endpoint Specification — Menu Manual Insert Excel

Dokumen ini menjelaskan blueprint API untuk **Manual Insert Data** berbasis upload file Excel yang akan dipanggil oleh aplikasi Android Studio. Semua logika validasi, pencegahan data ganda, dan perhitungan otomatis dicuri dari ASP.NET MVC (`ManualInsertController.cs` & `manualinsert.js`) dan diadaptasi ke FastAPI.

---

## 1. Penggantian Teknologi Driver Excel (Legacy OLEDB ke Modern Python)

Pada kode ASP.NET legacy, pembacaan file Excel dilakukan melalui driver Windows OLEDB (`Microsoft.ACE.OLEDB.12.0` / `Microsoft.Jet.OLEDB.4.0`) yang memerlukan instalasi software Microsoft Office di server host.

Untuk FastAPI (Python), kita menggantinya secara total dengan library Python modern yang **platform-independent** (bisa berjalan di Windows, Linux Docker, maupun Cloud):

1. **`pandas`**: Library analisis data utama yang memiliki fungsi parsing file Excel sangat efisien.
2. **`openpyxl`**: Engine pembaca file modern XML spreadsheet `.xlsx`.

*Dependencies tambahan untuk ditambahkan pada `requirements.txt`:*
```txt
pandas>=2.0.0
openpyxl>=3.1.0
```

---

## 2. Endpoint 1: Download Template Excel (`GET /api/v1/manual-insert/template`)

Mengunduh file template Excel standar (`Template_Insert.xlsx`) untuk diisi oleh pengguna Android.

- **HTTP Method**: `GET`
- **Response**: `FileResponse` (Binary Stream File download)

### A. Alur Kerja FastAPI
FastAPI akan membaca file template dari folder `reference/Template_Insert.xlsx` di server dan mengirimkannya langsung dengan header MIME-Type yang sesuai agar browser/aplikasi Android dapat mengunduhnya secara lokal.

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/template")
def download_template():
    file_path = "reference/Template_Insert.xlsx"
    if not os.path.exists(file_path):
        return {"success": False, "message": "Template file tidak ditemukan di server."}
        
    return FileResponse(
        path=file_path, 
        filename="Template_Insert.xlsx", 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
```

---

## 3. Endpoint 2: Upload & Process Excel (`POST /api/v1/manual-insert/upload`)

Menerima file Excel multipart form-data, melakukan validasi sel demi sel, menghitung parameter tanggal secara otomatis (*Ramadan, Weekend, dll.*), menyaring data ganda di SQL Server (`Vending_Aggregrated`), dan mengembalikan ringkasan statistik proses.

- **HTTP Method**: `POST`
- **Request Form-Data**: `file` (Binary File Upload, MIME-Type: `.xlsx` / `.xls`)

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "success": true,
  "message": "Proses selesai! 45 data berhasil ter-insert, 12 data ganda dilewati.",
  "inserted_count": 45,
  "duplicated_count": 12,
  "invalid_rows_skipped": 2
}
```

### B. Python SQL & Logic Implementation (Curi & Optimasi dari C#)

FastAPI akan memproses baris demi baris file Excel yang diunggah. Seluruh data diubah menjadi model terstandarisasi sebelum dimasukkan ke database:

```python
from fastapi import APIRouter, UploadFile, File
import pandas as pd
import io
from hijri_converter import Gregorian

@router.post("/upload")
def upload_excel(file: UploadFile = File(...)):
    # 1. Validasi Ekstensi File
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["xls", "xlsx"]:
        return {"success": False, "message": "Format file tidak valid. Hanya .xls atau .xlsx"}
    
    # 2. Baca file ke memori (tanpa disimpan fisik ke disk untuk efisiensi IO)
    content = file.file.read()
    df = pd.read_excel(io.BytesIO(content), engine="openxml" if ext == "xlsx" else None)
    
    inserted_count = 0
    duplicated_count = 0
    invalid_rows = 0
    
    # Kumpulan parameter database pyodbc
    conn = get_db_connection() # dari database core pool
    cursor = conn.cursor()
    
    for idx, row in df.iterrows():
        # Validasi kolom-kolom utama wajib diisi
        if pd.isna(row.get('tanggal')) or pd.isna(row.get('keterangan')) or pd.isna(row.get('nama_variant')):
            invalid_rows += 1
            continue
            
        # Parse tanggal
        try:
            tanggal = pd.to_datetime(row['tanggal']).date()
        except:
            invalid_rows += 1
            continue
            
        keterangan = str(row['keterangan']).strip()
        nama_variant = str(row['nama_variant']).strip()
        
        # Parse demand & holiday
        demand = int(row.get('demand', 0)) if not pd.isna(row.get('demand')) else 0
        is_holiday = int(row.get('is_holiday', 0)) if not pd.isna(row.get('is_holiday')) else 0
        
        # Kalkulasi otomatis is_weekend (Sabtu = 5, Minggu = 6 di python weekday)
        is_weekend = 1 if tanggal.weekday() in [5, 6] else 0
        
        # Kalkulasi otomatis is_ramadan
        is_ramadan = 0
        try:
            hijri_date = Gregorian(tanggal.year, tanggal.month, tanggal.day).to_hijri()
            is_ramadan = 1 if hijri_date.month == 9 else 0
        except:
            pass
            
        is_manual_insert = True # Flag penanda manual insert
        
        # A. Cek Duplikasi ke Database (tanggal + keterangan + nama_variant)
        sql_check = """
            SELECT COUNT(1) 
            FROM [dbo].[Vending_Aggregrated] 
            WHERE CAST(tanggal AS DATE) = CAST(? AS DATE) 
              AND keterangan = ? 
              AND nama_variant = ?
        """
        cursor.execute(sql_check, (tanggal, keterangan, nama_variant))
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            duplicated_count += 1
            continue
            
        # B. Eksekusi INSERT ke Tabel Vending_Aggregrated
        sql_insert = """
            INSERT INTO [dbo].[Vending_Aggregrated]
            (tanggal, keterangan, nama_variant, demand, is_holiday, is_manual_insert, is_ramadan, is_weekend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor.execute(sql_insert, (
                tanggal, keterangan, nama_variant, demand, is_holiday, is_manual_insert, is_ramadan, is_weekend
            ))
            inserted_count += 1
        except Exception as e:
            invalid_rows += 1
            continue
            
    conn.commit()
    
    return {
        "success": True,
        "message": f"Proses selesai! {inserted_count} data baru masuk, {duplicated_count} duplikasi dilewati.",
        "inserted_count": inserted_count,
        "duplicated_count": duplicated_count,
        "invalid_rows_skipped": invalid_rows
    }
```

---

## 4. Keamanan Kecepatan Batch Upload (PENTING)

1. **Transaction Wrapping**:
   FastAPI menguji satu koneksi SQL dengan pemrosesan berulang. Untuk performa optimal, seluruh baris Excel dimasukkan ke dalam **satu transaksi tunggal** (`conn.commit()`) di akhir proses. Jika terjadi error sistem total di tengah jalan, database dapat di-rollback (`conn.rollback()`) sehingga mencegah ketidaksinkronan data parsial.
2. **Keterbatasan Upload File Android**:
   Ukuran payload upload tidak boleh terlalu besar di mobile. Sangat disarankan menetapkan batasan ukuran maksimum file Excel yang dikirim dari Android maksimal **5 MegaBytes**.

---

## 💡 Tips untuk Developer Android Studio (Kotlin)

1. **Membuka File Picker**:
   Gunakan Android Jetpack Activity Result API `GetContent` untuk membuka pemilih file Excel di HP Android:
   ```kotlin
   val filePicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
       uri?.let {
           // Jalankan upload file multipart di latar belakang (WorkManager/Coroutines)
       }
   }
   filePicker.launch("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
   ```
2. **Multipart Request Retrofit**:
   Format API mewajibkan upload dengan `MultipartBody.Part`. Berikut representasi Kotlin Interface Retrofit-nya:
   ```kotlin
   @Multipart
   @POST("api/v1/manual-insert/upload")
   suspend fun uploadExcel(
       @Part file: MultipartBody.Part
   ): Response<UploadResponse>
   ```
3. **Feedback UI Real-Time**:
   Proses parsing data Excel di backend memerlukan waktu 1 hingga 5 detik tergantung jumlah baris data. Selalu tampilkan animasi loading block overlay (`CircularProgressIndicator` atau shimmer dialog) pada layout Android Studio Anda untuk mencegah pengguna menekan tombol upload berulang kali.
