import pandas as pd
from database import engine

df = pd.read_sql("SELECT Date, IsWorkingDay, Shift1_Active, Shift2_Active, Shift3_Active FROM dbo.OperationalCalendar WHERE YEAR(Date)=2026 AND MONTH(Date)=4", engine)
print(df.to_string())
print("Total IsWorkingDay:", df["IsWorkingDay"].sum())
