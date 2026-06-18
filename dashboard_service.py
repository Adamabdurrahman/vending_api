import datetime
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_shift_filter_sql(db: Session, shift_id: str, alias: str = ""):
    """
    Mengambil jam_mulai dan jam_akhir dari dbo.master_settime
    dan membuat klausa SQL filter berdasarkan update_time dengan dukungan alias tabel.
    """
    if not shift_id or shift_id == "ALL":
        return "", {}
    
    # Query shift time range
    query = """
        SELECT jam_mulai, jam_akhir 
        FROM dbo.master_settime 
        WHERE id_recnum_mst = :shift_id AND status_active = '1'
    """
    row = db.execute(text(query), {"shift_id": shift_id}).fetchone()
    if not row:
        return "", {}
        
    jam_mulai = row[0]
    jam_akhir = row[1]
    
    prefix = f"{alias}." if alias else ""
    
    # Jika overnight shift (misal start 23:00, end 01:00)
    if jam_mulai > jam_akhir:
        filter_sql = f" AND (CAST({prefix}update_time AS TIME) >= :jam_mulai OR CAST({prefix}update_time AS TIME) <= :jam_akhir)"
    else:
        filter_sql = f" AND CAST({prefix}update_time AS TIME) >= :jam_mulai AND CAST({prefix}update_time AS TIME) <= :jam_akhir"
        
    return filter_sql, {"jam_mulai": jam_mulai, "jam_akhir": jam_akhir}


def get_metrics_data(db: Session, start_date_str: str, end_date_str: str, shift_id: str):
    """
    Menghitung data untuk 4 kartu metrik utama di Dashboard:
    Taken, Failed, Restock, dan Taken Today dengan perbandingan mirror period.
    """
    # Parse dates
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)
    
    # Calculate duration
    duration = (end_date - start_date).days + 1
    
    # Mirror previous period
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=duration - 1)
    
    # Datetime range bounds
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)
    
    prev_start_dt = datetime.datetime.combine(prev_start_date, datetime.time.min)
    prev_end_dt = datetime.datetime.combine(prev_end_date, datetime.time.max)
    
    # Shift filter
    shift_sql, shift_params = get_shift_filter_sql(db, shift_id)
    
    # Define generic fetch helpers
    def get_count(kategori, s_dt, e_dt):
        sql = f"""
            SELECT COUNT(*) 
            FROM dbo.monitor_log_datatransaksi 
            WHERE kategori_transaksi = :kat 
              AND update_time >= :s_dt AND update_time <= :e_dt
              {shift_sql}
        """
        params = {"kat": kategori, "s_dt": s_dt, "e_dt": e_dt, **shift_params}
        return db.execute(text(sql), params).scalar() or 0

    def get_sum_qty(kategori, s_dt, e_dt):
        sql = f"""
            SELECT SUM(qty) 
            FROM dbo.monitor_log_datatransaksi 
            WHERE kategori_transaksi = :kat 
              AND update_time >= :s_dt AND update_time <= :e_dt
              {shift_sql}
        """
        params = {"kat": kategori, "s_dt": s_dt, "e_dt": e_dt, **shift_params}
        return db.execute(text(sql), params).scalar() or 0

    def calc_change_pct(curr, prev):
        if prev == 0:
            return "+100.0%" if curr > 0 else "0.0%"
        change = ((curr - prev) / prev) * 100
        return f"{change:+.1f}%"

    def is_positive_change(change_str):
        if change_str.startswith("-"):
            return False
        return True

    # 1. Orders (Taken)
    curr_orders = get_count("ambil", start_dt, end_dt)
    prev_orders = get_count("ambil", prev_start_dt, prev_end_dt)
    orders_change = calc_change_pct(curr_orders, prev_orders)
    
    # 2. Revenue (Failed)
    curr_failed = get_count("transaksigagal", start_dt, end_dt)
    prev_failed = get_count("transaksigagal", prev_start_dt, prev_end_dt)
    failed_change = calc_change_pct(curr_failed, prev_failed)
    
    # 3. AveragePrice (Restock)
    curr_restock = get_sum_qty("stocking", start_dt, end_dt)
    prev_restock = get_sum_qty("stocking", prev_start_dt, prev_end_dt)
    restock_change = calc_change_pct(curr_restock, prev_restock)
    
    # 4. ProductSold (Taken Today)
    today = datetime.date.today()
    yesterday = today - timedelta(days=1)
    now = datetime.datetime.now()
    
    today_start = datetime.datetime.combine(today, datetime.time.min)
    today_end = now
    
    yesterday_start = datetime.datetime.combine(yesterday, datetime.time.min)
    yesterday_end = now - timedelta(days=1)
    
    today_taken = get_count("ambil", today_start, today_end)
    yesterday_taken = get_count("ambil", yesterday_start, yesterday_end)
    today_change = calc_change_pct(today_taken, yesterday_taken)
    
    return {
        "orders": {
            "title": "TAKEN (SUSU DIAMBIL)",
            "value": f"{curr_orders:,}",
            "change": orders_change,
            "is_positive": is_positive_change(orders_change),
            "icon": "fa-cart-shopping"
        },
        "revenue": {
            "title": "TRANSAKSI GAGAL",
            "value": f"{curr_failed:,}",
            "change": failed_change,
            "is_positive": not is_positive_change(failed_change),  # Penurunan kegagalan adalah hal yang positif
            "icon": "fa-xmark"
        },
        "averagePrice": {
            "title": "RESTOCK",
            "value": f"{curr_restock:,}",
            "change": restock_change,
            "is_positive": is_positive_change(restock_change),
            "icon": "fa-rotate-right"
        },
        "productSold": {
            "title": "TAKEN TODAY",
            "value": f"{today_taken:,}",
            "change": today_change,
            "is_positive": is_positive_change(today_change),
            "icon": "fa-bag-shopping"
        }
    }


