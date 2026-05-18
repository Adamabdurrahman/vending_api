import sys, warnings, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════
# Script_fix_daily_2.py  (v2.1 — Layer 2 Improved)
# DISTRIBUSI HARIAN — HYBRID DAY WEIGHTING (ZERO LEAKAGE)
#
# Improvement Plan Tasks 1-4:
#   [TASK 1] Share-Based DOW Profile (menggantikan YoY Regression)
#   [TASK 2] Tiered Event Overlay (Factory Shutdown = 0)
#   [TASK 3] SQL Calendar Integration (fallback ke holidays.Indonesia())
#   [TASK 4] KPI Scorecard Otomatis
#
# Jalankan SETELAH Script_Model_XGBoost_V6_Fallback.py:
#   %run -i Script_Model_XGBoost_V6_Fallback.py
#   %run -i Script_fix_daily_2.py
#
# Output:
#   forecast_layer2_fixed2.csv     ← prediksi versi perbaikan hibrida
#   layer2_fixed_dashboard2.png    ← visualisasi perbandingan
# ══════════════════════════════════════════════════════════════════════

DAILY_CSV   = "vending_daily_FEATUREDFORV6.csv"
OUTPUT_CSV  = "forecast_layer2_fixed2.csv"
ACTUAL_CSV  = "SUSU_ready_v2.csv"

# ── Konfigurasi Kalender ─────────────────────────────────────────────
FACTORY_NON_HOLIDAYS = set()

FACTORY_EXTRA_HOLIDAYS = {
    pd.Timestamp("2026-01-02"),  # PT tutup — bukan bridge day!
}

RAMADAN_START = pd.Timestamp("2026-02-18")
RAMADAN_END   = pd.Timestamp("2026-03-19")
RAMADAN_TRANSITION_DAYS   = 2     
RAMADAN_TRANSITION_FACTOR = 0.70  

LEBARAN_CUTI = {
    pd.Timestamp("2026-03-19"),  
    pd.Timestamp("2026-03-20"),  
    pd.Timestamp("2026-03-21"),  
    pd.Timestamp("2026-03-23"),  
    pd.Timestamp("2026-03-24"),  
    pd.Timestamp("2026-03-25"),  
    pd.Timestamp("2026-03-26"),  
    pd.Timestamp("2026-03-27"),  
}

SHIFT_PROFILE_MONTHS = 1   # Desember 2025 saja (terbukti optimal)

# [TASK 2] Factory Shutdown: hari dimana pabrik tutup total (demand = 0)
# Dipisahkan dari Holiday biasa yang masih ada "reduced operation"
# Ini mengurangi CoV holiday factor (65.5%) karena shutdown (demand=0) tidak
# lagi dirata-rata bersama holiday yang masih berproduksi
FACTORY_SHUTDOWN_DATES = LEBARAN_CUTI | {
    pd.Timestamp("2026-01-01"),  # Tahun Baru — pabrik tutup total
}


# [TASK 1] Window untuk DOW Share Profile (menggantikan YoY regression)
DOW_PROFILE_WINDOW_MONTHS = 6  # 6 bulan terakhir — sangat stabil, CoV < 0.5%

print("=" * 70)
print("SCRIPT_FIX_DAILY v2.1 — Layer 2 Improved (Task 1-4)")
print("=" * 70)

# ── Pastikan variabel Layer 1 tersedia ────────────────────────────────
# Type annotations untuk IDE (Pylance) — variabel disuntikkan oleh Layer 1 via %run -i.
# Bare annotation TIDAK membuat variabel di runtime, sehingga guard dir() tetap berfungsi.
FORWARD_MONTHS: list
VARIANTS: list
fwd_results: dict

_required = ["fwd_results", "VARIANTS", "FORWARD_MONTHS"]
_missing  = [v for v in _required if v not in dir()]
if _missing:
    print(f"\n⚠ Variabel tidak ditemukan: {_missing}")
    print("  Jalankan dulu: %run -i Script_Model_XGBoost_V5_Fallback.py")
    raise SystemExit

# ══════════════════════════════════════════════════════════════════════
# STEP 1: LOAD HISTORIS
# ══════════════════════════════════════════════════════════════════════
print(f"\n[STEP 1] Load data historis: {DAILY_CSV}")
df_h = pd.read_csv(DAILY_CSV)
df_h["tanggal"]     = pd.to_datetime(df_h["tanggal"])
df_h["day_of_week"] = df_h["tanggal"].dt.dayofweek
df_h["day_name"]    = df_h["tanggal"].dt.day_name()
print(f"  Shape  : {df_h.shape}")
print(f"  Periode: {df_h['tanggal'].min().date()} → {df_h['tanggal'].max().date()}")

# ══════════════════════════════════════════════════════════════════════
# STEP 2: GLOBAL EVENT MULTIPLIERS (Hitung Faktor Holiday, Bridge, dll)
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 2] Day Weight: Global Event Multipliers dari Historis")

