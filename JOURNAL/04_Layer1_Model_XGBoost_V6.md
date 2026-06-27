# 04 — Layer 1: Model XGBoost V6

## 1. Pemilihan Algoritma

Model yang digunakan pada Layer 1 adalah **XGBoost** (*Extreme Gradient Boosting*), sebuah implementasi *gradient boosted decision tree* yang efisien dan sering mengungguli model lain pada dataset tabular berukuran kecil-menengah. XGBoost dipilih karena beberapa alasan:

1. **Kemampuan menangani fitur heterogen**: Dataset training mencakup fitur kalender (integer/float), fitur dummy varian (biner), fitur lag (float), dan fitur pangsa pasar (persentase). XGBoost menangani kombinasi ini dengan baik tanpa asumsi distribusi.
2. **Robustness terhadap missing values**: Melalui `SimpleImputer` yang mendahului XGBoost, nilai yang hilang pada awal dataset (lag bulan-bulan pertama belum tersedia) diisi dengan nilai median fitur.
3. **Non-linearity**: Hubungan antara fitur lag/tren dan demand target tidak linier — XGBoost mampu menangkap interaksi kompleks antar fitur tanpa perlu spesifikasi manual.
4. **Hasil empiris**: Pada evaluasi Walk-Forward Backtest dengan data April 2023 – Desember 2025, model mencapai MAPE 3.40%, jauh melampaui model baseline naïve (*naive forecast*) yang memiliki Skill Score > 60%.

---

## 2. Arsitektur Model dan Pipeline Training

Kelas `Layer1Model` di `ProductionML/Layer1_Core.py` merupakan *wrapper* yang menggabungkan tiga komponen dalam satu objek yang bisa diserialisasi (*self-contained artifact*):

```
Layer1Model
├── model      : XGBRegressor (terlatih)
├── scaler     : StandardScaler (fit pada data training)
├── imputer    : SimpleImputer(strategy="median")
├── feature_cols : daftar 22 nama fitur (dalam urutan yang konsisten)
├── historical_df: data historis ringkas (untuk menghitung lag saat inferensi)
└── metadata   : dict berisi versi, MAPE, parameter, dll.
```

Pipeline inferensi berjalan sebagai berikut:
```
Input fitur (22 kolom)
    ↓ imputer.transform()    — isi nilai NaN dengan median
    ↓ scaler.transform()     — normalisasi ke zero mean, unit variance
    ↓ model.predict()        — 4 nilai output (satu per varian)
    ↓ sum()                  — total prediksi bulanan
```

### 2.1 Proses Training (GridSearchCV)

Sebelum training final, sistem menjalankan **GridSearchCV** dengan 5-fold cross validation untuk menemukan kombinasi hyperparameter terbaik:

```python
param_grid = {
    "n_estimators"    : [50, 100],
    "learning_rate"   : [0.05, 0.1],
    "max_depth"       : [3, 4],
    "subsample"       : [0.8, 1.0],
    "colsample_bytree": [0.6, 0.8],
}
grid = GridSearchCV(
    XGBRegressor(random_state=42),
    param_grid,
    cv=5,
    scoring="neg_mean_absolute_error"
)
```

GridSearchCV hanya dijalankan pada data *pre-backtest* (data sebelum periode validasi). Ini penting untuk mencegah kebocoran data (*data leakage*): hyperparameter tidak boleh dipilih berdasarkan data yang akan diuji.

### 2.2 Walk-Forward Backtest

Setelah hyperparameter ditemukan, sistem menjalankan **Walk-Forward Backtest** untuk evaluasi yang tidak bias. Bulan-bulan backtest ditentukan secara **dinamis** — sistem selalu mengambil **4 bulan non-Ramadan terbaru** yang tersedia di dataset dan memiliki data aktual:

```python
# Pilih 4 bulan non-Ramadan terbaru sebagai pool backtest (DINAMIS)
available_months = [m for m in all_months if m not in RAMADAN_MONTHS and m in ACTUALS]
dynamic_bt_months = available_months[-4:]  # Selalu 4 terbaru
```

Contoh saat pertama kali dilatih (data hingga Desember 2025):
```
Iterasi 1: Train pada [Apr 2023 – Okt 2025] → Test pada [Nov 2025]
Iterasi 2: Train pada [Apr 2023 – Nov 2025] → Test pada [Des 2025]
Iterasi 3: Train pada [Apr 2023 – Des 2025] → Test pada [Jan 2026]
Iterasi 4: Train pada [Apr 2023 – Jan 2026] → Test pada [Feb 2026]
```