def get_consumption_chart(db: Session, start_date_str: str, end_date_str: str, shift_id: str):
    """
    Menyediakan data trend konsumsi harian untuk Line Chart.
    """
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)
    
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)
    
    shift_sql, shift_params = get_shift_filter_sql(db, shift_id)
    
    sql = f"""
        SELECT CAST(update_time AS DATE) as tanggal, COUNT(*) as jumlah
        FROM dbo.monitor_log_datatransaksi
        WHERE kategori_transaksi = 'ambil'
          AND update_time >= :start_dt AND update_time <= :end_dt
          {shift_sql}
        GROUP BY CAST(update_time AS DATE)
        ORDER BY CAST(update_time AS DATE) ASC
    """
    
    params = {"start_dt": start_dt, "end_dt": end_dt, **shift_params}
    rows = db.execute(text(sql), params).fetchall()
    
    labels = []
    data = []
    
    most_val = -1
    most_date = None
    least_val = 999999999
    least_date = None
    
    for row in rows:
        tgl = row[0]
        jumlah = row[1]
        
        label = tgl.strftime("%d %b")
        labels.append(label)
        data.append(jumlah)
        
        if jumlah > most_val:
            most_val = jumlah
            most_date = tgl.strftime("%d %b %Y")
            
        if jumlah < least_val:
            least_val = jumlah
            least_date = tgl.strftime("%d %b %Y")
            
    most_obj = {"date": most_date, "count": most_val} if most_date else None
    least_obj = {"date": least_date, "count": least_val} if least_date else None
    
    return {
        "labels": labels,
        "data": data,
        "most": most_obj,
        "least": least_obj
    }


