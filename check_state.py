from database import engine
from sqlalchemy import text
import pandas as pd
from datetime import datetime

print("=== STATUS DB SAAT INI ===")
df1 = pd.read_sql("SELECT PredictedMonth, TotalDemand, ActualDemand FROM dbo.ForecastResults_Layer1 ORDER BY PredictedMonth", engine)
print(df1.to_string(index=False))

r2 = pd.read_sql("SELECT COUNT(*) as n FROM dbo.ForecastResults_Layer2", engine)
print("L2 rows:", r2["n"].values[0])
print()

today = datetime(2026, 5, 16)
q2_start = datetime(2026, 4, 1)
days_elapsed = (today - q2_start).days
print(f"Hari ini          : {today.date()}")
print(f"Q2 mulai          : {q2_start.date()}")
print(f"Days since Q2 start: {days_elapsed}")
print(f"Timeout threshold : 45 hari")
print()

with engine.connect() as conn:
    hari_tercover = conn.execute(text(
        "SELECT COUNT(DISTINCT CAST(tanggal AS DATE)) FROM dbo.Vending_Aggregrated "
        "WHERE tanggal >= '2026-01-01' AND tanggal <= '2026-03-31'"
    )).scalar()
    cal_ref = conn.execute(text(
        "SELECT COUNT(Date) FROM dbo.OperationalCalendar "
        "WHERE Date >= '2026-01-01' AND Date <= '2026-03-31' "
        "AND IsRamadan = 0 AND IsWorkingDay = 1"
    )).scalar()
    pct = (hari_tercover / cal_ref * 100) if cal_ref else 0
    print(f"Hari tercover Q1  : {hari_tercover}")
    print(f"Target hari prod  : {cal_ref}")
    print(f"Kelengkapan data  : {pct:.1f}%")
    print()
    if pct >= 80:
        print(">> Keputusan Q2: NORMAL RUN (data >= 80%)")
    elif days_elapsed >= 45:
        print(f">> Keputusan Q2: FORCE RUN (timeout {days_elapsed} >= 45 hari)")
    else:
        print(f">> Keputusan Q2: WAITING ({days_elapsed}/45 hari, data {pct:.0f}%)")
