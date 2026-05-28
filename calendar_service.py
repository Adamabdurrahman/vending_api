import datetime
import holidays
from hijri_converter import Gregorian
from sqlalchemy.orm import Session
from sqlalchemy import text

INDONESIAN_MONTHS = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

def get_calendar_year_data(db: Session, year: int):
    """
    Mengambil daftar seluruh hari dalam satu tahun tertentu terbagi per bulan,
    jumlah total hari kerja, serta tahun-tahun yang tersedia di database.
    """
    # 1. Ambil list tahun yang ada di database
    sql_years = "SELECT DISTINCT YEAR(Date) FROM dbo.OperationalCalendar ORDER BY 1 DESC"
    years_rows = db.execute(text(sql_years)).fetchall()
    available_years = [r[0] for r in years_rows]
    
    if not available_years:
        available_years = [year]
        
    # Fallback jika tahun yang diminta tidak ada di DB
    if year not in available_years:
        year = available_years[0]
        
    # 2. Ambil seluruh data kalender pada tahun tersebut
    sql_calendar = """
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
        WHERE YEAR([Date]) = :year
        ORDER BY [Date] ASC
    """
    rows = db.execute(text(sql_calendar), {"year": year}).fetchall()
    
    # Calculate total working days in that year
    total_working_days = 0
    
    # Group by months
    months_dict = {m: [] for m in range(1, 13)}
    
    for r in rows:
        dt = r[0]
        # Handle string or date objects
        dt_val = datetime.date.fromisoformat(str(dt)) if isinstance(dt, str) else dt
        
        category = r[1] or "Kerja Normal"
        is_working = bool(r[2])
        is_ramadan = bool(r[3])
        shift1 = bool(r[4])
        shift2 = bool(r[5])
        shift3 = bool(r[6])
        is_shutdown = bool(r[7])
        
        if is_working:
            total_working_days += 1
            
        is_weekend = dt_val.weekday() in (5, 6)
        
        day_item = {
            "day": dt_val.day,
            "date": dt_val.isoformat(),
            "day_category": category,
            "is_working_day": is_working,
            "is_ramadan": is_ramadan,
            "is_shutdown": is_shutdown,
            "shift1_active": shift1,
            "shift2_active": shift2,
            "shift3_active": shift3,
            "is_weekend": is_weekend
        }
        months_dict[dt_val.month].append(day_item)
        
    months_resp = []
    for m_num in range(1, 13):
        days_in_month = months_dict[m_num]
        
        # Calculate monthly working days
        m_working_days = sum(1 for d in days_in_month if d["is_working_day"])
        
        # Calculate start day of week for that month (Monday=0, ..., Sunday=6)
        try:
            start_day = datetime.date(year, m_num, 1).weekday()
        except ValueError:
            start_day = 0 # fallback
            
        months_resp.append({
            "month_number": m_num,
            "month_name": INDONESIAN_MONTHS.get(m_num, ""),
            "total_working_days": m_working_days,
            "start_day_of_week": start_day,
            "days": days_in_month
        })
        
    return {
        "year": year,
        "total_working_days": total_working_days,
        "available_years": available_years,
        "months": months_resp
    }