def get_sales_analytics(db: Session, start_date_str: str, end_date_str: str, shift_id: str):
    """
    Menyediakan proporsi konsumsi per varian untuk Doughnut Chart.
    """
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)
    
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)
    
    shift_sql, shift_params = get_shift_filter_sql(db, shift_id, alias="m")
    
    sql = f"""
        SELECT 
            ISNULL(v.nama_variant, 'Unknown') as nama_variant,
            COUNT(*) as jumlah
        FROM dbo.monitor_log_datatransaksi m
        LEFT JOIN dbo.manage_map_slot_number map 
          ON m.id_recnum_mav = map.id_recnum_mav 
          AND SUBSTRING(m.slot_number, 1, 1) = map.slot_name
        LEFT JOIN dbo.master_variant v 
          ON map.id_recnum_variant = v.id_recnum_variant
        WHERE m.kategori_transaksi = 'ambil'
          AND m.update_time >= :start_dt AND m.update_time <= :end_dt
          {shift_sql}
        GROUP BY v.nama_variant
    """
    
    params = {"start_dt": start_dt, "end_dt": end_dt, **shift_params}
    rows = db.execute(text(sql), params).fetchall()
    
    labels = []
    data = []
    for row in rows:
        labels.append(row[0])
        data.append(row[1])
        
    return {
        "labels": labels,
        "data": data
    }


def get_latest_transactions(db: Session, start_date_str: str, end_date_str: str, shift_id: str):
    """
    Menampilkan daftar 10 transaksi terbaru (kategori: ambil / transaksigagal).
    """
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)
    
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)
    
    shift_sql, shift_params = get_shift_filter_sql(db, shift_id)
    
    sql = f"""
        SELECT TOP 10 
            rfid,
            update_time,
            kategori_transaksi
        FROM dbo.monitor_log_datatransaksi
        WHERE kategori_transaksi IN ('ambil', 'transaksigagal')
          AND update_time >= :start_dt AND update_time <= :end_dt
          {shift_sql}
        ORDER BY update_time DESC
    """
    
    params = {"start_dt": start_dt, "end_dt": end_dt, **shift_params}
    rows = db.execute(text(sql), params).fetchall()
    
    results = []
    for row in rows:
        rfid = row[0]
        update_time = row[1]
        kategori = row[2]
        
        status_str = "Berhasil" if kategori == "ambil" else "Gagal"
        timestamp_str = update_time.strftime("%d/%m/%Y %H:%M:%S") if update_time else ""
        
        results.append({
            "rfid": rfid,
            "timestamp": timestamp_str,
            "status": status_str,
            "kategori": kategori
        })
        
    return results


# ========================================================
# KUMPULAN LOGIKA UNTUK PREDICTION DASHBOARD
# ========================================================

INDONESIAN_MONTHS = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

