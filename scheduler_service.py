import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from database import engine
from forecast_service import generate_forecast
from retrain_service import run_retrain
import notif_service

def get_current_quarter(date_obj):
    m = date_obj.month
    if m in [1, 2, 3]: return 1, date_obj.year
    if m in [4, 5, 6]: return 2, date_obj.year
    if m in [7, 8, 9]: return 3, date_obj.year
    return 4, date_obj.year

def get_quarter_months(q, y):
    if q == 1: return [(y, 1), (y, 2), (y, 3)]
    if q == 2: return [(y, 4), (y, 5), (y, 6)]
    if q == 3: return [(y, 7), (y, 8), (y, 9)]
    return [(y, 10), (y, 11), (y, 12)]

def check_and_run_quarterly():
    """
    Menjalankan pengecekan rutin kuartalan (dengan fitur Smart Backfill).
    Sistem akan mencari kuartal tertua yang belum diprediksi (mulai Q1 2026)
    hingga kuartal saat ini, lalu memprosesnya secara berurutan.
    """
    today = datetime.now()
    actual_curr_q, actual_curr_y = get_current_quarter(today)
    
    print("\n" + "="*50)
    print(f"[SCHEDULER] Quarterly Check: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[SCHEDULER] Kuartal Kalender Hari Ini: Q{actual_curr_q} {actual_curr_y}")
    print("="*50)
    
    # 1. SMART BACKFILL: Cari kuartal tertua yang belum diprediksi
    target_y = 2026
    target_q = 1
    
    while True:
        start_y, start_m = get_quarter_months(target_q, target_y)[0]
        first_month_str = f"{start_y}-{start_m:02d}"
        
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT COUNT(*) FROM dbo.ForecastResults_Layer1 WHERE PredictedMonth = :m"),
                {"m": first_month_str}
            ).scalar()
            
        if exists == 0:
            break # Ketemu kuartal yang bolong/belum diprediksi
            
        # Jika sudah sampai kuartal saat ini dan semuanya sudah diprediksi
        if target_y == actual_curr_y and target_q == actual_curr_q:
            print(f"[SCHEDULER] Semua kuartal hingga Q{actual_curr_q} {actual_curr_y} SUDAH diprediksi. Skip.")
            return "ALREADY_DONE"
            
        # Lanjut cek kuartal berikutnya
        target_q += 1
        if target_q > 4:
            target_q = 1
            target_y += 1
            
    # Gunakan kuartal yang bolong tersebut sebagai fokus eksekusi
    curr_q = target_q
    curr_y = target_y
    
    print(f"[SCHEDULER] Target Eksekusi (Smart Backfill): Q{curr_q} {curr_y} (Mulai {first_month_str})")
            
    # 2. Belum diprediksi. Tentukan kuartal sebelumnya (Q_(n-1))
    prev_q = curr_q - 1
    prev_y = curr_y
    if prev_q == 0:
        prev_q = 4
        prev_y -= 1
        
    print(f"[SCHEDULER] Perlu memprediksi Kuartal Q{curr_q} {curr_y}.")
    print(f"[SCHEDULER] Mengecek kelengkapan data aktual kuartal sebelumnya (Q{prev_q} {prev_y})...")
    
    prev_months = get_quarter_months(prev_q, prev_y)
    start_dt = datetime(prev_months[0][0], prev_months[0][1], 1)
    # End date of previous quarter
    end_dt = datetime(prev_months[2][0], prev_months[2][1], 1) + relativedelta(months=1) - timedelta(days=1)
    
    with engine.connect() as conn:
        # [BUGFIX] Kecualikan hari Ramadan dan libur dari target kelengkapan data (karena VM memang mati)
        cal_ref = conn.execute(
            text("SELECT COUNT(Date) FROM dbo.OperationalCalendar WHERE Date >= :sd AND Date <= :ed AND IsRamadan = 0 AND IsWorkingDay = 1"),
            {"sd": start_dt.strftime('%Y-%m-%d'), "ed": end_dt.strftime('%Y-%m-%d')}
        ).scalar()
        
        if cal_ref is not None and cal_ref > 0:
            target_hari = cal_ref
        else:
            target_hari = max((end_dt - start_dt).days + 1 - 30, 1) # Fallback kasar kurangi 30 hari puasa
        
        hari_tercover = conn.execute(
            text("SELECT COUNT(DISTINCT CAST(tanggal AS DATE)) FROM dbo.Vending_Aggregrated WHERE tanggal >= :sd AND tanggal <= :ed"),
            {"sd": start_dt.strftime('%Y-%m-%d'), "ed": end_dt.strftime('%Y-%m-%d')}
        ).scalar()
        hari_tercover = hari_tercover if hari_tercover else 0
        
    pct = (hari_tercover / target_hari * 100) if target_hari > 0 else 0
    print(f"[SCHEDULER] Kelengkapan data Q{prev_q} {prev_y}: {hari_tercover}/{target_hari} hari ({pct:.1f}%)")
    
    # 3. Cek Timeout (45 hari sejak awal kuartal ini)
    start_of_curr_q = datetime(start_y, start_m, 1)
    days_elapsed = (today - start_of_curr_q).days
    
    is_data_gap = False
    is_retrained = False
    
    if pct >= 80.0:
        print("[SCHEDULER] Syarat >= 80% terpenuhi. Melakukan NORMAL RUN.")
        is_retrained = True
        # [BUGFIX] Skip retrain jika data historis sebelum kuartal ini < 6 bulan
        # (terlalu sedikit untuk membuat model yang reliable).
        # Kondisi ini menggantikan hardcode "Q1 2026" agar berlaku universal.
        with engine.connect() as conn:
            hist_count = conn.execute(
                text("SELECT COUNT(DISTINCT CAST(period AS VARCHAR(7))) FROM dbo.vending_training_ml WHERE CAST(period AS VARCHAR(7)) < :m"),
                {"m": first_month_str}
            ).scalar() or 0
        if hist_count < 6:
            print(f"[SCHEDULER] Data historis terlalu sedikit ({hist_count} bulan < 6). SKIP retrain.")
            is_retrained = False

    else:
        if days_elapsed >= 45:
            print(f"[SCHEDULER] TIMEOUT! Sudah {days_elapsed} hari (>= 45) sejak Q{curr_q} dimulai.")
            print("[SCHEDULER] Melakukan FORCE RUN (is_data_gap=True, SKIP retrain).")
            is_data_gap = True
            is_retrained = False
        else:
            print(f"[SCHEDULER] Belum timeout ({days_elapsed}/45 hari). Menunggu hari esok.")
            notif_service.info("QUARTERLY", f"Menunggu data Q{prev_q} {prev_y}", f"Data baru {pct:.1f}%. Menunggu hingga 80% atau timeout.")
            return "WAITING"
            
    # 4. Retrain jika perlu
    if is_retrained:
        try:
            print(f"\n[SCHEDULER] >>> Menjalankan RETRAIN sebelum prediksi (exclude parsial >= {first_month_str})...")
            res_retrain = run_retrain(exclude_month_and_beyond=first_month_str)
            if res_retrain.get("status") == "success":
                notif_service.success("RETRAIN", f"Retrain Q{curr_q} Berhasil", f"MAPE: {res_retrain.get('mape')}%")
            else:
                notif_service.error("RETRAIN", f"Retrain Q{curr_q} Gagal", res_retrain.get("error"))
        except Exception as e:
            print(f"[SCHEDULER] Error Retrain: {e}")
            notif_service.error_from_exception("RETRAIN", f"Error Retrain Q{curr_q}", e)
            
    # 5. Generate Forecast untuk kuartal ini
    try:
        print(f"\n[SCHEDULER] >>> Menjalankan CHAIN PREDICTION untuk Q{curr_q} {curr_y}...")
        end_m = start_m + 2
        # Panggil fungsi generate_forecast
        res_fc = generate_forecast(
            start_year=start_y, 
            start_month=start_m, 
            end_year=start_y, 
            end_month=end_m,
            is_data_gap=is_data_gap,
            is_retrained=is_retrained
        )
        
        # Smart Insight: ambil dari hasil generate_forecast (dinamis, tidak hardcode)
        smart_summary = res_fc.get("smart_insight", {}).get("summary", f"{len(res_fc.get('months_predicted', []))} bulan selesai diprediksi.")
        if is_data_gap:
            notif_service.warning("QUARTERLY", f"Prediksi Q{curr_q} {curr_y} DENGAN GAP", f"[FORCE RUN - timeout 45 hari] {smart_summary}")
        else:
            notif_service.success("QUARTERLY", f"Prediksi Q{curr_q} {curr_y} NORMAL", smart_summary)
            
        print("[SCHEDULER] Proses Quarterly Run Selesai!")
        return "SUCCESS"
    except Exception as e:
        print(f"[SCHEDULER] Error Forecast: {e}")
        notif_service.error_from_exception("QUARTERLY", f"Error Forecast Q{curr_q}", e)
        return "ERROR"
