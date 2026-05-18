import json
import os
import sys
import warnings

import matplotlib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

if not sys.stdout.isatty():
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════
# ██████  CONFIG — XGBoost V6+ (22 Fitur Kompak + Regularisasi)
# ══════════════════════════════════════════════════════════════════════
# Perbedaan dari V5 (42 fitur):
#   - FEATURE_COLS: 22 fitur inti (V6 18 + 3 tambahan kritis + share_trend_3m)
#   - Tambahan dari V6 awal: lag_12m, share_change, demand_acceleration
#     → lag_12m adalah satu-satunya yang hilang dari V6 tapi punya
#       importance signifikan (0.0092) sebagai referensi YoY absolut
# Perbedaan dari V6 awal (18 fitur):
#   - colsample_bytree ditambahkan ke GridSearch (cegah dominasi fitur)
#   - Tanpa colsample_bytree, var_Coklat mendominasi 45% importance
#     → model terlalu rigid untuk kondisi out-of-distribution (Ramadan)
# Perbedaan dari V6+ awal (21 fitur):
#   - share_trend_3m ditambahkan (atasi Coklat systematic bias)
#   - Bug fix: demand_acceleration kini pakai p1 (T-1), bukan p2 (T-2)
#   - Bug fix: share_change forward month dihitung, tidak lagi dipaksa 0.0
# Step 9 Business Logic Override Maret 2026 tetap sama
# ══════════════════════════════════════════════════════════════════════


CSV_PATH = "V3_m1_training_data.csv"
# CSV_PATH = "v6_fix_training_data.csv"
METADATA_PATH = "V3_metadata.json"

VARIANTS = ["Coklat", "Moca", "Original (Putih)", "Strawberry"]

ACTUALS_OVERRIDE = {
    "2026-01": 78_332,
    "2026-02": 48_515,
}

ACT_VAR_OVERRIDE = {
    "2026-01": {
        "Coklat": 37_051,
        "Moca": 10_968,
        "Original (Putih)": 14_422,
        "Strawberry": 15_891,
    },
    "2026-02": {
        "Coklat": 21_832,
        "Moca": 6_792,
        "Original (Putih)": 7_762,
        "Strawberry": 12_129,
    },
}

# Kalender Q1 2026 — dibaca dari OperationalCalendar SQL Server (single source of truth)
# Fallback ke nilai GS yang sudah diketahui jika koneksi SQL tidak tersedia.
# Jalankan Script_SqlCalendar.py sekali dulu untuk memastikan IsRamadan sudah terisi.
try:
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from Script_SqlCalendar import get_sql_engine as _get_engine, build_future_calendar as _build_cal
    _engine = _get_engine()
    FUTURE_CALENDAR = _build_cal(["2026-01", "2026-02", "2026-03"], _engine)
    print("[CONFIG] FUTURE_CALENDAR berhasil dibaca dari SQL Server (OperationalCalendar).")
    for _m, _c in FUTURE_CALENDAR.items():
        print(f"  {_m}: working_days={_c['working_days']}, prod_milk={_c.get('productive_milk_days','—')}, ramadan={_c['ramadan_days']}")
except Exception as _cal_err:
    print(f"[CONFIG] SQL tidak tersedia ({_cal_err}) — pakai fallback kalender GS.")
    FUTURE_CALENDAR = {
        "2026-01": {"n_days": 31, "working_days": 19.0, "productive_milk_days": 19.0,
                    "ramadan_days": 0,  "holiday_days": 2, "weekend_days": 9},
        "2026-02": {"n_days": 28, "working_days": 20.0, "productive_milk_days": 11.0,
                    "ramadan_days": 11, "holiday_days": 1, "weekend_days": 7},
        "2026-03": {"n_days": 31, "working_days": 15.0, "productive_milk_days": 2.0,
                    "ramadan_days": 19, "holiday_days": 3, "weekend_days": 6},
    }

FORWARD_MONTHS = ["2026-01", "2026-02", "2026-03"]

BACKTEST_MONTHS_EXPLICIT = [
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
]

# UNTUK MENGETES BULAN NOVEMBER DALAM 1 TAHUN SAJA   MAPE            0.38%   6929.56%  +6929.18%  ❌ Overfitting
# Dengan ini:
# BACKTEST_MONTHS_EXPLICIT = [
#     "2025-01", "2025-02",
#     # "2025-03" — dikecualikan: Ramadan ekstrem (2 hari produktif)
#     # "2025-04" — dikecualikan: bulan Lebaran, pola demand tidak representatif
#     "2025-05", "2025-06", "2025-07", "2025-08",
#     "2025-09", "2025-10", "2025-11", "2025-12",
# ]

ANOMALY_DEMAND_THRESHOLD = 100

# Daftar bulan Ramadan — single source of truth untuk Lag Skipper & metadata artifact.
# Update list ini setiap tahun agar forward prediction pasca-Ramadan tetap akurat.
RAMADAN_MONTHS = [
    "2023-03", "2023-04",
    "2024-03", "2024-04",
    "2025-03",
    "2026-02", "2026-03",
    "2027-02", "2027-03",
]

# ── Mode Prediksi Forward ──────────────────────────────────────────────────
# True  = CHAIN PREDICTION: setiap bulan pakai hasil prediksi bulan sebelumnya
#         → evaluasi jujur model untuk 3 bulan ke depan tanpa data 2026
# False = ROLLING CALIBRATION: pakai data aktual jika tersedia di ACT_VAR_OVERRIDE
#         → lebih akurat setelah data aktual bulan sebelumnya sudah ada
USE_CHAIN_PREDICTION = True

print("=" * 80)
print("XGBOOST V6+: 22-FITUR KOMPAK + COLSAMPLE REGULARISASI + STEP 9")
print("=" * 80)
print(
    "  22 fitur: V6 awal (18) + lag_12m + share_change + demand_acceleration + share_trend_3m"
)
print("  colsample_bytree [0.6, 0.8] mencegah dominasi var_Coklat (44.9% importance)")
print("  Step 9 Business Logic Override Maret 2026 tetap aktif")
_mode_label = "CHAIN PREDICTION" if USE_CHAIN_PREDICTION else "ROLLING CALIBRATION"
print(f"  Mode Forward : {_mode_label}")
if USE_CHAIN_PREDICTION:
    print("  (lag bulan berikutnya = hasil prediksi, bukan data aktual 2026)")
else:
    print("  (lag bulan berikutnya = aktual jika tersedia di ACT_VAR_OVERRIDE)")
print("=" * 80)