def get_prediction_summary(db: Session, year: int, quarter: int):
    """
    Menyediakan data ringkasan performa model ML (Akurasi, Prediksi Bulanan, Perbandingan, dan Insight).
    """
    m1_num = (quarter - 1) * 3 + 1
    m2_num = (quarter - 1) * 3 + 2
    m3_num = (quarter - 1) * 3 + 3
    
    m1 = f"{year}-{m1_num:02d}"
    m2 = f"{year}-{m2_num:02d}"
    m3 = f"{year}-{m3_num:02d}"
    
    prev_m1, prev_m2, prev_m3 = "", "", ""
    show_comparison = quarter > 1
    if show_comparison:
        prev_m1 = f"{year}-{(quarter - 2) * 3 + 1:02d}"
        prev_m2 = f"{year}-{(quarter - 2) * 3 + 2:02d}"
        prev_m3 = f"{year}-{(quarter - 2) * 3 + 3:02d}"
        
    sql_layer1 = """
        SELECT PredictedMonth, MAPE_Total, TotalDemand, ErrorPercent
        FROM dbo.ForecastResults_Layer1
        WHERE PredictedMonth IN (:m1, :m2, :m3, :pm1, :pm2, :pm3)
    """
    params = {
        "m1": m1, "m2": m2, "m3": m3,
        "pm1": prev_m1 or "XXXX", "pm2": prev_m2 or "XXXX", "pm3": prev_m3 or "XXXX"
    }
    
    rows = db.execute(text(sql_layer1), params).fetchall()
    
    data_dict = {}
    for r in rows:
        data_dict[r[0]] = {
            "mape": r[1],
            "total_demand": r[2],
            "error_percent": r[3]
        }
        
    mapes = []
    total_prediction_sum = 0
    
    for month_str in [m1, m2, m3]:
        if month_str in data_dict and data_dict[month_str]["mape"] is not None:
            mapes.append(data_dict[month_str]["mape"])
        if month_str in data_dict and data_dict[month_str]["total_demand"] is not None:
            total_prediction_sum += data_dict[month_str]["total_demand"]
            
    accuracy = round(100.0 - (sum(mapes) / len(mapes)), 2) if mapes else 100.0
    
    months_resp = {}
    month_keys = [("month_1", m1, m1_num, prev_m1), ("month_2", m2, m2_num, prev_m2), ("month_3", m3, m3_num, prev_m3)]
    
    for key, month_str, m_num, pm_str in month_keys:
        month_data = data_dict.get(month_str, {"total_demand": 0, "error_percent": None})
        total_d = month_data.get("total_demand") or 0
        err_p = month_data.get("error_percent")
        
        diff_show = False
        diff_pct = 0.0
        diff_is_pos = True
        diff_demand_txt = "0"
        
        if show_comparison and pm_str:
            pm_data = data_dict.get(pm_str)
            if pm_data:
                pm_total = pm_data.get("total_demand") or 0
                diff_show = True
                diff_val = total_d - pm_total
                diff_is_pos = diff_val >= 0
                diff_demand_txt = f"{abs(diff_val):,}"
                diff_pct = round((abs(diff_val) / pm_total * 100.0), 1) if pm_total > 0 else 0.0
                
        months_resp[key] = {
            "month_name": INDONESIAN_MONTHS.get(m_num, ""),
            "total_demand": f"{total_d:,}",
            "error_percent": round(err_p, 1) if err_p is not None else None,
            "diff": {
                "show_diff": diff_show,
                "diff_percentage": diff_pct,
                "diff_is_positive": diff_is_pos,
                "diff_demand_text": diff_demand_txt
            }
        }
        
    q_label = f"Q{quarter}"
    sql_notif = """
        SELECT TOP 2 NotifType, Message
        FROM dbo.SystemNotifications
        WHERE Title LIKE :title_pat
        ORDER BY CreatedAt DESC
    """
    notifs = db.execute(text(sql_notif), {"title_pat": f"%{q_label}%"}).fetchall()
    
    accuracy_notif = f"Akurasi model XGBoost kuartal ini stabil di {accuracy:.1f}%."
    model_text = "Model V6+ aktif menggunakan XGBoost Regressor."
    
    if len(notifs) >= 1:
        accuracy_notif = notifs[0][1]
    if len(notifs) >= 2:
        model_text = notifs[1][1]
        
    return {
        "accuracy": accuracy,
        "current_year": year,
        "current_quarter": quarter,
        "show_comparison": show_comparison,
        "months": months_resp,
        "insights": {
            "accuracy_notif": accuracy_notif,
            "model_text": model_text,
            "total_prediction": f"{total_prediction_sum:,}"
        }
    }


