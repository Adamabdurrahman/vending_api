# 📅 API Endpoint Specification — Menu Operational Calendar

Dokumen ini menjelaskan blueprint API untuk **Operational Calendar** yang akan dipanggil oleh aplikasi Android Studio. Semua logika CRUD dan perhitungan penanggalan dicuri dari ASP.NET MVC (`CalendarController.cs` & `calendar.js`) dan diadaptasi ke FastAPI.

---

## 1. Integrasi Library Python untuk Hari Libur & Ramadan

Pada kode ASP.NET legacy, sistem menggunakan library .NET `Nager.Date` dan `System.Globalization.HijriCalendar`. Untuk implementasi di FastAPI (Python), kami merekomendasikan dependencies berikut yang sangat matang:

1. **`holidays`** (Python library): Sangat akurat untuk mendeteksi Hari Libur Nasional Indonesia (kode negara `'ID'`).
   - *Install*: `pip install holidays`
2. **`hijri-converter`** (Python library): Untuk konversi penanggalan Masehi ke Hijriah guna mendeteksi bulan Ramadan (bulan ke-9 Hijriah).
   - *Install*: `pip install hijri-converter`

---

## 2. Endpoint 1: Fetch Calendar Data (`GET /api/v1/calendar`)

Mengambil daftar seluruh hari dalam satu tahun tertentu terbagi per bulan, jumlah total hari kerja, serta tahun-tahun yang tersedia di database.

- **HTTP Method**: `GET`
- **Request Query Params**: `year` (integer, default: `2026`)

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "year": 2026,
  "total_working_days": 245,
  "available_years": [2027, 2026, 2025],
  "months": [
    {
      "month_number": 1,
      "month_name": "Januari",
      "total_working_days": 21,
      "start_day_of_week": 3,
      "days": [
        {
          "day": 1,
          "date": "2026-01-01",
          "day_category": "Libur Nasional (Tahun Baru)",
          "is_working_day": false,
          "is_ramadan": false,
          "is_shutdown": false,
          "shift1_active": false,
          "shift2_active": false,
          "shift3_active": false,
          "is_weekend": false
        },
        {
          "day": 2,
          "date": "2026-01-02",
          "day_category": "Kerja Normal",
          "is_working_day": true,
          "is_ramadan": false,
          "is_shutdown": false,
          "shift1_active": true,
          "shift2_active": true,
          "shift3_active": true,
          "is_weekend": false
        }
      ]
    }
  ]
}
```

### B. Python SQL Query (Get Calendar Data)
```python
# Di dalam services/calendar_service.py:
def get_calendar_year_data(conn, year: int):
    cursor = conn.cursor()
    
    # 1. Ambil list tahun yang ada di database untuk sidebar dropdown
    cursor.execute("SELECT DISTINCT YEAR([Date]) FROM [OperationalCalendar] ORDER BY 1 DESC")
    available_years = [row[0] for row in cursor.fetchall()]
    
    if not available_years:
        available_years = [year]
        
    # Fallback jika tahun yang diminta tidak ada di DB
    if year not in available_years:
        year = available_years[0]

    # 2. Ambil seluruh data kalender pada tahun tersebut
    sql_query = """
        SELECT 
            [Date], 
            [DayCategory], 
            [IsWorkingDay], 
            [IsRamadan], 
            [Shift1_Active], 
            [Shift2_Active], 
            [Shift3_Active], 
            [IsShutdown]
        FROM [dbo].[OperationalCalendar]
        WHERE YEAR([Date]) = ?
        ORDER BY [Date] ASC
    """
    cursor.execute(sql_query, (year,))
    rows = cursor.fetchall()
    
    # Kelompokkan data menjadi format bulanan dengan kalkulasi index hari mulai (0 = Senin, ..., 6 = Minggu)
    # ...
```

---

## 3. Endpoint 2: Update Calendar Day (`POST /api/v1/calendar/day`)

Mengubah konfigurasi operasional pabrik pada tanggal tertentu di database.

- **HTTP Method**: `POST`
- **Request JSON Body**:
```json
{
  "date": "2026-05-25",
  "category": "Libur Nasional (Kustom)",
  "is_working_day": false,
  "is_ramadan": false,
  "is_shutdown": true
}
```

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "success": true,
  "message": "Calendar updated successfully."
}
```