# STEP 1: LOAD DATA
print(f"\n[STEP 1] Load {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
df["period_str"] = df["period"].astype(str).str[:7]
df["period_dt"] = pd.to_datetime(df["period_str"])
df = df.sort_values(["variant", "period_str"]).reset_index(drop=True)
csv_actuals = df.groupby("period_str")["demand"].sum().to_dict()
ACTUALS = {**csv_actuals, **ACTUALS_OVERRIDE}

_base_month_idx = {
    ps: int(df[df["period_str"] == ps]["month_idx"].values[0])
    for ps in df["period_str"].unique()
    if "month_idx" in df.columns
}
_last_ps = df["period_str"].max()
_last_idx = _base_month_idx.get(_last_ps, 35)
_last_yr = int(_last_ps[:4])
_last_mn = int(_last_ps[5:])

MIDX = dict(_base_month_idx)
for fwd in sorted(FUTURE_CALENDAR):
    if fwd not in MIDX:
        fy, fm = int(fwd[:4]), int(fwd[5:])
        offset = (fy - _last_yr) * 12 + (fm - _last_mn)
        MIDX[fwd] = _last_idx + offset

# STEP 2: FEATURE ENGINEERING
# (Dibuat semua dulu — V6 hanya memakai 18 dari hasil ini)
print("\n[STEP 2] Feature Engineering")
df["rolling_avg_6m"] = df.groupby("variant")["demand"].transform(
    lambda s: s.shift(1).rolling(6, min_periods=3).mean()
)
df["lag_6m"] = df.groupby("variant")["demand"].transform(lambda s: s.shift(6))

df["yoy_change"] = np.where(
    df["lag_12m"].abs() > 0, df["lag_1m"] / df["lag_12m"].clip(lower=1) - 1, 0
)
df["lag_1m_vs_rolling"] = np.where(
    df["rolling_avg_3m"].abs() > 0,
    df["lag_1m"] / df["rolling_avg_3m"].clip(lower=1) - 1,
    0,
)
df["seasonal_ratio"] = np.where(
    df["demand_mean_sm"].abs() > 0, df["lag_1m"] / df["demand_mean_sm"].clip(lower=1), 1
)

# lama
# def _slope3(row):
#     pts = [row["lag_3m"], row["lag_2m"], row["lag_1m"]]
#     if any(p == 0 for p in pts): return 0.0
#     return float(np.polyfit([0, 1, 2], pts, 1)[0])
# df["trend_slope_3m"] = df.apply(_slope3, axis=1)

# baru
_valid = (df["lag_3m"] != 0) & (df["lag_2m"] != 0) & (df["lag_1m"] != 0)
df["trend_slope_3m"] = np.where(_valid, (df["lag_1m"] - df["lag_3m"]) / 2.0, 0.0)


df["demand_direction"] = np.sign(df["lag_1m"] - df["lag_2m"])
df["momentum_strength"] = df["growth_rate"].abs() * df["demand_direction"]
df["mean_reversion_signal"] = df["lag_1m"] - df["rolling_avg_3m"]
df["demand_acceleration"] = df.groupby("variant")["growth_rate"].diff().fillna(0)
df["demand_percentile_3m"] = df.groupby("variant")["lag_1m"].transform(
    lambda s: s.rolling(3, min_periods=1).rank(pct=True)
)


def _consec(arr):
    res, cnt, prev = [], 0, 0
    for d in arr:
        cnt = (cnt + 1) if d == prev and d != 0 else (1 if d != 0 else 0)
        res.append(cnt)
        prev = d
    return res


df["consecutive_direction"] = df.groupby("variant")["demand_direction"].transform(
    lambda s: _consec(s.values)
)

tot_lag = df.groupby("period_str")["lag_1m"].sum().rename("total_market_momentum")
df = df.merge(tot_lag, on="period_str", suffixes=("", "_tot"))
df["seasonal_mom_12m"] = df["yoy_change"]

df["share_lag_2m"] = df.groupby("variant")["share_lag_1m"].shift(1)
df["share_lag_3m"] = df.groupby("variant")["share_lag_1m"].shift(2)
df["share_trend_3m"] = df["share_lag_1m"] - df["share_lag_3m"]

# ╔════════════════════════════════════════════════════════════════════╗
# ║  STEP 2B START ─ RAMADAN SHARE SMOOTHER (Non-Destructive Patch)           ║
# ║                                                                              ║
# ║  Cara menghapus blok ini (jika patch menurunkan akurasi):                   ║
# ║    Cari teks "STEP 2B START" dan "STEP 2B END" di file ini,                 ║
# ║    lalu hapus semua kode di antara kedua penanda tersebut.                  ║
# ║                                                                              ║
# ║  Toggle cepat (tanpa hapus kode): ubah ENABLE_SHARE_SMOOTHER = True        ║
# ╚════════════════════════════════════════════════════════════════════╝

ENABLE_SHARE_SMOOTHER = True
SMOOTHER_DEMAND_FLOOR = 500  # total demand semua variant se-bulan < ini = kandidat
SMOOTHER_SHARE_MAX = 85.0  # share_pct > 85% = distorted (1 variant monopoli)
SMOOTHER_SHARE_MIN = 2.0  # share_pct < 2% untuk variant yang biasanya ada

_SMOOTHER_PATCH_LOG = []  # log semua patch yang dilakukan (untuk ringkasan akhir)

if ENABLE_SHARE_SMOOTHER:
    print("\n[STEP 2B] Ramadan Share Smoother - Deteksi & Patch Distorsi Share")
    print(
        f"  Threshold: demand_floor={SMOOTHER_DEMAND_FLOOR}, "
        f"share_max={SMOOTHER_SHARE_MAX}%, share_min={SMOOTHER_SHARE_MIN}%"
    )

    monthly_total = df.groupby("period_str")["demand"].sum()
    df["_monthly_total"] = df["period_str"].map(monthly_total)

    patched_count = 0
    all_periods = sorted(df["period_str"].unique())

    for v in VARIANTS:
        df_v = df[df["variant"] == v].sort_values("period_str")
        med_shr = df_v["share_pct"].median()  # baseline median share variant ini

        for i, row in df_v.iterrows():
            ps = row["period_str"]
            total_m = row["_monthly_total"]
            shr = row["share_pct"]

            is_distorted = (
                (total_m < SMOOTHER_DEMAND_FLOOR)
                or (shr > SMOOTHER_SHARE_MAX)
                or (shr < SMOOTHER_SHARE_MIN and med_shr > 5.0)
            )
            if not is_distorted:
                continue

            idx = all_periods.index(ps) if ps in all_periods else -1
            ps_prev = all_periods[idx - 1] if idx > 0 else None
            ps_next = all_periods[idx + 1] if idx < len(all_periods) - 1 else None

            prev_r = df[(df["variant"] == v) & (df["period_str"] == ps_prev)]
            next_r = df[(df["variant"] == v) & (df["period_str"] == ps_next)]
            shr_prev = float(prev_r["share_pct"].values[0]) if len(prev_r) else shr
            shr_next = float(next_r["share_pct"].values[0]) if len(next_r) else shr

            shr_new = (shr_prev + shr_next) / 2.0

            print(
                f"  PATCH {ps} | {v:<22} "
                f"share_pct {shr:>6.1f}% → {shr_new:>6.1f}%  "
                f"[demand_bulan={total_m:.0f}, T-1={shr_prev:.1f}%, T+1={shr_next:.1f}%]"
            )

            _SMOOTHER_PATCH_LOG.append(
                {
                    "period": ps,
                    "variant": v,
                    "shr_before": round(shr, 4),
                    "shr_after": round(shr_new, 4),
                    "shr_prev": round(shr_prev, 4),
                    "shr_next": round(shr_next, 4),
                    "demand_bulan": int(total_m),
                }
            )

            df.loc[i, "share_pct"] = shr_new
            patched_count += 1

    if patched_count > 0:
        print(
            f"\n  Recomputing downstream share features ({patched_count} baris di-patch)..."
        )
        df = df.sort_values(["variant", "period_str"]).reset_index(drop=True)
        df["share_lag_1m"] = df.groupby("variant")["share_pct"].shift(1)
        df["share_change"] = df["share_pct"] - df["share_lag_1m"]
        if "share_lag_2m" in df.columns:
            df["share_lag_2m"] = df.groupby("variant")["share_pct"].shift(2)
        if "share_lag_3m" in df.columns:
            df["share_lag_3m"] = df.groupby("variant")["share_pct"].shift(3)
            df["share_trend_3m"] = df["share_lag_1m"] - df["share_lag_3m"]
        print(f"  ✅ Share features di-recompute — siap untuk training")
    else:
        print("  ✅ Tidak ada distorsi terdeteksi — data bersih")

    df.drop(columns=["_monthly_total"], inplace=True, errors="ignore")
else:
    print(
        "\n[STEP 2B] Ramadan Share Smoother ─ DINONAKTIFKAN (ENABLE_SHARE_SMOOTHER=False)"
    )
    print("  Data share dipakai apa adanya dari CSV (distorsi Ramadan tidak dikoreksi)")

# ╔════════════════════════════════════════════════════════════════════╗
# ║  STEP 2B END ─ RAMADAN SHARE SMOOTHER                                      ║
# ╚════════════════════════════════════════════════════════════════════╝

# STEP 3: DEFINE FEATURE COLUMNS (V6+ — 21 Fitur)
# Berdasarkan feature importance analysis:
#   - V6 awal (18 fitur) menanggung 96.3% importance
#   - Satu-satunya fitur penting yang hilang: lag_12m (0.92% importance)
#   - colsample_bytree di GridSearch mengatasi dominasi var_Coklat (44.9%)

# lama
# FEATURE_COLS = [
#     # Kalender (inti)
#     "working_days", "ramadan_pct", "holiday_pct",
#     # Cyclical & Trend
#     "month_sin", "month_cos", "month_idx",
#     # Varian (one-hot)
#     "var_Coklat", "var_Moca", "var_Original (Putih)", "var_Strawberry",
#     # Histori Pendek
#     "lag_1m", "lag_2m", "rolling_avg_3m",
#     # Momentum
#     "growth_rate", "trend_slope_3m", "yoy_change",
#     # Market Share
#     "share_lag_1m", "total_demand_lag_1m",
#     # ── Tambahan V6+ (kritis untuk seasonal accuracy) ──
#     "lag_12m",            # Referensi YoY absolut — importance 0.92%
#     "share_change",       # Dinamika perubahan market share — 0.46%
#     "demand_acceleration",# Akselerasi momentum demand — 0.40%
# ]

# baru
FEATURE_COLS = [
    # Kalender (inti)
    "working_days",
    "ramadan_pct",
    "holiday_pct",
    # Cyclical & Trend
    "month_sin",
    "month_cos",
    "month_idx",
    # Varian (one-hot)
    "var_Coklat",
    "var_Moca",
    "var_Original (Putih)",
    "var_Strawberry",
    # Histori Pendek
    "lag_1m",
    "lag_2m",
    "rolling_avg_3m",
    # Momentum
    "growth_rate",
    "trend_slope_3m",
    "yoy_change",
    # Market Share
    "share_lag_1m",
    "total_demand_lag_1m",
    # ── Tambahan V6+ (kritis untuk seasonal accuracy) ──
    "lag_12m",  # Referensi YoY absolut — importance 0.92%
    "share_change",  # Dinamika perubahan market share — 0.46%
    "demand_acceleration",  # Akselerasi momentum demand — 0.40%
    "share_trend_3m",
]

FEATURE_COLS = [c for c in FEATURE_COLS if c in df.columns]
print(f"  Jumlah fitur aktif: {len(FEATURE_COLS)} (V6+)")
print(f"  Fitur: {', '.join(FEATURE_COLS)}")

# STEP 4: PARAM SELECTION VIA CROSS-VALIDATION
print("\n[STEP 4] Model Parameter Selection (XGBoost GridSearchCV)")
print("  colsample_bytree ditambahkan untuk mencegah dominasi fitur tunggal")

_imp0 = SimpleImputer(strategy="median")
_sc0 = StandardScaler()

# lama
# Xcv   = _sc0.fit_transform(_imp0.fit_transform(df[FEATURE_COLS].values))

# Tentukan cutoff: hanya data SEBELUM bulan backtest pertama
CUTOFF_FOR_TUNING = BACKTEST_MONTHS_EXPLICIT[0]  # "2025-09"

df_tune = df[df["period_str"] < CUTOFF_FOR_TUNING]
Xcv = _sc0.fit_transform(_imp0.fit_transform(df_tune[FEATURE_COLS].values))

param_grid = {
    "n_estimators": [50, 100],
    "learning_rate": [0.05, 0.1],
    "max_depth": [3, 4],
    "subsample": [0.8, 1.0],
    # colsample_bytree: paksa setiap tree hanya lihat subset fitur
    # → mencegah var_Coklat selalu menang di setiap split
    # → model lebih robust untuk kondisi out-of-distribution (Ramadan)
    "colsample_bytree": [0.6, 0.8],
}

xgb_cv = GridSearchCV(
    XGBRegressor(random_state=42),
    param_grid,
    cv=5,
    scoring="neg_mean_absolute_error",
)

# xgb_cv = GridSearchCV(XGBRegressor(random_state=42), param_grid,
#                       cv=5, scoring='neg_mean_absolute_error')

xgb_cv.fit(Xcv, df_tune["demand"].values)

# xgb_cv.fit(Xcv, df["demand"].values)
BEST_PARAMS = xgb_cv.best_params_

print(f"  Best params: {BEST_PARAMS}")


def _gate(e):
    """Status gate: ✓<7% | ~<10% | ✗>10% berdasarkan absolute error persen."""
    return "✓<7%" if abs(e) <= 7 else ("~<10%" if abs(e) <= 10 else "✗>10%")


def _ve(pred, actual):
    """Error persen per varian; fallback '—' jika aktual nol."""
    return f"{(pred - actual) / actual * 100:+.1f}%" if actual else "—"


_ts_mape_cv = None  # placeholder — diisi Step 4B, dibandingkan setelah Step 5

# STEP 4B: TIMESERIES SPLIT FORMAL CV
# Mengevaluasi model di berbagai era data (2023-2024-2025),
# bukan hanya 4 bulan terakhir — gambaran akurasi yang lebih representatif
print("\n[STEP 4B] TimeSeriesSplit Formal Cross-Validation (k=5)")
print("  Tujuan: evaluasi di berbagai era, bukan hanya Sep-Des 2025")

all_periods = sorted(df["period_str"].unique())
df_agg = df.groupby("period_str")["demand"].sum().reset_index()
df_agg = df_agg.sort_values("period_str").reset_index(drop=True)

N_SPLITS = 5
tss = TimeSeriesSplit(n_splits=N_SPLITS, test_size=1)

tscv_results = []
print(
    f"  {'Fold':<6} {'Train Era':<22} {'Test Bulan':<12} "
    f"{'Pred':>8} {'Actual':>8} {'Err':>8}  Status"
)
print("  " + "-" * 72)

_tscv_cache = {}

for fold, (tr_idx, te_idx) in enumerate(tss.split(df_agg), 1):
    tr_months = df_agg.iloc[tr_idx]["period_str"].tolist()
    te_month = df_agg.iloc[te_idx]["period_str"].values[0]

    if te_month not in ACTUALS:
        continue

    act = ACTUALS[te_month]

    tr_df = df[df["period_str"].isin(tr_months)]
    te_df = df[df["period_str"] == te_month]
    if tr_df.empty or te_df.empty:
        continue

    # lama
    # _imp  = SimpleImputer(strategy="median")
    # _sc   = StandardScaler()
    # Xtr_  = _sc.fit_transform(_imp.fit_transform(tr_df[FEATURE_COLS].values))
    # _m = XGBRegressor(**BEST_PARAMS, random_state=42)
    # _m.fit(Xtr_, tr_df["demand"].values)

    # baru
    cache_key = tuple(tr_months)
    if cache_key not in _tscv_cache:
        _imp = SimpleImputer(strategy="median")
        _sc = StandardScaler()
        Xtr_ = _sc.fit_transform(_imp.fit_transform(tr_df[FEATURE_COLS].values))
        _m = XGBRegressor(**BEST_PARAMS, random_state=42)
        _m.fit(Xtr_, tr_df["demand"].values)
        _tscv_cache[cache_key] = (_m, _sc, _imp)
    else:
        _m, _sc, _imp = _tscv_cache[cache_key]

    Xte_ = _sc.transform(_imp.transform(te_df[FEATURE_COLS].values))

    pred_ts = int(np.sum(_m.predict(Xte_)))
    err_ts = (pred_ts - act) / act * 100

    era_str = f"{tr_months[0]} → {tr_months[-1]}"
    tscv_results.append(
        {
            "fold": fold,
            "month": te_month,
            "pred": pred_ts,
            "actual": act,
            "error": err_ts,
        }
    )
    print(
        f"  Fold {fold}  {era_str:<22} {te_month:<12} "
        f"{pred_ts:>8,} {act:>8,} {err_ts:>+7.2f}%  {_gate(err_ts)}"
    )

if tscv_results:
    ts_mape = np.mean([abs(r["error"]) for r in tscv_results])
    ts_mae = np.mean([abs(r["pred"] - r["actual"]) for r in tscv_results])
    ts_rmse = np.sqrt(np.mean([(r["pred"] - r["actual"]) ** 2 for r in tscv_results]))
    print()
    print(
        f"  TimeSeriesSplit CV  →  MAPE={ts_mape:.2f}%  "
        f"MAE={ts_mae:,.0f}  RMSE={ts_rmse:,.0f}"
    )
    print(f"  Catatan: CV mencakup era yg lebih beragam dari manual backtest")
    _ts_mape_cv = (
        ts_mape  # disimpan — perbandingan vs Walk-Forward MAPE dicetak setelah Step 5
    )


# STEP 5: WALK-FORWARD BACKTEST
print(
    f"\n[STEP 5] Walk-Forward Backtest ({BACKTEST_MONTHS_EXPLICIT[0]} – {BACKTEST_MONTHS_EXPLICIT[-1]})"
)
BT_MONTHS = [m for m in BACKTEST_MONTHS_EXPLICIT if m in df["period_str"].values]

# _gate() sudah didefinisikan sebelum Step 4B — tidak perlu didefinisikan ulang

bt = {}

_bt_cache = {}

# lama
# for tm in BT_MONTHS:
#     tr = df[df["period_str"] <  tm]
#     te = df[df["period_str"] == tm]
#     if te.empty or tm not in ACTUALS: continue
#     act = ACTUALS[tm]

#     imp_ = SimpleImputer(strategy="median")
#     sc_  = StandardScaler()
#     Xtr  = sc_.fit_transform(imp_.fit_transform(tr[FEATURE_COLS].values))
#     Xte  = sc_.transform(imp_.transform(te[FEATURE_COLS].values))

#     model = XGBRegressor(**BEST_PARAMS, random_state=42)
#     model.fit(Xtr, tr["demand"].values)

#     pv_raw = model.predict(Xte)  # prediksi per baris (per varian)
#     pred   = int(np.sum(pv_raw))
#     err    = (pred - act) / act * 100

#     # Simpan per-varian: mapping variant -> pred & actual dari te
#     te_sorted = te.sort_values("variant").reset_index(drop=True)
#     var_pred_bt   = {row["variant"]: float(pv) for row, pv in
#                      zip(te_sorted.to_dict("records"),
#                          model.predict(sc_.transform(imp_.transform(
#                              te_sorted[FEATURE_COLS].values))))}
#     var_actual_bt = te_sorted.set_index("variant")["demand"].to_dict()

# baru ---
for tm in BT_MONTHS:
    tr = df[df["period_str"] < tm]
    te = df[df["period_str"] == tm]
    if te.empty or tm not in ACTUALS:
        continue
    act = ACTUALS[tm]

    cache_key = tuple(sorted(tr["period_str"].unique()))
    if cache_key not in _bt_cache:
        imp_ = SimpleImputer(strategy="median")
        sc_ = StandardScaler()
        Xtr = sc_.fit_transform(imp_.fit_transform(tr[FEATURE_COLS].values))
        model = XGBRegressor(**BEST_PARAMS, random_state=42)
        model.fit(Xtr, tr["demand"].values)
        _bt_cache[cache_key] = (model, sc_, imp_)
    else:
        model, sc_, imp_ = _bt_cache[cache_key]

    # Sort di awal — predict SEKALI, pakai untuk total dan per-varian
    te_sorted = te.sort_values("variant").reset_index(drop=True)
    Xte = sc_.transform(imp_.transform(te_sorted[FEATURE_COLS].values))
    pv_raw = model.predict(Xte)  # ← hanya dipanggil sekali

    pred = int(np.sum(pv_raw))
    err = (pred - act) / act * 100

    var_pred_bt = {
        row["variant"]: float(pv)
        for row, pv in zip(te_sorted.to_dict("records"), pv_raw)
    }
    var_actual_bt = te_sorted.set_index("variant")["demand"].to_dict()
    # ----
    bt[tm] = {
        "pred": pred,
        "actual": act,
        "error": err,
        "by_variant_pred": var_pred_bt,
        "by_variant_actual": var_actual_bt,
    }
    print(f"  {tm}  Pred={pred:>8,}  Actual={act:>8,}  Err={err:>+7.2f}%  {_gate(err)}")

preds = [r["pred"] for r in bt.values()]
actuals = [r["actual"] for r in bt.values()]
errors = [r["error"] for r in bt.values()]

mape = np.mean([abs(e) for e in errors])
mae = np.mean([abs(p - a) for p, a in zip(preds, actuals)])
rmse = np.sqrt(np.mean([(p - a) ** 2 for p, a in zip(preds, actuals)]))

print()
print("  " + "═" * 55)
print(f"  {'Metrik':<25} {'Nilai':>12}  Keterangan")
print("  " + "-" * 55)
print(f"  {'MAPE':<25} {mape:>11.2f}%  Rata-rata error persen")
print(f"  {'MAE':<25} {mae:>10,.0f}   unit susu / bulan")
print(f"  {'RMSE':<25} {rmse:>10,.0f}   unit (hukum error besar)")
print("  " + "═" * 55)
print(f"  Best params: {BEST_PARAMS}")

# ── Interpretasi Jujur ──────────────────────────────────────
_worst = max(bt.items(), key=lambda x: abs(x[1]["error"]))
_best = min(bt.items(), key=lambda x: abs(x[1]["error"]))
print(f"\n  Backtest terbaik  : {_best[0]}  (err {_best[1]['error']:+.2f}%)")
print(f"  Backtest terburuk : {_worst[0]}  (err {_worst[1]['error']:+.2f}%)")
if mape <= 5:
    print(f"  Status: ✅ SANGAT BAIK — MAPE {mape:.2f}% (target <7%)")
elif mape <= 7:
    print(f"  Status: ✅ BAIK — MAPE {mape:.2f}% masih dalam target <7%")
elif mape <= 10:
    print(f"  Status: ⚠ CUKUP — MAPE {mape:.2f}% perlu perhatian")
else:
    print(f"  Status: ❌ KURANG — MAPE {mape:.2f}% melebihi target")

# ── TimeSeriesCV vs Walk-Forward Comparison (deferred dari Step 4B) ──────────
if _ts_mape_cv is not None:
    if _ts_mape_cv > mape * 1.5:
        print(
            f"\n  ⚠ CV MAPE ({_ts_mape_cv:.2f}%) jauh > Walk-Forward ({mape:.2f}%) "
            f"→ model kurang konsisten di era lama"
        )
    else:
        print(
            f"\n  ✅ CV MAPE ({_ts_mape_cv:.2f}%) konsisten dengan Walk-Forward ({mape:.2f}%)"
        )

# ── ZeroR BASELINE COMPARISON ──────────────────────────────
print("\n  ── ZeroR Baseline (Prediksi = Demand Bulan Sebelumnya) ──")
zeror_errs, zeror_maes, zeror_rmses = [], [], []
for tm in BT_MONTHS:
    if tm not in ACTUALS:
        continue
    act = ACTUALS[tm]
    # ZeroR: ambil total demand bulan sebelumnya
    yr_, mn_ = int(tm[:4]), int(tm[5:])
    prev_ps = f"{yr_ - 1}-{mn_:02d}" if mn_ == 1 else f"{yr_}-{mn_ - 1:02d}"
    prev_rows = df[df["period_str"] == prev_ps]
    zeror_pred = int(prev_rows["demand"].sum()) if not prev_rows.empty else act
    zeror_err = (zeror_pred - act) / act * 100
    zeror_errs.append(abs(zeror_err))
    zeror_maes.append(abs(zeror_pred - act))
    zeror_rmses.append((zeror_pred - act) ** 2)
    print(f"  {tm}  ZeroR={zeror_pred:>8,}  Actual={act:>8,}  Err={zeror_err:>+7.2f}%")

z_mape = np.mean(zeror_errs)
z_mae = np.mean(zeror_maes)
z_rmse = np.sqrt(np.mean(zeror_rmses))

print()
print("  " + "═" * 65)
print(f"  {'Model':<28} {'MAPE':>6}  {'MAE':>8}  {'RMSE':>8}  Verdict")
print("  " + "-" * 65)
print(
    f"  {'ZeroR (bulan sebelumnya)':<28} {z_mape:>5.2f}%  {z_mae:>8,.0f}  {z_rmse:>8,.0f}  baseline"
)
print(
    f"  {'XGBoost V6+ (21 fitur)':<28} {mape:>5.2f}%  {mae:>8,.0f}  {rmse:>8,.0f}  ML model"
)
print("  " + "═" * 65)

improvement = (z_mape - mape) / z_mape * 100
if improvement > 30:
    verdict = f"✅ XGBoost JAUH lebih baik (+{improvement:.1f}% improvement)"
elif improvement > 10:
    verdict = f"✅ XGBoost lebih baik (+{improvement:.1f}% improvement)"
elif improvement > 0:
    verdict = (
        f"⚠ XGBoost sedikit lebih baik (+{improvement:.1f}%) — worth the complexity?"
    )
else:
    verdict = f"❌ ZeroR lebih baik! XGBoost ({mape:.2f}%) kalah dari baseline — review diperlukan"
print(f"  {verdict}")

# ── STEP 5C: PER-VARIANT BACKTEST EVALUATION ───────────────────────────
print("\n[STEP 5C] Per-Variant Backtest Evaluation (Sep–Des 2025)")
print("  Tujuan: periksa apakah error distribusi varian sudah ada di bulan NORMAL")
print("  (sebelum tambah fitur baru, kita perlu baseline ini)")

_VCOL = "    {:<8}  {:>10}  {:>8}  {:>10}  {:>12}  {:>10}"
print("\n" + _VCOL.format("", "Coklat", "Moca", "Original", "Strawberry", "Total"))
print("  " + "─" * 68)

# Kumpulkan error per varian per bulan
_var_errs = {v: [] for v in VARIANTS}  # untuk hitung MAPE per varian

for tm in BT_MONTHS:
    if tm not in bt:
        continue
    vp = bt[tm]["by_variant_pred"]
    va = bt[tm]["by_variant_actual"]
    tot_p = bt[tm]["pred"]
    tot_a = bt[tm]["actual"]

    print(f"  {tm}")
    print(
        _VCOL.format(
            "PRED",
            f"{vp.get('Coklat', 0):,.0f}",
            f"{vp.get('Moca', 0):,.0f}",
            f"{vp.get('Original (Putih)', 0):,.0f}",
            f"{vp.get('Strawberry', 0):,.0f}",
            f"{tot_p:,}",
        )
    )
    print(
        _VCOL.format(
            "ACTUAL",
            f"{va.get('Coklat', 0):,.0f}",
            f"{va.get('Moca', 0):,.0f}",
            f"{va.get('Original (Putih)', 0):,.0f}",
            f"{va.get('Strawberry', 0):,.0f}",
            f"{tot_a:,}",
        )
    )

    # ERR% per varian + kumpulkan untuk MAPE
    row_errs = []
    for v in VARIANTS:
        p_v = vp.get(v, 0)
        a_v = va.get(v, 0)
        if a_v > 0:
            e_v = (p_v - a_v) / a_v * 100
            _var_errs[v].append(abs(e_v))
            row_errs.append(f"{e_v:>+.1f}%")
        else:
            row_errs.append("—")
    tot_err = _ve(tot_p, tot_a) if tot_a else "—"
    print(_VCOL.format("ERR%", *row_errs, tot_err))
    print("  " + "─" * 68)

# Ringkasan MAPE per varian
print("\n  MAPE PER VARIAN (Sep–Des 2025 Backtest):")
print(f"  {'Varian':<20} {'MAPE':>8}  Diagnosis")
print("  " + "-" * 50)
for v in VARIANTS:
    if _var_errs[v]:
        v_mape = np.mean(_var_errs[v])
        if v_mape <= 7:
            diag = "✅ Akurat"
        elif v_mape <= 15:
            diag = "⚠ Perlu perhatian"
        else:
            diag = "❌ Masalah sistemik — perlu fitur baru"
        print(f"  {v:<20} {v_mape:>7.2f}%  {diag}")
print("  " + "-" * 50)
print("  Catatan: error tinggi di bulan normal (Sep-Des) = masalah share feature,")
print("           bukan hanya Ramadan — perlu investigasi lebih dalam.")
# ╔════════════════════════════════════════════════════════════════════╗
# ║  STEP 5C COMPARISON START ─ Before vs After Share Smoother            ║
# ║  Sistem ini menyimpan MAPE per-varian ke file JSON agar kamu bisa      ║
# ║  membandingkan hasil dengan ENABLE_SHARE_SMOOTHER = True vs False.     ║
# ║  Cara kerja:                                                            ║
# ║    1) Run pertama (misal ON) → tersimpan V6_mape_smoother_ON.json      ║
# ║    2) Ganti ke OFF, run lagi → tersimpan OFF.json + tampil perbandingan ║
# ║  Untuk menghapus: hapus dari penanda ini hingga STEP 5C COMPARISON END  ║
# ╚════════════════════════════════════════════════════════════════════╝

_smoother_state = "ON" if ENABLE_SHARE_SMOOTHER else "OFF"
_opposite_state = "OFF" if ENABLE_SHARE_SMOOTHER else "ON"
_save_path = f"V6_mape_smoother_{_smoother_state}.json"
_compare_path = f"V6_mape_smoother_{_opposite_state}.json"

# Simpan MAPE per-varian run ini
_current_mape_data = {
    "smoother": _smoother_state,
    "mape_total": round(mape, 4),
    "mae_total": round(mae, 2),
    "rmse_total": round(rmse, 2),
    "per_variant": {
        v: round(float(np.mean(_var_errs[v])), 4) for v in VARIANTS if _var_errs[v]
    },
    "patch_log": _SMOOTHER_PATCH_LOG,
}
with open(_save_path, "w", encoding="utf-8") as _f:
    json.dump(_current_mape_data, _f, ensure_ascii=False, indent=2)
print(f"\n  ✅ STEP 2B Result disimpan ke: {_save_path}")

# Coba load state sebaliknya untuk perbandingan
if os.path.exists(_compare_path):
    with open(_compare_path, "r", encoding="utf-8") as _f:
        _other = json.load(_f)

    print(f"\n  ┌─ BEFORE vs AFTER Share Smoother ─────────────────────────────┐")
    _lbl_on = "Smoother ON (patch)"
    _lbl_off = "Smoother OFF (raw)"
    _cur_lbl = _lbl_on if _smoother_state == "ON" else _lbl_off
    _oth_lbl = _lbl_off if _smoother_state == "ON" else _lbl_on

    print(f"  │  {'Metrik':<22} {_oth_lbl:>22} {_cur_lbl:>22}  Delta  │")
    print(f"  ├{'─' * 40}┤")

    # Total MAPE
    _d_mape = _current_mape_data["mape_total"] - _other["mape_total"]
    _arrow = "↓" if _d_mape < 0 else ("↑" if _d_mape > 0 else "=")
    _ok = "✅" if _d_mape <= 0 else "⚠"
    print(
        f"  │  {'MAPE Total':<22} {_other['mape_total']:>21.2f}% {_current_mape_data['mape_total']:>21.2f}%  {_arrow}{abs(_d_mape):.2f}pp {_ok}  │"
    )

    # Per varian
    for _v in VARIANTS:
        _cur_v = _current_mape_data["per_variant"].get(_v, 0.0)
        _oth_v = _other["per_variant"].get(_v, 0.0)
        _dv = _cur_v - _oth_v
        _av = "↓" if _dv < 0 else ("↑" if _dv > 0 else "=")
        _ov = "✅" if _dv <= 0 else "⚠"
        print(
            f"  │  {_v:<22} {_oth_v:>21.2f}% {_cur_v:>21.2f}%  {_av}{abs(_dv):.2f}pp {_ov}  │"
        )

    print(f"  └{'─' * 40}┘")

    _improved_variants = [
        _v
        for _v in VARIANTS
        if _current_mape_data["per_variant"].get(_v, 0)
        < _other["per_variant"].get(_v, 0)
    ]
    _worsened_variants = [
        _v
        for _v in VARIANTS
        if _current_mape_data["per_variant"].get(_v, 0)
        > _other["per_variant"].get(_v, 0)
    ]
    _d_total = _current_mape_data["mape_total"] - _other["mape_total"]

    if _d_total <= 0 and len(_improved_variants) >= 2:
        _verdict = "✅ IDEAL: MAPE total tidak memburuk + per-varian membaik — PATCH DIREKOMENDASIKAN"
    elif _d_total <= 0.5 and len(_improved_variants) >= 2:
        _verdict = "✅ BAIK: MAPE total stabil, per-varian membaik — PATCH AMAN"
    elif _d_total <= 0:
        _verdict = "✅ MAPE total membaik, tapi periksa per-varian secara manual"
    elif _d_total <= 1.0:
        _verdict = f"⚠ MAPE total sedikit naik ({_d_total:+.2f}pp) — timbang tradeoff"
    else:
        _verdict = f"❌ MAPE total NAIK {_d_total:+.2f}pp — pertimbangkan ENABLE_SHARE_SMOOTHER=False"
    print(f"  ➤ Verdict: {_verdict}")
else:
    print(f"\n  ℹ Belum ada data pembanding ({_compare_path} tidak ditemukan).")
    print(f"    Untuk melihat perbandingan, run ulang script ini dengan:")
    print(
        f"    ENABLE_SHARE_SMOOTHER = {'False' if _smoother_state == 'ON' else 'True'}"
    )
    print(f"    lalu bandingkan hasilnya secara otomatis di sini.")

# ╔════════════════════════════════════════════════════════════════════╗
# ║  STEP 5C COMPARISON END                                                   ║
# ╚════════════════════════════════════════════════════════════════════╝


# STEP 5B: RESIDUAL PLOT — Backtest
# Residual = Pred - Aktual → positif berarti over-predict, negatif under-predict
print("\n[STEP 5B] Residual Plot (Pred - Aktual per bulan)")
_res_months = list(bt.keys())
_residuals = [bt[m]["pred"] - bt[m]["actual"] for m in _res_months]
_colors = ["#e74c3c" if r > 0 else "#2ecc71" for r in _residuals]

fig_res, ax_res = plt.subplots(figsize=(10, 4))
bars = ax_res.bar(
    _res_months, _residuals, color=_colors, alpha=0.85, edgecolor="white", lw=1.2
)
ax_res.axhline(0, color="black", lw=1.5, linestyle="-")
ax_res.axhline(
    mae, color="#e74c3c", lw=1, linestyle="--", alpha=0.6, label=f"+MAE ({mae:,.0f})"
)
ax_res.axhline(
    -mae, color="#2ecc71", lw=1, linestyle="--", alpha=0.6, label=f"-MAE ({mae:,.0f})"
)

for bar, res, m in zip(bars, _residuals, _res_months):
    err_pct = bt[m]["error"]
    ax_res.text(
        bar.get_x() + bar.get_width() / 2,
        res + (500 if res >= 0 else -1200),
        f"{res:+,.0f}\n({err_pct:+.1f}%)",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
    )

ax_res.set_title(
    f"XGBoost V6+ — Residual Plot Backtest (Sep–Des 2025)\n"
    f"Merah = Over-predict | Hijau = Under-predict | "
    f"MAPE={mape:.2f}%  MAE={mae:,.0f}  RMSE={rmse:,.0f}",
    fontsize=10,
    fontweight="bold",
)
ax_res.set_ylabel("Residual (Pred - Aktual) [unit]")
ax_res.legend(fontsize=9)
ax_res.grid(axis="y", linestyle=":", alpha=0.4)
plt.tight_layout()
plt.savefig("V6_residual_plot.png", dpi=130, bbox_inches="tight")
plt.show()
print("  Plot saved: V6_residual_plot.png")

# STEP 6: FINAL MODEL TRAINING
print("\n[STEP 6] Final Model Training (semua data)")
imp_f = SimpleImputer(strategy="median")
sc_f = StandardScaler()
Xall = sc_f.fit_transform(imp_f.fit_transform(df[FEATURE_COLS].values))
xgb_final = XGBRegressor(**BEST_PARAMS, random_state=42)
xgb_final.fit(Xall, df["demand"].values)


# STEP 7: HELPER FUNCTIONS (Feature Builder)
def _get_hist_demand(period_str, variant=None, historical_df=None, actual_overrides=None, use_chain=True):
    # Guard: dalam chain prediction mode, 2026 aktual TIDAK boleh masuk sebagai lag input
    # (ACT_VAR_OVERRIDE hanya untuk validasi/output comparison, bukan model input)
    if historical_df is None:
        historical_df = df
    if actual_overrides is None:
        actual_overrides = ACT_VAR_OVERRIDE

    if not use_chain and period_str in actual_overrides and variant:
        return actual_overrides[period_str].get(variant, 0)
    if variant:
        row = historical_df[(historical_df["period_str"] == period_str) & (historical_df["variant"] == variant)]
        return float(row["demand"].values[0]) if len(row) else 0.0
    total = historical_df[historical_df["period_str"] == period_str]["demand"].sum()
    return float(total) if total else 0.0


def _month_str(yr, mn):
    t = (yr - 1) * 12 + mn
    return f"{(t - 1) // 12 + 1}-{(t - 1) % 12 + 1:02d}"


def _get_seasonal(period_str, variant, col):
    mn = int(period_str[5:7])
    rows = df[
        (df["variant"] == variant)
        & (df["period_str"].str[5:7].astype(int) == mn)
        & (df["period_str"] < period_str)
    ]
    if rows.empty:
        return 0.0
    if col == "peak":
        return float(rows["demand"].max())
    if col == "min":
        return float(rows["demand"].min())
    if col == "mean":
        return float(rows["demand"].mean())
    if col == "range":
        return float(rows["demand"].max() - rows["demand"].min())
    return 0.0


def build_features_for_month(year, month, fwd_cache, historical_df=None, target_calendar=None):
    if historical_df is None:
        historical_df = df
    if target_calendar is None:
        target_calendar = FUTURE_CALENDAR

    ps = f"{year}-{month:02d}"
    cal = target_calendar.get(
        ps,
        {
            "n_days": 30,
            "ramadan_days": 0,
            "holiday_days": 1,
            "weekend_days": 9,
            "working_days": 21,
        },
    )
    n_days = cal["n_days"]
    ram_d = cal["ramadan_days"]
    hol_d = cal["holiday_days"]
    wknd_d = cal["weekend_days"]
    wday = cal["working_days"]

    def _is_ramadan(period_str):
        # Pakai konstanta modul-level RAMADAN_MONTHS — tidak hardcode di sini
        return period_str in RAMADAN_MONTHS

    def _get_normal_lag_month(yr, mn, lag_n):
        curr_yr, curr_mn = yr, mn
        count = 0
        while count < lag_n:
            curr_mn -= 1
            if curr_mn == 0:
                curr_mn = 12
                curr_yr -= 1
            ps = f"{curr_yr}-{curr_mn:02d}"
            if not _is_ramadan(ps):
                count += 1
        return f"{curr_yr}-{curr_mn:02d}"

    rows = []
    for vi, v in enumerate(VARIANTS):
        p1 = _get_normal_lag_month(year, month, 1)
        p2 = _get_normal_lag_month(year, month, 2)
        p3 = _get_normal_lag_month(year, month, 3)
        p12 = _month_str(year, month - 12)

        def _get(p, var):
            return (
                fwd_cache[p][var]
                if p in fwd_cache and var in fwd_cache[p]
                else _get_hist_demand(p, var, historical_df=historical_df, actual_overrides=ACT_VAR_OVERRIDE, use_chain=USE_CHAIN_PREDICTION)
            )

        lag1 = _get(p1, v)
        lag2 = _get(p2, v)
        lag3 = _get(p3, v)
        lag12 = _get(p12, v)
        roll3 = np.mean([lag1, lag2, lag3])

        gr = np.clip(lag1 / max(lag2, 1) - 1 if lag2 > 0 else 0, -1, 5)

        if lag12 < ANOMALY_DEMAND_THRESHOLD:
            yoy = 0.0
        else:
            yoy = np.clip(lag1 / lag12 - 1, -1, 5)

        tot_l1 = sum(_get(p1, vv) for vv in VARIANTS)
        tot_l1_v = max(tot_l1, 1)
        shr_lag1 = lag1 / tot_l1_v * 100

        prev_row = historical_df[(historical_df["variant"] == v) & (historical_df["period_str"] == p1)]
        shr_lag1 = float(prev_row["share_pct"].values[0]) if len(prev_row) else shr_lag1

        # ── share_change ──────────────────────────────────────────────────────
        # Training definition: share_change = perubahan share_pct dari T-2 ke T-1
        # Jika p1 ada di historis → ambil langsung dari kolom share_change
        # Jika p1 adalah forward month (tidak di df) → hitung: shr_lag1 - share_p2
        # LAMA (jatuh ke 0.0 jika p1 forward — distribusi mismatch):
        # shr_chg = float(prev_row["share_change"].values[0]) if len(prev_row) else 0.0
        # BARU:
        if len(prev_row):
            shr_chg = float(prev_row["share_change"].values[0])
        else:
            # p1 adalah forward month → hitung share_change secara manual
            _p2_share_row = historical_df[(historical_df["variant"] == v) & (historical_df["period_str"] == p2)]
            _shr_p2 = (
                float(_p2_share_row["share_pct"].values[0])
                if len(_p2_share_row)
                else shr_lag1
            )
            shr_chg = shr_lag1 - _shr_p2

        # share_trend_3m: share bulan lalu (p1) dikurangi share 3 bulan lalu (p3)
        # Data p3 selalu tersedia di historis (tidak butuh prediksi chain)
        # Jan 2026: p1=Des'25, p3=Okt'25 → keduanya historis ✅
        # Feb 2026: p1=Jan'26 prediksi, p3=Nov'25 historis → p3 tetap historis ✅
        p3_row = historical_df[(historical_df["variant"] == v) & (historical_df["period_str"] == p3)]
        shr_lag3 = float(p3_row["share_pct"].values[0]) if len(p3_row) else shr_lag1
        shr_trend_3m = shr_lag1 - shr_lag3

        # membuat agar selaras
        # t_slope = float(np.polyfit([0, 1, 2], [lag3, lag2, lag1], 1)[0]
        #                 if all([lag3, lag2, lag1]) else 0)

        # Baris 726 — ganti t_slope dengan:
        t_slope = (lag1 - lag3) / 2.0 if all([lag3, lag2, lag1]) else 0.0

        # ── demand_acceleration ───────────────────────────────────────────────
        # Training definition: growth_rate[T] - growth_rate[T-1]  (.diff())
        # → gr_prev harus dari row T-1 = p1, bukan T-2 = p2
        # LAMA (periode salah → menggunakan T-2 bukan T-1):
        # p2_row = df[(df["variant"] == v) & (df["period_str"] == p2)]
        # gr_prev = float(p2_row["growth_rate"].values[0]) if len(p2_row) else 0.0
        # BARU (reuse prev_row yang sudah ada = T-1 = p1):
        gr_prev = float(prev_row["growth_rate"].values[0]) if len(prev_row) else 0.0
        d_accel = gr - gr_prev

        rows.append(
            {
                # Kalender
                "working_days": wday,
                "ramadan_pct": ram_d / n_days,
                "holiday_pct": hol_d / n_days,
                # Cyclical & Trend
                "month_sin": np.sin(2 * np.pi * month / 12),
                "month_cos": np.cos(2 * np.pi * month / 12),
                "month_idx": MIDX.get(ps, max(MIDX.values()) + 1),
                # Varian (one-hot)
                "var_Coklat": 1 * (v == "Coklat"),
                "var_Moca": 1 * (v == "Moca"),
                "var_Original (Putih)": 1 * (v == "Original (Putih)"),
                "var_Strawberry": 1 * (v == "Strawberry"),
                # Histori
                "lag_1m": lag1,
                "lag_2m": lag2,
                "rolling_avg_3m": roll3,
                # Momentum
                "growth_rate": gr,
                "trend_slope_3m": t_slope,
                "yoy_change": yoy,
                # Market Share
                "share_lag_1m": shr_lag1,
                "total_demand_lag_1m": tot_l1,
                # ── V6+ Tambahan ──
                "lag_12m": lag12,  # Referensi YoY absolut
                "share_change": shr_chg,  # Dinamika market share
                "demand_acceleration": d_accel,  # Akselerasi momentum
                "share_trend_3m": shr_trend_3m,  # Tren share 3 bulan (dihitung dari historis)
                # (untuk Step 9)
                "rolling_avg_3m_ref": roll3,
                "variant": v,
            }
        )
    return pd.DataFrame(rows)


# STEP 8 & 9: FORWARD PREDICTION + BUSINESS LOGIC FALLBACK
print(f"\n[STEP 8 & 9] Forward Prediction => Fallback Business Override")
fwd_cache = {}
fwd_results = {}

print(f"  {'Bulan':<10} {'Prediksi Awal':>15} {'Fallback (Step 9)':>18}  Note")
print("  " + "─" * 70)

for m in FORWARD_MONTHS:
    yr, mn = int(m[:4]), int(m[5:])
    df_in = build_features_for_month(yr, mn, fwd_cache)
    for c in FEATURE_COLS:
        if c not in df_in.columns:
            df_in[c] = 0.0

    Xin = sc_f.transform(imp_f.transform(df_in[FEATURE_COLS].values))
    pv_raw = xgb_final.predict(Xin)
    pred_raw = int(np.sum(pv_raw))

    pv_raw_d = {VARIANTS[i]: pv_raw[i] for i in range(len(VARIANTS))}
    pv_final_d = pv_raw_d.copy()

    # ══════════════════════════════════════════════════════════════════
    # STEP 9: BUSINESS LOGIC OVERRIDE (Maret 2026)
    # Sama persis dengan V5 — 2 hari kerja produktif sesudah Lebaran
    # ══════════════════════════════════════════════════════════════════
    note = "Pure ML (XGBoost V6)"

    # Step 9: aktivasi dinamis berdasarkan productive_milk_days dari kalender
    # (bukan hardcode ke "2026-03" atau "2 hari")
    _cal_m = FUTURE_CALENDAR.get(m, {})
    _prod_days = _cal_m.get("productive_milk_days", _cal_m.get("working_days", 30))
    _use_override = _prod_days <= 10

    if _use_override:
        pred_fallback = 0
        for vi, v in enumerate(VARIANTS):
            lag_3m_avg = df_in.loc[vi, "rolling_avg_3m"]
            daily_run = lag_3m_avg / 25.0
            override_val = int(daily_run * _prod_days)
            pv_final_d[v] = override_val
            pred_fallback += override_val
        pred_final = pred_fallback
        note = f"Business Rule Override ({_prod_days:.0f} Hari Produktif)"
    else:
        pred_final = pred_raw

    act = ACTUALS.get(m)
    fwd_results[m] = {
        "pred_raw": pred_raw,
        "pred_final": pred_final,
        "actual": act,
        "by_variant": pv_final_d,
        "business_logic": _use_override,      # True jika Step 9 aktif
        "productive_days": _prod_days,        # hari produktif dari kalender
    }

    err_str = (
        f"  Actual={act:,}  Err={((pred_final - act) / act * 100):+.2f}%" if act else ""
    )
    print(f"  {m:<10} {pred_raw:>15,} {pred_final:>18,}  {note}{err_str}")

    # Inject untuk lag bulan berikutnya
    # Chain Prediction : selalu pakai hasil prediksi (evaluasi jujur 3 bulan ke depan)
    # Rolling Calibration: pakai actual jika tersedia (lebih akurat secara operasional)
    if not USE_CHAIN_PREDICTION and m in ACT_VAR_OVERRIDE:
        fwd_cache[m] = ACT_VAR_OVERRIDE[m]  # Rolling: pakai actual
        _src = "actual (rolling calibration)"
    else:
        fwd_cache[m] = fwd_results[m]["by_variant"]  # Chain: pakai prediksi
        _src = "predicted (chain)"
    if m != FORWARD_MONTHS[-1]:
        print(f"    └─ lag untuk {FORWARD_MONTHS[FORWARD_MONTHS.index(m) + 1]}: {_src}")

print()
print("=" * 80)
print("HASIL PREDIKSI Q1 2026 PER VARIAN (V6+ — 21 Fitur):")
_COL = "    {:<8}  {:>10}  {:>8}  {:>10}  {:>12}  {:>10}"
print(_COL.format("", "Coklat", "Moca", "Original", "Strawberry", "Total"))
print("  " + "─" * 68)

# _ve() sudah didefinisikan sebelum STEP 5C — tidak perlu didefinisikan ulang

for m in FORWARD_MONTHS:
    bv = fwd_results[m]["by_variant"]
    tot = fwd_results[m]["pred_final"]
    act_total = fwd_results[m]["actual"]
    av = ACT_VAR_OVERRIDE.get(m, {})

    _pd = fwd_results[m].get("productive_days", 0)
    note = f"  ← Business Logic ({_pd:.0f} Hari Produktif)" if fwd_results[m].get("business_logic") else ""
    print(f"  {m}{note}")

    # ── Baris PRED ──
    print(
        _COL.format(
            "PRED",
            f"{bv.get('Coklat', 0):,.0f}",
            f"{bv.get('Moca', 0):,.0f}",
            f"{bv.get('Original (Putih)', 0):,.0f}",
            f"{bv.get('Strawberry', 0):,.0f}",
            f"{tot:,}",
        )
    )

    if av:
        ack = av.get("Coklat", 0)
        acm = av.get("Moca", 0)
        aco = av.get("Original (Putih)", 0)
        acs = av.get("Strawberry", 0)
        act_tot = act_total if act_total else ack + acm + aco + acs

        # ── Baris ACTUAL ──
        print(
            _COL.format(
                "ACTUAL",
                f"{ack:,.0f}",
                f"{acm:,.0f}",
                f"{aco:,.0f}",
                f"{acs:,.0f}",
                f"{act_tot:,}",
            )
        )

        # ── Baris ERR% per varian ──
        print(
            _COL.format(
                "ERR%",
                _ve(bv.get("Coklat", 0), ack),
                _ve(bv.get("Moca", 0), acm),
                _ve(bv.get("Original (Putih)", 0), aco),
                _ve(bv.get("Strawberry", 0), acs),
                _ve(tot, act_tot),
            )
        )
    else:
        # ── Tidak ada aktual (Maret 2026) ──
        print(_COL.format("ACTUAL", "—", "—", "—", "—", "—"))

    print("  " + "─" * 68)

print("=" * 80)

print("\nRINGKASAN V6+ vs V5:")
print(f"  V5 (42 fitur)  — lihat compare_feature.py untuk MAPE")
print(f"  V6+ (21 fitur) — MAPE: {mape:.2f}%  MAE: {mae:,.0f}  RMSE: {rmse:,.0f}")
print(f"  Best params    : {BEST_PARAMS}")

# PLOT
all_m = sorted(set(list(ACTUALS) + list(fwd_results)))
all_m = [m for m in all_m if ACTUALS.get(m) or m in fwd_results]
act_v = [ACTUALS.get(m, np.nan) for m in all_m]
pred_raw_v = [
    bt.get(m, {}).get("pred", fwd_results.get(m, {}).get("pred_raw", np.nan))
    for m in all_m
]
pred_fin_v = [
    bt.get(m, {}).get("pred", fwd_results.get(m, {}).get("pred_final", np.nan))
    for m in all_m
]

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(range(len(all_m)), act_v, "ko-", lw=2.5, ms=8, label="Aktual")
ax.plot(
    range(len(all_m)),
    pred_raw_v,
    color="gray",
    linestyle=":",
    lw=2,
    ms=6,
    label="XGBoost V6 Raw (tanpa Business Logic)",
)
ax.plot(
    range(len(all_m)),
    pred_fin_v,
    "b--^",
    lw=2.5,
    ms=8,
    label="XGBoost V6 Final (dengan Step 9)",
)

try:
    split_idx = all_m.index(FORWARD_MONTHS[0]) - 0.5
    ax.axvline(x=split_idx, color="gray", linestyle=":", alpha=0.8)
    ax.text(
        split_idx + 0.1,
        max(v for v in act_v if not np.isnan(v)) * 0.97,
        "→ Forward Zone",
        fontsize=8,
        color="gray",
    )
    # Annotasi dinamis untuk semua bulan yang trigger Business Logic
    for _bl_m in [mx for mx in all_m if fwd_results.get(mx, {}).get("business_logic")]:
        _bl_idx = all_m.index(_bl_m)
        _bl_val = pred_fin_v[_bl_idx]
        _bl_pd  = fwd_results[_bl_m].get("productive_days", 2)
        ax.annotate(
            f"Business Logic\n({_bl_pd:.0f} Hari Kerja)",
            xy=(_bl_idx, _bl_val),
            xytext=(_bl_idx - 1.5, _bl_val + 12000),
            arrowprops=dict(facecolor="red", shrink=0.05, width=1.5, headwidth=6),
            color="red",
            fontweight="bold",
            fontsize=9,
        )
except (ValueError, TypeError):
    pass

ax.set_title(
    f"XGBoost V6+ (21 Fitur) — MAPE: {mape:.2f}%  MAE: {mae:,.0f}  RMSE: {rmse:,.0f}",
    fontweight="bold",
    fontsize=12,
)
ax.set_xticks(range(len(all_m)))
ax.set_xticklabels(all_m, rotation=45, fontsize=8)
ax.set_ylabel("Unit Susu")
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend()
plt.tight_layout()
plt.savefig("V6_XGBoost_Final_with_Step9.png", dpi=130, bbox_inches="tight")
plt.show()
print("  Plot saved: V6_XGBoost_Final_with_Step9.png")

# ══════════════════════════════════════════════════════════════════════
# MODEL HEALTH CHECK — Diagnostic Dashboard Layer 1
# Tujuan: deteksi underfitting, overfitting, dan data leakage
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("MODEL HEALTH CHECK — Diagnostic Dashboard")
print("=" * 70)

# ── CHECK 1: Data Leakage Verification (teks) ────────────────────────
print("\n[CHECK 1] Data Leakage Verification")
LAG_FEATURES = {
    "lag_1m": "demand t-1  (shift 1 bln) ✅",
    "lag_2m": "demand t-2  (shift 2 bln) ✅",
    "lag_12m": "demand t-12 (shift 12 bln) ✅",
    "rolling_avg_3m": "rata-rata t-1,t-2,t-3     ✅",
    "growth_rate": "lag1/lag2 - 1              ✅",
    "yoy_change": "lag1/lag12 - 1             ✅",
    "share_lag_1m": "share_pct bulan lalu       ✅",
    "share_change": "perubahan share bulan lalu ✅",
    "demand_acceleration": "delta growth_rate lalu ✅",
}
print(f"  {'Fitur':<25} {'Sumber data':<35} Status")
print("  " + "-" * 65)
for feat, desc in LAG_FEATURES.items():
    status = "✅ ADA" if feat in FEATURE_COLS else "── tidak dipakai"
    print(f"  {feat:<25} {desc:<35} {status}")

# Cek ACTUALS_OVERRIDE tidak bocor ke training
train_periods = set(df["period_str"].unique())
leaked = [m for m in ACTUALS_OVERRIDE if m in train_periods]
if leaked:
    print(f"\n  ⚠ POTENSI LEAKAGE: {leaked} ada di training data!")
else:
    print(
        f"\n  ✅ ACTUALS_OVERRIDE ({list(ACTUALS_OVERRIDE.keys())}) "
        f"TIDAK ada di training data — aman"
    )

# ── CHECK 2: Overfitting Detector ────────────────────────────────────
print("\n[CHECK 2] Overfitting Detector (Train Error vs Test Error)")
print("  CATATAN: keduanya dihitung di level TOTAL BULANAN agar bisa dibandingkan")
print("  Logika: Train MAPE << Test MAPE → overfitting")
print("          Keduanya tinggi         → underfitting")
print("          Keduanya rendah & dekat → generalize baik")

# Hitung train error di level BULANAN (sama dengan walk-forward)
Xtr_all = sc_f.transform(imp_f.transform(df[FEATURE_COLS].values))
y_tr_pred = xgb_final.predict(Xtr_all)

df_train_eval = df[["period_str"]].copy()
df_train_eval["pred"] = y_tr_pred
df_train_eval["actual"] = df["demand"].values

monthly_train = (
    df_train_eval.groupby("period_str")
    .agg(pred_total=("pred", "sum"), act_total=("actual", "sum"))
    .reset_index()
)

# Hanya bulan yang ada aktualnya (hindari bulan awal yg demand ~0)
monthly_train = monthly_train[monthly_train["act_total"] > 500]

tr_mape_v = (
    np.abs(
        (monthly_train["pred_total"] - monthly_train["act_total"])
        / monthly_train["act_total"]
    )
    * 100
)
tr_mae_v = np.abs(monthly_train["pred_total"] - monthly_train["act_total"])
tr_rmse_v = (monthly_train["pred_total"] - monthly_train["act_total"]) ** 2

train_mape = float(tr_mape_v.mean())
train_mae = float(tr_mae_v.mean())
train_rmse = float(np.sqrt(tr_rmse_v.mean()))
gap_mape = mape - train_mape

print(f"\n  {'Metric':<10} {'Train':>10} {'Test (WF)':>10} {'Gap':>10}  Interpretasi")
print("  " + "-" * 62)
gap_label = (
    "✅ Normal"
    if gap_mape < 5
    else ("⚠ Perhatian" if gap_mape < 10 else "❌ Overfitting")
)
print(
    f"  {'MAPE':<10} {train_mape:>9.2f}% {mape:>9.2f}% {gap_mape:>+9.2f}%  {gap_label}"
)
print(f"  {'MAE':<10} {train_mae:>10,.0f} {mae:>10,.0f} {mae - train_mae:>+10,.0f}")
print(
    f"  {'RMSE':<10} {train_rmse:>10,.0f} {rmse:>10,.0f} {rmse - train_rmse:>+10,.0f}"
)
print(f"  (basis: {len(monthly_train)} bulan training dengan aktual > 500 unit)")

if train_mape < 1 and gap_mape > 5:
    of_verdict = "⚠ OVERFITTING — model terlalu 'hafal' data training"
elif train_mape > 10 and mape > 10:
    of_verdict = "❌ UNDERFITTING — model tidak cukup belajar"
elif gap_mape <= 5:
    of_verdict = "✅ GENERALIZE BAIK — gap train vs test dalam batas wajar"
else:
    of_verdict = "⚠ Perlu investigasi lebih lanjut"
print(f"\n  Verdict: {of_verdict}")


# ── DASHBOARD VISUALISASI (3 Panel) ──────────────────────────────────
print("\n[CHECK 3] Membuat Diagnostic Dashboard (3 panel)...")

fig_diag, axes = plt.subplots(1, 3, figsize=(18, 5))
fig_diag.suptitle(
    f"XGBoost V6+ — Model Health Check Dashboard\n"
    f"MAPE Train={train_mape:.2f}%  Test={mape:.2f}%  Gap={gap_mape:+.2f}%  |  "
    f"Leakage=TIDAK  |  ZeroR improvement={improvement:.1f}%",
    fontsize=11,
    fontweight="bold",
)

# Panel 1: Overfitting Detector — Train vs Test bar
ax1 = axes[0]
metrics_lbl = ["MAPE (%)", "MAE (k unit)", "RMSE (k unit)"]
train_vals = [train_mape, train_mae / 1000, train_rmse / 1000]
test_vals = [mape, mae / 1000, rmse / 1000]
x1 = np.arange(len(metrics_lbl))
w1 = 0.35
b1 = ax1.bar(x1 - w1 / 2, train_vals, w1, label="Train", color="#3498db", alpha=0.85)
b2 = ax1.bar(
    x1 + w1 / 2, test_vals, w1, label="Test (Walk-Forward)", color="#e67e22", alpha=0.85
)
ax1.set_xticks(x1)
ax1.set_xticklabels(metrics_lbl, fontsize=9)
ax1.set_title(
    "Panel 1: Overfitting Detector\nTrain vs Test Error", fontweight="bold", fontsize=10
)
ax1.legend(fontsize=9)
ax1.grid(axis="y", linestyle=":", alpha=0.4)
for bar in list(b1) + list(b2):
    h = bar.get_height()
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        h + 0.05,
        f"{h:.2f}",
        ha="center",
        va="bottom",
        fontsize=8,
    )