def get_variant_errors(db: Session, year: int, quarter: int):
    """
    Menyediakan persentase error per varian susu per bulan dalam kuartal.
    """
    m1_num = (quarter - 1) * 3 + 1
    m2_num = (quarter - 1) * 3 + 2
    m3_num = (quarter - 1) * 3 + 3
    
    m1 = f"{year}-{m1_num:02d}"
    m2 = f"{year}-{m2_num:02d}"
    m3 = f"{year}-{m3_num:02d}"
    
    sql = """
        SELECT 
            Variant,
            PredictedMonth,
            ISNULL(SUM(PredictedDemand), 0) AS TotalPred,
            ISNULL(SUM(ActualDemand), 0) AS TotalAct
        FROM dbo.ForecastResults_Layer2
        WHERE PredictedMonth IN (:m1, :m2, :m3)
        GROUP BY Variant, PredictedMonth
        ORDER BY Variant, PredictedMonth
    """
    rows = db.execute(text(sql), {"m1": m1, "m2": m2, "m3": m3}).fetchall()
    
    variant_data = {}
    for r in rows:
        var_name = r[0]
        month_str = r[1]
        pred = r[2]
        act = r[3]
        
        error = round(((pred - act) / act * 100.0), 1) if act > 0 else None
        abs_error = abs(error) if error is not None else None
        
        if var_name not in variant_data:
            variant_data[var_name] = {}
            
        variant_data[var_name][month_str] = {
            "error": error,
            "abs_error": abs_error
        }
        
    results = []
    for var, months_info in variant_data.items():
        results.append({
            "variant_name": var,
            "month_1_error": months_info.get(m1, {}).get("error"),
            "month_1_abs_error": months_info.get(m1, {}).get("abs_error"),
            "month_2_error": months_info.get(m2, {}).get("error"),
            "month_2_abs_error": months_info.get(m2, {}).get("abs_error"),
            "month_3_error": months_info.get(m3, {}).get("error"),
            "month_3_abs_error": months_info.get(m3, {}).get("abs_error")
        })
        
    return results


def get_shift_errors(db: Session, year: int, quarter: int):
    """
    Menyediakan persentase error mutlak per shift kerja per bulan dalam kuartal.
    """
    m1_num = (quarter - 1) * 3 + 1
    m2_num = (quarter - 1) * 3 + 2
    m3_num = (quarter - 1) * 3 + 3
    
    m1 = f"{year}-{m1_num:02d}"
    m2 = f"{year}-{m2_num:02d}"
    m3 = f"{year}-{m3_num:02d}"
    
    sql = """
        SELECT 
            Shift,
            PredictedMonth,
            ISNULL(SUM(PredictedDemand), 0) AS TotalPred,
            ISNULL(SUM(ActualDemand), 0) AS TotalAct
        FROM dbo.ForecastResults_Layer2
        WHERE PredictedMonth IN (:m1, :m2, :m3)
        GROUP BY Shift, PredictedMonth
        ORDER BY Shift, PredictedMonth
    """
    rows = db.execute(text(sql), {"m1": m1, "m2": m2, "m3": m3}).fetchall()
    
    shift_data = {}
    for r in rows:
        shift_name = r[0]
        month_str = r[1]
        pred = r[2]
        act = r[3]
        
        abs_error = round((abs(pred - act) / act * 100.0), 1) if act > 0 else None
        
        if shift_name not in shift_data:
            shift_data[shift_name] = {}
            
        shift_data[shift_name][month_str] = abs_error
        
    results = []
    for s_name, months_info in shift_data.items():
        results.append({
            "shift_name": s_name,
            "month_1_abs_error": months_info.get(m1),
            "month_2_abs_error": months_info.get(m2),
            "month_3_abs_error": months_info.get(m3)
        })
        
    return results