def flag_bridge_days(df_dates, hol_set):
    bridge = set()
    all_dates = sorted(df_dates)
    off_dates = set(d for d in all_dates if d in hol_set or d.weekday() >= 5)
    for d in all_dates:
        if d in off_dates: continue
        if (d - pd.Timedelta(days=1)) in off_dates and (d + pd.Timedelta(days=1)) in off_dates:
            bridge.add(d)
    return bridge

hist_hol_dates = set(df_h.loc[df_h["is_holiday"]==1, "tanggal"].dt.normalize())
hist_all_dates = set(df_h["tanggal"].dt.normalize())
hist_bridge    = flag_bridge_days(hist_all_dates, hist_hol_dates)

df_h["is_bridge"] = df_h["tanggal"].dt.normalize().apply(lambda d: 1 if d in hist_bridge else 0)
print(f"  Bridge days terdeteksi di historis: {df_h['is_bridge'].sum()} baris")

# Hitung rata-rata global untuk setiap kategori
normal_wd = df_h[(df_h["is_holiday"]==0)&(df_h["is_ramadan"]==0)&(df_h["is_bridge"]==0)&(df_h["is_weekend"]==0)]["demand"]
global_nwd_avg = normal_wd.mean() if len(normal_wd) > 0 else 1.0

global_hol = df_h[(df_h["is_holiday"]==1)]["demand"]
HOLIDAY_FACTOR = (global_hol.mean() / global_nwd_avg) if len(global_hol) > 0 else 0.3

global_ram = df_h[(df_h["is_ramadan"]==1)&(df_h["is_holiday"]==0)]["demand"]
RAMADAN_FACTOR = (global_ram.mean() / global_nwd_avg) if len(global_ram) > 0 else 0.6

global_br = df_h[(df_h["is_bridge"]==1)]["demand"]
BRIDGE_FACTOR = (global_br.mean() / global_nwd_avg) if len(global_br) > 0 else 0.15

print(f"  Faktor Global: Holiday = {HOLIDAY_FACTOR:.2f}x | Ramadan = {RAMADAN_FACTOR:.2f}x | Bridge = {BRIDGE_FACTOR:.2f}x benchmark Normal")

# ── [TASK 1] FUNGSI BARU: Share-Based DOW Profile ─────────────────────
def build_dow_share_profile(df_hist, target_year, target_month, window_months=DOW_PROFILE_WINDOW_MONTHS):
    """
    [TASK 1] Menggantikan build_month_dow_projection().
    Menghitung SHARE per day-of-week dari window N bulan SEBELUM target.
    Jauh lebih stabil dari YoY regression (2-3 titik, CoV 3-8% saja).
    
    Weekday (Mon-Fri): share = avg_demand_dow / sum(avg_demand_all_dow)
    Weekend (Sat, Sun): faktor relatif terhadap rata-rata weekday
    
    Returns: dow_shares dict, weekday_avg float
    """
    target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")
    window_start = target_date - pd.DateOffset(months=window_months)
    
    # ZERO LEAKAGE: hanya data SEBELUM bulan target
    df_w = df_hist[
        (df_hist["tanggal"] >= window_start) &
        (df_hist["tanggal"] < target_date) &
        (df_hist["is_holiday"] == 0) &
        (df_hist["is_ramadan"] == 0) &
        (df_hist["is_bridge"] == 0)
    ].copy()
    
    # Agregasi ke level harian (total semua shift & varian per hari)
    daily = df_w.groupby(["tanggal", "day_of_week", "is_weekend"])["demand"].sum().reset_index()
    weekday_daily = daily[daily["is_weekend"] == 0]
    weekend_daily = daily[daily["is_weekend"] == 1]
    
    # Weekday DOW share (Mon-Fri)
    dow_avg = weekday_daily.groupby("day_of_week")["demand"].mean()
    total_wd_avg = dow_avg.sum()
    
    dow_shares = {}
    for d in range(5):
        dow_shares[d] = (dow_avg.get(d, 0) / total_wd_avg) if total_wd_avg > 0 else 0.2
    
    # Weekend: faktor relatif terhadap rata-rata weekday harian
    weekday_per_day_avg = total_wd_avg / 5.0 if total_wd_avg > 0 else 1.0
    for d in [5, 6]:
        wknd_avg = weekend_daily[weekend_daily["day_of_week"] == d]["demand"].mean()
        dow_shares[d] = (wknd_avg / weekday_per_day_avg) if not pd.isna(wknd_avg) and wknd_avg > 0 else 0.5
    
    return dow_shares, weekday_per_day_avg

