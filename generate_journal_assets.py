"""
generate_journal_assets.py
Menghasilkan 4 PNG untuk Bab Hasil & Pembahasan jurnal ilmiah
Simpan ke folder Asset/ di root project
"""
import sys, os
sys.path.insert(0, r'c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from database import engine
from sqlalchemy import text

# ── Setup folder output ──────────────────────────────────────────
OUT_DIR = r'c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\Asset'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Style global ─────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'axes.facecolor': '#F8F9FA',
    'figure.facecolor': 'white',
    'axes.grid': True,
    'grid.alpha': 0.4,
    'axes.spines.top': False,
    'axes.spines.right': False,
})
BLUE   = '#2563EB'
ORANGE = '#F97316'
GREEN  = '#16A34A'
RED    = '#DC2626'
GRAY   = '#6B7280'

print("Connecting to database...")
with engine.connect() as conn:

    # ── Query Layer 2 Januari 2026 ────────────────────────────────
    l2_jan = conn.execute(text("""
        SELECT CONVERT(varchar(10), Date, 23) AS tgl,
               SUM(PredictedDemand) AS pred
        FROM dbo.ForecastResults_Layer2
        WHERE PredictedMonth = '2026-01'
        GROUP BY CONVERT(varchar(10), Date, 23)
        ORDER BY tgl
    """)).fetchall()

    act_jan = conn.execute(text("""
        SELECT CONVERT(varchar(10), tanggal, 23) AS tgl,
               SUM(demand) AS aktual
        FROM dbo.Vending_Aggregrated
        WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 1
        GROUP BY CONVERT(varchar(10), tanggal, 23)
        ORDER BY tgl
    """)).fetchall()

    # ── Query Layer 2 Februari 2026 ───────────────────────────────
    l2_feb = conn.execute(text("""
        SELECT CONVERT(varchar(10), Date, 23) AS tgl,
               SUM(PredictedDemand) AS pred
        FROM dbo.ForecastResults_Layer2
        WHERE PredictedMonth = '2026-02'
        GROUP BY CONVERT(varchar(10), Date, 23)
        ORDER BY tgl
    """)).fetchall()

    act_feb = conn.execute(text("""
        SELECT CONVERT(varchar(10), tanggal, 23) AS tgl,
               SUM(demand) AS aktual
        FROM dbo.Vending_Aggregrated
        WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 2
        GROUP BY CONVERT(varchar(10), tanggal, 23)
        ORDER BY tgl
    """)).fetchall()

print("Data fetched. Generating plots...")

# ─────────────────────────────────────────────────────────────────
# HELPER: build DataFrame gabungan prediksi + aktual
# ─────────────────────────────────────────────────────────────────
def build_df(pred_rows, act_rows):
    df_pred = pd.DataFrame(pred_rows, columns=['date','pred'])
    df_act  = pd.DataFrame(act_rows,  columns=['date','aktual'])
    df = pd.merge(df_pred, df_act, on='date', how='outer').sort_values('date')
    df['date'] = pd.to_datetime(df['date'])
    df['pred']   = df['pred'].fillna(0)
    df['aktual'] = df['aktual'].fillna(0)
    df['error_pct'] = np.where(
        df['aktual'] > 0,
        (df['pred'] - df['aktual']) / df['aktual'] * 100,
        np.nan
    )
    return df

df_jan = build_df(l2_jan, act_jan)
df_feb = build_df(l2_feb, act_feb)

# ─────────────────────────────────────────────────────────────────
# PLOT 1: Prediksi vs Aktual — Januari 2026 (daily)
# ─────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                gridspec_kw={'height_ratios': [3, 1]})
fig.suptitle('Perbandingan Prediksi vs Aktual Harian — Januari 2026\n(Layer 2: Smart Event Classifier v2.2)',
             fontsize=14, fontweight='bold', y=0.98)

ax1.plot(df_jan['date'], df_jan['aktual'], '-o', color=BLUE,   linewidth=2.2,
         markersize=5, label='Aktual', zorder=3)
