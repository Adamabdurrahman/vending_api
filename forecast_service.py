"""
forecast_service.py
================================================================================
Orchestrator tipis untuk menjalankan prediksi Layer 1 + Layer 2.
TIDAK menduplikasi logika — semua di-import dari ProductionML/ (source of truth).

Source of Truth:
  - Layer 1: ProductionML/Layer1_Core.py
  - Layer 2: ProductionML/Script_production_daily_2_prod_v2.py
  - Kalender: ProductionML/Script_SqlCalendar.py

Yang dilakukan file ini:
  1. Menerima parameter range bulan (start -> end)
  2. Import fungsi dari ProductionML/
  3. Jalankan chain prediction (Layer 1 -> Layer 2) per bulan
  4. Simpan hasil ke SQL Server (ForecastResults_Layer1 & Layer2)
================================================================================
"""

import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text

from database import engine

warnings.filterwarnings("ignore")

# Path ke folder ProductionML agar bisa import module dari sana
_PROD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ProductionML")
sys.path.insert(0, _PROD_DIR)

# ── IMPORT DARI SOURCE OF TRUTH ──────────────────────────────────────────────
# Import via package path agar IDE (Pyright/Pylance) bisa resolve module.
# Kemudian register sebagai "Layer1_Core" di sys.modules agar joblib
# artifact bisa deserialize class reference "Layer1_Core.Layer1Model" dengan benar.
import ProductionML.Layer1_Core

sys.modules["Layer1_Core"] = ProductionML.Layer1_Core
from ProductionML.Layer1_Core import Layer1Model
from ProductionML.Script_production_daily_2_prod_v2 import (
    RAMADAN_CONFIG,
    build_dow_share_profile,
    build_shift_profile,
    distribute_with_dow_profile,
    fetch_calendar_from_sql,
    print_kpi_scorecard,
    translate_to_layer1_calendar,
)

# ── KONFIGURASI LOKAL (hanya path artifact) ──────────────────────────────────
ARTIFACT_PATH = os.path.join(_PROD_DIR, "Layer1_XGBoost_V6_Artifact.joblib")