def get_daily_logs(db: Session, year: int, quarter: int):
    """
    Menyediakan 30 log harian teratas per bulan dalam kuartal (actual vs predicted).
    """
    m1_num = (quarter - 1) * 3 + 1
    m2_num = (quarter - 1) * 3 + 2
    m3_num = (quarter - 1) * 3 + 3
    
    m1 = f"{year}-{m1_num:02d}"
    m2 = f"{year}-{m2_num:02d}"
    m3 = f"{year}-{m3_num:02d}"
    
    sql = """
        WITH RankedLogs AS (
            SELECT 
                PredictedMonth,
                [Date],
                Shift,
                Variant,
                ISNULL(ActualDemand, 0) AS ActualDemand,
                ISNULL(PredictedDemand, 0) AS PredictedDemand,
                ROW_NUMBER() OVER(PARTITION BY PredictedMonth ORDER BY [Date] ASC, Shift ASC) as rn
            FROM dbo.ForecastResults_Layer2
            WHERE PredictedMonth IN (:m1, :m2, :m3)
        )
        SELECT 
            PredictedMonth,
            [Date],
            Shift,
            Variant,
            ActualDemand,
            PredictedDemand
        FROM RankedLogs
        WHERE rn <= 30
        ORDER BY PredictedMonth ASC, [Date] ASC
    """
    rows = db.execute(text(sql), {"m1": m1, "m2": m2, "m3": m3}).fetchall()
    
    results = []
    for r in rows:
        month_str = r[0]
        dt = r[1]
        shift = r[2]
        variant = r[3]
        act = r[4]
        pred = r[5]
        
        diff = abs(act - pred)
        pct_err = (diff / act * 100.0) if act > 0 else 0.0
        
        is_close = (pct_err < 20.0) or (diff <= 8)
        
        dt_val = datetime.date.fromisoformat(str(dt)) if isinstance(dt, str) else dt
        date_str_formatted = dt_val.strftime("%d %b %Y") if dt_val else ""
        
        results.append({
            "predicted_month": month_str,
            "date": str(dt_val) if dt_val else "",
            "date_string": date_str_formatted,
            "shift_name": shift,
            "variant_name": variant,
            "actual_demand": act,
            "predicted_demand": pred,
            "is_close": is_close
        })
        
    return results


