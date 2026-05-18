import warnings
import numpy as np
import pandas as pd
import datetime

warnings.filterwarnings("ignore")

try:
    import holidays as pyholidays
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'holidays', '-q'])
    import holidays as pyholidays

RAMADAN_PERIODS = [
    ('2023-03-22', '2023-04-21'),
    ('2024-03-11', '2024-04-09'),
    ('2025-02-28', '2025-03-30'),
    ('2026-02-17', '2026-03-18'),
]

# ─────────────────────────────────────────────────────────────────────────────
# BUG FIX #2: Tambahkan hari libur yang tidak terdeteksi oleh holidays library
# 25 Des 2025 (Natal) jatuh pada hari Kamis (weekday) — harus dihitung sebagai
# holiday_weekday_days, tapi library pyholidays.PUBLIC tidak selalu mendeteksinya.
# Tambahkan secara manual di sini jika diperlukan.
# ─────────────────────────────────────────────────────────────────────────────
EXTRA_HOLIDAYS = {
    datetime.date(2025, 12, 25),   # Natal — tidak terdeteksi library (fix Des 2025)
}

def is_ramadan(date):
    for start, end in RAMADAN_PERIODS:
        if pd.to_datetime(start) <= pd.to_datetime(date) <= pd.to_datetime(end):
            return 1
    return 0

