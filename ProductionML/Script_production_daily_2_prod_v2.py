import os, sys, warnings
import pandas as pd
import numpy as np
import joblib
from datetime import date

warnings.filterwarnings("ignore")

# ==============================================================================
# SCRIPT_FIX_DAILY_2_PROD_V2.PY (PRODUCTION — STANDALONE)
#
# Layer 2 Production Orchestrator v2 — Semua improvement dari Task 1-4:
#   [TASK 1] Share-Based DOW Profile (menggantikan fractional_weight-only)
#   [TASK 2] Tiered Event Overlay (Factory Shutdown = 0)
#   [TASK 3] SQL Calendar sebagai sumber utama
#   [TASK 4] KPI Scorecard Otomatis
#
# Cara jalankan: python Script_fix_daily_2_prod_v2.py
#
# Output:
#   Produksi_Prediksi_Q1_2026.csv  — prediksi per hari × shift × varian
#   KPI Scorecard tercetak di console
# ==============================================================================

# ── Path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
_PROD_DIR = os.path.join(_SCRIPT_DIR, "ProductionML")
if os.path.isdir(_PROD_DIR):
    sys.path.insert(0, _PROD_DIR)

# ==============================================================================
# CONFIG
# ==============================================================================
# ── STANDALONE-ONLY (tidak dipakai saat diimport oleh forecast_service.py) ──
# Variabel di bawah hanya relevan jika script ini dijalankan langsung
# (python Script_production_daily_2_prod_v2.py) untuk keperluan debug/standalone.
# Dalam production flow (via FastAPI), semua data dibaca dari SQL.
DAILY_HIST_CSV = "../vending_daily_FEATUREDFORV6.csv"  # [STANDALONE-ONLY]
ACTUAL_CSV     = "../SUSU_ready_v2.csv"                # [STANDALONE-ONLY]
ARTIFACT_PATH  = "Layer1_XGBoost_V6_Artifact.joblib"  # [STANDALONE-ONLY]
OUTPUT_CSV     = "../Produksi_Prediksi_Q1_2026.csv"   # [STANDALONE-ONLY]

TARGET_MONTHS = ["2026-01", "2026-02", "2026-03"]

RAMADAN_CONFIG = {
    2026: {
        "start": pd.Timestamp("2026-02-18"),
        "end":   pd.Timestamp("2026-03-19"),
    },
}
RAMADAN_START = pd.Timestamp("2026-02-18")
RAMADAN_END   = pd.Timestamp("2026-03-19")
RAMADAN_TRANSITION_DAYS   = 2
RAMADAN_TRANSITION_FACTOR = 0.70

# [DEPRECATED] FACTORY_SHUTDOWN_DATES telah dipindahkan ke SQL.
# Kolom IsShutdown di dbo.OperationalCalendar sekarang menjadi sumber tunggal.
# Untuk menambah hari shutdown di tahun mendatang:
#   UPDATE dbo.OperationalCalendar SET IsShutdown = 1 WHERE Date IN (...)
# Tidak perlu mengubah kode Python ini sama sekali.
FACTORY_SHUTDOWN_DATES = set()  # Dikosongkan — hanya dipertahankan agar tidak error jika ada referensi lama

# [TASK 1] DOW Profile window
DOW_PROFILE_WINDOW_MONTHS = 6

# [FIX] Ramadan Start Dates — digunakan oleh adaptive pre-Ramadan weekend profiler
RAMADAN_START_MONTHS = {
    2023: (2023, 3), 2024: (2024, 3), 2025: (2025, 3),
    2026: (2026, 2), 2027: (2027, 2),
}


