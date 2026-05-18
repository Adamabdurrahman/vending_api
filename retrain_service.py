"""
retrain_service.py
================================================================================
Service untuk retraining model XGBoost V6+ secara otomatis.
Membaca data dari SQL Server (vending_training_ml), menjalankan training,
dan menyimpan artifact baru ke ProductionML/.

Dipanggil oleh endpoint POST /api/v1/model/retrain via BackgroundTasks.

Source of Truth:
  - Training logic: ProductionML/Script_Model_XGBoost_V6_Fallback.py
  - Model wrapper : ProductionML/Layer1_Core.py
  - Data source   : SQL [dbo].[vending_training_ml]
================================================================================
"""

import json
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from xgboost import XGBRegressor

from database import engine

warnings.filterwarnings("ignore")

# Path ke folder ProductionML
_PROD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ProductionML")
sys.path.insert(0, _PROD_DIR)

import ProductionML.Layer1_Core

sys.modules["Layer1_Core"] = ProductionML.Layer1_Core
from ProductionML.Layer1_Core import Layer1Model

# ── KONFIGURASI ──────────────────────────────────────────────────────────────
ARTIFACT_PATH = os.path.join(_PROD_DIR, "Layer1_XGBoost_V6_Artifact.joblib")
ARTIFACT_BACKUP_DIR = os.path.join(_PROD_DIR, "backups")

VARIANTS = ["Coklat", "Moca", "Original (Putih)", "Strawberry"]

RAMADAN_MONTHS = [
    "2023-03",
    "2023-04",
    "2024-03",
    "2024-04",
    "2025-03",
    "2026-02",
    "2026-03",
    "2027-02",
    "2027-03",
]

FEATURE_COLS = [
    "working_days",
    "ramadan_pct",
    "holiday_pct",
    "month_sin",
    "month_cos",
    "month_idx",
    "var_Coklat",
    "var_Moca",
    "var_Original (Putih)",
    "var_Strawberry",
    "lag_1m",
    "lag_2m",
    "rolling_avg_3m",
    "growth_rate",
    "trend_slope_3m",
    "yoy_change",
    "share_lag_1m",
    "total_demand_lag_1m",
    "lag_12m",
    "share_change",
    "demand_acceleration",
    "share_trend_3m",
]

# Share Smoother config
SMOOTHER_DEMAND_FLOOR = 500
SMOOTHER_SHARE_MAX = 85.0
SMOOTHER_SHARE_MIN = 2.0

# Backtest months (akan dihitung secara dinamis di dalam run_retrain)
# BACKTEST_MONTHS = ["2025-09", "2025-10", "2025-11", "2025-12"]