def update_calendar_day(db: Session, date_str: str, category: str, is_working_day: bool, is_ramadan: bool, is_shutdown: bool):
    """
    Mengubah konfigurasi operasional pabrik pada tanggal tertentu di database.
    """
    # Batasi panjang category agar tidak melebihi kolom varchar(50) di database
    category = category[:50]
    # Shift dihitung otomatis: is_working_day AND NOT is_shutdown
    shift_active = is_working_day and not is_shutdown
    
    sql_update = """
        UPDATE [dbo].[OperationalCalendar]
        SET [DayCategory] = :cat,
            [IsWorkingDay] = :is_working,
            [IsRamadan] = :is_ramadan,
            [IsShutdown] = :is_shutdown,
            [Shift1_Active] = :shift,
            [Shift2_Active] = :shift,
            [Shift3_Active] = :shift
        WHERE CAST([Date] AS DATE) = CAST(:date_str AS DATE)
    """
    params = {
        "cat": category,
        "is_working": 1 if is_working_day else 0,
        "is_ramadan": 1 if is_ramadan else 0,
        "is_shutdown": 1 if is_shutdown else 0,
        "shift": 1 if shift_active else 0,
        "date_str": date_str
    }
    
    result = db.execute(text(sql_update), params)
    db.commit()
    
    if result.rowcount == 0:
        # Jika tidak ada baris yang ter-update, coba insert baru
        # (jaga-jaga jika tanggal tersebut belum ada di database)
        dt_val = datetime.date.fromisoformat(date_str)
        sql_insert = """
            INSERT INTO [dbo].[OperationalCalendar]
            ([Date], [DayCategory], [IsWorkingDay], [IsRamadan], [IsShutdown], [Shift1_Active], [Shift2_Active], [Shift3_Active])
            VALUES (:dt, :cat, :is_working, :is_ramadan, :is_shutdown, :shift, :shift, :shift)
        """
        ins_params = {
            "dt": dt_val,
            "cat": category,
            "is_working": 1 if is_working_day else 0,
            "is_ramadan": 1 if is_ramadan else 0,
            "is_shutdown": 1 if is_shutdown else 0,
            "shift": 1 if shift_active else 0
        }
        db.execute(text(sql_insert), ins_params)
        db.commit()
        
    return {
        "success": True,
        "message": f"Calendar day {date_str} updated successfully."
    }


def generate_calendar_year(db: Session, year: int):
    """
    Menjabarkan 365/366 baris kalender untuk satu tahun baru di database.
    Mendeteksi akhir pekan, hari libur nasional Indonesia, dan bulan Ramadan.
    """
    # 1. Validasi apakah tahun sudah pernah dibuat
    sql_check = "SELECT COUNT(1) FROM [dbo].[OperationalCalendar] WHERE YEAR([Date]) = :year"
    count = db.execute(text(sql_check), {"year": year}).scalar() or 0
    if count > 0:
        raise ValueError(f"Tahun {year} sudah ada di kalender.")
        
    # 2. Tarik daftar Libur Nasional Indonesia via library
    id_holidays = holidays.country_holidays('ID', years=year)
    
    # Tambahkan libur kustom penting jika tidak terdeteksi otomatis
    # (Natal 25 Desember dll)
    id_holidays[datetime.date(year, 12, 25)] = "Hari Raya Natal"
    
    # 3. Definisikan rentang tanggal
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    
    rows_generated = 0
    
    current_date = start_date
    while current_date <= end_date:
        is_weekend = current_date.weekday() in (5, 6) # 5 = Sabtu, 6 = Minggu
        
        # Deteksi Ramadan (Bulan ke-9 Hijriah) menggunakan hijri-converter
        try:
            hijri_date = Gregorian(current_date.year, current_date.month, current_date.day).to_hijri()
            is_ramadan = hijri_date.month == 9
        except Exception:
            is_ramadan = False
            
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
            
        # Batasi panjang category agar tidak melebihi kolom varchar(50) di database
        category = category[:50]
        shift_active = is_working and not is_shutdown
        
        sql_insert = """
            INSERT INTO [dbo].[OperationalCalendar]
            ([Date], [DayCategory], [IsWorkingDay], [IsRamadan], [IsShutdown], [Shift1_Active], [Shift2_Active], [Shift3_Active])
            VALUES (:dt, :cat, :is_working, :is_ramadan, :is_shutdown, :shift, :shift, :shift)
        """
        params = {
            "dt": current_date,
            "cat": category,
            "is_working": 1 if is_working else 0,
            "is_ramadan": 1 if is_ramadan else 0,
            "is_shutdown": 1 if is_shutdown else 0,
            "shift": 1 if shift_active else 0
        }
        db.execute(text(sql_insert), params)
        rows_generated += 1
        
        current_date += datetime.timedelta(days=1)
        
    db.commit()
    
    return {
        "success": True,
        "message": f"Calendar for year {year} generated with {rows_generated} rows."
    }


def delete_calendar_year(db: Session, year: int):
    """
    Menghapus seluruh record kalender untuk satu tahun tertentu.
    """
    sql_delete = "DELETE FROM [dbo].[OperationalCalendar] WHERE YEAR([Date]) = :year"
    result = db.execute(text(sql_delete), {"year": year})
    db.commit()
    
    return {
        "success": True,
        "message": f"Calendar for year {year} deleted successfully (affected {result.rowcount} rows)."
    }