# ==============================================================================
# FUNGSI UTAMA: generate_forecast (dipanggil oleh endpoint API)
# ==============================================================================
def generate_forecast(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    is_data_gap: bool = False,
    is_retrained: bool = False,
):
    """
    Generate prediksi masa depan dari bulan/tahun awal hingga bulan/tahun akhir (inklusif).
    Menggunakan konsep Chain Prediction (prediksi bulan ini menjadi lag bulan depan).
    """
    # [SATPAM DATA COMPLETENESS] Cek apakah data bulan lalu sudah masuk via ETL
    prev_month = start_month - 1 if start_month > 1 else 12
    prev_year = start_year if start_month > 1 else start_year - 1
    with engine.connect() as conn:
        # Pengecekan kelengkapan hari (Ide Brilian User)
        cek_data = conn.execute(
            text("""
                SELECT
                    COUNT(DISTINCT CAST(tanggal AS DATE)) as total_hari_ada,
                    MAX(DAY(tanggal)) as hari_terakhir
                FROM dbo.Vending_Aggregrated
                WHERE YEAR(tanggal) = :y AND MONTH(tanggal) = :m
            """),
            {"y": prev_year, "m": prev_month},
        ).fetchone()

        # [BUGFIX] Ambil total hari produktif (non-Ramadan & hari kerja) di bulan tersebut
        cal_ref = conn.execute(
            text(
                "SELECT COUNT(Date) FROM dbo.OperationalCalendar WHERE YEAR(Date) = :y AND MONTH(Date) = :m AND IsRamadan = 0 AND IsWorkingDay = 1"
            ),
            {"y": prev_year, "m": prev_month},
        ).scalar()

        total_hari_ada = cek_data[0] if cek_data[0] else 0
        hari_terakhir = cek_data[1] if cek_data[1] else 0
        target_hari = cal_ref if cal_ref and cal_ref > 0 else 0

        # Toleransi Pabrik: Kita pastikan data terekam setidaknya 80% dari target hari produktif.
        # [BUGFIX] Khusus untuk bulan dengan target hari produktif sangat sedikit (<= 10 hari),
        # yang biasanya adalah bulan puncak Ramadan (seperti Maret 2026), kita lewati pengecekan
        # ini. Karena Lag Skipper akan mengabaikan bulan ini, dan tidak masuk akal memblokir 
        # prediksi kuartal berikutnya hanya karena kehilangan data di 2 hari produktif.
        if target_hari > 10 and total_hari_ada < (target_hari * 0.8):
            if is_data_gap:
                print(
                    f"[SATPAM] PERINGATAN: Data historis bulan lalu ({prev_year}-{prev_month:02d}) TIDAK LENGKAP "
                    f"({total_hari_ada}/{target_hari} hari). Namun karena is_data_gap=True (Timeout 45 hari), "
                    f"Satpam mengizinkan proses tetap berjalan secara paksa."
                )
            else:
                raise ValueError(
                    f"[SATPAM] Prediksi {start_year}-{start_month:02d} DITOLAK: Data historis bulan lalu ({prev_year}-{prev_month:02d}) "
                    f"TIDAK LENGKAP! Hanya tercatat {total_hari_ada} hari dari {target_hari} hari produktif. "
                    f"Sistem membutuhkan minimal 80% kelengkapan data agar Lag XGBoost akurat."
                )

    print("\n" + "=" * 50)
    run_timestamp = datetime.now()

    # Bangun daftar bulan
    target_months = []
    y, m = start_year, start_month
    while (y < end_year) or (y == end_year and m <= end_month):
        target_months.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1

    print(f"[FORECAST] Chain Prediction: {target_months}")

    # 1. Load Layer 1 artifact
    print("[FORECAST] Loading Layer 1 artifact...")
    layer1_model = Layer1Model.load_model(ARTIFACT_PATH)

    # 2. Load historical data dari SQL
    print("[FORECAST] Loading data historis dari Vending_Aggregrated (SQL)...")
    df_daily_hist = pd.read_sql("SELECT * FROM dbo.Vending_Aggregrated", engine)
    df_daily_hist["tanggal"] = pd.to_datetime(df_daily_hist["tanggal"])

    # Tambahkan kolom yang dibutuhkan Layer 2 jika belum ada
    if "is_ramadan" not in df_daily_hist.columns:
        df_daily_hist["is_ramadan"] = 0
        for yr_cfg, cfg in RAMADAN_CONFIG.items():
            mask = (df_daily_hist["tanggal"] >= cfg["start"]) & (
                df_daily_hist["tanggal"] <= cfg["end"]
            )
            df_daily_hist.loc[mask, "is_ramadan"] = 1
    if "is_weekend" not in df_daily_hist.columns:
        df_daily_hist["is_weekend"] = (
            df_daily_hist["tanggal"].dt.dayofweek >= 5
        ).astype(int)

    print(f"  Data historis: {len(df_daily_hist):,} baris")

    # [TIME MACHINE SIMULATION]
    # Agar hasil prediksi yang di-run secara telat (misal: di bulan Mei)
    # 100% konsisten dengan prediksi yang seharusnya di-run pada 1 Januari,
    # kita potong paksa histori data HANYA sampai tepat sebelum start_month.
    start_date = pd.Timestamp(start_year, start_month, 1)
    df_daily_hist = df_daily_hist[df_daily_hist["tanggal"] < start_date]
    print(f"  Data historis (setelah dipotong per {start_date.date()}): {len(df_daily_hist):,} baris")

    # [BUGFIX] Shift Profile dibangun SEKALI di awal menggunakan data yang sudah dipotong.
    # Profil ini digunakan untuk seluruh bulan di kuartal ini.
    shift_profile = build_shift_profile(df_daily_hist)

    # 4. CHAIN PREDICTION
    fwd_cache = {}
    
    # [BUGFIX] Pre-load fwd_cache dari ForecastResults_Layer1 agar Chain tidak terputus
    # saat mengeksekusi kuartal di tengah-tengah.
    try:
        with engine.connect() as conn:
            prev_preds = conn.execute(text(
                "SELECT PredictedMonth, DemandCoklat, DemandMoca, DemandOriginal, DemandStrawberry "
                "FROM dbo.ForecastResults_Layer1"
            )).fetchall()
            for r in prev_preds:
                fwd_cache[r[0]] = {
                    "Coklat": r[1],
                    "Moca": r[2],
                    "Original (Putih)": r[3],
                    "Strawberry": r[4]
                }
    except Exception as e:
        print(f"[FORECAST] Gagal meload fwd_cache dari database: {e}")
        
    all_results = []

    for month_str in target_months:
        yr = int(month_str[:4])
        mn = int(month_str[5:7])
        print(f"\n--- Memproses {month_str} ---")

        # Kalender dari SQL
        ram_cfg = RAMADAN_CONFIG.get(yr, {})
        df_sql_cal = fetch_calendar_from_sql(
            yr,
            mn,
            ramadan_start=ram_cfg.get("start"),
            ramadan_end=ram_cfg.get("end"),
        )
        target_cal, df_cal = translate_to_layer1_calendar(df_sql_cal)
        print(
            f"  Kalender: working_days={target_cal['working_days']}, ramadan={target_cal['ramadan_days']}"
        )

        # Layer 1 (chain: pakai fwd_cache bulan sebelumnya)
        budget = layer1_model.predict(yr, mn, target_cal, fwd_cache=fwd_cache)
        fwd_cache[month_str] = budget["by_variant"]
        print(f"  Layer 1: {budget['pred_final']:,} kotak")

        # (Shift profile sudah dibangun 1x di luar loop)

        # DOW Profile
        dow_shares, weekday_avg, event_factors = build_dow_share_profile(
            df_daily_hist, yr, mn
        )

        # [BUGFIX] Step 9 Override: jika Business Logic aktif (bulan Ramadan ekstrem,
        # productive_milk_days <= 10), paksa ramadan_factor = 0.0 agar Layer 2
        # TIDAK membagi budget ke hari-hari Ramadan.
        # Dengan ini, seluruh budget 5,544 unit terkonsentrasi ke 2 hari produktif
        # (30-31 Maret), sesuai dengan apa yang Layer 1 maksudkan.
        if budget.get("business_logic", False):
            event_factors = dict(event_factors)  # copy agar tidak mutate original
            event_factors["ramadan"] = 0.0
            print(f"  [Step 9 Override] Ramadan event_factor diset 0.0 — budget terkonsentrasi ke {budget['productive_days']} hari produktif saja.")

        # Layer 2 Distribution
        df_layer2 = distribute_with_dow_profile(
            month_str=month_str,
            budget_dict=budget,
            dow_shares=dow_shares,
            weekday_avg=weekday_avg,
            event_factors=event_factors,
            shift_profile=shift_profile,
            ram_start=ram_cfg.get("start"),
            ram_end=ram_cfg.get("end"),
        )
        print(f"  Layer 2: {len(df_layer2):,} baris distribusi")

        # SAVE ke SQL: ForecastResults_Layer1
        metrics = layer1_model.metadata.get("performance_metrics", {})
        mape_pv = metrics.get("mape_per_variant", {})
        layer1_row = {
            "PredictedMonth": month_str,
            "RunTimestamp": run_timestamp,
            "ModelVersion": str(layer1_model.metadata.get("model_version", "V6+"))[:20],
            "TotalDemand": int(budget["pred_final"]),
            "DemandCoklat": int(budget["by_variant"].get("Coklat", 0)),
            "DemandMoca": int(budget["by_variant"].get("Moca", 0)),
            "DemandOriginal": int(budget["by_variant"].get("Original (Putih)", 0)),
            "DemandStrawberry": int(budget["by_variant"].get("Strawberry", 0)),
            "IsBusinessLogic": 1 if budget.get("business_logic", False) else 0,
            "ProductiveDays": target_cal.get("productive_milk_days"),
            "SmootherEnabled": 1,
            "MAPE_Total": metrics.get("mape"),
            "MAE_Total": metrics.get("mae"),
            "RMSE_Total": metrics.get("rmse"),
            "MAPE_Coklat": mape_pv.get("Coklat"),
            "MAPE_Moca": mape_pv.get("Moca"),
            "MAPE_Original": mape_pv.get("Original (Putih)"),
            "MAPE_Strawberry": mape_pv.get("Strawberry"),
            "is_data_gap": 1 if is_data_gap else 0,
            "is_retrained": 1 if is_retrained else 0,
        }
        pd.DataFrame([layer1_row]).to_sql(
            "ForecastResults_Layer1",
            engine,
            if_exists="append",
            index=False,
            schema="dbo",
        )

        # SAVE ke SQL: ForecastResults_Layer2
        df_l2_sql = pd.DataFrame(
            {
                "RunTimestamp": run_timestamp,
                "PredictedMonth": df_layer2["bulan"],
                "Date": df_layer2["tanggal"],
                "DayName": pd.to_datetime(df_layer2["tanggal"]).dt.day_name(),
                "Shift": df_layer2["shift"],
                "Variant": df_layer2["varian"],
                "PredictedDemand": df_layer2["demand_pred_int"],
                "IsHoliday": df_layer2["is_holiday"],
                "IsRamadan": df_layer2["is_ramadan"],
                "IsWeekend": df_layer2["is_weekend"],
            }
        )
        # [BUGFIX] Sorting agar data di database rapi secara kronologis
        df_l2_sql = df_l2_sql.sort_values(by=["Date", "Variant", "Shift"]).reset_index(drop=True)

        df_l2_sql.to_sql(
            "ForecastResults_Layer2",
            engine,
            if_exists="append",
            index=False,
            schema="dbo",
        )

        all_results.append(
            {
                "month": month_str,
                "total_demand": int(budget["pred_final"]),
                "by_variant": {k: int(v) for k, v in budget["by_variant"].items()},
                "rows_layer2": len(df_l2_sql),
                "is_business_logic": budget.get("business_logic", False),
            }
        )
        print(f"  [SQL] Saved -> ForecastResults_Layer1 & Layer2")

        # KPI Scorecard — hanya mencetak jika aktual sudah tersedia di SQL
        # Skip untuk bulan Ramadan ekstrem (Step 9 Business Logic):
        # terlalu sedikit hari produktif untuk evaluasi distribusi shift yang bermakna.
        if budget.get("business_logic", False):
            print(f"  [SCORECARD] Dilewati: bulan Ramadan ekstrem ({budget['productive_days']:.0f} hari produktif) — KPI Layer 2 tidak valid")
        else:
            try:
                print_kpi_scorecard(df_layer2, engine=engine)
            except Exception as sc_err:
                print(f"  [SCORECARD] Dilewati: {sc_err}")

    smart_insight = generate_smart_insight(all_results)
    result = {
        "status": "success",
        "months_predicted": target_months,
        "results": all_results,
        "total_rows_layer2": sum(r["rows_layer2"] for r in all_results),
        "run_timestamp": run_timestamp.isoformat(),
        "smart_insight": smart_insight,
    }
    print(f"\n[FORECAST] Selesai! {len(target_months)} bulan diprediksi.")
    print(f"[FORECAST] Smart Insight: {smart_insight['summary']}")
    return result