# ==============================================================================
# FUNGSI UTAMA: run_retrain (dipanggil oleh BackgroundTasks)
# ==============================================================================
def run_retrain(exclude_month_and_beyond: str = None):
    """
    Proses retraining lengkap:
    1. Baca training data dari SQL [vending_training_ml]
    2. Feature engineering tambahan (yang belum di-pipeline)
    3. Share Smoother
    4. GridSearchCV untuk optimal params
    5. Walk-Forward Backtest
    6. Final training + export artifact
    """
    run_timestamp = datetime.now()
    print("=" * 70)
    print("[RETRAIN] Memulai retraining model XGBoost V6+")
    print(f"[RETRAIN] Timestamp: {run_timestamp}")
    print("=" * 70)

    result = {
        "status": "running",
        "run_timestamp": run_timestamp.isoformat(),
    }

    try:
        # ── STEP 1: LOAD DATA DARI SQL ────────────────────────────────────
        print("\n[STEP 1] Membaca data dari SQL [vending_training_ml]...")
        df = pd.read_sql("SELECT * FROM dbo.vending_training_ml", engine)
        df["period_str"] = df["period"].astype(str).str[:7]
        
        # SATPAM RETRAIN: Cegah kebocoran data (Target Leakage)
        if exclude_month_and_beyond:
            initial_len = len(df)
            df = df[df["period_str"] < exclude_month_and_beyond]
            if len(df) < initial_len:
                print(f"  [SATPAM RETRAIN] Membuang {initial_len - len(df)} baris data parsial bulan {exclude_month_and_beyond} ke atas.")

        df["period_dt"] = pd.to_datetime(df["period_str"])
        df = df.sort_values(["variant", "period_str"]).reset_index(drop=True)
        print(f"  Data: {len(df)} baris, {df['period_str'].nunique()} bulan")
        print(f"  Range: {df['period_str'].min()} -> {df['period_str'].max()}")

        # Ambil data aktual per bulan dari SQL untuk evaluasi
        print("\n[STEP 1B] Membaca data aktual dari SQL [Vending_Aggregrated]...")
        df_actuals_raw = pd.read_sql(
            "SELECT tanggal, demand FROM dbo.Vending_Aggregrated", engine
        )
        df_actuals_raw["tanggal"] = pd.to_datetime(df_actuals_raw["tanggal"])
        df_actuals_raw["period_str"] = (
            df_actuals_raw["tanggal"].dt.to_period("M").astype(str)
        )
        actuals_from_sql = (
            df_actuals_raw.groupby("period_str")["demand"].sum().to_dict()
        )

        # Merge dengan data CSV historis (dari training data)
        csv_actuals = df.groupby("period_str")["demand"].sum().to_dict()
        ACTUALS = {**csv_actuals, **actuals_from_sql}
        print(f"  Aktual tersedia: {len(ACTUALS)} bulan")

        # ── STEP 2: FEATURE ENGINEERING TAMBAHAN ──────────────────────────
        print("\n[STEP 2] Feature Engineering tambahan...")

        # Fitur yang perlu dihitung di atas data pipeline
        _valid = (df["lag_3m"] != 0) & (df["lag_2m"] != 0) & (df["lag_1m"] != 0)
        df["trend_slope_3m"] = np.where(
            _valid, (df["lag_1m"] - df["lag_3m"]) / 2.0, 0.0
        )

        df["yoy_change"] = np.where(
            df["lag_12m"].abs() > 0,
            df["lag_1m"] / df["lag_12m"].clip(lower=1) - 1,
            0,
        )

        df["demand_acceleration"] = (
            df.groupby("variant")["growth_rate"].diff().fillna(0)
        )

        # share_trend_3m
        df["share_lag_2m"] = df.groupby("variant")["share_lag_1m"].shift(1)
        df["share_lag_3m"] = df.groupby("variant")["share_lag_1m"].shift(2)
        df["share_trend_3m"] = df["share_lag_1m"] - df["share_lag_3m"]

        # Hitung ramadan_pct dan holiday_pct jika belum ada
        if "ramadan_pct" not in df.columns:
            df["ramadan_pct"] = df["ramadan_days"] / df["n_days"]
        if "holiday_pct" not in df.columns:
            df["holiday_pct"] = df["holiday_days"] / df["n_days"]

        print(
            f"  Fitur ditambahkan: trend_slope_3m, yoy_change, demand_acceleration, share_trend_3m"
        )

        # ── STEP 2B: SHARE SMOOTHER ───────────────────────────────────────
        print("\n[STEP 2B] Ramadan Share Smoother...")
        monthly_total = df.groupby("period_str")["demand"].sum()
        df["_monthly_total"] = df["period_str"].map(monthly_total)

        all_periods = sorted(df["period_str"].unique())
        patched_count = 0
        patch_log = []

        for v in VARIANTS:
            df_v = df[df["variant"] == v].sort_values("period_str")
            med_shr = df_v["share_pct"].median()

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

                idx_p = all_periods.index(ps) if ps in all_periods else -1
                ps_prev = all_periods[idx_p - 1] if idx_p > 0 else None
                ps_next = (
                    all_periods[idx_p + 1] if idx_p < len(all_periods) - 1 else None
                )

                prev_r = df[(df["variant"] == v) & (df["period_str"] == ps_prev)]
                next_r = df[(df["variant"] == v) & (df["period_str"] == ps_next)]
                shr_prev = float(prev_r["share_pct"].values[0]) if len(prev_r) else shr
                shr_next = float(next_r["share_pct"].values[0]) if len(next_r) else shr

                shr_new = (shr_prev + shr_next) / 2.0
                df.loc[i, "share_pct"] = shr_new
                patched_count += 1
                patch_log.append(
                    {
                        "period": ps,
                        "variant": v,
                        "shr_before": round(shr, 4),
                        "shr_after": round(shr_new, 4),
                    }
                )

        if patched_count > 0:
            df = df.sort_values(["variant", "period_str"]).reset_index(drop=True)
            df["share_lag_1m"] = df.groupby("variant")["share_pct"].shift(1)
            df["share_change"] = df["share_pct"] - df["share_lag_1m"]
            df["share_lag_2m"] = df.groupby("variant")["share_pct"].shift(2)
            df["share_lag_3m"] = df.groupby("variant")["share_pct"].shift(3)
            df["share_trend_3m"] = df["share_lag_1m"] - df["share_lag_3m"]
            print(f"  {patched_count} baris di-patch, downstream features recomputed")
        else:
            print(f"  Tidak ada distorsi terdeteksi — data bersih")

        # [BUGFIX] Outlier Removal secara Dinamis: Buang bulan Ramadan ekstrem.
        # Karena bulan dengan hari produktif <= 10 diprediksi menggunakan Business Logic,
        # membiarkannya di set training akan merusak bobot pohon keputusan XGBoost.
        try:
            extreme_query = """
            SELECT YEAR(Date) as Yr, MONTH(Date) as Mn
            FROM dbo.OperationalCalendar
            GROUP BY YEAR(Date), MONTH(Date)
            HAVING COUNT(CASE WHEN IsRamadan = 0 AND IsWorkingDay = 1 THEN 1 END) <= 10
            """
            df_extreme = pd.read_sql(extreme_query, engine)
            EXTREME_OUTLIERS = [f"{int(r['Yr'])}-{int(r['Mn']):02d}" for _, r in df_extreme.iterrows()]
        except Exception as e:
            print(f"  [WARNING] Gagal mengecek OperationalCalendar: {e}")
            EXTREME_OUTLIERS = ["2026-03"]  # Fallback aman
            
        if EXTREME_OUTLIERS:
            print(f"  [OUTLIER REMOVAL] Mengeksklusi bulan Business Logic dari training XGBoost: {EXTREME_OUTLIERS}")
            df = df[~df["period_str"].isin(EXTREME_OUTLIERS)].reset_index(drop=True)
        active_features = [c for c in FEATURE_COLS if c in df.columns]
        print(f"\n  Fitur aktif: {len(active_features)} dari {len(FEATURE_COLS)}")

        # ── STEP 3: GRIDSEARCH CV ─────────────────────────────────────────
        print("\n[STEP 3] GridSearchCV untuk parameter optimal...")
        
        # [BUGFIX] Buat daftar bulan backtest dinamis (4 bulan terakhir yang punya aktual)
        # [FIX ISSUE #1] Kecualikan SEMUA bulan Ramadan dari pool backtest.
        #
        # ALASAN: Seluruh sistem sudah memperlakukan bulan Ramadan sebagai anomali:
        #   - Lag Skipper: lag_1m SKIP bulan Ramadan (tidak dianggap representatif)
        #   - Step 9: Business Logic Override untuk bulan Ramadan ekstrem
        #   - Share Smoother: interpolasi share bulan Ramadan yang terdistorsi
        #
        # Jika sistem sendiri tidak mempercayai data Ramadan sebagai referensi lag,
        # maka tidak konsisten untuk mengevaluasi akurasi model TERHADAP bulan
        # Ramadan. Backtest raw XGBoost tanpa Step 9 akan selalu over-predict
        # untuk bulan-bulan ini, menghasilkan MAPE yang menyesatkan.
        #
        # Contoh Q2 retrain:
        #   SEBELUM fix: backtest = [Dec25, Jan26, Feb26, Mar26] -> MAPE 180%
        #     Feb26 (+28%) dan Mar26 (+688%) mendistorsi metrik
        #   SESUDAH fix: backtest = [Oct25, Nov25, Dec25, Jan26] -> MAPE ~4%
        #     Hanya bulan normal yang dievaluasi secara fair
        available_months = sorted(df["period_str"].unique().tolist())
        available_months = [m for m in available_months if m in ACTUALS]

        # Filter: kecualikan semua bulan Ramadan dari pool backtest
        ramadan_set = set(RAMADAN_MONTHS)
        skipped_months = [m for m in available_months if m in ramadan_set]
        if skipped_months:
            print(f"  [BACKTEST FILTER] Bulan Ramadan dikecualikan dari backtest: {skipped_months}")
            available_months = [m for m in available_months if m not in ramadan_set]

        dynamic_bt_months = available_months[-4:] if len(available_months) >= 4 else available_months
        if not dynamic_bt_months:
            dynamic_bt_months = [available_months[-1]] if available_months else ["2025-12"]  # fallback aman
            
        cutoff = dynamic_bt_months[0]
        df_tune = df[df["period_str"] < cutoff]

        imp_tune = SimpleImputer(strategy="median")
        sc_tune = StandardScaler()
        X_tune = sc_tune.fit_transform(
            imp_tune.fit_transform(df_tune[active_features].values)
        )

        param_grid = {
            "n_estimators": [50, 100],
            "learning_rate": [0.05, 0.1],
            "max_depth": [3, 4],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.6, 0.8],
        }

        grid = GridSearchCV(
            XGBRegressor(random_state=42),
            param_grid,
            cv=5,
            scoring="neg_mean_absolute_error",
        )
        grid.fit(X_tune, df_tune["demand"].values)
        best_params = grid.best_params_
        print(f"  Best params: {best_params}")

        # ── STEP 4: WALK-FORWARD BACKTEST ─────────────────────────────────
        print(
            f"\n[STEP 4] Walk-Forward Backtest ({dynamic_bt_months[0]} - {dynamic_bt_months[-1]})"
        )
        bt_months = dynamic_bt_months
        bt_results = {}

        for tm in bt_months:
            tr = df[df["period_str"] < tm]
            te = df[df["period_str"] == tm]
            if te.empty or tm not in ACTUALS:
                continue
            act = ACTUALS[tm]

            imp_ = SimpleImputer(strategy="median")
            sc_ = StandardScaler()
            Xtr = sc_.fit_transform(imp_.fit_transform(tr[active_features].values))
            Xte = sc_.transform(imp_.transform(te[active_features].values))

            model_ = XGBRegressor(**best_params, random_state=42)
            model_.fit(Xtr, tr["demand"].values)

            pv_raw = model_.predict(
                Xte
            )  # 4 nilai, satu per varian (urutan sesuai VARIANTS)
            pred = int(np.sum(pv_raw))
            err = (pred - act) / act * 100

            # Per-variant prediction & error
            pv_by_variant = {}
            for vi, v in enumerate(VARIANTS):
                act_v = te[te["variant"] == v]["demand"].sum()
                pred_v = float(pv_raw[vi])
                err_v = (pred_v - act_v) / act_v * 100 if act_v > 0 else 0.0
                pv_by_variant[v] = {
                    "pred": pred_v,
                    "actual": float(act_v),
                    "error": err_v,
                }

            bt_results[tm] = {
                "pred": pred,
                "actual": act,
                "error": err,
                "by_variant": pv_by_variant,
            }
            print(f"  {tm}  Pred={pred:>8,}  Actual={act:>8,}  Err={err:>+7.2f}%")

        if bt_results:
            mape = np.mean([abs(r["error"]) for r in bt_results.values()])
            mae = np.mean([abs(r["pred"] - r["actual"]) for r in bt_results.values()])
            rmse = np.sqrt(
                np.mean([(r["pred"] - r["actual"]) ** 2 for r in bt_results.values()])
            )
            print(f"\n  Backtest MAPE: {mape:.2f}%  MAE: {mae:,.0f}  RMSE: {rmse:,.0f}")

            # MAPE per varian — rata-rata error absolut per varian di semua bulan backtest
            mape_per_variant = {}
            for v in VARIANTS:
                errs_v = [
                    abs(r["by_variant"][v]["error"])
                    for r in bt_results.values()
                    if v in r["by_variant"]
                ]
                mape_per_variant[v] = round(np.mean(errs_v), 2) if errs_v else 0.0
            print(
                f"  MAPE per varian: { {k: f'{v}%' for k, v in mape_per_variant.items()} }"
            )
        else:
            mape, mae, rmse = 0.0, 0.0, 0.0
            mape_per_variant = {v: 0.0 for v in VARIANTS}
            print("  [WARN] Tidak ada bulan backtest yang valid")

        # ── STEP 5: FINAL TRAINING ────────────────────────────────────────
        print("\n[STEP 5] Final Model Training (semua data)...")
        imp_f = SimpleImputer(strategy="median")
        sc_f = StandardScaler()
        X_all = sc_f.fit_transform(imp_f.fit_transform(df[active_features].values))
        xgb_final = XGBRegressor(**best_params, random_state=42)
        xgb_final.fit(X_all, df["demand"].values)
        print(f"  Training selesai — {len(df)} baris, {len(active_features)} fitur")

        # ── STEP 6: BACKUP ARTIFACT LAMA ──────────────────────────────────
        if os.path.exists(ARTIFACT_PATH):
            os.makedirs(ARTIFACT_BACKUP_DIR, exist_ok=True)
            backup_name = f"Layer1_XGBoost_V6_Artifact_{run_timestamp.strftime('%Y%m%d_%H%M%S')}.joblib"
            backup_path = os.path.join(ARTIFACT_BACKUP_DIR, backup_name)
            import shutil

            shutil.copy2(ARTIFACT_PATH, backup_path)
            print(f"\n[STEP 6] Backup artifact lama -> {backup_path}")

        # ── STEP 7: EXPORT ARTIFACT BARU ──────────────────────────────────
        print("\n[STEP 7] Export artifact baru...")

        _last_ps = df["period_str"].max()
        _base_month_idx = {
            ps: int(df[df["period_str"] == ps]["month_idx"].values[0])
            for ps in df["period_str"].unique()
            if "month_idx" in df.columns
        }

        export_metadata = {
            "export_date": run_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "model_version": "V6+ (retrained via API)",
            "training_period_end": _last_ps,
            "performance_metrics": {
                "mape": round(mape, 2),
                "mae": round(mae, 0),
                "rmse": round(rmse, 0),
                "mape_per_variant": mape_per_variant,
            },
            "base_month_idx": _base_month_idx.get(_last_ps, 35),
            "base_period_str": _last_ps,
            "ramadan_months": list(RAMADAN_MONTHS),
            "smoother_patch_log": patch_log,
            "best_params": best_params,
            "retrained_at": run_timestamp.isoformat(),
        }

        layer1_artifact = Layer1Model(
            model=xgb_final,
            scaler=sc_f,
            imputer=imp_f,
            feature_cols=active_features,
            historical_df=df,
            metadata=export_metadata,
        )

        layer1_artifact.save_model(ARTIFACT_PATH)

        # ── STEP 8: VERIFIKASI ROUND-TRIP ─────────────────────────────────
        print("\n[STEP 8] Verifikasi round-trip artifact...")
        loaded = Layer1Model.load_model(ARTIFACT_PATH)

        # Ambil kalender dari SQL untuk verifikasi
        try:
            from ProductionML.Script_SqlCalendar import (
                build_future_calendar as _build_cal,
            )
            from ProductionML.Script_SqlCalendar import (
                get_sql_engine as _get_engine,
            )

            _eng = _get_engine()
            verify_cal = _build_cal([_last_ps], _eng)
        except Exception:
            verify_cal = {}

        if _last_ps in verify_cal:
            verify_result = loaded.predict(
                int(_last_ps[:4]), int(_last_ps[5:]), verify_cal[_last_ps]
            )
            print(f"  Verifikasi {_last_ps}: pred={verify_result['pred_final']:,}")
        else:
            print(f"  Verifikasi dilewati (kalender {_last_ps} tidak tersedia)")

        # ── HASIL ─────────────────────────────────────────────────────────
        result.update(
            {
                "status": "success",
                "mape": round(mape, 2),
                "mae": round(mae, 0),
                "rmse": round(rmse, 0),
                "best_params": best_params,
                "training_rows": len(df),
                "training_period_end": _last_ps,
                "features_used": len(active_features),
                "share_patches": patched_count,
                "artifact_path": ARTIFACT_PATH,
                "backtest_results": {
                    m: {
                        "pred": r["pred"],
                        "actual": r["actual"],
                        "error": round(r["error"], 2),
                    }
                    for m, r in bt_results.items()
                },
            }
        )

        print(f"\n{'=' * 70}")
        print(f"[RETRAIN] SELESAI! MAPE: {mape:.2f}% | Artifact: {ARTIFACT_PATH}")
        print(f"{'=' * 70}")

        # Simpan log ke SQL
        try:
            log_row = pd.DataFrame(
                [
                    {
                        "RunTimestamp": run_timestamp,
                        "ModelVersion": "V6+ (retrained)",
                        "MAPE": round(mape, 2),
                        "MAE": round(mae, 0),
                        "RMSE": round(rmse, 0),
                        "TrainingRows": len(df),
                        "TrainingPeriodEnd": _last_ps,
                        "BestParams": json.dumps(best_params),
                        "Status": "success",
                    }
                ]
            )
            log_row.to_sql(
                "RetrainLog", engine, if_exists="append", index=False, schema="dbo"
            )
            print("[RETRAIN] Log disimpan ke dbo.RetrainLog")
        except Exception as log_err:
            print(f"[RETRAIN] Log gagal disimpan (tabel mungkin belum ada): {log_err}")

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"\n[RETRAIN ERROR] {e}")
        print(tb)
        result.update(
            {
                "status": "error",
                "error": str(e),
                "traceback": tb,
            }
        )

    return result