Saat retrain berikutnya (misalnya data hingga Juni 2026), bulan backtestnya akan bergeser secara otomatis — bukan tetap di Nov 2025–Feb 2026. Ini memastikan evaluasi selalu relevan dengan kondisi terkini.

Bulan-bulan Ramadan dikecualikan dari pool backtest. Alasannya: sistem sendiri tidak mempercayai data Ramadan sebagai referensi (Lag Skipper melewatinya, Step 9 mengoverride prediksi), sehingga tidak konsisten untuk mengevaluasi akurasi model *terhadap* bulan Ramadan menggunakan raw XGBoost.

Metrik yang dihitung:
- **MAPE** (*Mean Absolute Percentage Error*): Metrik utama, sensitivitas proporsional terhadap demand
- **MAE** (*Mean Absolute Error*): Error absolut rata-rata
- **RMSE** (*Root Mean Squared Error*): Error dengan penalti lebih besar untuk kesalahan besar

### 2.3 Final Training

Setelah backtest selesai, model dilatih ulang menggunakan **seluruh data** (termasuk periode backtest) dengan hyperparameter terbaik dari GridSearchCV. Ini adalah model yang kemudian disimpan ke artifact.

---

## 3. Penanganan Anomali Ramadan di Layer 1

### 3.1 Ramadan Lag Skipper (Saat Inferensi)

Saat model melakukan inferensi (*prediksi*), fitur lag_1m, lag_2m, dan lag_3m dihitung menggunakan algoritma berikut pada kelas `Layer1Model`:

```python
def _get_normal_lag_month(self, yr, mn, lag_n):
    """Mundur lag_n bulan, melewatkan bulan Ramadan."""
    curr_yr, curr_mn = yr, mn
    count = 0
    while count < lag_n:
        curr_mn -= 1
        if curr_mn == 0:
            curr_mn = 12
            curr_yr -= 1
        ps = f"{curr_yr}-{curr_mn:02d}"
        if not self._is_ramadan(ps):  # Hanya hitung jika bukan Ramadan
            count += 1
    return f"{curr_yr}-{curr_mn:02d}"
```

Daftar bulan Ramadan (`RAMADAN_MONTHS`) disimpan di dalam metadata artifact — bukan hardcode di kode Python. Ini berarti menambahkan Ramadan tahun baru cukup dilakukan dengan retraining dan memperbarui metadata, tanpa mengubah kode inferensi.

### 3.2 Guard YoY: Proteksi lag_12m

Untuk fitur `yoy_change`, sistem menambahkan guard khusus:

```python
# Guard YoY: set 0.0 jika referensi 12 bulan lalu adalah Ramadan
if lag12 < self.ANOMALY_DEMAND_THRESHOLD or self._is_ramadan(p12):
    yoy = 0.0
else:
    yoy = np.clip(lag1 / lag12 - 1, -1, 5)
```

Threshold `ANOMALY_DEMAND_THRESHOLD = 100` unit memastikan bahwa perbandingan YoY tidak dilakukan jika demand referensi sangat rendah (yang bisa menghasilkan rasio ekstrem meskipun teknisnya bukan bulan Ramadan).

### 3.3 Step 9 Business Logic Fallback

Saat prediksi dilakukan untuk bulan dengan sangat sedikit hari produktif (misalnya Maret 2026 yang memiliki 19 hari Ramadan dari 31 hari), XGBoost tidak dapat diandalkan karena:
1. Training data tidak mengandung pola untuk bulan "hampir seluruhnya Ramadan" (sudah di-remove)
2. Demand yang diharapkan sangat rendah dan bergantung pada hitungan hari produktif aktual

Pada kondisi ini (`productive_milk_days ≤ 10`), model melakukan override:

```python
if productive_days <= 10:
    for vi, v in enumerate(self.VARIANTS):
        lag_3m_avg = df_in.loc[vi]["rolling_avg_3m"]  # Rata-rata 3 bulan normal terakhir
        daily_run = lag_3m_avg / 25.0                  # Estimasi demand per hari
        override_val = int(daily_run * productive_days) # Skala ke hari produktif aktual
        pv_final_d[v] = override_val
```

Angka 25.0 digunakan sebagai perkiraan rata-rata hari kerja dalam sebulan normal (mengindari pembagian dengan hari produktif aktual yang bervariasi).

---