# Panel 2: Learning Curve — MAPE per fold vs training size
ax2 = axes[1]
if tscv_results:
    fold_sizes = []
    fold_mapes = []
    for r in tscv_results:
        tr_m = df[df["period_str"] < r["month"]]["period_str"].nunique()
        fold_sizes.append(tr_m)
        fold_mapes.append(abs(r["error"]))
    ax2.plot(
        fold_sizes,
        fold_mapes,
        "o-",
        color="#9b59b6",
        lw=2.5,
        ms=8,
        markerfacecolor="white",
        markeredgewidth=2,
    )
    ax2.axhline(
        mape,
        color="#e74c3c",
        lw=1.5,
        linestyle="--",
        label=f"Walk-Forward MAPE ({mape:.2f}%)",
    )
    ax2.axhline(7, color="gray", lw=1, linestyle=":", alpha=0.7, label="Target 7%")
    for x_, y_, r in zip(fold_sizes, fold_mapes, tscv_results):
        ax2.annotate(
            f"{r['month']}\n{y_:.1f}%",
            xy=(x_, y_),
            xytext=(x_ + 0.3, y_ + 0.3),
            fontsize=8,
            color="#9b59b6",
        )
    ax2.set_xlabel("Jumlah Bulan Training")
    ax2.set_ylabel("Test MAPE (%)")
    ax2.set_title(
        "Panel 2: Learning Curve\n(MAPE per TimeSeriesSplit fold)",
        fontweight="bold",
        fontsize=10,
    )
    ax2.legend(fontsize=9)
    ax2.grid(linestyle=":", alpha=0.4)