def get_chart_data(db: Session, year: int, quarter: int):
    """
    Menyediakan dataset line chart raksasa (27 deret data).
    """
    m1_num = (quarter - 1) * 3 + 1
    m2_num = (quarter - 1) * 3 + 2
    m3_num = (quarter - 1) * 3 + 3
    
    m1 = f"{year}-{m1_num:02d}"
    m2 = f"{year}-{m2_num:02d}"
    m3 = f"{year}-{m3_num:02d}"
    
    sql = """
        SELECT 
            [Date],
            ISNULL(SUM(PredictedDemand), 0) AS TotalPred,
            ISNULL(SUM(ActualDemand), 0) AS TotalAct,
            
            ISNULL(SUM(CASE WHEN Variant = 'Coklat' THEN PredictedDemand ELSE 0 END), 0) AS PredCoklat,
            ISNULL(SUM(CASE WHEN Variant = 'Coklat' THEN ActualDemand ELSE 0 END), 0) AS ActCoklat,
            ISNULL(SUM(CASE WHEN Variant = 'Strawberry' THEN PredictedDemand ELSE 0 END), 0) AS PredStrawberry,
            ISNULL(SUM(CASE WHEN Variant = 'Strawberry' THEN ActualDemand ELSE 0 END), 0) AS ActStrawberry,
            ISNULL(SUM(CASE WHEN Variant = 'Moca' THEN PredictedDemand ELSE 0 END), 0) AS PredMoca,
            ISNULL(SUM(CASE WHEN Variant = 'Moca' THEN ActualDemand ELSE 0 END), 0) AS ActMoca,
            ISNULL(SUM(CASE WHEN Variant = 'Original (Putih)' THEN PredictedDemand ELSE 0 END), 0) AS PredOriginal,
            ISNULL(SUM(CASE WHEN Variant = 'Original (Putih)' THEN ActualDemand ELSE 0 END), 0) AS ActOriginal,

            ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS1Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS1Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS1Akhir,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS1Akhir,

            ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS2Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS2Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS2Akhir,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS2Akhir,

            ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS3Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS3Awal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS3Akhir,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS3Akhir,

            ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredSPutihAwal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActSPutihAwal,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredSPutihAkhir,
            ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActSPutihAkhir
        FROM dbo.ForecastResults_Layer2
        WHERE PredictedMonth IN (:m1, :m2, :m3)
        GROUP BY [Date]
        ORDER BY [Date] ASC
    """
    rows = db.execute(text(sql), {"m1": m1, "m2": m2, "m3": m3}).fetchall()
    
    labels = []
    
    total_pred, total_act = [], []
    coklat_pred, coklat_act = [], []
    strawberry_pred, strawberry_act = [], []
    moca_pred, moca_act = [], []
    original_pred, original_act = [], []
    
    s1_awal_pred, s1_awal_act = [], []
    s1_akhir_pred, s1_akhir_act = [], []
    s2_awal_pred, s2_awal_act = [], []
    s2_akhir_pred, s2_akhir_act = [], []
    s3_awal_pred, s3_awal_act = [], []
    s3_akhir_pred, s3_akhir_act = [], []
    s_putih_awal_pred, s_putih_awal_act = [], []
    s_putih_akhir_pred, s_putih_akhir_act = [], []
    
    for r in rows:
        dt = r[0]
        dt_val = datetime.date.fromisoformat(str(dt)) if isinstance(dt, str) else dt
        labels.append(str(dt_val) if dt_val else "")
        
        total_pred.append(int(r[1]))
        total_act.append(int(r[2]))
        
        coklat_pred.append(int(r[3]))
        coklat_act.append(int(r[4]))
        
        strawberry_pred.append(int(r[5]))
        strawberry_act.append(int(r[6]))
        
        moca_pred.append(int(r[7]))
        moca_act.append(int(r[8]))
        
        original_pred.append(int(r[9]))
        original_act.append(int(r[10]))
        
        s1_awal_pred.append(int(r[11]))
        s1_awal_act.append(int(r[12]))
        
        s1_akhir_pred.append(int(r[13]))
        s1_akhir_act.append(int(r[14]))
        
        s2_awal_pred.append(int(r[15]))
        s2_awal_act.append(int(r[16]))
        
        s2_akhir_pred.append(int(r[17]))
        s2_akhir_act.append(int(r[18]))
        
        s3_awal_pred.append(int(r[19]))
        s3_awal_act.append(int(r[20]))
        
        s3_akhir_pred.append(int(r[21]))
        s3_akhir_act.append(int(r[22]))
        
        s_putih_awal_pred.append(int(r[23]))
        s_putih_awal_act.append(int(r[24]))
        
        s_putih_akhir_pred.append(int(r[25]))
        s_putih_akhir_act.append(int(r[26]))
        
    return {
        "labels": labels,
        "total": {
            "predicted": total_pred,
            "actual": total_act
        },
        "variants": {
            "coklat": {
                "predicted": coklat_pred,
                "actual": coklat_act
            },
            "strawberry": {
                "predicted": strawberry_pred,
                "actual": strawberry_act
            },
            "moca": {
                "predicted": moca_pred,
                "actual": moca_act
            },
            "original": {
                "predicted": original_pred,
                "actual": original_act
            }
        },
        "shifts": {
            "s1_awal": {
                "predicted": s1_awal_pred,
                "actual": s1_awal_act
            },
            "s1_akhir": {
                "predicted": s1_akhir_pred,
                "actual": s1_akhir_act
            },
            "s2_awal": {
                "predicted": s2_awal_pred,
                "actual": s2_awal_act
            },
            "s2_akhir": {
                "predicted": s2_akhir_pred,
                "actual": s2_akhir_act
            },
            "s3_awal": {
                "predicted": s3_awal_pred,
                "actual": s3_awal_act
            },
            "s3_akhir": {
                "predicted": s3_akhir_pred,
                "actual": s3_akhir_act
            },
            "s_putih_awal": {
                "predicted": s_putih_awal_pred,
                "actual": s_putih_awal_act
            },
            "s_putih_akhir": {
                "predicted": s_putih_akhir_pred,
                "actual": s_putih_akhir_act
            }
        }
    }