# ==============================================================================
# FUNGSI: generate_smart_insight
# ==============================================================================
def generate_smart_insight(all_results: list) -> dict:
    """
    Menganalisis hasil prediksi dan menghasilkan pesan notifikasi yang kontekstual.
    Semua analisis bersifat DINAMIS — tidak ada hardcode bulan/tahun tertentu.

    Trigger yang dideteksi otomatis:
      1. Business Logic (Ramadan ekstrem): "via Business Logic, hanya N hari produktif"
      2. Ramadan parsial: "-X% karena Ramadan (ramadan_days hari dari n_days)"
      3. Demand drop >20% vs bulan normal sebelumnya: "turun vs bulan sebelumnya"
      4. Seasonality: jika demand bulan ini < bulan sebelumnya tapi bukan Ramadan
         dan ada pola berulang di historis SQL → "pola historis N tahun"
      5. Recovery pasca-Ramadan: demand bulan ini > 3x bulan sebelumnya

    Returns:
      dict {
        "per_month": {month_str: insight_str},
        "summary": str  ← untuk SystemNotifications.Message
      }
    """
    if not all_results:
        return {"per_month": {}, "summary": "Tidak ada bulan yang diprediksi."}

    RAMADAN_MONTHS_SET = {
        "2023-03", "2023-04", "2024-03", "2024-04",
        "2025-03", "2026-02", "2026-03", "2027-02", "2027-03",
    }

    # ── Ambil konteks kalender dari SQL ──────────────────────────────────────
    months_str = [r["month"] for r in all_results]
    cal_info = {}  # {month_str: {ramadan_days, productive_days, n_days}}
    try:
        with engine.connect() as conn:
            for ms in months_str:
                yr, mn = int(ms[:4]), int(ms[5:7])
                row = conn.execute(text("""
                    SELECT
                        COUNT(*) AS n_days,
                        SUM(CAST(IsRamadan AS INT)) AS ramadan_days,
                        COUNT(CASE WHEN IsRamadan = 0 AND IsWorkingDay = 1 THEN 1 END) AS productive_days
                    FROM dbo.OperationalCalendar
                    WHERE YEAR(Date) = :y AND MONTH(Date) = :m
                """), {"y": yr, "m": mn}).fetchone()
                if row:
                    cal_info[ms] = {
                        "n_days": row[0] or 0,
                        "ramadan_days": row[1] or 0,
                        "productive_days": row[2] or 0,
                    }
    except Exception as e:
        print(f"  [INSIGHT] Gagal ambil kalender: {e}")

    # ── Ambil historis demand per bulan dari SQL (untuk seasonality) ─────────
    historical_by_month = {}  # {month_key "MM": [demand_list]}
    try:
        with engine.connect() as conn:
            hist = conn.execute(text("""
                SELECT CAST(period AS VARCHAR(7)) AS period_str,
                       SUM(demand) AS total_demand
                FROM dbo.vending_training_ml
                GROUP BY CAST(period AS VARCHAR(7))
                ORDER BY period_str
            """)).fetchall()
            for row in hist:
                ps = str(row[0])  # "YYYY-MM"
                mn_key = ps[5:7]  # "MM"
                if mn_key not in historical_by_month:
                    historical_by_month[mn_key] = []
                historical_by_month[mn_key].append(row[1])
    except Exception as e:
        print(f"  [INSIGHT] Gagal ambil historis: {e}")

    # ── Analisis per bulan ───────────────────────────────────────────────────
    per_month = {}
    total_q = sum(r["total_demand"] for r in all_results)
    demands = [r["total_demand"] for r in all_results]

    for i, res in enumerate(all_results):
        ms = res["month"]
        demand = res["total_demand"]
        is_bl = res.get("is_business_logic", False)
        cal = cal_info.get(ms, {})
        ram_days = cal.get("ramadan_days", 0)
        prod_days = cal.get("productive_days", 0)
        n_days = cal.get("n_days", 30)
        mn_key = ms[5:7]

        tags = []

        # Trigger 1 — Business Logic (Ramadan penuh / ekstrem)
        if is_bl:
            tags.append(f"via Business Logic ({prod_days:.0f} hari produktif, Ramadan penuh)")

        # Trigger 2 — Ramadan parsial (ada hari Ramadan tapi bukan ekstrem)
        elif ram_days > 0:
            pct_ram = ram_days / n_days * 100
            tags.append(f"Ramadan parsial ({ram_days} hari, {pct_ram:.0f}% bulan)")

        # Trigger 3 — Recovery pasca-Ramadan (demand bulan ini > 3x bulan sebelumnya)
        if i > 0 and demands[i - 1] > 0:
            ratio = demand / demands[i - 1]
            if ratio >= 2.5 and not is_bl:
                tags.append(f"recovery pasca-Ramadan (+{(ratio-1)*100:.0f}% vs bulan lalu)")

        # Trigger 4 — Demand drop signifikan (>20%) vs bulan sebelumnya yang normal
        elif i > 0:
            prev_demand = demands[i - 1]
            prev_ms = all_results[i - 1]["month"]
            prev_is_bl = all_results[i - 1].get("is_business_logic", False)
            if prev_demand > 0 and not prev_is_bl and not is_bl and ram_days == 0:
                drop_pct = (demand - prev_demand) / prev_demand * 100
                if drop_pct <= -20:
                    tags.append(f"turun {abs(drop_pct):.0f}% vs bulan lalu")

        # Trigger 5 — Seasonality (demand bulan ini biasanya lebih rendah secara historis)
        hist_vals = [v for v in historical_by_month.get(mn_key, []) if v and v > 0]
        if hist_vals and len(hist_vals) >= 2 and not is_bl and ram_days == 0 and i > 0:
            hist_avg = sum(hist_vals) / len(hist_vals)
            prev_demand = demands[i - 1]
            if demand < prev_demand * 0.97 and demand < hist_avg * 1.05:
                # Hitung berapa tahun bulan ini selalu lebih rendah dari bulan sebelumnya
                mn_int = int(mn_key)
                prev_mn_key = f"{mn_int - 1:02d}" if mn_int > 1 else "12"
                prev_hist = [v for v in historical_by_month.get(prev_mn_key, []) if v and v > 0]
                if prev_hist and len(prev_hist) >= 2:
                    n_years_lower = sum(1 for ph, ch in zip(prev_hist, hist_vals) if ch < ph)
                    if n_years_lower >= 2:
                        tags.append(f"pola historis {n_years_lower} tahun berturut-turut, bukan anomali")

        # Format insight per bulan
        demand_fmt = f"{demand:,}"
        if tags:
            per_month[ms] = f"{ms}={demand_fmt} ({'; '.join(tags)})"
        else:
            per_month[ms] = f"{ms}={demand_fmt} (normal)"

    # ── Susun summary satu baris ─────────────────────────────────────────────
    parts = list(per_month.values())
    detail = " | ".join(parts)
    summary = f"{detail} | Total={total_q:,}"

    return {"per_month": per_month, "summary": summary}




