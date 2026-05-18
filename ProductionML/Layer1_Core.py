import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

class Layer1Model:
    """
    Self-contained model wrapper for Layer 1 XGBoost V6+
    """
    def __init__(self, model, scaler, imputer, feature_cols, historical_df, metadata):
        self.model = model
        self.scaler = scaler
        self.imputer = imputer
        self.feature_cols = feature_cols

        # Bersihkan dataframe dari kolom sementara/fungsi
        # Kita hanya butuh data dasar untuk menghitung lag/momentum saat inference
        keep_cols = ["period_str", "variant", "demand", "share_pct", "share_change", "growth_rate"]

        # Pastikan hanya mengambil kolom yang eksis di historical_df
        existing_cols = [c for c in keep_cols if c in historical_df.columns]
        self.historical_df = historical_df[existing_cols].copy()
        
        # [BUGFIX] Cegah NotImplementedError saat unpickling di Pandas 2.x
        if "period_str" in self.historical_df.columns:
            self.historical_df["period_str"] = self.historical_df["period_str"].astype(object)

        # Hapus index dan ubah menjadi dictionary-like internal jika mau lebih aman dari lambda
        # Tapi copy dataframe string/numerik biasanya 100% aman diserialisasi joblib.

        self.metadata = metadata
        self.VARIANTS = ["Coklat", "Moca", "Original (Putih)", "Strawberry"]
        self.ANOMALY_DEMAND_THRESHOLD = 100

        # Baca RAMADAN_MONTHS dari metadata artifact.
        # Jika tidak ada (artifact lama), pakai default hardcode sebagai fallback.
        _default_ramadan = [
            "2023-03", "2023-04",
            "2024-03", "2024-04",
            "2025-03",
            "2026-02", "2026-03",
            "2027-02", "2027-03",
        ]
        self.RAMADAN_MONTHS = metadata.get("ramadan_months", _default_ramadan)

        self.base_month_idx = metadata.get("base_month_idx", 35)
        self.base_period_str = metadata.get("base_period_str", "2025-12")

    def _get_month_idx(self, period_str):
        try:
            b_yr, b_mn = int(self.base_period_str[:4]), int(self.base_period_str[5:])
            t_yr, t_mn = int(period_str[:4]), int(period_str[5:])
            offset = (t_yr - b_yr) * 12 + (t_mn - b_mn)
            return self.base_month_idx + offset
        except Exception:
            return self.base_month_idx + 1

    def _month_str(self, yr, mn):
        t = (yr - 1) * 12 + mn
        return f"{(t - 1) // 12 + 1}-{(t - 1) % 12 + 1:02d}"

    def _is_ramadan(self, period_str):
        # Baca dari self.RAMADAN_MONTHS yang diisi metadata saat load.
        # Tambah tahun baru: cukup update metadata artifact, tanpa retraining.
        return period_str in self.RAMADAN_MONTHS

    def _get_normal_lag_month(self, yr, mn, lag_n):
        curr_yr, curr_mn = yr, mn
        count = 0
        while count < lag_n:
            curr_mn -= 1
            if curr_mn == 0:
                curr_mn = 12
                curr_yr -= 1
            ps = f"{curr_yr}-{curr_mn:02d}"
            # Lompat jika bulan ini adalah Ramadan
            if not self._is_ramadan(ps):
                count += 1
        return f"{curr_yr}-{curr_mn:02d}"

    def _get_hist_demand(self, period_str, variant=None):
        if variant:
            row = self.historical_df[(self.historical_df["period_str"] == period_str) & (self.historical_df["variant"] == variant)]
            return float(row["demand"].values[0]) if len(row) else 0.0
        total = self.historical_df[self.historical_df["period_str"] == period_str]["demand"].sum()
        return float(total) if total else 0.0

    def build_features(self, year, month, target_calendar, fwd_cache=None):
        if fwd_cache is None:
            fwd_cache = {}

        ps = f"{year}-{month:02d}"
        cal = target_calendar
        n_days = cal.get("n_days", 30)
        ram_d = cal.get("ramadan_days", 0)
        hol_d = cal.get("holiday_days", 0)
        wknd_d = cal.get("weekend_days", 8)
        wday = cal.get("working_days", 22)

        rows = []
        for v in self.VARIANTS:
            # Menggunakan INFERENCE-ONLY Lag Skipper:
            # Memastikan lag_1, lag_2, lag_3 mengambil bulan normal terakhir (mengabaikan puasa)
            p1 = self._get_normal_lag_month(year, month, 1)
            p2 = self._get_normal_lag_month(year, month, 2)
            p3 = self._get_normal_lag_month(year, month, 3)
            # lag_12m harus TETAP absolut 12 bulan yang lalu (karena untuk Year-over-Year)
            p12 = self._month_str(year, month - 12)

            def _get(p, var):
                return (
                    fwd_cache[p][var]
                    if p in fwd_cache and var in fwd_cache[p]
                    else self._get_hist_demand(p, var)
                )

            lag1 = _get(p1, v)
            lag2 = _get(p2, v)
            lag3 = _get(p3, v)
            lag12 = _get(p12, v)
            roll3 = np.mean([lag1, lag2, lag3])

            gr = np.clip(lag1 / max(lag2, 1) - 1 if lag2 > 0 else 0, -1, 5)

            # Guard YoY: set 0.0 jika referensi 12-bulan-lalu adalah Ramadan
            # (menghindari perbandingan "normal bulan ini" vs "Ramadan setahun lalu")
            # Ini inference-only — tidak mengubah feature training.
            if lag12 < self.ANOMALY_DEMAND_THRESHOLD or self._is_ramadan(p12):
                yoy = 0.0
            else:
                yoy = np.clip(lag1 / lag12 - 1, -1, 5)

            tot_l1 = sum(_get(p1, vv) for vv in self.VARIANTS)
            tot_l1_v = max(tot_l1, 1)
            shr_lag1 = lag1 / tot_l1_v * 100

            prev_row = self.historical_df[(self.historical_df["variant"] == v) & (self.historical_df["period_str"] == p1)]
            shr_lag1 = float(prev_row["share_pct"].values[0]) if len(prev_row) else shr_lag1

            if len(prev_row):
                shr_chg = float(prev_row["share_change"].values[0])
            else:
                _p2_share_row = self.historical_df[(self.historical_df["variant"] == v) & (self.historical_df["period_str"] == p2)]
                _shr_p2 = float(_p2_share_row["share_pct"].values[0]) if len(_p2_share_row) else shr_lag1
                shr_chg = shr_lag1 - _shr_p2

            p3_row = self.historical_df[(self.historical_df["variant"] == v) & (self.historical_df["period_str"] == p3)]
            shr_lag3 = float(p3_row["share_pct"].values[0]) if len(p3_row) else shr_lag1
            shr_trend_3m = shr_lag1 - shr_lag3

            t_slope = (lag1 - lag3) / 2.0 if all([lag3, lag2, lag1]) else 0.0

            gr_prev = float(prev_row["growth_rate"].values[0]) if len(prev_row) else 0.0
            d_accel = gr - gr_prev

            rows.append({
                "working_days": wday,
                "ramadan_pct": ram_d / n_days,
                "holiday_pct": hol_d / n_days,
                "month_sin": np.sin(2 * np.pi * month / 12),
                "month_cos": np.cos(2 * np.pi * month / 12),
                "month_idx": self._get_month_idx(ps),
                "var_Coklat": 1 * (v == "Coklat"),
                "var_Moca": 1 * (v == "Moca"),
                "var_Original (Putih)": 1 * (v == "Original (Putih)"),
                "var_Strawberry": 1 * (v == "Strawberry"),
                "lag_1m": lag1,
                "lag_2m": lag2,
                "rolling_avg_3m": roll3,
                "growth_rate": gr,
                "trend_slope_3m": t_slope,
                "yoy_change": yoy,
                "share_lag_1m": shr_lag1,
                "total_demand_lag_1m": tot_l1,
                "lag_12m": lag12,
                "share_change": shr_chg,
                "demand_acceleration": d_accel,
                "share_trend_3m": shr_trend_3m,
                "variant": v,
            })
        return pd.DataFrame(rows)

    def predict(self, year, month, target_calendar, fwd_cache=None):
        df_in = self.build_features(year, month, target_calendar, fwd_cache)
        for c in self.feature_cols:
            if c not in df_in.columns:
                df_in[c] = 0.0

        Xin = self.scaler.transform(self.imputer.transform(df_in[self.feature_cols].values))
        pv_raw = self.model.predict(Xin)
        pred_raw = int(np.sum(pv_raw))

        pv_raw_d = {self.VARIANTS[i]: pv_raw[i] for i in range(len(self.VARIANTS))}
        pv_final_d = pv_raw_d.copy()

        # Step 9 Business Logic Fallback
        # Gunakan 'productive_milk_days' jika didefinisikan (hari aktif NON-puasa),
        # jika tidak ada, fallback mengecek 'working_days'.
        productive_days = target_calendar.get("productive_milk_days", target_calendar.get("working_days", 30))

        # Batas aktivasi Step 9 diperlebar menjadi <= 10 hari untuk antisipasi masa depan
        if productive_days <= 10:
            pred_fallback = 0
            for vi, v in enumerate(self.VARIANTS):
                lag_3m_avg = df_in.loc[vi]["rolling_avg_3m"]
                daily_run = lag_3m_avg / 25.0
                # Kalikan dengan jumlah hari produktif
                override_val = int(daily_run * productive_days)
                pv_final_d[v] = override_val
                pred_fallback += override_val
            pred_final = pred_fallback
        else:
            pred_final = pred_raw

        return {
            "pred_raw": pred_raw,
            "pred_final": pred_final,
            "by_variant": pv_final_d,
            "business_logic": productive_days <= 10,
            "productive_days": productive_days,
        }

    # ─────────────────────────────────────────────────────────────────
    # SERIALISASI — save_model() & load_model()
    # ─────────────────────────────────────────────────────────────────

    def save_model(self, filepath: str = "Layer1_XGBoost_V6_Artifact.joblib") -> str:
        """
        Simpan seluruh instance Layer1Model ke file .joblib.
        File ini self-contained: berisi model, scaler, imputer,
        historical_df (yang sudah di-patch Smoother), dan metadata.

        Parameters
        ----------
        filepath : str
            Path tujuan file .joblib. Default: 'Layer1_XGBoost_V6_Artifact.joblib'

        Returns
        -------
        str
            Absolute path dari file yang berhasil disimpan.
        """
        # Pastikan ekstensi .joblib
        if not str(filepath).endswith(".joblib"):
            filepath = str(filepath) + ".joblib"

        abs_path = str(Path(filepath).resolve())
        joblib.dump(self, abs_path)

        file_size_kb = os.path.getsize(abs_path) / 1024
        print(f"  [SAVED] Model disimpan ke: {abs_path}")
        print(f"     Ukuran file   : {file_size_kb:.1f} KB")
        print(f"     Versi model   : {self.metadata.get('model_version', 'N/A')}")
        print(f"     Training s/d  : {self.metadata.get('training_period_end', 'N/A')}")
        print(f"     MAPE backtest : {self.metadata.get('performance_metrics', {}).get('mape', 'N/A')}%")
        return abs_path

    @classmethod
    def load_model(cls, filepath: str) -> "Layer1Model":
        """
        Load Layer1Model dari file .joblib.
        Mengembalikan instance Layer1Model yang siap dipakai untuk inference.

        Parameters
        ----------
        filepath : str
            Path ke file .joblib yang akan di-load.

        Returns
        -------
        Layer1Model
            Instance yang sudah di-load dan siap dipanggil .predict().

        Raises
        ------
        FileNotFoundError
            Jika file tidak ditemukan di path yang diberikan.
        TypeError
            Jika file yang di-load bukan instance Layer1Model.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"File artifact tidak ditemukan: '{filepath}'\n"
                f"Pastikan path benar atau jalankan Script_Model_XGBoost_V6_Fallback.py dulu."
            )

        instance = joblib.load(filepath)

        if not isinstance(instance, cls):
            raise TypeError(
                f"File '{filepath}' bukan instance Layer1Model. "
                f"Type aktual: {type(instance)}"
            )

        file_size_kb = os.path.getsize(filepath) / 1024
        print(f"  [OK] Model berhasil di-load dari: {filepath}")
        print(f"     Ukuran file   : {file_size_kb:.1f} KB")
        print(f"     Versi model   : {instance.metadata.get('model_version', 'N/A')}")
        print(f"     Training s/d  : {instance.metadata.get('training_period_end', 'N/A')}")
        print(f"     Export date   : {instance.metadata.get('export_date', 'N/A')}")
        print(f"     MAPE backtest : {instance.metadata.get('performance_metrics', {}).get('mape', 'N/A')}%")
        return instance

    def __repr__(self) -> str:
        mv = self.metadata.get("model_version", "?")
        pe = self.metadata.get("training_period_end", "?")
        mp = self.metadata.get("performance_metrics", {}).get("mape", "?")
        n_hist = len(self.historical_df)
        return (
            f"<Layer1Model version='{mv}' "
            f"trained_up_to='{pe}' "
            f"mape={mp}% "
            f"hist_rows={n_hist}>"
        )
