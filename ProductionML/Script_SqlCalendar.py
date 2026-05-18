"""
Script_SqlCalendar.py
================================================================================
Modul untuk membaca OperationalCalendar dari SQL Server dan menghasilkan
dict FUTURE_CALENDAR yang siap dipakai Layer 1 Model.

Menggantikan hardcode FUTURE_CALENDAR di Fallback script & Test script.

Fungsi utama:
    - update_ramadan_flags(engine, year)  → isi IsRamadan di SQL
    - get_calendar_from_sql(year, month, engine) → return dict siap Layer 1
================================================================================
"""

import urllib
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

# ──────────────────────────────────────────────────────────────────────────────
# Tanggal Ramadan yang sudah diketahui (dikonfirmasi pemerintah/astronomis)
# Update setiap tahun jika tabel diperluas ke tahun baru
# ──────────────────────────────────────────────────────────────────────────────
RAMADAN_RANGES = {
    2026: (date(2026, 2, 18), date(2026, 3, 19)),  # 30 hari Ramadan 1447 H
    # 2027: (date(2027, 2, 7), date(2027, 3, 8)),  # estimasi — konfirmasi dulu
}

# Bobot Shift 2 untuk fractional working_days
# Referensi: Prediction_Update.txt — "Fractional Working Days" insight 5 Mei 2026
# Nilai 0.38 = perkiraan kontribusi Shift 2 terhadap total demand harian
SHIFT2_WEIGHT = 0.38


def get_sql_engine(
    server=r"ADAM123\SQLEXPRESS",
    database="db_vending_machine",
    username="sa",
    password="07Mei2005",
    driver="ODBC Driver 17 for SQL Server",
):
    """Buat SQLAlchemy engine ke SQL Server PT GS Battery."""
    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password}"
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    # Test koneksi
    with engine.connect() as conn:
        pass
    return engine


# ──────────────────────────────────────────────────────────────────────────────
# FUNGSI 1: Isi kolom IsRamadan di SQL
# ──────────────────────────────────────────────────────────────────────────────