# ==============================================================================
# FUNGSI: update_actuals (Step 3B)
# ==============================================================================
def update_actuals(month_str: str):
    """
    Sinkronisasi data aktual dari Vending_Aggregrated ke ForecastResults Layer 1 & 2.
    """
    run_timestamp = datetime.now()
    yr, mn = int(month_str[:4]), int(month_str[5:7])

    print(f"\n[UPDATE ACTUALS] Memulai sinkronisasi data aktual untuk {month_str}...")

    with engine.begin() as conn:
        # Check actual availability
        total_actual = conn.execute(
            text(
                "SELECT SUM(demand) FROM dbo.Vending_Aggregrated WHERE YEAR(tanggal) = :y AND MONTH(tanggal) = :m"
            ),
            {"y": yr, "m": mn},
        ).scalar()

        if not total_actual or total_actual <= 0:
            print("[UPDATE ACTUALS] Tidak ada data aktual.")
            return {
                "status": "warning",
                "message": f"Data aktual untuk bulan {month_str} belum tersedia atau 0",
            }

        # [SATPAM VM MATI] Cek apakah ada mesin yang belum sync
        df_vm = pd.read_sql("SELECT nama_vm, update_time FROM dbo.master_alat_vm", conn)
        dead_vms = []
        if not df_vm.empty:
            for _, row in df_vm.iterrows():
                if pd.isna(row["update_time"]):
                    dead_vms.append(row["nama_vm"])

        warning_msg = None
        if dead_vms:
            vms_str = ", ".join(dead_vms[:2]) + ("..." if len(dead_vms) > 2 else "")
            warning_msg = f"SATPAM WARNING: {len(dead_vms)} mesin ({vms_str}) belum sinkron/mati. Akurasi mungkin tidak valid 100%."

        # 1. Update Layer 1
        conn.execute(
            text("""
            UPDATE dbo.ForecastResults_Layer1
            SET ActualDemand = :act,
                ErrorPercent = ROUND((CAST(TotalDemand AS FLOAT) - :act) / :act * 100.0, 2),
                ActualUpdatedAt = :ts
            WHERE PredictedMonth = :m_str
        """),
            {"act": total_actual, "ts": run_timestamp, "m_str": month_str},
        )

        # 2. Update Layer 2
        res = conn.execute(
            text("""
            UPDATE l2
            SET l2.ActualDemand = va.demand,
                l2.ErrorPercent = CASE WHEN va.demand > 0
                                       THEN ROUND((CAST(l2.PredictedDemand AS FLOAT) - va.demand) / va.demand * 100.0, 2)
                                       ELSE NULL END
            FROM dbo.ForecastResults_Layer2 l2
            INNER JOIN dbo.Vending_Aggregrated va
              ON l2.[Date] = va.tanggal
              AND l2.Shift = va.keterangan
              AND l2.Variant = va.nama_variant
            WHERE l2.PredictedMonth = :m_str
        """),
            {"m_str": month_str},
        )

        final_check = conn.execute(
            text(
                "SELECT TotalDemand, ActualDemand, ErrorPercent FROM dbo.ForecastResults_Layer1 WHERE PredictedMonth = :m_str ORDER BY Id DESC"
            ),
            {"m_str": month_str},
        ).fetchone()

    if final_check:
        print("[UPDATE ACTUALS] Selesai sukses.")
        res = {
            "status": "success",
            "message": f"Data aktual untuk {month_str} berhasil disinkronisasi",
            "month": month_str,
            "predicted_total": final_check.TotalDemand,
            "actual_total": final_check.ActualDemand,
            "error_percent_total": f"{final_check.ErrorPercent:+.2f}%"
            if final_check.ErrorPercent is not None
            else "N/A",
        }

        if warning_msg:
            res["vm_status_warning"] = warning_msg

        return res