else:
    ax2.text(
        0.5,
        0.5,
        "TimeSeriesSplit\ntidak menghasilkan\ndata dengan aktual",
        ha="center",
        va="center",
        transform=ax2.transAxes,
        fontsize=11,
    )

# Panel 3: Feature Importance Top 10
ax3 = axes[2]
fi_vals = xgb_final.feature_importances_
fi_pairs = sorted(zip(FEATURE_COLS, fi_vals), key=lambda x: x[1], reverse=True)[:10]
fi_names = [p[0] for p in fi_pairs]
fi_imps = [p[1] for p in fi_pairs]
colors3 = [
    "#e74c3c" if imp > 0.1 else ("#f39c12" if imp > 0.02 else "#2ecc71")
    for imp in fi_imps
]
bars3 = ax3.barh(range(len(fi_names)), fi_imps, color=colors3, alpha=0.85)
ax3.set_yticks(range(len(fi_names)))
ax3.set_yticklabels(fi_names, fontsize=9)
ax3.invert_yaxis()
ax3.set_xlabel("Importance")
ax3.set_title(
    "Panel 3: Feature Importance Top 10\nMerah=dominan | Kuning=sedang | Hijau=rendah",
    fontweight="bold",
    fontsize=10,
)
ax3.grid(axis="x", linestyle=":", alpha=0.4)
for bar, imp in zip(bars3, fi_imps):
    ax3.text(
        bar.get_width() + 0.002,
        bar.get_y() + bar.get_height() / 2,
        f"{imp:.3f}",
        va="center",
        fontsize=8,
    )