ax1.plot(df_jan['date'], df_jan['pred'],   '-s', color=ORANGE, linewidth=2.2,
         markersize=4, linestyle='--', label='Prediksi', zorder=3, alpha=0.9)
ax1.fill_between(df_jan['date'], df_jan['aktual'], df_jan['pred'],
                 alpha=0.12, color='purple', label='Selisih')

# Annotasi 2 Jan dan 3 Jan
for tgl_str, label, yoff in [('2026-01-02', '2 Jan\n(Cuti Bersama)', -500),
                               ('2026-01-03', '3 Jan\n(Sabtu post-shutdown)', -700)]:
    tgl = pd.Timestamp(tgl_str)
    row = df_jan[df_jan['date'] == tgl].iloc[0]
    ax1.annotate(label, xy=(tgl, row['aktual']),
                 xytext=(tgl, row['aktual'] + yoff),
                 fontsize=8, color=RED, ha='center',
                 arrowprops=dict(arrowstyle='->', color=RED, lw=1.2))

ax1.set_ylabel('Jumlah Unit Susu UHT', fontsize=11)
ax1.legend(fontsize=10, loc='upper right')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax1.set_xlim(df_jan['date'].min(), df_jan['date'].max())
ax1.tick_params(axis='x', labelsize=9)

# Subplot error %
colors_err = [GREEN if abs(e) < 10 else (ORANGE if abs(e) < 20 else RED)
              for e in df_jan['error_pct'].fillna(0)]
ax2.bar(df_jan['date'], df_jan['error_pct'], color=colors_err, width=0.7, zorder=3)
ax2.axhline(0, color='black', linewidth=0.8)
ax2.axhline(10,  color=GREEN, linewidth=1, linestyle=':', alpha=0.7)
ax2.axhline(-10, color=GREEN, linewidth=1, linestyle=':', alpha=0.7)
ax2.set_ylabel('Error (%)', fontsize=10)
ax2.set_xlabel('Tanggal', fontsize=10)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax2.set_xlim(df_jan['date'].min(), df_jan['date'].max())
ax2.tick_params(axis='x', labelsize=9)

# Hitung WAPE Januari
jan_act_total = df_jan['aktual'].sum()
jan_wape = (df_jan['aktual'] - df_jan['pred']).abs().sum() / jan_act_total * 100 if jan_act_total > 0 else 0
fig.text(0.13, 0.01, f'WAPE Januari 2026: {jan_wape:.2f}%  |  Total Aktual: {int(jan_act_total):,}  |  Total Prediksi: {int(df_jan["pred"].sum()):,}',
         fontsize=9, color=GRAY)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
out1 = os.path.join(OUT_DIR, 'plot_01_prediksi_vs_aktual_jan2026.png')
plt.savefig(out1, dpi=150, bbox_inches='tight')
plt.close()
print(f'  [OK] Saved: {out1}')

# ─────────────────────────────────────────────────────────────────
# PLOT 2: Prediksi vs Aktual — Februari 2026 (daily, Ramadan parsial)
# ─────────────────────────────────────────────────────────────────
# Ramadan 2026 start ~17 Feb
RAMADAN_START = pd.Timestamp('2026-02-17')

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                gridspec_kw={'height_ratios': [3, 1]})
fig.suptitle('Perbandingan Prediksi vs Aktual Harian — Februari 2026\n(Layer 2: Smart Event Classifier v2.2 | Ramadan Parsial)',
             fontsize=14, fontweight='bold', y=0.98)

# Shading Ramadan
ax1.axvspan(RAMADAN_START, df_feb['date'].max(), alpha=0.08, color='green',
            label='Periode Ramadan')
ax2.axvspan(RAMADAN_START, df_feb['date'].max(), alpha=0.08, color='green')

# Hanya plot hingga data aktual ada (18 Feb)
df_feb_plot = df_feb[df_feb['date'] <= pd.Timestamp('2026-02-18')]

ax1.plot(df_feb_plot['date'], df_feb_plot['aktual'], '-o', color=BLUE, linewidth=2.2,
         markersize=5, label='Aktual', zorder=3)
