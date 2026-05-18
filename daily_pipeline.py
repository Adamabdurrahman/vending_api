import time
from datetime import datetime
import pandas as pd
from etl_service import run_etl_pipeline
from forecast_service import update_actuals
from scheduler_service import check_and_run_quarterly
import notif_service

def job():
    start_time = datetime.now()
    print("="*60)
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] MEMULAI DAILY PIPELINE")
    print("="*60)
    
    # 1. Proses ETL (Extract, Transform, Load) harian
    try:
        run_etl_pipeline()
    except Exception as e:
        print(f"\n[DAILY PIPELINE] ETL Gagal: {e}")
        notif_service.error_from_exception("ETL", "ETL Gagal (Harian)", e)
        print("\n[DAILY PIPELINE] Menghentikan pipeline karena ETL gagal.")
        return # Berhenti jika ETL gagal, besok coba lagi
        
    # 2. Update Actuals (Sinkronisasi data aktual untuk SEMUA bulan yang belum ter-update)
    print("\n" + "-"*60)
    print("[DAILY PIPELINE] Memulai Sinkronisasi Data Aktual...")

    # [BUGFIX] Ganti window 3 bulan terakhir dengan query dinamis ke ForecastResults_Layer1.
    # Sebelumnya: range(3) → hanya update Mei/Apr/Mar → Jan & Feb Q1 TIDAK PERNAH ter-update!
    # Sekarang: ambil semua bulan yang punya prediksi tapi ActualDemand masih NULL,
    # lalu coba update masing-masing. Bulan masa depan (belum ada aktual) akan
    # di-skip secara otomatis oleh update_actuals() karena SUM(demand) = 0.
    from database import engine as _engine
    from sqlalchemy import text as _text
    try:
        with _engine.connect() as _conn:
            pending_months = _conn.execute(
                _text(
                    "SELECT DISTINCT PredictedMonth FROM dbo.ForecastResults_Layer1 "
                    "WHERE ActualDemand IS NULL ORDER BY PredictedMonth"
                )
            ).fetchall()
        pending_months = [r[0] for r in pending_months]
        print(f"[DAILY PIPELINE] Bulan dengan aktual belum tersinkron: {pending_months or 'Tidak ada'}")
    except Exception as e:
        print(f"[DAILY PIPELINE] Gagal query pending months, fallback ke 3 bulan terakhir: {e}")
        today = datetime.now()
        pending_months = [(today - pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(3)]

    for m_str in pending_months:
        try:
            res_act = update_actuals(m_str)
            if isinstance(res_act, dict) and res_act.get("status") == "success":
                print(f"[DAILY PIPELINE] Update Actuals {m_str}: OK "
                      f"(Pred={res_act.get('predicted_total')}, "
                      f"Actual={res_act.get('actual_total')}, "
                      f"Error={res_act.get('error_percent_total')})")
        except Exception as e:
            print(f"[DAILY PIPELINE] Update Actuals untuk {m_str} Gagal: {e}")
            notif_service.error_from_exception("UPDATE_ACTUALS", f"Update Actuals {m_str} Gagal", e)
            
    # 3. Quarterly Check (Memulai Kuartal Baru jika waktunya tiba)
    print("\n" + "-"*60)
    try:
        check_and_run_quarterly()
    except Exception as e:
        print(f"[DAILY PIPELINE] Quarterly Check Gagal: {e}")
        notif_service.error_from_exception("QUARTERLY", "Quarterly Check Gagal", e)
        
    end_time = datetime.now()
    duration = end_time - start_time
    print("="*60)
    print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] DAILY PIPELINE SELESAI (Durasi: {duration})")
    print("="*60)

if __name__ == "__main__":
    job()