### B. Python SQL Query (Update Day)
```python
# Di dalam router:
# shift_active dihitung otomatis: is_working_day AND NOT is_shutdown
shift_active = request.is_working_day and not request.is_shutdown

sql_update = """
    UPDATE [dbo].[OperationalCalendar]
    SET [DayCategory] = ?,
        [IsWorkingDay] = ?,
        [IsRamadan] = ?,
        [IsShutdown] = ?,
        [Shift1_Active] = ?,
        [Shift2_Active] = ?,
        [Shift3_Active] = ?
    WHERE CAST([Date] AS DATE) = CAST(? AS DATE)
"""
# Jalankan dengan parameter yang sesuai di cursor pyodbc...
```

---

## 4. Endpoint 3: Generate New Year Calendar (`POST /api/v1/calendar/generate`)

Secara otomatis menjabarkan 365/366 baris tanggal ke database untuk satu tahun baru. Logika mengintegrasikan deteksi otomatis akhir pekan (Sabtu-Minggu), library `holidays` untuk Libur Nasional Indonesia, dan `hijri-converter` untuk bulan Ramadan.

- **HTTP Method**: `POST`
- **Request JSON Body**:
```json
{
  "year": 2027
}
```

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "success": true,
  "message": "Calendar for year 2027 generated with 365 rows."
}
```

### B. Python SQL Transaction Logic
```python
import datetime
import holidays
from hijri_converter import Gregorian

def generate_calendar_year(conn, year: int):
    cursor = conn.cursor()
    
    # 1. Validasi apakah tahun sudah pernah dibuat
    cursor.execute("SELECT COUNT(1) FROM [dbo].[OperationalCalendar] WHERE YEAR([Date]) = ?", (year,))
    if cursor.fetchone()[0] > 0:
        raise ValueError(f"Tahun {year} sudah ada di kalender.")
        
    # 2. Tarik daftar Libur Nasional Indonesia via library
    id_holidays = holidays.country_holidays('ID', years=year)
    
    # 3. Definisikan rentang tanggal
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    
    # Mulai transaksi DB
    conn.autocommit = False
    try:
        current_date = start_date
        while current_date <= end_date:
            is_weekend = current_date.weekday() in (5, 6) # 5 = Sabtu, 6 = Minggu
            
            # Deteksi Ramadan (Bulan ke-9 Hijriah)
            hijri_date = Gregorian(current_date.year, current_date.month, current_date.day).to_hijri()
            is_ramadan = hijri_date.month == 9
            
            # Tentukan kategori hari & status kerja default
            category = "Kerja Normal"
            is_working = True
            is_shutdown = False
            
            if current_date in id_holidays:
                category = f"Libur Nasional ({id_holidays.get(current_date)})"
                is_working = False
            elif is_weekend:
                category = "Libur Akhir Pekan"
                is_working = False
                
            shift_active = is_working and not is_shutdown
            
            sql_insert = """
                INSERT INTO [dbo].[OperationalCalendar]
                ([Date], [DayCategory], [IsWorkingDay], [IsRamadan], [IsShutdown], [Shift1_Active], [Shift2_Active], [Shift3_Active])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert, (
                current_date, category, is_working, is_ramadan, is_shutdown, shift_active, shift_active, shift_active
            ))
            current_date += datetime.timedelta(days=1)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.autocommit = True
```

---

## 5. Endpoint 4: Delete Year Calendar (`DELETE /api/v1/calendar/year/{year}`)

Menghapus seluruh record kalender untuk satu tahun tertentu.

- **HTTP Method**: `DELETE`
- **Request URL Param**: `year` (integer)

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "success": true,
  "message": "Calendar for year 2026 deleted successfully."
}
```

### B. Python SQL Query
```sql
DELETE FROM [dbo].[OperationalCalendar] 
WHERE YEAR([Date]) = ?
```

---

## 💡 Tips untuk Developer Android Studio (Kotlin)

1. **Struktur Grid Bulan di Android (RecyclerView)**:
   - Gunakan parameter `start_day_of_week` (nilai `0` = Senin s.d. `6` = Minggu) dari API untuk menentukan berapa banyak slot kosong (*blank cells*) yang harus dirender di awal baris pertama grid tanggal pada kalender bulanan aplikasi Anda.
2. **Optimalisasi Bandwidth**:
   - Data kalender 1 tahun berjumlah ~365 objek. Gunakan kompresi Gzip di FastAPI middleware (`GZipMiddleware`) untuk menghemat pengiriman data ke mobile app secara dramatis.
3. **Pemberian Warna Visual**:
   - Manfaatkan status bendera (*flag*) dari API untuk mewarnai lingkaran kalender di HP Android: **Merah** untuk non-working day / holiday, **Hijau** untuk working day aktif, dan ornamen **Bulan Sabit/Kuning** jika `is_ramadan` bernilai true.