# ── [REFERENSI] Fungsi lama — di-comment, jangan hapus ────────────────
# def build_month_dow_projection(df_hist, target_year, target_month):
#     """[DEPRECATED Task 1] Proyeksi YoY linear — hanya 2-3 data point."""
#     df_m = df_hist[(df_hist["tanggal"].dt.month == target_month) & 
#                    (df_hist["tanggal"].dt.year < target_year) &
#                    (df_hist["is_holiday"] == 0) & (df_hist["is_ramadan"] == 0) & 
#                    (df_hist["is_bridge"] == 0)]
#     proj_dow_weight = {}
#     for dow in range(7):
#         df_dow = df_m[df_m["day_of_week"] == dow]
#         if df_dow.empty: proj_dow_weight[dow] = 1.0; continue
#         yearly_avg = df_dow.groupby(df_dow["tanggal"].dt.year)["demand"].mean()
#         if len(yearly_avg) >= 2:
#             years, vals = yearly_avg.index.values, yearly_avg.values
#             slope, intercept = np.polyfit(years, vals, 1)
#             pred_val = slope * target_year + intercept
#             if pred_val < (vals.mean() * 0.1): pred_val = vals.mean()
#         else: pred_val = yearly_avg.values.mean()
#         proj_dow_weight[dow] = float(pred_val)
#     avg_wd = np.mean([proj_dow_weight[d] for d in range(5)])
#     return proj_dow_weight, avg_wd


# ══════════════════════════════════════════════════════════════════════
# STEP 3: SHIFT WEIGHT PROFILE (Custom: SHIFT1=3 bulan, lainnya=1 bulan)
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 3] Shift Profile — Custom Window (SHIFT1 = 3 bulan, Lainnya = 1 bulan)")
_max_h     = df_h["tanggal"].max()

def get_profile_for_months(months):
    _cut = _max_h - pd.DateOffset(months=months)
    df_s = df_h[df_h["tanggal"] > _cut].copy()
    st_t = df_s.groupby(["tanggal","is_holiday","is_ramadan","is_weekend"])["demand"].sum().reset_index().rename(columns={"demand":"daily_total"})
    sd   = df_s.groupby(["tanggal","keterangan","is_holiday","is_ramadan","is_weekend"])["demand"].sum().reset_index()
    sd   = sd.merge(st_t, on=["tanggal","is_holiday","is_ramadan","is_weekend"])
    sd["shift_share"] = sd["demand"] / sd["daily_total"].replace(0, np.nan)
    return sd.groupby(["keterangan","is_holiday","is_ramadan","is_weekend"])["shift_share"].mean().reset_index().rename(columns={"shift_share":"avg_share"})

profile_1m = get_profile_for_months(1)
profile_3m = get_profile_for_months(3)

shift_profile = profile_1m.copy()

# Override khusus SHIFT1 dengan profile 3 bulan
# [OPSI B DIUJI] Menambah SHIFTPUTIH-AWAL & SHIFT3-AWAL ke 3m → tidak berdampak
# karena share-nya terlalu kecil (0.1pp) dan ter-absorb oleh normalisasi.
# Kembali ke SHIFT1-only yang sudah terbukti optimal.
for idx, row in shift_profile.iterrows():
    if "SHIFT1" in row["keterangan"]:
        m = ((profile_3m["keterangan"] == row["keterangan"]) & 
             (profile_3m["is_holiday"] == row["is_holiday"]) & 
             (profile_3m["is_ramadan"] == row["is_ramadan"]) & 
             (profile_3m["is_weekend"] == row["is_weekend"]))
        match_3m = profile_3m[m]
        if not match_3m.empty:
            shift_profile.at[idx, "avg_share"] = match_3m["avg_share"].values[0]

def get_shift_weights(is_hol, is_ram, is_wknd):
    m   = ((shift_profile["is_holiday"]==is_hol) & (shift_profile["is_ramadan"]==is_ram) & (shift_profile["is_weekend"]==is_wknd))
    sub = shift_profile.loc[m, ["keterangan","avg_share"]].copy()
    if sub.empty or sub["avg_share"].sum() == 0:
        mn  = ((shift_profile["is_holiday"]==0) & (shift_profile["is_ramadan"]==0) & (shift_profile["is_weekend"]==0))
        sub = shift_profile.loc[mn, ["keterangan","avg_share"]].copy()
    total = sub["avg_share"].sum()
    sub["avg_share"] = sub["avg_share"] / total if total > 0 else 1.0 / len(sub)
    return dict(zip(sub["keterangan"], sub["avg_share"]))

# ══════════════════════════════════════════════════════════════════════
# STEP 4: KALENDER Q1 2026 — [TASK 3] SQL FIRST, FALLBACK KE LIBRARY
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 4] Kalender Q1 2026 — SQL Calendar (fallback: holidays.Indonesia())")