ax1.plot(df_feb_plot['date'], df_feb_plot['pred'],   '-s', color=ORANGE, linewidth=2.2,
         markersize=4, linestyle='--', label='Prediksi', zorder=3, alpha=0.9)
ax1.fill_between(df_feb_plot['date'], df_feb_plot['aktual'], df_feb_plot['pred'],
                 alpha=0.12, color='purple', label='Selisih')

ax1.set_ylabel('Jumlah Unit Susu UHT', fontsize=11)
ax1.legend(fontsize=10, loc='upper right')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax1.set_xlim(df_feb_plot['date'].min(), df_feb_plot['date'].max())
ax1.tick_params(axis='x', labelsize=9)

colors_err2 = [GREEN if abs(e) < 10 else (ORANGE if abs(e) < 20 else RED)
               for e in df_feb_plot['error_pct'].fillna(0)]
ax2.bar(df_feb_plot['date'], df_feb_plot['error_pct'], color=colors_err2, width=0.7, zorder=3)
ax2.axhline(0, color='black', linewidth=0.8)
ax2.axhline(10,  color=GREEN, linewidth=1, linestyle=':', alpha=0.7)
ax2.axhline(-10, color=GREEN, linewidth=1, linestyle=':', alpha=0.7)
ax2.set_ylabel('Error (%)', fontsize=10)
ax2.set_xlabel('Tanggal', fontsize=10)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax2.set_xlim(df_feb_plot['date'].min(), df_feb_plot['date'].max())
ax2.tick_params(axis='x', labelsize=9)

feb_act_total = df_feb_plot['aktual'].sum()
feb_wape = (df_feb_plot['aktual'] - df_feb_plot['pred']).abs().sum() / feb_act_total * 100 if feb_act_total > 0 else 0
fig.text(0.13, 0.01, f'WAPE Februari 2026: {feb_wape:.2f}%  |  Total Aktual: {int(feb_act_total):,}  |  Total Prediksi: {int(df_feb_plot["pred"].sum()):,}',
         fontsize=9, color=GRAY)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
out2 = os.path.join(OUT_DIR, 'plot_02_prediksi_vs_aktual_feb2026.png')
plt.savefig(out2, dpi=150, bbox_inches='tight')
plt.close()
print(f'  [OK] Saved: {out2}')

# ─────────────────────────────────────────────────────────────────
# PLOT 3: Walk-Forward Backtest — Layer 1 XGBoost V6
# ─────────────────────────────────────────────────────────────────
backtest_data = {
    'Iterasi': ['1', '2', '3', '4'],
    'Period Train': ['Apr 2023 – Agu 2025', 'Apr 2023 – Sep 2025', 'Apr 2023 – Okt 2025', 'Apr 2023 – Nov 2025'],
    'Bulan Test': ['Sep 2025', 'Okt 2025', 'Nov 2025', 'Des 2025'],
    'Prediksi (unit)': [78745, 83076, 79712, 81723],
    'Aktual (unit)':   [79442, 84188, 74432, 78531],
    'Error (%)': [-0.88, -1.32, 7.09, 4.06],
}
df_bt = pd.DataFrame(backtest_data)

fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(df_bt))
w = 0.35
bars1 = ax.bar(x - w/2, df_bt['Aktual (unit)'],   w, label='Aktual',   color=BLUE,   alpha=0.85)
bars2 = ax.bar(x + w/2, df_bt['Prediksi (unit)'], w, label='Prediksi', color=ORANGE, alpha=0.85)

# Label error di atas bar
for i, (b1, b2, err) in enumerate(zip(bars1, bars2, df_bt['Error (%)'])):
    y_pos = max(b1.get_height(), b2.get_height()) + 200
    color = GREEN if abs(err) < 5 else ORANGE
    ax.text(i, y_pos, f'{err:+.2f}%', ha='center', fontsize=10, fontweight='bold', color=color)

