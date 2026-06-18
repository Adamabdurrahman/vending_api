import sys, os
sys.path.insert(0, os.getcwd())
import forecast_service
for m in [4, 5, 6]:
    df_cal = forecast_service.fetch_calendar_from_sql(2026, m)
    cal = forecast_service.translate_to_layer1_calendar(df_cal)[0]
    print(f'2026-{m:02d}: Productive={cal.get("productive_milk_days")}, Working={cal.get("working_days")}, Ramadan={cal.get("ramadan_days")}, n_days={cal.get("n_days")}, wkend={cal.get("weekend_days")}')