_calendar_source = "unknown"
try:
    import sys as _sys
    _script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
    _prod_dir = os.path.join(_script_dir, "ProductionML")
    if _prod_dir not in _sys.path:
        _sys.path.insert(0, _prod_dir)
    if _script_dir not in _sys.path:
        _sys.path.insert(0, _script_dir)
    from Script_SqlCalendar import get_sql_engine as _get_sql_engine

    _sql_engine = _get_sql_engine()
    _sql_query = """
        SELECT [Date], IsWorkingDay, Shift1_Active, Shift2_Active, Shift3_Active,
               ISNULL(IsRamadan, 0) as IsRamadan
        FROM dbo.OperationalCalendar
        WHERE [Date] BETWEEN '2026-01-01' AND '2026-03-31'
    """
    _df_sql_cal = pd.read_sql(_sql_query, _sql_engine)
    _df_sql_cal["Date"] = pd.to_datetime(_df_sql_cal["Date"])

    # Map: non-working weekday = holiday
    LIB_HOLIDAYS = set()
    for _, row in _df_sql_cal.iterrows():
        d = pd.Timestamp(row["Date"])
        if row["IsWorkingDay"] == 0 and d.weekday() < 5:
            LIB_HOLIDAYS.add(d)

    # Update FACTORY_SHUTDOWN_DATES dari SQL (all shifts inactive)
    for _, row in _df_sql_cal.iterrows():
        d = pd.Timestamp(row["Date"])
        if (row["IsWorkingDay"] == 0 and d.weekday() < 5 and
            row["Shift1_Active"] == 0 and row["Shift2_Active"] == 0 and row["Shift3_Active"] == 0):
            FACTORY_SHUTDOWN_DATES.add(d)

    _calendar_source = "SQL Server"
    print(f"  ✅ Kalender dibaca dari SQL Server")
    print(f"     Holidays dari SQL: {len(LIB_HOLIDAYS)} hari")
    print(f"     Shutdown dates (total): {len(FACTORY_SHUTDOWN_DATES)} hari")

except Exception as _sql_err:
    print(f"  ⚠ SQL Calendar gagal: {_sql_err}")
    print(f"    Fallback ke holidays.Indonesia()...")
    try:
        import holidays as hol_lib
        id_hol_2026 = hol_lib.Indonesia(years=2026)
        LIB_HOLIDAYS = {pd.Timestamp(d) for d in id_hol_2026.keys()}
    except ImportError:
        print("  ⚠ Library holidays juga tidak ada, gunakan fallback manual")
        LIB_HOLIDAYS = {
            pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-16"), pd.Timestamp("2026-02-17"),
            pd.Timestamp("2026-03-19"), pd.Timestamp("2026-03-20"), pd.Timestamp("2026-03-21"),
        }
    _calendar_source = "holidays.Indonesia() (fallback)"

print(f"  Sumber kalender: {_calendar_source}")

HOLIDAYS_FIXED = (LIB_HOLIDAYS | LEBARAN_CUTI | FACTORY_EXTRA_HOLIDAYS) - FACTORY_NON_HOLIDAYS

# ══════════════════════════════════════════════════════════════════════
# STEP 5: BANGUN KALENDER DENGAN BRIDGE & RAMADAN
# ══════════════════════════════════════════════════════════════════════
q1_dates = pd.date_range("2026-01-01", "2026-03-31")
off_dates_q1 = {d for d in q1_dates if d in HOLIDAYS_FIXED or d.weekday() >= 5}

cal_rows = []
for dt in q1_dates:
    dow      = dt.dayofweek
    is_wknd  = 1 if dow >= 5 else 0
    is_hol   = 1 if dt in HOLIDAYS_FIXED else 0
    is_ram   = 1 if RAMADAN_START <= dt <= RAMADAN_END else 0

    is_bridge = 0
    if is_wknd == 0 and is_hol == 0:
        prev_off = (dt - pd.Timedelta(days=1)) in off_dates_q1
        next_off = (dt + pd.Timedelta(days=1)) in off_dates_q1
        if prev_off and next_off: is_bridge = 1

    ram_day_num = (dt - RAMADAN_START).days + 1 if is_ram else 0
    is_ram_trans = 1 if (is_ram and 1 <= ram_day_num <= RAMADAN_TRANSITION_DAYS) else 0

    cal_rows.append({
        "tanggal": dt, "month_str": dt.strftime("%Y-%m"), "day_of_week": dow, "day_name": dt.day_name(),
        "is_weekend": is_wknd, "is_holiday": is_hol, "is_ramadan": is_ram, 
        "is_bridge": is_bridge, "is_ram_trans": is_ram_trans, "ram_day_num": ram_day_num,
    })
cal_df = pd.DataFrame(cal_rows)

# ══════════════════════════════════════════════════════════════════════
# STEP 6: DISTRIBUSI ALGORITMA HIBRIDA
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 5 & 6] Mengkalkulasi Base Weight Hibrida & Distribusi Akhir")