ax.set_xticks(x)
ax.set_xticklabels([f'Iter {i+1}\nTest: {m}' for i, m in enumerate(df_bt['Bulan Test'])], fontsize=10)
ax.set_ylabel('Jumlah Unit Susu UHT', fontsize=11)
ax.set_title(f'Walk-Forward Backtest — Layer 1 XGBoost V6\n(MAPE Keseluruhan: 3.34% | Periode Data: Apr 2023 – Des 2025)',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.set_ylim(0, max(df_bt['Aktual (unit)'].max(), df_bt['Prediksi (unit)'].max()) * 1.15)

# Grid horisontal saja
ax.yaxis.grid(True, alpha=0.4)
ax.set_axisbelow(True)

plt.tight_layout()
out3 = os.path.join(OUT_DIR, 'plot_03_walkforward_backtest_layer1.png')
plt.savefig(out3, dpi=150, bbox_inches='tight')
plt.close()
print(f'  [OK] Saved: {out3}')

# ─────────────────────────────────────────────────────────────────
# PLOT 4: Smart Event Classifier — Perbandingan Error Sebelum/Sesudah v2.2
# ─────────────────────────────────────────────────────────────────
event_data = {
    'Tanggal': ['2 Jan 2026\n(Cuti Bersama)', '3 Jan 2026\n(Sabtu Post-Shutdown)',
                '1 Jan 2026\n(Tahun Baru / Shutdown)', 'Weekend Rata-rata\n(n=14 hari)',
                'Holiday Rata-rata\n(n=3 hari)'],
    'Sebelum v2.2': [73.8, 195.0, None, 35.7, 80.0],
    'Sesudah v2.2':  [-5.2,  -2.3,  0.0,   3.5,  5.5],
}
df_ev = pd.DataFrame(event_data)

fig, ax = plt.subplots(figsize=(13, 6))
x = np.arange(len(df_ev))
w = 0.38

# Sebelum (hanya yang tidak None)
before_vals = [v if v is not None else 0 for v in df_ev['Sebelum v2.2']]
bars_before = ax.bar(x - w/2, before_vals, w, label='Sebelum v2.2 (Baseline)',
                     color=RED, alpha=0.8)
bars_after  = ax.bar(x + w/2, df_ev['Sesudah v2.2'], w, label='Sesudah v2.2',
                     color=GREEN, alpha=0.8)

# Label nilai
for b, v in zip(bars_before, before_vals):
    if v > 0:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 2,
                f'+{v:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color=RED)
for b, v in zip(bars_after, df_ev['Sesudah v2.2']):
    ypos = b.get_height() + 1 if v >= 0 else b.get_height() - 8
    ax.text(b.get_x() + b.get_width()/2, ypos,
            f'{v:+.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color=GREEN)

# Garis threshold ±10%
ax.axhline(10,  color=BLUE, linewidth=1.2, linestyle='--', alpha=0.6, label='Threshold ±10%')
ax.axhline(-10, color=BLUE, linewidth=1.2, linestyle='--', alpha=0.6)
ax.axhline(0,   color='black', linewidth=0.8)

# Annotasi 1 Jan (tidak ada baseline karena sudah 0 dari shutdown)
ax.text(0 - w/2, 2, 'Tidak ada\nbaseline\n(shutdown)', ha='center', fontsize=7.5, color=GRAY)

ax.set_xticks(x)
ax.set_xticklabels(df_ev['Tanggal'], fontsize=10)
ax.set_ylabel('Error Prediksi (%)', fontsize=11)
ax.set_title('Dampak Smart Event Classifier v2.2 terhadap Akurasi Event Handling\n(Perbandingan Error Sebelum dan Sesudah Implementasi)',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=10, loc='upper right')
ax.set_ylim(-25, 215)

plt.tight_layout()
out4 = os.path.join(OUT_DIR, 'plot_04_smart_event_classifier_impact.png')
plt.savefig(out4, dpi=150, bbox_inches='tight')
plt.close()
print(f'  [OK] Saved: {out4}')

print('\n✅ Semua 4 grafik berhasil disimpan di:')
print(f'   {OUT_DIR}')