plt.tight_layout()
plt.savefig("V6_diagnostic_dashboard.png", dpi=130, bbox_inches="tight")
plt.show()
print("  Dashboard saved: V6_diagnostic_dashboard.png")
print("=" * 70)
print("\n[DONE] fwd_results tersedia untuk Script_layer2_distribution.py")

# ==============================================================================
# STEP 10: SERIALISASI MODEL (JOBLIB DUMP)
# Mengekspor XGBoost model, imputer, scaler, dan historical df ke dalam 1 file
# ==============================================================================
print("\n[STEP 10] Export Model Artifact to Joblib")
try:
    import joblib
    from datetime import datetime

    # 1. Pastikan Layer1_Core.py ada di direktori yang sama
    from Layer1_Core import Layer1Model

    # 2. Susun Metadata
    export_metadata = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_version": "V6+ (22 features + share smoother)",
        "training_period_end": _last_ps,
        "performance_metrics": {
            "mape": round(mape, 2),
            "mae": round(mae, 0),
            "rmse": round(rmse, 0),
        },
        "base_month_idx": MIDX.get(_last_ps, 35),
        "base_period_str": _last_ps,
        # Forward prediction results — disimpan agar test script tidak perlu hardcode referensi
        "fwd_results": {
            m: {
                "pred_final": int(fwd_results[m]["pred_final"]),
                "by_variant": {v: int(val) for v, val in fwd_results[m]["by_variant"].items()},
            }
            for m in FORWARD_MONTHS
        },
        # Kalender yang dipakai saat training (untuk referensi dan konsistensi)
        "future_calendar": {
            m: dict(FUTURE_CALENDAR[m]) for m in FORWARD_MONTHS
        },
        # Data aktual per varian (untuk validasi di test script)
        "act_var_override": {
            m: dict(vals) for m, vals in ACT_VAR_OVERRIDE.items()
        },
        "actuals_override": dict(ACTUALS_OVERRIDE),
        # Daftar Ramadan — disimpan agar bisa diupdate di artifact tanpa retraining
        "ramadan_months": list(RAMADAN_MONTHS),
    }

    # 3. Instantiate Wrapper
    layer1_artifact = Layer1Model(
        model=xgb_final,
        scaler=sc_f,
        imputer=imp_f,
        feature_cols=FEATURE_COLS,
        historical_df=df,
        metadata=export_metadata,
    )

    # 4. Dump ke Joblib — pakai method save_model() dari class
    artifact_filename = "Layer1_XGBoost_V6_Artifact.joblib"
    layer1_artifact.save_model(artifact_filename)
    print(f"  \u2139 File ini self-contained dan bisa diload di server produksi.")
    print(f"  \u2139 Representasi  : {repr(layer1_artifact)}")