records = []
for month_str in FORWARD_MONTHS:
    target_year = int(month_str[:4])
    target_month = int(month_str[5:7])

    # 1. [TASK 1] Share-Based DOW Profile (menggantikan YoY regression)
    dow_shares, weekday_avg = build_dow_share_profile(df_h, target_year, target_month)
    
    _dow_names = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    print(f"\n  ➤ DOW Share Profile untuk {month_str} (window {DOW_PROFILE_WINDOW_MONTHS}m):")
    print(f"    {'Sen':>6} {'Sel':>6} {'Rab':>6} {'Kam':>6} {'Jum':>6} | {'Sab':>6} {'Min':>6}")
    _wd_str = " ".join([f"{dow_shares[d]*100:5.1f}%" for d in range(5)])
    _we_str = f"{dow_shares[5]:.3f}x {dow_shares[6]:.3f}x"
    print(f"    {_wd_str} | {_we_str}")
    print(f"    Weekday avg (anchor): {weekday_avg:,.0f} unit/hari")

    month_cal = cal_df[cal_df["month_str"] == month_str].copy()
    
    # 2. [TASK 1+2] Daily Weight Evaluator — dengan Factory Shutdown tier
    def get_day_weight_hibrida(row):
        dow       = row["day_of_week"]
        dt        = row["tanggal"]
        is_hol    = row["is_holiday"]
        is_ram    = row["is_ramadan"]
        is_bridge = row["is_bridge"]
        is_rt     = row["is_ram_trans"]
        
        # [TASK 2] Tier 0: Factory Shutdown → demand = 0
        if dt in FACTORY_SHUTDOWN_DATES:
            return 0.0
        
        # Tier 1: Ramadan Transition (blending)
        if is_rt:
            w_normal = weekday_avg
            w_ram    = weekday_avg * RAMADAN_FACTOR
            return RAMADAN_TRANSITION_FACTOR * w_normal + (1 - RAMADAN_TRANSITION_FACTOR) * w_ram
        # Tier 2: Holiday (non-shutdown, reduced operation)
        if is_hol:
            return weekday_avg * HOLIDAY_FACTOR
        # Tier 3: Bridge Day
        if is_bridge:
            return weekday_avg * BRIDGE_FACTOR
        # Tier 4: Ramadan
        if is_ram:
            return weekday_avg * RAMADAN_FACTOR
        
        # Tier 5: Normal — [TASK 1] gunakan DOW share profile
        if dow >= 5:  # Weekend
            return weekday_avg * dow_shares[dow]
        else:  # Weekday
            return weekday_avg * dow_shares[dow] * 5  # share × 5 = absolute weight

    month_cal["day_weight"] = month_cal.apply(get_day_weight_hibrida, axis=1)
    tw = month_cal["day_weight"].sum() or 1.0
    month_cal["day_weight_norm"] = month_cal["day_weight"] / tw
    
    # [TASK 2] Log shutdown vs normal
    n_shutdown = sum(1 for _, r in month_cal.iterrows() if r["tanggal"] in FACTORY_SHUTDOWN_DATES)
    n_normal = len(month_cal) - n_shutdown
    if n_shutdown > 0:
        print(f"    ⚠ {n_shutdown} hari shutdown (demand=0), {n_normal} hari aktif")

    # 3. Distribusi Shift & Variant
    for variant in VARIANTS:
        budget = fwd_results[month_str]["by_variant"].get(variant, 0)
        for _, dr in month_cal.iterrows():
            daily_vol = budget * dr["day_weight_norm"]
            sw_is_ram = 1 if (dr["is_ramadan"] and not dr["is_ram_trans"]) else 0
            sw = get_shift_weights(int(dr["is_holiday"]), sw_is_ram, int(dr["is_weekend"]))

            for shift, share in sw.items():
                records.append({
                    "tanggal":         dr["tanggal"].date(),
                    "bulan":           month_str,
                    "hari":            dr["day_name"],
                    "shift":           shift,
                    "varian":          variant,
                    "is_holiday":      int(dr["is_holiday"]),
                    "is_ramadan":      int(dr["is_ramadan"]),
                    "is_weekend":      int(dr["is_weekend"]),
                    "is_bridge":       int(dr["is_bridge"]),
                    "is_ram_trans":    int(dr["is_ram_trans"]),
                    "demand_pred":     round(daily_vol * share, 2),
                    "demand_pred_int": int(round(daily_vol * share)),
                })

result_fixed2 = pd.DataFrame(records)
result_fixed2["tanggal"] = pd.to_datetime(result_fixed2["tanggal"])
result_fixed2 = result_fixed2.sort_values(["tanggal","shift","varian"]).reset_index(drop=True)
result_fixed2.to_csv(OUTPUT_CSV, index=False)
print(f"\n  Saved → {OUTPUT_CSV} ({len(result_fixed2):,} baris)")

# ══════════════════════════════════════════════════════════════════════
# STEP 7: VALIDASI & PERBANDINGAN VS KALENDER LAMA
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 7] Validasi & Perbandingan Metode Hibrida vs Kalender Asli LAMA")

