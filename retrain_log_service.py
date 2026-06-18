from sqlalchemy.orm import Session
from sqlalchemy import text

def get_retrain_logs_data(db: Session, limit: int = 100, offset: int = 0) -> list:
    """Mengambil seluruh riwayat ML retraining log dari dbo.RetrainLog.
    Menggunakan CTE untuk memberikan SequenceNum kronologis, lalu menghitung
    quarter dan year sekuensial secara dinamis, serta menjaga null safety nilai metrik.
    """
    sql_query = text("""
        WITH RankedLogs AS (
            SELECT 
                [Id],
                [RunTimestamp],
                [ModelVersion],
                [MAPE],
                [MAE],
                [RMSE],
                [TrainingRows],
                [TrainingPeriodEnd],
                [BestParams],
                [Status],
                ROW_NUMBER() OVER(ORDER BY RunTimestamp ASC) as SequenceNum 
            FROM [dbo].[RetrainLog]
        )
        SELECT * 
        FROM RankedLogs 
        ORDER BY RunTimestamp DESC
    """)
    
    res = db.execute(sql_query).fetchall()
    
    logs = []
    for r in res:
        seq_num = r.SequenceNum
        
        # Logika Quarter: ((seqNum - 1) % 4) + 1
        q_num = ((seq_num - 1) % 4) + 1
        quarter_label = f"Q{q_num}"
        
        # Logika Tahun: 2026 + ((seqNum - 1) // 4)
        calculated_year = 2026 + ((seq_num - 1) // 4)
        
        # Null safety & string formatting
        run_ts = r.RunTimestamp.isoformat() if r.RunTimestamp else None
        model_ver = r.ModelVersion.strip() if r.ModelVersion else ""
        mape_val = round(float(r.MAPE), 2) if r.MAPE is not None else 0.0
        mae_val = round(float(r.MAE), 2) if r.MAE is not None else 0.0
        rmse_val = round(float(r.RMSE), 2) if r.RMSE is not None else 0.0
        tr_rows = int(r.TrainingRows) if r.TrainingRows is not None else 0
        tr_period_end = r.TrainingPeriodEnd.strip() if r.TrainingPeriodEnd else ""
        best_params_val = r.BestParams or "{}"
        status_val = r.Status.strip() if r.Status else "Failed"
        
        logs.append({
            "id": r.Id,
            "quarter_label": quarter_label,
            "calculated_quarter": q_num,
            "calculated_year": calculated_year,
            "run_timestamp": run_ts,
            "model_version": model_ver,
            "mape": mape_val,
            "mae": mae_val,
            "rmse": rmse_val,
            "training_rows": tr_rows,
            "training_period_end": tr_period_end,
            "best_params": best_params_val,
            "status": status_val
        })
        
    # Manual slicing untuk pagination
    return logs[offset:offset + limit]