except ImportError as e:
    print(f"  \u274c GAGAL DUMP: {e}")
    print("     Pastikan file Layer1_Core.py ada di folder yang sama.")
except Exception as e:
    print(f"  \u274c GAGAL DUMP: Terjadi error saat serialisasi -> {e}")

# ==============================================================================
# STEP 10B: VERIFIKASI ROUND-TRIP (Load Balik & Bandingkan Output)
# Memastikan artifact yang tersimpan menghasilkan prediksi identik dengan training
# ==============================================================================
print("\n[STEP 10B] Verifikasi Round-Trip Artifact")
_roundtrip_ok = False

try:
    from Layer1_Core import Layer1Model as _L1M  # noqa: F811

    print("  Mencoba load artifact yang baru disimpan...")
    loaded_model = _L1M.load_model(artifact_filename)

    print(f"\n  {'Bulan':<10} {'Pred Training':>15} {'Pred Loaded':>14} {'Selisih':>10}  Status")
    print("  " + "\u2500" * 58)

    _all_match = True
    _verify_months = [m for m in FORWARD_MONTHS if fwd_results[m].get("pred_final") is not None]

    for m in _verify_months:
        yr_v, mn_v = int(m[:4]), int(m[5:])
        cal_v = FUTURE_CALENDAR.get(m, {})

        # Rebuild fwd_cache untuk bulan ini (chain mode — sama seperti saat training)
        _fc_verify = {}
        for _prev_m in FORWARD_MONTHS:
            if _prev_m == m:
                break
            _fc_verify[_prev_m] = fwd_results[_prev_m]["by_variant"]

        result_loaded = loaded_model.predict(yr_v, mn_v, cal_v, fwd_cache=_fc_verify)
        pred_training = fwd_results[m]["pred_final"]
        pred_loaded   = result_loaded["pred_final"]
        delta         = pred_loaded - pred_training

        # Toleransi: selisih <= 1 unit (efek rounding integer yang tidak bisa dihindari)
        status = "\u2705 MATCH" if abs(delta) <= 1 else f"\u26a0 BEDA ({delta:+})"
        if abs(delta) > 1:
            _all_match = False

        print(f"  {m:<10} {pred_training:>15,} {pred_loaded:>14,} {delta:>+10}  {status}")

    print()
    if _all_match:
        print("  \u2705 ROUND-TRIP VERIFIED: Semua bulan match \u2014 artifact siap dipakai production!")
        _roundtrip_ok = True
    else:
        print("  \u26a0  ROUND-TRIP MISMATCH: Ada perbedaan output \u2014 periksa fwd_cache atau Step 9 logic.")

except FileNotFoundError:
    print("  \u26a0  Verifikasi dilewati \u2014 artifact belum berhasil disimpan di step sebelumnya.")
except Exception as e:
    print(f"  \u274c Verifikasi gagal: {e}")

print("\n" + "=" * 70)
if _roundtrip_ok:
    print(f"  [FINAL] Artifact '{artifact_filename}' VERIFIED & READY FOR PRODUCTION.")
else:
    print(f"  [FINAL] Artifact mungkin bermasalah \u2014 periksa log di atas sebelum deploy.")
print("=" * 70)