_has_actual = os.path.exists(ACTUAL_CSV)
if _has_actual:
    df_act  = pd.read_csv(ACTUAL_CSV)
    df_act["tanggal"] = pd.to_datetime(df_act["tanggal"])
    df_act  = df_act.rename(columns={"keterangan":"shift", "nama_variant":"varian"})
    _d0, _d1 = df_act["tanggal"].min(), df_act["tanggal"].max()
    df_act   = df_act[(_d0 <= df_act["tanggal"]) & (df_act["tanggal"] <= _d1)]

    df_fixed2 = result_fixed2[(result_fixed2["tanggal"] >= _d0) & (result_fixed2["tanggal"] <= _d1)].copy()

    df_cmp = df_fixed2[["tanggal","bulan","hari","shift","varian",
                        "is_holiday","is_ramadan","is_weekend",
                        "is_bridge","is_ram_trans","demand_pred_int"]].merge(
        df_act[["tanggal","shift","varian","demand"]].rename(columns={"demand":"actual"}),
        on=["tanggal","shift","varian"], how="left"
    )
    df_cmp["actual"]  = df_cmp["actual"].fillna(0).astype(int)
    df_cmp["error"]   = df_cmp["demand_pred_int"] - df_cmp["actual"]

    old_pred_csv = "forecast_layer2_Q1_2026.csv"
    has_old = os.path.exists(old_pred_csv)
    if has_old:
        df_old = pd.read_csv(old_pred_csv)
        df_old["tanggal"] = pd.to_datetime(df_old["tanggal"])
        df_old = df_old[(df_old["tanggal"] >= _d0) & (df_old["tanggal"] <= _d1)]
        daily_old = df_old.groupby("tanggal")["demand_pred_int"].sum().reset_index()
        daily_old.columns = ["tanggal","pred_old"]

    total_p = df_cmp["demand_pred_int"].sum()
    total_a = df_cmp["actual"].sum()
    print(f"\n  OVERVIEW: Pred(Hibrida)={total_p:,} | Actual={total_a:,} | Error={(total_p-total_a)/total_a*100:+.1f}%")

    print(f"\n  {'='*64}")
    print(f"  RINGKASAN BULANAN PER SHIFT (Versi Hibrida Zero-Leakage)")
    print(f"  {'='*64}")
    for bulan_str, grp_b in df_cmp.groupby("bulan"):
        tgl_min = grp_b["tanggal"].min().date()
        tgl_max = grp_b["tanggal"].max().date()
        tp, ta  = grp_b["demand_pred_int"].sum(), grp_b["actual"].sum()
        te      = (tp-ta)/ta*100 if ta > 0 else float("nan")
        hari_ada = grp_b["tanggal"].nunique()
        hari_bln = pd.Period(bulan_str, "M").days_in_month

        print(f"\n  ┌─ {bulan_str} ({tgl_min} – {tgl_max})")
        print(f"  │  Total Prediksi: {tp:>10,} vs Aktual: {ta:>10,} (Err: {te:>+6.1f}%)")
        print(f"  │  {'Shift':<22} {'Pred(hib)':>10} {'Aktual':>10} {'Err%':>8}  Status")
        print(f"  │  " + "-" * 58)
        for s in sorted(grp_b["shift"].unique()):
            sub = grp_b[grp_b["shift"]==s]
            p, a = sub["demand_pred_int"].sum(), sub["actual"].sum()
            e    = (p-a)/a*100 if a > 0 else float("nan")
            if pd.isna(e):    st = "—"
            elif abs(e) < 5:  st = "✅ Akurat"
            elif abs(e) < 10: st = "⚠ Mendekati"
            else:             st = "❌ Meleset"
            print(f"  │  {s:<22} {p:>10,} {a:>10,} {e:>+7.1f}%  {st}")
        print(f"  └{'─'*63}")

    layer2_hibrida_validation = df_cmp

    # ══════════════════════════════════════════════════════════════════
    # [TASK 4] KPI SCORECARD OTOMATIS
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*72}")
    print(f"  LAYER 2 KPI SCORECARD")
    print(f"{'='*72}")

    all_shifts = sorted(df_cmp["shift"].unique())
    all_bulans = sorted(df_cmp["bulan"].unique())

    # Header
    hdr = f"  {'Shift':<22}"
    for b in all_bulans:
        hdr += f" {b:>10}"
    hdr += f"  {'Avg':>8}  Status"
    print(hdr)
    print(f"  " + "─" * (24 + 12 * len(all_bulans) + 20))

    scorecard_rows = []
    for s in all_shifts:
        row_str = f"  {s:<22}"
        errs = []
        for b in all_bulans:
            sub = df_cmp[(df_cmp["shift"] == s) & (df_cmp["bulan"] == b)]
            p, a = sub["demand_pred_int"].sum(), sub["actual"].sum()
            e = (p - a) / a * 100 if a > 0 else float("nan")
            errs.append(e)
            row_str += f" {e:>+9.1f}%"
        avg_e = np.nanmean(errs)
        if pd.isna(avg_e):     st = "—"
        elif abs(avg_e) < 5:   st = "✅"
        elif abs(avg_e) < 10:  st = "⚠"
        else:                  st = "❌"
        row_str += f"  {avg_e:>+7.1f}%  {st}"
        scorecard_rows.append({"shift": s, "avg_err": avg_e, "errs": errs})
        print(row_str)

    print(f"  " + "─" * (24 + 12 * len(all_bulans) + 20))

    # Total per bulan
    total_row = f"  {'TOTAL':<22}"
    for b in all_bulans:
        sub = df_cmp[df_cmp["bulan"] == b]
        tp, ta = sub["demand_pred_int"].sum(), sub["actual"].sum()
        te = (tp - ta) / ta * 100 if ta > 0 else float("nan")
        total_row += f" {te:>+9.1f}%"
    total_row += f"  {'':>8}  {'✅' if abs(te) < 2 else '⚠'}"
    print(total_row)

    # Shift < 10% count per bulan
    count_row = f"  {'Shift <10%':<22}"
    for bi, b in enumerate(all_bulans):
        cnt = sum(1 for sr in scorecard_rows if abs(sr["errs"][bi]) < 10)
        count_row += f" {f'{cnt}/8':>10}"
    count_row += f"  {'':>8}  Target: 6/8"
    print(count_row)

    # Best & Worst shift
    valid_rows = [r for r in scorecard_rows if not pd.isna(r["avg_err"])]
    if valid_rows:
        best = min(valid_rows, key=lambda r: abs(r["avg_err"]))
        worst = max(valid_rows, key=lambda r: abs(r["avg_err"]))
        print(f"\n  Best shift  : {best['shift']} (avg {best['avg_err']:+.1f}%)")
        print(f"  Worst shift : {worst['shift']} (avg {worst['avg_err']:+.1f}%)")

    print(f"{'='*72}")

