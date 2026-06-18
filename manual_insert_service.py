import os
import io
import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from hijri_converter import Gregorian

TEMPLATE_PATH = "reference/Template_Insert.xlsx"

def ensure_template_exists():
    """Memastikan file template Excel tersedia di server. 
    Jika tidak ada, direktori 'reference/' akan dibuat dan template akan digenerate programmatically.
    """
    directory = os.path.dirname(TEMPLATE_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    if not os.path.exists(TEMPLATE_PATH):
        # Generate clean template programmatically
        headers = ['tanggal', 'keterangan', 'nama_variant', 'demand', 'is_holiday']
        mock_data = [
            ['2026-05-25', 'SHIFT1 - AWAL', 'Coklat', 99, 0],
            ['2026-05-25', 'SHIFT2 - AWAL', 'Strawberry', 99, 0],
            ['2026-05-25', 'SHIFT3 - AWAL', 'Moca', 99, 0],
            ['2026-05-25', 'SHIFT1 - AKHIR', 'Original (Putih)', 99, 0]
        ]
        
        df = pd.DataFrame(mock_data, columns=headers)
        # Write to excel using openpyxl engine
        df.to_excel(TEMPLATE_PATH, index=False, engine='openpyxl')
        print(f"[Manual Insert] Template generated successfully at {TEMPLATE_PATH}")

def process_excel_upload(db: Session, file_contents: bytes, filename: str) -> dict:
    """Membaca file Excel dari stream memori, memvalidasi per baris, 
    menghitung parameter tanggal otomatis (Ramadan, Weekend), 
    menyaring data duplikat, dan menginsert data baru dalam satu transaksi.
    """
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["xls", "xlsx"]:
        return {
            "success": False,
            "message": "Format file tidak valid. Hanya menerima format .xls atau .xlsx",
            "inserted_count": 0,
            "duplicated_count": 0,
            "invalid_rows_skipped": 0
        }
        
    try:
        # Load excel file into memory pandas DataFrame
        df = pd.read_excel(io.BytesIO(file_contents), engine="openpyxl" if ext == "xlsx" else None)
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal membaca file Excel: {str(e)}",
            "inserted_count": 0,
            "duplicated_count": 0,
            "invalid_rows_skipped": 0
        }
        
    # Validasi keberadaan kolom wajib
    required_cols = ['tanggal', 'keterangan', 'nama_variant']
    for col in required_cols:
        if col not in df.columns:
            return {
                "success": False,
                "message": f"Kolom wajib '{col}' tidak ditemukan di dalam dokumen Excel.",
                "inserted_count": 0,
                "duplicated_count": 0,
                "invalid_rows_skipped": 0
            }
            
    inserted_count = 0
    duplicated_count = 0
    invalid_rows_skipped = 0
    
    # Bungkus dalam transaksi tunggal
    try:
        for idx, row in df.iterrows():
            # 1. Validasi nilai wajib (non-null / non-empty)
            tanggal_raw = row.get('tanggal')
            keterangan_raw = row.get('keterangan')
            nama_variant_raw = row.get('nama_variant')
            
            if pd.isna(tanggal_raw) or pd.isna(keterangan_raw) or pd.isna(nama_variant_raw):
                invalid_rows_skipped += 1
                continue
                
            # 2. Parsing Tanggal
            try:
                # pandas to_datetime dapat memparse string/date/timestamp dengan andal
                tanggal = pd.to_datetime(tanggal_raw).date()
            except Exception:
                invalid_rows_skipped += 1
                continue
                
            # 3. Truncate & Clean string variables (mencegah data truncation error)
            keterangan = str(keterangan_raw).strip()[:50]
            nama_variant = str(nama_variant_raw).strip()[:100]
            
            if not keterangan or not nama_variant:
                invalid_rows_skipped += 1
                continue
                
            # 4. Parsing demand & holiday (default to 0 if null or invalid)
            try:
                demand_val = row.get('demand', 0)
                demand = int(demand_val) if not pd.isna(demand_val) else 0
            except Exception:
                demand = 0
                
            try:
                holiday_val = row.get('is_holiday', 0)
                is_holiday = int(holiday_val) if not pd.isna(holiday_val) else 0
            except Exception:
                is_holiday = 0
                
            # 5. Hitung is_weekend secara otomatis (weekday 5=Sabtu, 6=Minggu)
            is_weekend = 1 if tanggal.weekday() in [5, 6] else 0
            
            # 6. Hitung is_ramadan secara otomatis menggunakan hijri_converter
            is_ramadan = 0
            try:
                hijri_date = Gregorian(tanggal.year, tanggal.month, tanggal.day).to_hijri()
                is_ramadan = 1 if hijri_date.month == 9 else 0
            except Exception:
                pass
                
            # 7. Duplication Check di SQL Server (tanggal, keterangan, nama_variant)
            sql_check = text("""
                SELECT COUNT(1) 
                FROM dbo.Vending_Aggregrated 
                WHERE CAST(tanggal AS DATE) = CAST(:tanggal AS DATE) 
                  AND keterangan = :keterangan 
                  AND nama_variant = :nama_variant
            """)
            
            exists = db.execute(sql_check, {
                "tanggal": tanggal,
                "keterangan": keterangan,
                "nama_variant": nama_variant
            }).scalar()
            
            if exists > 0:
                duplicated_count += 1
                continue
                
            # 8. Insert ke Database
            sql_insert = text("""
                INSERT INTO dbo.Vending_Aggregrated 
                (tanggal, keterangan, nama_variant, demand, is_holiday, is_manual_insert, is_ramadan, is_weekend)
                VALUES 
                (:tanggal, :keterangan, :nama_variant, :demand, :is_holiday, 1, :is_ramadan, :is_weekend)
            """)
            
            db.execute(sql_insert, {
                "tanggal": tanggal,
                "keterangan": keterangan,
                "nama_variant": nama_variant,
                "demand": demand,
                "is_holiday": is_holiday,
                "is_ramadan": is_ramadan,
                "is_weekend": is_weekend
            })
            inserted_count += 1
            
        # Commit seluruh data di akhir proses (single transaction commit)
        db.commit()
        
    except Exception as e:
        # Rollback jika ada error tak terduga untuk menjaga integritas database
        db.rollback()
        return {
            "success": False,
            "message": f"Terjadi kesalahan database internal: {str(e)}",
            "inserted_count": 0,
            "duplicated_count": 0,
            "invalid_rows_skipped": 0
        }
        
    return {
        "success": True,
        "message": f"Proses selesai! {inserted_count} data baru masuk, {duplicated_count} duplikasi dilewati.",
        "inserted_count": inserted_count,
        "duplicated_count": duplicated_count,
        "invalid_rows_skipped": invalid_rows_skipped
    }