## 4. Self-Contained Artifact

Model artifact (`Layer1_XGBoost_V6_Artifact.joblib`) dirancang untuk bersifat *self-contained* — setelah dimuat, model siap langsung melakukan inferensi tanpa memerlukan file konfigurasi tambahan. Artifact mengandung:

| Komponen | Isi |
|---|---|
| `model` | Instance XGBRegressor yang sudah terlatih |
| `scaler` | Instance StandardScaler (fit pada training data) |
| `imputer` | Instance SimpleImputer |
| `feature_cols` | List 22 nama fitur dalam urutan yang benar |
| `historical_df` | DataFrame historis ringkas (period_str, variant, demand, share_pct, dll.) |
| `metadata` | Dict: versi, tanggal export, MAPE, MAE, RMSE, best_params, ramadan_months |

Komponen `historical_df` yang disimpan di dalam artifact adalah inovasi kunci yang membuat model *portable*. Saat inferensi, model membutuhkan data historis untuk menghitung lag bulan-bulan sebelumnya. Dengan menyimpan data ini di dalam artifact, model dapat berjalan di environment manapun tanpa bergantung pada koneksi database.

Untuk mencegah error saat *unpickling* dengan Pandas versi baru (≥ 2.0), kolom `period_str` di `historical_df` dikonversi ke tipe `object` sebelum disimpan:

```python
# Bugfix: Pandas 2.x NotImplementedError saat unpickling Period dtype
self.historical_df["period_str"] = self.historical_df["period_str"].astype(object)
```

---

## 5. Mekanisme Chain Prediction

Karena kuartal diprediksi tiga bulan sekaligus, dan fitur lag bergantung pada prediksi bulan sebelumnya, sistem menggunakan struktur `fwd_cache`:

```python
fwd_cache = {}

# Pre-load dari database (agar chain tidak terputus saat eksekusi mid-quarter)
prev_preds = conn.execute("SELECT PredictedMonth, DemandCoklat, ... FROM ForecastResults_Layer1")
for r in prev_preds:
    fwd_cache[r[0]] = {"Coklat": r[1], "Moca": r[2], ...}

# Loop prediksi per bulan
for month_str in ["2026-01", "2026-02", "2026-03"]:
    budget = layer1_model.predict(yr, mn, target_cal, fwd_cache=fwd_cache)
    fwd_cache[month_str] = budget["by_variant"]  # Hasil masuk ke cache
```

Saat `predict()` dipanggil dengan `fwd_cache`, model memeriksa cache terlebih dahulu sebelum mengakses `historical_df`. Jika prediksi bulan lalu ada di cache, itu yang digunakan sebagai lag — bukan data historis aktual.

---

## 6. Backward Compatibility dan Versioning

Artifact model menggunakan konvensi versi `V6+` untuk model production. Sistem menyimpan backup artifact lama sebelum setiap retraining:

```
ProductionML/
├── Layer1_XGBoost_V6_Artifact.joblib          ← Artifact aktif (production)
└── backups/
    ├── Layer1_XGBoost_V6_Artifact_20260115_083022.joblib
    ├── Layer1_XGBoost_V6_Artifact_20260401_091500.joblib
    └── ...
```

Setiap artifact menyimpan metadata yang mencatat kapan ia di-export, pada data mana ia dilatih, dan MAPE yang dicapai. Ini memungkinkan rollback jika retraining menghasilkan model yang lebih buruk.

Untuk backward compatibility: saat `Layer1Model.load_model()` memuat artifact lama yang tidak memiliki field `ramadan_months` di metadata, sistem menggunakan daftar Ramadan default yang di-hardcode sebagai fallback. Daftar default ini sudah mencakup jadwal Ramadan hingga tahun **2027** agar artifact yang di-retrain saat ini masih valid untuk dua tahun ke depan:

```python
_default_ramadan = [
    "2023-03", "2023-04",
    "2024-03", "2024-04",
    "2025-03",
    "2026-02", "2026-03",
    "2027-02", "2027-03",  # Sudah mencakup 2027
]
self.RAMADAN_MONTHS = metadata.get("ramadan_months", _default_ramadan)
```

> **Catatan maintenance tahunan**: Setiap akhir tahun, daftar `RAMADAN_MONTHS` di dalam metadata artifact (dan default fallback di atas) perlu diperbarui untuk mengantisipasi jadwal Ramadan tahun berikutnya. Ini dilakukan saat proses retrain rutin kuartalan.