# ══════════════════════════════════════════════════════════════════════
# STEP 8: VISUALISASI DASHBOARD
# ══════════════════════════════════════════════════════════════════════
print("\n[STEP 8] Membuat Dashboard Visualisasi...")

import matplotlib.dates as mdates
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.spines.top"]   = False
plt.rcParams["axes.spines.right"] = False

C = {"old":"#e67e22","fix":"#8e44ad","actual":"#2ecc71","bridge":"#2980b9"}
MONTH_LABELS = {m: pd.Timestamp(m+"-01").strftime("%b %Y") for m in FORWARD_MONTHS}

fig = plt.figure(figsize=(18, 16))
fig.patch.set_facecolor("#f8f9fa")
gs  = GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.33, top=0.93, bottom=0.06, left=0.07, right=0.97)

ax1  = fig.add_subplot(gs[0, :])
ax2a = fig.add_subplot(gs[1, 0])
ax2b = fig.add_subplot(gs[1, 1])
ax3  = fig.add_subplot(gs[2, 0])
ax4  = fig.add_subplot(gs[2, 1])

fig.suptitle("Script_fix_daily ver 2 — Hibrida (Zero Leakage)\nProyeksi YoY Khusus Bulan Target + Multiplier Normalisasi Event", fontsize=13, fontweight="bold", y=0.97)

if _has_actual:
    daily_fix2 = result_fixed2.groupby("tanggal")["demand_pred_int"].sum().reset_index()
    daily_fix2 = daily_fix2[daily_fix2["tanggal"] <= _d1].sort_values("tanggal")
    daily_act2 = df_act.groupby("tanggal")["demand"].sum().reset_index().sort_values("tanggal")

    ax1.plot(daily_fix2["tanggal"], daily_fix2["demand_pred_int"], color=C["fix"], lw=2.5, label="Prediksi Hibrida (Zero Leakage)", zorder=4)
    ax1.plot(daily_act2["tanggal"], daily_act2["demand"], color=C["actual"], lw=2, label="Aktual", zorder=5)
    if has_old: ax1.plot(daily_old["tanggal"], daily_old["pred_old"], color=C["old"], lw=1.5, ls="--", alpha=0.7, label="Prediksi Lama Statis", zorder=3)

    for fd, label, col in [(pd.Timestamp("2026-01-02"), "Bridge", C["bridge"]), (pd.Timestamp("2026-02-18"), "Ramadan", "#f39c12")]:
        if fd <= _d1: ax1.axvline(fd, color=col, ls=":", lw=1.5, alpha=0.7)

ax1.set_title("① Demand Harian: Hibrida Tervalidasi Akademik vs Aktual", fontsize=9, loc="left")
ax1.legend(fontsize=8)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{int(v):,}"))
plt.setp(ax1.get_xticklabels(), rotation=45, fontsize=7)
ax1.grid(alpha=0.25); ax1.set_facecolor("#fdfdfd")