# ==============================================================================
# 1. SQL CALENDAR EXTRACTION
# ==============================================================================
def fetch_calendar_from_sql(year, month, ramadan_start=None, ramadan_end=None):
    """Menarik kalender operasional dari SQL Server untuk bulan tertentu."""
    import sys
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from database import engine

    if engine is None:
        raise ConnectionError("Gagal terkoneksi ke SQL Server.")

    query = (
        f"SELECT * FROM dbo.OperationalCalendar "
        f"WHERE YEAR(Date) = {year} AND MONTH(Date) = {month}"
    )
    df = pd.read_sql(query, engine)
    if df.empty:
        raise ValueError(f"Tidak ada data SQL untuk {year}-{month:02d}")

    required = {"Date", "IsWorkingDay", "Shift1_Active", "Shift2_Active", "Shift3_Active"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Kolom tidak ditemukan: {missing}")

    # Sertakan IsShutdown jika tersedia di SQL (kolom baru, backward-compatible)
    rename_map = {
        "Date": "tanggal", "IsWorkingDay": "is_working_day_sql",
        "Shift1_Active": "s1_active", "Shift2_Active": "s2_active",
        "Shift3_Active": "s3_active",
    }
    if "IsShutdown" in df.columns:
        rename_map["IsShutdown"] = "is_shutdown_sql"
    df = df.rename(columns=rename_map)
    if "is_shutdown_sql" not in df.columns:
        df["is_shutdown_sql"] = 0  # fallback jika kolom belum ada
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["is_weekend"] = df["tanggal"].dt.weekday.apply(lambda x: 1 if x >= 5 else 0)

    if ramadan_start is not None and ramadan_end is not None:
        df["is_ramadan"] = df["tanggal"].apply(lambda x: 1 if ramadan_start <= x <= ramadan_end else 0)
    else:
        df["is_ramadan"] = 0

    return df


# ==============================================================================
# 2. TRANSLATE TO LAYER 1 FORMAT
# ==============================================================================
def translate_to_layer1_calendar(df_cal):
    """Konversi kalender SQL ke dict yang dimengerti Layer1Model.predict()."""
    WEIGHT_S1, WEIGHT_S2, WEIGHT_S3 = 0.42, 0.38, 0.20
    for c in ["s1_active", "s2_active", "s3_active"]:
        df_cal[c] = df_cal[c].astype(int)

    df_cal["fractional_weight"] = (
        df_cal["s1_active"] * WEIGHT_S1 +
        df_cal["s2_active"] * WEIGHT_S2 +
        df_cal["s3_active"] * WEIGHT_S3
    )
    working_days_frac = df_cal["fractional_weight"].sum()
    productive_milk_days = df_cal[df_cal["is_ramadan"] == 0]["fractional_weight"].sum()
    holiday_days = len(df_cal[(df_cal["is_working_day_sql"] == 0) & (df_cal["is_weekend"] == 0)])

    return {
        "n_days": len(df_cal),
        "ramadan_days": int(df_cal["is_ramadan"].sum()),
        "weekend_days": int(df_cal["is_weekend"].sum()),
        "holiday_days": int(holiday_days),
        "working_days": round(working_days_frac, 2),
        "productive_milk_days": round(productive_milk_days, 2),
    }, df_cal


# ==============================================================================
# 3. LAYER 1 ORCHESTRATOR
# ==============================================================================
def get_monthly_budget(year, month, target_cal, fwd_cache, model):
    """Panggil Layer1Model untuk budget bulanan per varian."""
    print(f"  [LAYER 1] Kalender: {target_cal}")
    hasil = model.predict(year, month, target_cal, fwd_cache=fwd_cache)
    print(f"  [OK] Budget: {hasil['pred_final']:,} kotak")
    return hasil


# ==============================================================================
# 4A. SHIFT PROFILE (Hybrid Lookback — dari prod v1, tidak berubah)
# ==============================================================================
def build_shift_profile(df_daily_hist):
    """Hybrid: SHIFT1=3m, lainnya=1m. Sudah terbukti optimal."""
    df_h = df_daily_hist.copy()
    df_h["tanggal"] = pd.to_datetime(df_h["tanggal"])
    _max_h = df_h["tanggal"].max()

    def get_profile_for_months(n):
        cutoff = _max_h - pd.DateOffset(months=n)
        df_s = df_h[df_h["tanggal"] > cutoff].copy()
        dt = df_s.groupby(["tanggal","is_holiday","is_ramadan","is_weekend"])["demand"].sum().reset_index().rename(columns={"demand":"daily_total"})
        sd = df_s.groupby(["tanggal","keterangan","is_holiday","is_ramadan","is_weekend"])["demand"].sum().reset_index()
        sd = sd.merge(dt, on=["tanggal","is_holiday","is_ramadan","is_weekend"])
        sd["shift_share"] = sd["demand"] / sd["daily_total"].replace(0, np.nan)
        return sd.groupby(["keterangan","is_holiday","is_ramadan","is_weekend"])["shift_share"].mean().reset_index().rename(columns={"shift_share":"avg_share"})

    p1m, p3m = get_profile_for_months(1), get_profile_for_months(3)
    sp = p1m.copy()
    for idx, row in sp.iterrows():
        if "SHIFT1" in row["keterangan"]:
            mask = ((p3m["keterangan"]==row["keterangan"])&(p3m["is_holiday"]==row["is_holiday"])&(p3m["is_ramadan"]==row["is_ramadan"])&(p3m["is_weekend"]==row["is_weekend"]))
            m3 = p3m[mask]
            if not m3.empty:
                sp.at[idx, "avg_share"] = m3["avg_share"].values[0]
    return sp


def get_shift_weights(shift_profile, is_hol, is_ram, is_wknd):
    """Ambil bobot shift, normalisasi ke total=1.0."""
    mask = ((shift_profile["is_holiday"]==is_hol)&(shift_profile["is_ramadan"]==is_ram)&(shift_profile["is_weekend"]==is_wknd))
    sub = shift_profile.loc[mask, ["keterangan","avg_share"]].copy()
    if sub.empty or sub["avg_share"].sum() == 0:
        mn = ((shift_profile["is_holiday"]==0)&(shift_profile["is_ramadan"]==0)&(shift_profile["is_weekend"]==0))
        sub = shift_profile.loc[mn, ["keterangan","avg_share"]].copy()
    total = sub["avg_share"].sum()
    if len(sub) > 0:
        sub["avg_share"] = sub["avg_share"] / total if total > 0 else 1.0 / len(sub)
        return dict(zip(sub["keterangan"], sub["avg_share"]))
    else:
        # Fallback darurat jika shift_profile tidak valid (misal data dummy tidak ada kolom shift)
        return {"SHIFT_DUMMY": 1.0}


# ==============================================================================
# 4B. [TASK 1] DOW SHARE PROFILE + ADAPTIVE PRE-RAMADAN WEEKEND
# ==============================================================================
def _is_pre_ramadan_month(year, month):
    """Cek apakah bulan ini adalah 1 bulan sebelum Ramadan atau bulan Ramadan (untuk boost awal bulan)."""
    for ry, (ram_y, ram_m) in RAMADAN_START_MONTHS.items():
        pre_m = ram_m - 1 if ram_m > 1 else 12
        pre_y = ram_y if ram_m > 1 else ram_y - 1
        if (year == pre_y and month == pre_m) or (year == ram_y and month == ram_m):
            return True
    return False

def _get_adaptive_weekend_ratios(df_hist, target_year, target_month):
    """[FIX Opsi D] Compute Sat/Sun WD-ratio from historical pre-Ramadan months."""
    if not _is_pre_ramadan_month(target_year, target_month):
        return None

    df_h = df_hist.copy()
    df_h["tanggal"] = pd.to_datetime(df_h["tanggal"])
    df_h["day_of_week"] = df_h["tanggal"].dt.dayofweek

    # Flag bridge
    hol_set = set(df_h.loc[df_h["is_holiday"]==1, "tanggal"].dt.normalize())
    all_set = set(df_h["tanggal"].dt.normalize())
    off = {d for d in all_set if d in hol_set or d.weekday() >= 5}
    br = set()
    for d in sorted(all_set):
        if d in off: continue
        if (d - pd.Timedelta(days=1)) in off and (d + pd.Timedelta(days=1)) in off:
            br.add(d)
    df_h["is_bridge"] = df_h["tanggal"].dt.normalize().isin(br).astype(int)

    df_clean = df_h[(df_h["is_holiday"]==0)&(df_h["is_ramadan"]==0)&(df_h["is_bridge"]==0)]
    daily = df_clean.groupby(["tanggal","day_of_week"])["demand"].sum().reset_index()

    sat_ratios, sun_ratios = [], []
    for ry, (ram_y, ram_m) in RAMADAN_START_MONTHS.items():
        pre_m = ram_m - 1 if ram_m > 1 else 12
        pre_y = ram_y if ram_m > 1 else ram_y - 1
        if (pre_y > target_year) or (pre_y == target_year and pre_m >= target_month):
            continue
        pre_start = pd.Timestamp(f"{pre_y}-{pre_m:02d}-01")
        pre_end = pre_start + pd.DateOffset(months=1)
        sub = daily[(daily["tanggal"] >= pre_start) & (daily["tanggal"] < pre_end)]
        if sub.empty: continue
        wd = sub[sub["day_of_week"] < 5]["demand"].mean()
        if wd <= 0: continue
        sat = sub[sub["day_of_week"]==5]
        sun = sub[sub["day_of_week"]==6]
        if not sat.empty: sat_ratios.append(sat["demand"].mean() / wd)
        if not sun.empty: sun_ratios.append(sun["demand"].mean() / wd)

    if not sat_ratios or not sun_ratios:
        return None
    # Menggunakan tahun terakhir (paling baru) karena tren DOW berubah seiring waktu
    return sat_ratios[-1], sun_ratios[-1]

def build_dow_share_profile(df_hist, target_year, target_month, window_months=DOW_PROFILE_WINDOW_MONTHS):
    """Share-Based DOW Profile + Adaptive Pre-Ramadan Weekend."""
    target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")
    window_start = target_date - pd.DateOffset(months=window_months)

    df_h = df_hist.copy()
    df_h["tanggal"] = pd.to_datetime(df_h["tanggal"])
    df_h["day_of_week"] = df_h["tanggal"].dt.dayofweek
    df_h["is_weekend"] = (df_h["day_of_week"] >= 5).astype(int)

    hist_hol = set(df_h.loc[df_h["is_holiday"]==1, "tanggal"].dt.normalize())
    hist_all = set(df_h["tanggal"].dt.normalize())
    off = set(d for d in hist_all if d in hist_hol or d.weekday() >= 5)
    bridge = set()
    for d in sorted(hist_all):
        if d in off: continue
        if (d - pd.Timedelta(days=1)) in off and (d + pd.Timedelta(days=1)) in off:
            bridge.add(d)
    df_h["is_bridge"] = df_h["tanggal"].dt.normalize().isin(bridge).astype(int)

    df_w = df_h[
        (df_h["tanggal"] >= window_start) & (df_h["tanggal"] < target_date) &
        (df_h["is_holiday"] == 0) & (df_h["is_ramadan"] == 0) & (df_h["is_bridge"] == 0)
    ]
    daily = df_w.groupby(["tanggal","day_of_week","is_weekend"])["demand"].sum().reset_index()
    wd_daily = daily[daily["is_weekend"]==0]
    we_daily = daily[daily["is_weekend"]==1]

    dow_avg = wd_daily.groupby("day_of_week")["demand"].mean()
    total_wd = dow_avg.sum()
    dow_shares = {}
    for d in range(5):
        dow_shares[d] = (dow_avg.get(d,0)/total_wd) if total_wd > 0 else 0.2
    wd_per_day = total_wd / 5.0 if total_wd > 0 else 1.0
    for d in [5,6]:
        wa = we_daily[we_daily["day_of_week"]==d]["demand"].mean()
        dow_shares[d] = (wa/wd_per_day) if not pd.isna(wa) and wa > 0 else 0.5

    # [FIX Opsi D] Adaptive Pre-Ramadan Weekend Override
    adaptive_we = _get_adaptive_weekend_ratios(df_hist, target_year, target_month)
    if adaptive_we is not None:
        pre_sat, pre_sun = adaptive_we
        old_sat, old_sun = dow_shares[5], dow_shares[6]
        dow_shares[5] = pre_sat  # Override langsung dengan ratio historis
        dow_shares[6] = pre_sun
        print(f"    [ADAPTIVE] Pre-Ramadan weekend profile:")
        print(f"       Sabtu : {old_sat:.3f}x -> {dow_shares[5]:.3f}x (dari {len(RAMADAN_START_MONTHS)-1} tahun historis)")
        print(f"       Minggu: {old_sun:.3f}x -> {dow_shares[6]:.3f}x (dari {len(RAMADAN_START_MONTHS)-1} tahun historis)")


    # Global event factors
    nwd = df_h[(df_h["is_holiday"]==0)&(df_h["is_ramadan"]==0)&(df_h["is_bridge"]==0)&(df_h["is_weekend"]==0)]
    nwd_avg = nwd.groupby("tanggal")["demand"].sum().mean() if len(nwd) > 0 else 1.0
    hol_avg = df_h[df_h["is_holiday"]==1].groupby("tanggal")["demand"].sum().mean()
    ram_avg = df_h[(df_h["is_ramadan"]==1)&(df_h["is_holiday"]==0)].groupby("tanggal")["demand"].sum().mean()
    br_avg = df_h[df_h["is_bridge"]==1].groupby("tanggal")["demand"].sum().mean()

    factors = {
        "holiday": hol_avg / nwd_avg if not pd.isna(hol_avg) else 0.15,
        "ramadan": ram_avg / nwd_avg if not pd.isna(ram_avg) else 0.01,
        "bridge": br_avg / nwd_avg if not pd.isna(br_avg) else 0.75,
    }
    return dow_shares, wd_per_day, factors


# ==============================================================================
# 4C. [TASK 1+2] DISTRIBUTION WITH DOW PROFILE + TIERED EVENTS
# ==============================================================================
def distribute_with_dow_profile(month_str, budget_dict, dow_shares, weekday_avg, event_factors, shift_profile, ram_start=None, ram_end=None):
    """Membagikan target layer 1 ke hari dan shift menggunakan hybrid day-weighting."""
    import holidays
    target_year = int(month_str[:4])
    id_hols_cache = holidays.Indonesia(years=[target_year, target_year-1])
    shutdown_kws = ["New Year", "Good Friday", "Easter", "Eid al-Fitr", "Nyepi", "Christmas", "Silence"]

    cal_sql = fetch_calendar_from_sql(target_year, int(month_str[5:7]), ram_start, ram_end)
    records = []

    # Build calendar flags
    cal_rows = []
    for _, row in cal_sql.iterrows():
        dt = row["tanggal"]
        dow = dt.dayofweek
        is_wknd = 1 if dow >= 5 else 0
        is_hol = 1 if row.get("is_working_day_sql", 1) == 0 and is_wknd == 0 else 0
        is_ram = int(row.get("is_ramadan", 0))

        # Bridge detection
        is_bridge = 0
        # (simplified — using SQL is_working_day as proxy)

        ram_day_num = (dt - ram_start).days + 1 if (ram_start and ram_end and ram_start <= dt <= ram_end) else 0
        is_rt = 1 if (is_ram and 1 <= ram_day_num <= RAMADAN_TRANSITION_DAYS) else 0

        # [TASK 2] Tiered day weight (Smart Event Classifier)
        hol_name = id_hols_cache.get(dt.date())
        is_shutdown = False
        if hol_name:
            for kw in shutdown_kws:
                if kw in hol_name:
                    is_shutdown = True
                    break

        # [SQL-FIRST] Baca IsShutdown dari OperationalCalendar (sumber kebenaran).
        # Mekanisme 2 (is_shutdown via holidays.Indonesia) tetap aktif sebagai fallback safety net.
        is_shutdown_sql = int(row.get("is_shutdown_sql", 0)) == 1
        if is_shutdown_sql or is_shutdown:
            w = 0.0
        else:
            is_hangover = False
            if hol_name and ("Cuti Bersama" in hol_name or "Joint Leave" in hol_name):
                is_hangover = True
            else:
                prev1 = dt - pd.Timedelta(days=1)
                prev2 = dt - pd.Timedelta(days=2)
                p1_name = id_hols_cache.get(prev1.date())
                p2_name = id_hols_cache.get(prev2.date())
                p1_shut = (prev1 in FACTORY_SHUTDOWN_DATES) or any(kw in (p1_name or "") for kw in shutdown_kws)
                p2_shut = (prev2 in FACTORY_SHUTDOWN_DATES) or any(kw in (p2_name or "") for kw in shutdown_kws)
                if (p1_shut or p2_shut) and (is_hol or dow >= 5):
                    is_hangover = True

            if is_rt:
                w = RAMADAN_TRANSITION_FACTOR * weekday_avg + (1 - RAMADAN_TRANSITION_FACTOR) * weekday_avg * event_factors["ramadan"]
            elif is_hangover:
                if dow >= 5:
                    w = weekday_avg * 0.24  # Hangover Weekend -> jadi Standalone Holiday
                else:
                    w = weekday_avg * 0.08  # Hangover Normal -> Sepi
            elif is_hol:
                w = weekday_avg * 0.24      # Standalone Holiday
            elif is_ram:
                w = weekday_avg * event_factors["ramadan"]
            elif dow >= 5:
                w = weekday_avg * dow_shares[dow]
            else:
                w = weekday_avg * dow_shares[dow] * 5

        cal_rows.append({
            "tanggal": dt, "dow": dow, "is_weekend": is_wknd, "is_holiday": is_hol,
            "is_ramadan": is_ram, "is_ram_trans": is_rt, "day_weight": w,
        })

    cal = pd.DataFrame(cal_rows)
    tw = cal["day_weight"].sum() or 1.0
    cal["day_weight_norm"] = cal["day_weight"] / tw

    for variant, total_budget in budget_dict["by_variant"].items():
        for _, dr in cal.iterrows():
            daily_vol = total_budget * dr["day_weight_norm"]
            sw_is_ram = 1 if (dr["is_ramadan"] and not dr["is_ram_trans"]) else 0
            sw = get_shift_weights(shift_profile, int(dr["is_holiday"]), sw_is_ram, int(dr["is_weekend"]))
            for shift_name, share in sw.items():
                records.append({
                    "tanggal": dr["tanggal"].date(),
                    "bulan": month_str,
                    "varian": variant,
                    "shift": shift_name,
                    "is_holiday": int(dr["is_holiday"]),
                    "is_ramadan": int(dr["is_ramadan"]),
                    "is_weekend": int(dr["is_weekend"]),
                    "demand_pred": round(daily_vol * share, 2),
                    "demand_pred_int": int(round(daily_vol * share)),
                })
    return pd.DataFrame(records)


# ==============================================================================
# [TASK 4] KPI SCORECARD
# ==============================================================================
def print_kpi_scorecard(df_pred, engine=None, actual_csv=None):
    """Cetak KPI scorecard perbandingan prediksi vs aktual.

    Sumber aktual (prioritas):
      1. engine (SQL) → query dbo.Vending_Aggregrated  [production]
      2. actual_csv   → baca CSV                        [standalone/debug]
    """
    if engine is not None:
        # SQL-First: tarik aktual dari Vending_Aggregrated sesuai range tanggal df_pred
        min_date = pd.to_datetime(df_pred["tanggal"]).min().date()
        max_date = pd.to_datetime(df_pred["tanggal"]).max().date()
        try:
            act = pd.read_sql(
                "SELECT tanggal, keterangan, nama_variant, demand "
                "FROM dbo.Vending_Aggregrated "
                f"WHERE tanggal >= '{min_date}' AND tanggal <= '{max_date}'",
                engine
            )
        except Exception as e:
            print(f"  [SKIP] Gagal baca aktual dari SQL: {e}")
            return
        if act.empty:
            print("  [SKIP] Data aktual belum tersedia di Vending_Aggregrated untuk periode ini.")
            return
        act["tanggal"] = pd.to_datetime(act["tanggal"])
        act = act.rename(columns={"keterangan": "shift", "nama_variant": "varian"})

    elif actual_csv is not None:
        # Fallback CSV untuk mode standalone
        if not os.path.exists(actual_csv):
            print("  [SKIP] File aktual tidak ditemukan — scorecard dilewati.")
            return
        act = pd.read_csv(actual_csv)
        act["tanggal"] = pd.to_datetime(act["tanggal"])
        act = act.rename(columns={"keterangan": "shift", "nama_variant": "varian"})

    else:
        print("  [SKIP] Tidak ada sumber aktual (engine/actual_csv) — scorecard dilewati.")
        return

    d0, d1 = act["tanggal"].min(), act["tanggal"].max()
    pred = df_pred.copy()
    pred["tanggal"] = pd.to_datetime(pred["tanggal"])
    pred = pred[(pred["tanggal"] >= d0) & (pred["tanggal"] <= d1)]

    cmp = pred[["tanggal","bulan","shift","varian","demand_pred_int"]].merge(
        act[["tanggal","shift","varian","demand"]].rename(columns={"demand":"actual"}),
        on=["tanggal","shift","varian"], how="left",
    )
    cmp["actual"] = cmp["actual"].fillna(0).astype(int)

    print(f"\n{'='*72}")
    print(f"  LAYER 2 KPI SCORECARD (Production v2)")
    print(f"{'='*72}")

    shifts = sorted(cmp["shift"].unique())
    bulans = sorted(cmp["bulan"].unique())

    hdr = f"  {'Shift':<22}"
    for b in bulans:
        hdr += f" {b:>10}"
    hdr += f"  {'Avg':>8}  Status"
    print(hdr)
    print("  " + "-" * 70)

    sc_rows = []
    for s in shifts:
        row_str = f"  {s:<22}"
        errs = []
        for b in bulans:
            sub = cmp[(cmp["shift"]==s) & (cmp["bulan"]==b)]
            p, a = sub["demand_pred_int"].sum(), sub["actual"].sum()
            e = (p-a)/a*100 if a > 0 else float("nan")
            errs.append(e)
            row_str += f" {e:>+9.1f}%"
        avg_e = np.nanmean(errs)
        st = "[OK]" if abs(avg_e) < 5 else ("[WARN]" if abs(avg_e) < 10 else "[FAIL]")
        row_str += f"  {avg_e:>+7.1f}%  {st}"
        sc_rows.append({"shift": s, "avg": avg_e, "errs": errs})
        print(row_str)

    print("  " + "-" * 70)
    total_str = f"  {'TOTAL':<22}"
    for b in bulans:
        sub = cmp[cmp["bulan"]==b]
        tp, ta = sub["demand_pred_int"].sum(), sub["actual"].sum()
        te = (tp-ta)/ta*100 if ta > 0 else float("nan")
        total_str += f" {te:>+9.1f}%"
    print(total_str)

    cnt_str = f"  {'Shift <10%':<22}"
    for bi, b in enumerate(bulans):
        cnt = sum(1 for r in sc_rows if abs(r["errs"][bi]) < 10)
        cnt_str += f" {f'{cnt}/8':>10}"
    cnt_str += "  Target: 6/8"
    print(cnt_str)

    valid = [r for r in sc_rows if not np.isnan(r["avg"])]
    if valid:
        best = min(valid, key=lambda r: abs(r["avg"]))
        worst = max(valid, key=lambda r: abs(r["avg"]))
        print(f"\n  Best : {best['shift']} (avg {best['avg']:+.1f}%)")
        print(f"  Worst: {worst['shift']} (avg {worst['avg']:+.1f}%)")
    print(f"{'='*72}")


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("[START] PRODUCTION v2: PREDIKSI DEMAND (STANDALONE)")
    print("=" * 70)

    # ── Load Layer 1 artifact ─────────────────────────────────────────────
    print(f"\n[INIT] Loading Layer 1 artifact: {ARTIFACT_PATH}")
    try:
        from Layer1_Core import Layer1Model
        layer1_model = Layer1Model.load_model(ARTIFACT_PATH)
    except Exception as e:
        # Try from ProductionML
        try:
            sys.path.insert(0, os.path.join(_SCRIPT_DIR, "ProductionML"))
            from Layer1_Core import Layer1Model
            _alt = os.path.join("ProductionML", ARTIFACT_PATH)
            layer1_model = Layer1Model.load_model(_alt)
        except Exception as e2:
            print(f"  [ERROR] Gagal load artifact: {e2}")
            raise

    # ── Load historical data ──────────────────────────────────────────────
    print(f"\n[INIT] Loading data historis: {DAILY_HIST_CSV}")
    df_daily_hist = pd.read_csv(DAILY_HIST_CSV)
    df_daily_hist["tanggal"] = pd.to_datetime(df_daily_hist["tanggal"])
    print(f"  [OK] {len(df_daily_hist):,} baris | {df_daily_hist['tanggal'].min().date()} to {df_daily_hist['tanggal'].max().date()}")

    # ── Build shift profile ───────────────────────────────────────────────
    print("\n[INIT] Membangun hybrid shift profile...")
    shift_profile = build_shift_profile(df_daily_hist)

    # ── Process each month ────────────────────────────────────────────────
    all_distributions = []
    fwd_cache = {}

    for ym in TARGET_MONTHS:
        year, month = int(ym[:4]), int(ym[5:7])
        print(f"\n{'>'*3} Memproses {ym} {'<'*3}")

        ram_cfg = RAMADAN_CONFIG.get(year, {})

        # 1. SQL Calendar
        df_sql = fetch_calendar_from_sql(
            year, month,
            ramadan_start=ram_cfg.get("start"),
            ramadan_end=ram_cfg.get("end"),
        )

        # 2. Layer 1 calendar
        target_cal, df_cal = translate_to_layer1_calendar(df_sql)

        # 3. Layer 1 prediction
        budget = get_monthly_budget(year, month, target_cal, fwd_cache, layer1_model)
        fwd_cache[ym] = budget["by_variant"]

        # 4. [TASK 1] DOW Share Profile
        dow_shares, weekday_avg, event_factors = build_dow_share_profile(
            df_daily_hist, year, month
        )
        print(f"  [DOW Profile] WD shares: Mon={dow_shares[0]*100:.1f}% Tue={dow_shares[1]*100:.1f}% "
              f"Wed={dow_shares[2]*100:.1f}% Thu={dow_shares[3]*100:.1f}% Fri={dow_shares[4]*100:.1f}%")

        # 5. [TASK 1+2] Distribute with DOW profile + tiered events
        df_final = distribute_with_dow_profile(
            month_str=ym,
            budget_dict=budget,
            dow_shares=dow_shares,
            weekday_avg=weekday_avg,
            event_factors=event_factors,
            shift_profile=shift_profile,
            ram_start=ram_cfg.get("start"),
            ram_end=ram_cfg.get("end")
        )
        all_distributions.append(df_final)
        print(f"  [OK] Distribusi: {len(df_final):,} baris")

    # ── Gabungkan & simpan ────────────────────────────────────────────────
    df_out = pd.concat(all_distributions, ignore_index=True)
    df_out = df_out.sort_values(["tanggal","varian","shift"]).reset_index(drop=True)
    df_out.to_csv(OUTPUT_CSV, index=False)

    print(f"\n{'='*70}")
    print(f"[DONE] Output: {OUTPUT_CSV} ({len(df_out):,} baris)")
    print(f"{'='*70}")

    # ── [TASK 4] KPI Scorecard ────────────────────────────────────────────
    print_kpi_scorecard(df_out, ACTUAL_CSV)

    print(f"\n[SELESAI] Production v2 complete.")
