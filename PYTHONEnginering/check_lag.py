import pandas as pd
from database import engine

df = pd.read_sql("SELECT period, demand, lag_1m, lag_2m, lag_3m FROM dbo.vending_training_ml WHERE period >= '2026-01' AND variant='Coklat'", engine)
print(df.to_string())
