import pandas as pd
from ProductionML.Script_production_daily_2_prod_v2 import fetch_calendar_from_sql, translate_to_layer1_calendar

df = fetch_calendar_from_sql(2026, 4)
print(df[["tanggal", "s1_active", "s2_active", "s3_active"]].head())
print("Dtypes:", df.dtypes)
cal, df2 = translate_to_layer1_calendar(df)
print(cal)