def build_v3_exact_features(input_csv, output_csv):
    print(f"\n[1] Membaca data mentah: {input_csv}")
    df_raw = pd.read_csv(input_csv)
    df_raw['tanggal'] = pd.to_datetime(df_raw['tanggal'])
    
    # ─────────────────────────────────────────────────────────────────────────
    # BUG FIX #3: Inject tanggal yang hilang dari raw data
    # 25 Des 2025 (Natal) tidak ada di CSV sumber karena mesin mati/libur total,
    # sehingga n_days Des 2025 terhitung 30 bukan 31.
    # Solusi: tambahkan baris demand=0 untuk setiap variant pada tanggal hilang tsb.
    # ─────────────────────────────────────────────────────────────────────────
    MISSING_HOLIDAY_DATES = [
        ('2025-12-25', 'Hari Natal'),
    ]
    variants = df_raw['nama_variant'].unique()
    inject_rows = []
    for date_str, ket in MISSING_HOLIDAY_DATES:
        ts = pd.Timestamp(date_str)
        if ts not in df_raw['tanggal'].values:
            for v in variants:
                inject_rows.append({
                    'tanggal': ts,
                    'keterangan': ket,
                    'nama_variant': v,
                    'demand': 0,
                    'is_holiday': 1
                })
    if inject_rows:
        df_inject = pd.DataFrame(inject_rows)
        df_raw = pd.concat([df_raw, df_inject], ignore_index=True).sort_values(['tanggal', 'nama_variant']).reset_index(drop=True)
        print(f"    Injected {len(inject_rows)} baris untuk tanggal libur yang hilang: {[d for d,_ in MISSING_HOLIDAY_DATES]}")

    print("[2] Mengekstrak fitur kalender (Holiday, Weekend, Ramadan)...")
    holidays_id = pyholidays.Indonesia(years=[2023, 2024, 2025, 2026], categories=(pyholidays.PUBLIC,))
    holidays_set = set(holidays_id.keys())

    # BUG FIX #2: gabungkan dengan EXTRA_HOLIDAYS agar Natal Des 2025 terdeteksi
    holidays_set = holidays_set | EXTRA_HOLIDAYS
    print(f"    Total hari libur (library + manual): {len(holidays_set)} hari")

    df_raw['is_holiday'] = df_raw['tanggal'].dt.date.isin(holidays_set).astype(int)
    df_raw['is_weekend'] = (df_raw['tanggal'].dt.dayofweek >= 5).astype(int)
    df_raw['is_ramadan'] = df_raw['tanggal'].apply(is_ramadan)
    
    print("[3] Agregasi harian menjadi bulanan per variant...")
    df_raw['period'] = df_raw['tanggal'].dt.to_period('M')
    
    daily_unique = df_raw.groupby(['period', 'tanggal']).agg({
        'is_ramadan': 'first',
        'is_holiday': 'first',
        'is_weekend': 'first'
    }).reset_index()
    
    monthly_cal = daily_unique.groupby('period').agg(
        n_days=('tanggal', 'nunique'),
        ramadan_days=('is_ramadan', 'sum'),
        holiday_days=('is_holiday', 'sum'),
        weekend_days=('is_weekend', 'sum')
    ).reset_index()
    
    daily_unique['is_holiday_weekday'] = ((daily_unique['is_holiday'] == 1) & (daily_unique['is_weekend'] == 0)).astype(int)
    monthly_cal['holiday_weekday_days'] = daily_unique.groupby('period')['is_holiday_weekday'].sum().values
    monthly_cal['working_days'] = monthly_cal['n_days'] - monthly_cal['weekend_days'] - monthly_cal['holiday_weekday_days']
    
    df_monthly = df_raw.groupby(['period', 'nama_variant']).agg(demand=('demand', 'sum')).reset_index()
    df_monthly = df_monthly.merge(monthly_cal, on='period', how='left')
    df_monthly.rename(columns={'nama_variant': 'variant'}, inplace=True)
    df_monthly['period_str'] = df_monthly['period'].astype(str)
    
    df_monthly['period_ts'] = df_monthly['period'].dt.to_timestamp()
    df_monthly['year'] = df_monthly['period_ts'].dt.year
    df_monthly['month'] = df_monthly['period_ts'].dt.month
    df_monthly['quarter'] = df_monthly['period_ts'].dt.quarter
    
    df_monthly['ramadan_pct'] = df_monthly['ramadan_days'] / df_monthly['n_days']
    df_monthly['holiday_pct'] = df_monthly['holiday_days'] / df_monthly['n_days']
    df_monthly['weekend_pct'] = df_monthly['weekend_days'] / df_monthly['n_days']
    
    df_monthly['month_sin'] = np.sin(2 * np.pi * df_monthly['month'] / 12)
    df_monthly['month_cos'] = np.cos(2 * np.pi * df_monthly['month'] / 12)
    
    unique_periods = sorted(df_monthly['period_str'].unique())
    period_to_idx = {p: i for i, p in enumerate(unique_periods)}
    df_monthly['month_idx'] = df_monthly['period_str'].map(period_to_idx)
    
    df_monthly = pd.get_dummies(df_monthly, columns=['variant'], prefix='var', dtype=int)
    df_monthly['variant'] = df_monthly.apply(
        lambda r: 'Coklat' if r.get('var_Coklat', 0) else 
                  'Moca' if r.get('var_Moca', 0) else 
                  'Original (Putih)' if r.get('var_Original (Putih)', 0) else 'Strawberry', axis=1)

    df_monthly = df_monthly.sort_values(['variant', 'month_idx']).reset_index(drop=True)
    
    print("[4] Menghitung Lags, Trend, dan Market Share...")
    total_demand = df_monthly.groupby('period_str')['demand'].transform('sum')
    df_monthly['share_pct'] = df_monthly['demand'] / total_demand.clip(lower=1) * 100
    
    total_demand_by_period = df_monthly.groupby('period_str')['demand'].sum().reset_index(name='total_demand')
    total_demand_by_period['total_demand_lag_1m'] = total_demand_by_period['total_demand'].shift(1)
    df_monthly = df_monthly.merge(total_demand_by_period[['period_str', 'total_demand_lag_1m']], on='period_str', how='left')
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONDITIONAL RAMADAN LAG SKIPPER (Section 7E — Blueprint)
    # ─────────────────────────────────────────────────────────────────────────
    # DUAL-MODE LAG COMPUTATION:
    #   Historis (< 2026-01): lag_1m, lag_2m, lag_3m dihitung NATURAL (shift biasa)
    #     → Model belajar pola "setelah Ramadan → rebound" dari data historis
    #   Data 2026+         : lag_1m, lag_2m, lag_3m SKIP bulan Ramadan
    #     → Mencegah model melihat demand Ramadan (5K) sebagai "penurunan nyata"
    #     → Tanpa ini, prediksi April 2026 jatuh dari ~76K ke ~50K
    #
    # lag_12m TETAP absolut (tidak di-skip) — untuk referensi Year-over-Year.
    # Jika lag_12m jatuh di bulan Ramadan, YoY Ramadan Guard di Layer1_Core sudah
    # menanganinya (yoy=0.0).
    # ─────────────────────────────────────────────────────────────────────────
    RAMADAN_MONTHS_SET = {
        "2023-03", "2023-04",
        "2024-03", "2024-04",
        "2025-03",
        "2026-02", "2026-03",
        "2027-02", "2027-03",
    }
    SKIP_CUTOFF = "2026-01"  # Mulai dari data 2026, lag di-skip

    def _prev_month_str(period_str):
        """Mundur 1 bulan dari period_str (format 'YYYY-MM')."""
        yr, mn = int(period_str[:4]), int(period_str[5:7])
        mn -= 1
        if mn == 0:
            mn = 12
            yr -= 1
        return f"{yr}-{mn:02d}"

    def _compute_skip_lag(df_var, period_str, lag_n):
        """Hitung lag dengan skip bulan Ramadan (untuk data 2026+)."""
        curr = period_str
        count = 0
        while count < lag_n:
            curr = _prev_month_str(curr)
            if curr not in RAMADAN_MONTHS_SET:
                count += 1
        # Cari demand variant ini di bulan curr
        row = df_var[df_var['period_str'] == curr]
        return float(row['demand'].values[0]) if len(row) > 0 else np.nan

    # Step A: Hitung lag NATURAL dulu (untuk historis < 2026-01)
    df_monthly['lag_1m'] = df_monthly.groupby('variant')['demand'].shift(1)
    df_monthly['lag_2m'] = df_monthly.groupby('variant')['demand'].shift(2)
    df_monthly['lag_3m'] = df_monthly.groupby('variant')['demand'].shift(3)
    df_monthly['lag_12m'] = df_monthly.groupby('variant')['demand'].shift(12)

    # Step B: Override lag untuk data >= SKIP_CUTOFF (2026+)
    mask_skip = df_monthly['period_str'] >= SKIP_CUTOFF
    skip_count = int(mask_skip.sum())
    if skip_count > 0:
        print(f"    [LAG SKIPPER] Menerapkan Conditional Ramadan Lag Skipper untuk {skip_count} baris (>= {SKIP_CUTOFF})")
        print(f"    [LAG SKIPPER] Bulan Ramadan yang di-skip: {sorted(RAMADAN_MONTHS_SET)}")
        for variant in df_monthly['variant'].unique():
            df_var = df_monthly[df_monthly['variant'] == variant][['period_str', 'demand']].copy()
            var_mask = (df_monthly['variant'] == variant) & mask_skip
            for idx in df_monthly[var_mask].index:
                ps = df_monthly.at[idx, 'period_str']
                df_monthly.at[idx, 'lag_1m'] = _compute_skip_lag(df_var, ps, 1)
                df_monthly.at[idx, 'lag_2m'] = _compute_skip_lag(df_var, ps, 2)
                df_monthly.at[idx, 'lag_3m'] = _compute_skip_lag(df_var, ps, 3)
                # lag_12m TETAP absolut — tidak di-skip
        print(f"    [LAG SKIPPER] Selesai — lag 2026+ sekarang mengacu ke bulan normal (bukan Ramadan)")
    else:
        print(f"    [LAG SKIPPER] Tidak ada data >= {SKIP_CUTOFF} — lag dihitung natural (historis saja)")

    # Step C: Recompute downstream features yang bergantung pada lag
    # rolling_avg_3m harus dihitung ULANG dari lag yang sudah di-skip
    df_monthly['rolling_avg_3m'] = df_monthly[['lag_1m', 'lag_2m', 'lag_3m']].mean(axis=1)
    # Untuk baris historis yang lag masih NaN, fallback ke rolling biasa
    hist_nan_mask = df_monthly['rolling_avg_3m'].isna()
    if hist_nan_mask.any():
        rolling_fallback = df_monthly.groupby('variant')['demand'].transform(
            lambda x: x.shift(1).rolling(3, min_periods=1).mean()
        )
        df_monthly.loc[hist_nan_mask, 'rolling_avg_3m'] = rolling_fallback[hist_nan_mask]

    df_monthly['share_lag_1m'] = df_monthly.groupby('variant')['share_pct'].shift(1)
    df_monthly['share_change'] = df_monthly['share_pct'] - df_monthly['share_lag_1m']

    # ─────────────────────────────────────────────────────────────────────────
    # BUG FIX #1: Formula growth_rate yang benar
    # SALAH (lama): (lag_1m / lag_2m) - 1  → mengukur pertumbuhan 2 bulan lalu vs 3 bulan lalu
    # BENAR (fix) : (demand / lag_1m) - 1  → mengukur pertumbuhan bulan ini vs bulan lalu
    # Referensi: V3_m1 Apr-2023 Coklat → demand=3893, lag_1m=28012
    #            growth_rate = (3893/28012)-1 = -0.861024 ✓
    # ─────────────────────────────────────────────────────────────────────────
    df_monthly['growth_rate'] = np.where(
        df_monthly['lag_1m'] > 0,
        (df_monthly['demand'] / df_monthly['lag_1m']) - 1,
        0
    )
    
    print("[5] Menghitung Fitur Same-Month (Histori Tahunan)...")
    def compute_sm_stats(group):
        group = group.sort_values('month_idx')
        for stat in ['share_peak_sm', 'share_min_sm', 'share_mean_sm', 'share_range_sm', 'demand_peak_sm', 'demand_mean_sm']:
            group[stat] = np.nan
            
        for i, row in group.iterrows():
            past = group[(group['month'] == row['month']) & (group['month_idx'] < row['month_idx'])]
            if len(past) > 0:
                shares = past['share_pct'].values
                demands = past['demand'].values
                group.at[i, 'share_peak_sm'] = shares.max()
                group.at[i, 'share_min_sm'] = shares.min()
                group.at[i, 'share_mean_sm'] = shares.mean()
                group.at[i, 'share_range_sm'] = shares.max() - shares.min()
                group.at[i, 'demand_peak_sm'] = demands.max()
                group.at[i, 'demand_mean_sm'] = demands.mean()
        return group
    
    df_monthly = df_monthly.groupby('variant', group_keys=False).apply(compute_sm_stats).reset_index(drop=True)

    # ─────────────────────────────────────────────────────────────────────────
    # BUG FIX #4: groupby('variant').apply() menghapus kolom 'variant' karena
    # dijadikan groupby key secara internal oleh pandas. Reconstruct dari kolom
    # var_ dummy setelah apply selesai.
    # ─────────────────────────────────────────────────────────────────────────
    df_monthly['variant'] = df_monthly.apply(
        lambda r: 'Coklat' if r.get('var_Coklat', 0) else
                  'Moca' if r.get('var_Moca', 0) else
                  'Original (Putih)' if r.get('var_Original (Putih)', 0) else 'Strawberry', axis=1)

    # Filter hanya bulan April 2023 ke atas agar tepat 132 baris seperti V3
    df_monthly = df_monthly[df_monthly['period_str'] >= '2023-04']
    
    # Urutan kolom persis seperti V3
    v3_cols = [
        'period', 'demand', 'n_days', 'ramadan_days', 'holiday_days', 'weekend_days', 
        'period_ts', 'holiday_weekday_days', 'year', 'month', 'quarter', 
        'ramadan_pct', 'holiday_pct', 'weekend_pct', 'working_days', 'month_idx', 
        'var_Coklat', 'var_Moca', 'var_Original (Putih)', 'var_Strawberry', 
        'month_sin', 'month_cos', 'variant', 'lag_1m', 'lag_2m', 'lag_3m', 
        'rolling_avg_3m', 'growth_rate', 'share_pct', 'share_lag_1m', 'share_change', 
        'total_demand_lag_1m', 'lag_12m', 'share_peak_sm', 'share_min_sm', 
        'share_mean_sm', 'share_range_sm', 'demand_peak_sm', 'demand_mean_sm'
    ]
    
    df_final = df_monthly[v3_cols].copy()
    
    print(f"\n[6] Menyimpan dataset siap latih ke: {output_csv}")
    df_final.to_csv(output_csv, index=False)
    print(f"    Berhasil! Shape dataset V3 Exact: {df_final.shape}")
    print("=" * 70)

if __name__ == "__main__":
    print("=" * 70)
    print("PIPELINE DATA BUILDER: V3 EXACT MATCH (FIXED)")
    print("Bug Fix #1: growth_rate = (demand / lag_1m) - 1")
    print("Bug Fix #2: EXTRA_HOLIDAYS mencakup 25 Des 2025 (Natal)")
    print("Bug Fix #3: Inject baris demand=0 untuk tanggal libur yang hilang di raw CSV")
    print("Bug Fix #4: Reconstruct kolom 'variant' setelah groupby apply menghapusnya")
    print("=" * 70)
    
    build_v3_exact_features("vending_daily_aggregated_FORV6.csv", "V6_fix_training_data.csv")

    