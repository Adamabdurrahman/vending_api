import sys, os, pandas as pd
from sqlalchemy import text
sys.path.insert(0, os.getcwd())
from database import engine

df = pd.read_sql("SELECT PredictedMonth, TotalDemand, ActualDemand FROM dbo.ForecastResults_Layer1 WHERE PredictedMonth >= '2026-04' ORDER BY PredictedMonth", engine)
print(df.to_string(index=False))