def draw_shift_cmp(ax, bulan_str, df_cmp_in):
    shifts   = sorted(result_fixed2["shift"].unique())
    x        = np.arange(len(shifts)); w = 0.25
    pred_fix = [result_fixed2[(result_fixed2["bulan"]==bulan_str)&(result_fixed2["shift"]==s)]["demand_pred_int"].sum() for s in shifts]
    
    has_act = False
    if df_cmp_in is not None and bulan_str in df_cmp_in["bulan"].values:
        sub_a   = df_cmp_in[df_cmp_in["bulan"]==bulan_str]
        act_v   = [sub_a[sub_a["shift"]==s]["actual"].sum() for s in shifts]
        has_act = True
    else: act_v = [0]*len(shifts)

    ax.bar(x - w, pred_fix, w, color=C["fix"], alpha=0.8, label="Pred Hibrida", zorder=3)
    if has_act:
        ax.bar(x, act_v, w, color=C["actual"], alpha=0.8, label="Aktual", zorder=3)
        for i, (p,a) in enumerate(zip(pred_fix, act_v)):
            if a > 0:
                e = (p-a)/a*100; col = "#27ae60" if abs(e)<10 else "#e74c3c"
                ax.text(i - w/2, max(p,a)+150, f"{e:+.0f}%", ha="center", fontsize=6.5, color=col, fontweight="bold")

    ax.set_xticks(x); ax.set_xticklabels([s.replace("SHIFT","S").replace(" - ","\n") for s in shifts], fontsize=7)
    ax.set_title(f"② Shift {MONTH_LABELS.get(bulan_str,bulan_str)}", fontsize=9, loc="left")
    if has_act: ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3); ax.set_facecolor("#fdfdfd")

avail_m = [m for m in FORWARD_MONTHS if result_fixed2[result_fixed2["bulan"]==m].shape[0]>0]
draw_shift_cmp(ax2a, avail_m[0] if avail_m else FORWARD_MONTHS[0], df_cmp if _has_actual else None)
draw_shift_cmp(ax2b, avail_m[1] if len(avail_m)>1 else FORWARD_MONTHS[1], df_cmp if _has_actual else None)

if _has_actual and has_old:
    daily_all = daily_fix2.rename(columns={"demand_pred_int":"pred_fix2"}).merge(daily_old, on="tanggal", how="left").merge(daily_act2.rename(columns={"demand":"act2"}), on="tanggal", how="left").dropna()
    daily_all["err_hibrida"] = (daily_all["pred_fix2"]-daily_all["act2"])/daily_all["act2"]*100
    daily_all["err_old"]     = (daily_all["pred_old"]-daily_all["act2"])/daily_all["act2"]*100

    idx = np.arange(len(daily_all)); w3 = 0.35
    ax3.bar(idx-w3/2, daily_all["err_old"], w3, color=C["old"], alpha=0.7, label="Error Lama", zorder=3)
    ax3.bar(idx+w3/2, daily_all["err_hibrida"], w3, color=C["fix"], alpha=0.7, label="Error Hibrida", zorder=3)
    ax3.axhline(0, color="black", lw=0.8, alpha=0.5)
    ax3.set_xticks(idx[::3]); ax3.set_xticklabels([str(d.date()) for d in daily_all["tanggal"].iloc[::3]], rotation=45, fontsize=6)
    ax3.set_ylabel("Error% (Pred - Aktual)")
    ax3.set_title("③ Error Harian", fontsize=9, loc="left"); ax3.legend(fontsize=7, ncol=2); ax3.grid(axis="y", alpha=0.3)

    daily_all2 = daily_all.merge(cal_df[["tanggal","is_holiday","is_weekend","is_bridge","is_ramadan"]], on="tanggal", how="left")
    def calc_mae(df, mask):
        sub = df[mask]; return (sub["pred_old"]-sub["act2"]).abs().mean() if len(sub)>0 else float("nan"), (sub["pred_fix2"]-sub["act2"]).abs().mean() if len(sub)>0 else float("nan")

    cats = ["Holiday", "Bridge", "Normal WD", "Weekend"]
    masks = [(daily_all2["is_holiday"]==1), (daily_all2["is_bridge"]==1), ((daily_all2["is_holiday"]==0)&(daily_all2["is_weekend"]==0)&(daily_all2["is_bridge"]==0)&(daily_all2["is_ramadan"]==0)), (daily_all2["is_weekend"]==1)]
    old_maes, fix_maes = zip(*[calc_mae(daily_all2, m) for m in masks])

    x4 = np.arange(len(cats)); w4 = 0.35
    ax4.bar(x4-w4/2, old_maes, w4, color=C["old"], alpha=0.8, label="Kalender Lama")
    ax4.bar(x4+w4/2, fix_maes, w4, color=C["fix"], alpha=0.8, label="Kalender Hibrida")
    ax4.set_xticks(x4); ax4.set_xticklabels(cats, fontsize=9); ax4.set_ylabel("MAE (unit)"); ax4.set_title("④ MAE per Kategori", fontsize=9, loc="left"); ax4.legend(fontsize=8); ax4.grid(axis="y", alpha=0.3)

DASH_PATH = "layer2_fixed_dashboard2.png"
plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig(DASH_PATH, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())

print(f"\n{'='*70}")
print(f"SCRIPT_FIX_DAILY V2 (HIBRIDA) SELESAI")
print(f"  Prediksi fix hibrida → {OUTPUT_CSV}")
print(f"  Dashboard evaluasi   → {DASH_PATH}")
print(f"{'='*70}")
