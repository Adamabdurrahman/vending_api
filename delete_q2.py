import sys, os
from sqlalchemy import text
sys.path.insert(0, os.getcwd())
from database import engine

with engine.begin() as conn:
    conn.execute(text("DELETE FROM dbo.ForecastResults_Layer2 WHERE PredictedMonth IN ('2026-04', '2026-05', '2026-06')"))
    conn.execute(text("DELETE FROM dbo.ForecastResults_Layer1 WHERE PredictedMonth IN ('2026-04', '2026-05', '2026-06')"))
print('Q2 predictions deleted. Ready for clean pipeline run.')