def update_ramadan_flags(engine, year: int, dry_run: bool = False) -> int:
    """
    Tambahkan kolom IsRamadan ke OperationalCalendar (jika belum ada),
    lalu isi berdasarkan rentang Ramadan yang sudah diketahui.

    Parameters
    ----------
    engine : SQLAlchemy engine
    year   : Tahun yang ingin di-update (harus ada di RAMADAN_RANGES)
    dry_run: Jika True, hanya print SQL tanpa eksekusi

    Returns
    -------
    int: jumlah hari yang di-flag sebagai IsRamadan=1
    """
    if year not in RAMADAN_RANGES:
        raise ValueError(
            f"Tahun {year} tidak ada di RAMADAN_RANGES. "
            f"Tersedia: {list(RAMADAN_RANGES.keys())}"
        )

    start, end = RAMADAN_RANGES[year]
    print(f"\n[update_ramadan_flags] Tahun {year}")
    print(f"  Ramadan: {start} → {end} ({(end - start).days + 1} hari)")

    with engine.begin() as conn:
        # 1. Cek apakah kolom IsRamadan sudah ada
        check = conn.execute(text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'OperationalCalendar'
              AND COLUMN_NAME = 'IsRamadan'
        """)).scalar()

        if check == 0:
            if dry_run:
                print("  [DRY RUN] ALTER TABLE OperationalCalendar ADD IsRamadan BIT NOT NULL DEFAULT 0")
            else:
                conn.execute(text(
                    "ALTER TABLE OperationalCalendar ADD IsRamadan BIT NOT NULL DEFAULT 0"
                ))
                print("  ✅ Kolom IsRamadan berhasil ditambahkan.")
        else:
            print("  ℹ Kolom IsRamadan sudah ada — skip ALTER TABLE.")

        # 2. Reset semua IsRamadan = 0 untuk tahun ini dulu
        reset_sql = text("""
            UPDATE OperationalCalendar
            SET IsRamadan = 0
            WHERE YEAR([Date]) = :yr
        """)
        if dry_run:
            print(f"  [DRY RUN] RESET IsRamadan=0 untuk tahun {year}")
        else:
            conn.execute(reset_sql, {"yr": year})

        # 3. Set IsRamadan = 1 untuk rentang Ramadan
        update_sql = text("""
            UPDATE OperationalCalendar
            SET IsRamadan = 1
            WHERE [Date] >= :start_dt AND [Date] <= :end_dt
        """)
        if dry_run:
            print(f"  [DRY RUN] SET IsRamadan=1 untuk {start} s.d. {end}")
            return (end - start).days + 1
        else:
            conn.execute(update_sql, {"start_dt": start, "end_dt": end})

        # 4. Verifikasi
        count = conn.execute(text("""
            SELECT COUNT(*) FROM OperationalCalendar
            WHERE IsRamadan = 1 AND YEAR([Date]) = :yr
        """), {"yr": year}).scalar()

        print(f"  ✅ {count} hari berhasil di-flag IsRamadan=1 untuk {year}.")
        return count


# ──────────────────────────────────────────────────────────────────────────────
# FUNGSI 2: Bangun FUTURE_CALENDAR dict dari SQL
# ──────────────────────────────────────────────────────────────────────────────

def get_calendar_from_sql(
    year: int,
    month: int,
    engine,
    shift2_weight: float = SHIFT2_WEIGHT,
) -> dict:
    """
    Baca OperationalCalendar dari SQL dan kembalikan dict siap pakai Layer 1.

    Dict yang dihasilkan (format sama dengan FUTURE_CALENDAR di Fallback script):
    {
        "n_days"              : total hari dalam bulan,
        "working_days"        : hari kerja (fractional jika ada shift adjustment),
        "productive_milk_days": working_days yang BUKAN Ramadan (untuk Step 9),
        "ramadan_days"        : total hari Ramadan dalam bulan (semua hari, bukan hanya kerja),
        "holiday_days"        : Libur Nasional,
        "weekend_days"        : Libur Akhir Pekan,
    }

    Fractional working_days:
        - Hari di mana hanya Shift2 yang aktif (misal Minggu masuk): +shift2_weight
          (sudah tercatat IsWorkingDay=True, tapi kontribusinya hanya fraksi)
        - Hari di mana Shift2 libur tapi hari kerja: 1 - shift2_weight

    Parameters
    ----------
    year, month    : target bulan
    engine         : SQLAlchemy engine
    shift2_weight  : bobot kontribusi Shift 2 terhadap demand harian (default 0.38)

    Returns
    -------
    dict dengan key-key di atas
    """
    period_str = f"{year}-{month:02d}"
    start_dt = date(year, month, 1)
    # Hitung hari terakhir bulan
    if month == 12:
        end_dt = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_dt = date(year, month + 1, 1) - timedelta(days=1)

    # Cek apakah IsRamadan sudah ada di tabel
    with engine.connect() as conn:
        has_ramadan_col = conn.execute(text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'OperationalCalendar'
              AND COLUMN_NAME = 'IsRamadan'
        """)).scalar() > 0

        if has_ramadan_col:
            query = text("""
                SELECT [Date], DayCategory, IsWorkingDay,
                       Shift1_Active, Shift2_Active, Shift3_Active, IsRamadan
                FROM OperationalCalendar
                WHERE [Date] >= :s AND [Date] <= :e
                ORDER BY [Date]
            """)
        else:
            query = text("""
                SELECT [Date], DayCategory, IsWorkingDay,
                       Shift1_Active, Shift2_Active, Shift3_Active
                FROM OperationalCalendar
                WHERE [Date] >= :s AND [Date] <= :e
                ORDER BY [Date]
            """)

        rows = conn.execute(query, {"s": start_dt, "e": end_dt}).fetchall()
        cols = conn.execute(query, {"s": start_dt, "e": end_dt}).keys()

    if not rows:
        raise ValueError(
            f"Tidak ada data di OperationalCalendar untuk {period_str}. "
            f"Pastikan tabel sudah terisi untuk tahun {year}."
        )

    df = pd.DataFrame(rows, columns=list(
        ["Date", "DayCategory", "IsWorkingDay",
         "Shift1_Active", "Shift2_Active", "Shift3_Active"]
        + (["IsRamadan"] if has_ramadan_col else [])
    ))

    # ── Konversi bit ke bool ──────────────────────────────────────────────────
    for col in ["IsWorkingDay", "Shift1_Active", "Shift2_Active", "Shift3_Active"]:
        df[col] = df[col].astype(bool)
    if has_ramadan_col:
        df["IsRamadan"] = df["IsRamadan"].astype(bool)
    else:
        # Fallback: taksir dari RAMADAN_RANGES jika kolom belum ada
        if year in RAMADAN_RANGES:
            r_start, r_end = RAMADAN_RANGES[year]
            df["IsRamadan"] = df["Date"].apply(
                lambda d: r_start <= d.date() <= r_end if hasattr(d, "date") else False
            )
            print(f"  ⚠ Kolom IsRamadan belum ada di SQL — menggunakan RAMADAN_RANGES fallback.")
        else:
            df["IsRamadan"] = False
            print(f"  ⚠ Kolom IsRamadan belum ada & {year} tidak di RAMADAN_RANGES → ramadan=0.")

    # ── Hitung setiap field ───────────────────────────────────────────────────
    n_days = len(df)

    # Fractional working_days
    # - Hari normal (semua shift aktif)     → 1.0
    # - Hanya Shift2 aktif (Shift1+3=False) → shift2_weight   (∆ = -(1-shift2_weight))
    # - Shift2 libur, Shift1/3 aktif        → 1-shift2_weight (∆ = -shift2_weight)
    wd_df = df[df["IsWorkingDay"]].copy()

    s2_only    = wd_df["Shift2_Active"] & ~wd_df["Shift1_Active"] & ~wd_df["Shift3_Active"]
    s2_off     = ~wd_df["Shift2_Active"] & (wd_df["Shift1_Active"] | wd_df["Shift3_Active"])

    base_wd    = len(wd_df)
    adj_s2only = -(1 - shift2_weight) * s2_only.sum()   # kontribusi dikurangi
    adj_s2off  = -shift2_weight       * s2_off.sum()     # hilang fraksi Shift2
    working_days_frac = round(base_wd + adj_s2only + adj_s2off, 4)

    # Productive milk days = hari kerja yang BUKAN Ramadan (support Step 9)
    productive_df   = wd_df[~wd_df["IsRamadan"]]
    # Terapkan fractional juga di productive
    ps2_only        = productive_df["Shift2_Active"] & ~productive_df["Shift1_Active"] & ~productive_df["Shift3_Active"]
    ps2_off         = ~productive_df["Shift2_Active"] & (productive_df["Shift1_Active"] | productive_df["Shift3_Active"])
    prod_base       = len(productive_df)
    prod_frac       = round(prod_base - (1 - shift2_weight) * ps2_only.sum() - shift2_weight * ps2_off.sum(), 4)

    ramadan_days    = int(df["IsRamadan"].sum())
    holiday_days    = int(df["DayCategory"].str.contains("Libur Nasional", na=False).sum())
    weekend_days    = int(df["DayCategory"].str.contains("Akhir Pekan", na=False).sum())

    result = {
        "n_days"               : n_days,
        "working_days"         : working_days_frac,
        "productive_milk_days" : prod_frac,
        "ramadan_days"         : ramadan_days,
        "holiday_days"         : holiday_days,
        "weekend_days"         : weekend_days,
    }

    return result


# ──────────────────────────────────────────────────────────────────────────────
# FUNGSI 3: Bangun seluruh FUTURE_CALENDAR untuk satu kuartal/daftar bulan
# ──────────────────────────────────────────────────────────────────────────────

def build_future_calendar(months: list, engine) -> dict:
    """
    Bangun FUTURE_CALENDAR dict untuk list of 'YYYY-MM' string.

    Parameters
    ----------
    months : list of str, e.g. ["2026-01", "2026-02", "2026-03"]
    engine : SQLAlchemy engine

    Returns
    -------
    dict keyed by 'YYYY-MM'
    """
    calendar = {}
    for m in months:
        yr, mn = int(m[:4]), int(m[5:])
        try:
            cal = get_calendar_from_sql(yr, mn, engine)
            calendar[m] = cal
        except Exception as e:
            print(f"  ⚠ Gagal ambil kalender {m}: {e}")
    return calendar


# ──────────────────────────────────────────────────────────────────────────────
# MAIN — Jalankan langsung untuk setup & preview
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("Script_SqlCalendar.py — Setup & Preview")
    print("=" * 65)

    print("\n[1] Koneksi ke SQL Server...")
    try:
        engine = get_sql_engine()
        print("  ✅ Koneksi berhasil.")
    except Exception as e:
        print(f"  ❌ Gagal koneksi: {e}")
        raise SystemExit(1)

    print("\n[2] Update IsRamadan 2026 di OperationalCalendar...")
    update_ramadan_flags(engine, year=2026, dry_run=False)

    print("\n[3] Build FUTURE_CALENDAR Q1 2026 dari SQL...")
    Q1_2026 = ["2026-01", "2026-02", "2026-03"]
    future_cal = build_future_calendar(Q1_2026, engine)

    print("\n  Hasil FUTURE_CALENDAR Q1 2026:")
    print(f"  {'Bulan':<10} {'n_days':>7} {'work_days':>10} {'prod_milk':>10} "
          f"{'ramadan':>8} {'holiday':>8} {'weekend':>8}")
    print("  " + "─" * 68)
    for m, cal in future_cal.items():
        print(
            f"  {m:<10} {cal['n_days']:>7} {cal['working_days']:>10.2f} "
            f"{cal['productive_milk_days']:>10.2f} {cal['ramadan_days']:>8} "
            f"{cal['holiday_days']:>8} {cal['weekend_days']:>8}"
        )

    print("\n  Perbandingan vs FUTURE_CALENDAR lama (hardcode):")
    OLD = {
        "2026-01": {"working_days": 22, "ramadan_days": 0,  "holiday_days": 1},
        "2026-02": {"working_days": 17, "ramadan_days": 11, "holiday_days": 0},
        "2026-03": {"working_days": 1,  "ramadan_days": 18, "holiday_days": 2},
    }
    print(f"  {'Bulan':<10} {'field':<22} {'Lama':>8} {'SQL Baru':>10} {'Delta':>8}")
    print("  " + "─" * 55)
    for m in Q1_2026:
        for field in ["working_days", "ramadan_days", "holiday_days"]:
            old_v = OLD[m].get(field, "—")
            new_v = future_cal[m].get(field, "—")
            try:
                delta = f"{new_v - old_v:+.2f}"
            except Exception:
                delta = "—"
            flag = " ⚠" if delta not in ("—", "+0.00", "0") and delta != "+0" else ""
            print(f"  {m:<10} {field:<22} {str(old_v):>8} {str(new_v):>10} {delta:>8}{flag}")

    print("\n[DONE] Gunakan build_future_calendar() atau get_calendar_from_sql()")
    print("       di Script_Model_XGBoost_V6_Fallback.py dan Script_Test_Layer1_Artifact.py")
    print("=" * 65)
