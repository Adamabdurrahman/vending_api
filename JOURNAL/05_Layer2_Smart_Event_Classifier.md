# 05 — Layer 2: Smart Event Classifier v2.2

## 1. Mengapa Rule-Based, Bukan ML?

Salah satu keputusan desain paling penting dalam sistem ini adalah penggunaan pendekatan *rule-based* untuk Layer 2. Dalam iterasi pengembangan awal, telah dicoba menggunakan model **Prophet** dari Meta (sebuah model time-series berbasis Bayesian yang populer) untuk mendistribusikan prediksi bulanan ke level harian. Hasilnya tidak memuaskan:

| Pendekatan | WAPE (Weighted Absolute Percentage Error) |
|---|---|
| Prophet (ML murni) | 27.0% |
| Rule-Based + Smart Event Classifier v1.0 | 10.6% |
| **Rule-Based + Smart Event Classifier v2.2** | **3.99%** |

Penyebab utama kegagalan Prophet adalah ketidakmampuannya menangani *regime change* yang abrupt — transisi tiba-tiba dari hari kerja normal ke hari libur besar (Hari Raya Idul Fitri, Natal), atau dari hari Ramadan ke hari pasca-Ramadan. Model probabilistik berbasis data historis membutuhkan banyak contoh setiap jenis transisi, sementara beberapa event (seperti Cuti Bersama yang jatuh tepat setelah Natal) hanya terjadi 1-2 kali dalam seluruh dataset.

Pendekatan *rule-based* lebih tepat di sini karena:
1. **Domain knowledge bisa dikodekan langsung**: Admin pabrik tahu persis hari mana pabrik tutup total, hari mana setengah beroperasi, dan hari mana normal.
2. **Interpretabilitas**: Setiap angka prediksi bisa ditelusuri ke aturan yang menghasilkannya.
3. **Adaptasi instan**: Menambahkan hari libur baru cukup dengan UPDATE satu baris di tabel SQL — tidak perlu retraining.

---

## 2. Komponen-Komponen Layer 2

Layer 2 terdiri dari empat komponen yang bekerja bersama:

```
Budget Bulanan (dari Layer 1)
    ↓
[A] DOW Share Profile    ← Bobot per hari dalam seminggu (dari data historis)
    +
[B] Shift Profile        ← Bobot per shift (dari data historis)
    +
[C] Tiered Day Weighting ← Faktor pengali per kategori hari (Smart Event Classifier)
    +
[D] SQL Calendar         ← Sumber kebenaran kalender (hari kerja, Ramadan, shutdown)
    ↓
Prediksi Harian per Shift per Varian
```

---

## 3. Komponen A: DOW Share Profile

### 3.1 Definisi

DOW (*Day of Week*) Share Profile adalah tabel bobot relatif yang menyatakan berapa proporsi demand total mingguan yang jatuh pada masing-masing hari (Senin-Minggu). Profil ini dihitung dari data historis 6 bulan ke belakang dari bulan yang diprediksi.

### 3.2 Proses Pembangunan Profil

```python
DOW_PROFILE_WINDOW_MONTHS = 6  # Lookback 6 bulan

# Filter data: hanya hari NORMAL (bukan holiday, Ramadan, atau bridge day)
df_w = df_hist[
    (df_hist["tanggal"] >= window_start) &
    (df_hist["is_holiday"] == 0) &
    (df_hist["is_ramadan"] == 0) &
    (df_hist["is_bridge"] == 0)
]

# Hitung rata-rata demand per hari dalam seminggu
dow_avg = wd_daily.groupby("day_of_week")["demand"].mean()
total_wd = dow_avg.sum()

# Normalisasi ke share (0-1)
dow_shares = {d: dow_avg.get(d, 0) / total_wd for d in range(5)}  # Senin-Jumat

# Weekend: dinyatakan sebagai rasio terhadap rata-rata hari kerja
wd_per_day = total_wd / 5.0
for d in [5, 6]:  # Sabtu=5, Minggu=6
    wa = we_daily[we_daily["day_of_week"] == d]["demand"].mean()
    dow_shares[d] = wa / wd_per_day  # Misal: Sabtu = 0.65x dari rata-rata hari kerja
```

### 3.3 Adaptive Pre-Ramadan Weekend Override

Pada bulan menjelang Ramadan, pola konsumsi akhir pekan berbeda dari normal. Secara empiris, data historis menunjukkan bahwa konsumsi susu pada hari Sabtu dan Minggu di bulan sebelum Ramadan cenderung lebih tinggi dibandingkan rata-rata akhir pekan biasa. Hal ini diduga berkaitan dengan pola kehadiran karyawan yang berubah menjelang periode puasa — misalnya adanya lembur, penyesuaian jadwal produksi, atau kegiatan khusus pabrik yang meningkatkan jumlah karyawan hadir pada akhir pekan tersebut. DOW Share Profile standar yang dihitung dari 6 bulan data normal tidak mampu menangkap dinamika spesifik ini.

Sistem mengatasi ini dengan **Adaptive Pre-Ramadan Weekend Override**: jika bulan yang diprediksi adalah 1 bulan sebelum Ramadan atau bulan Ramadan itu sendiri, rasio Sabtu dan Minggu dioverride menggunakan data historis dari bulan-bulan pra-Ramadan di tahun-tahun sebelumnya:

```python
def _get_adaptive_weekend_ratios(df_hist, target_year, target_month):
    """Hitung rasio Sabtu/Minggu dari data pra-Ramadan historis."""
    if not _is_pre_ramadan_month(target_year, target_month):
        return None  # Tidak ada override untuk bulan normal

    sat_ratios, sun_ratios = [], []
    for ry, (ram_y, ram_m) in RAMADAN_START_MONTHS.items():
        # Ambil data dari bulan sebelum Ramadan di tiap tahun historis
        pre_m = ram_m - 1 if ram_m > 1 else 12
        sub = daily[(daily["tanggal"] >= pre_start) & (daily["tanggal"] < pre_end)]
        wd = sub[sub["day_of_week"] < 5]["demand"].mean()
        sat_ratios.append(sat["demand"].mean() / wd)
        sun_ratios.append(sun["demand"].mean() / wd)

    # Gunakan tahun terbaru (paling relevan karena tren berubah)
    return sat_ratios[-1], sun_ratios[-1]
```

---

## 4. Komponen B: Shift Profile (Hybrid Lookback)

Shift Profile menentukan bagaimana demand harian dibagi ke masing-masing shift. Pola ini berbeda tergantung jenis hari:

| Jenis Hari | Komposisi Shift Tipikal |
|---|---|
| Hari Kerja Normal | Shift 1 dominan (~42%), Shift 2 (~38%), Shift 3 (~20%) |
| Hari Libur | Shift 2 lebih dominan (karyawan yang tetap masuk) |
| Hari Ramadan | Shift 1 hampir nol (orang berpuasa tidak membeli susu pagi) |

Sistem menggunakan **Hybrid Lookback**: Shift 1 menggunakan rata-rata 3 bulan terakhir, sementara Shift 2 dan Shift 3 menggunakan rata-rata 1 bulan terakhir saja. Ini karena Shift 1 memiliki volatilitas yang lebih tinggi dan memerlukan periode perataan yang lebih panjang.

```python
def build_shift_profile(df_daily_hist):
    """Hybrid: SHIFT1 = 3m lookback, lainnya = 1m lookback."""
    p1m = get_profile_for_months(1)   # 1 bulan terakhir
    p3m = get_profile_for_months(3)   # 3 bulan terakhir
    sp = p1m.copy()
    for idx, row in sp.iterrows():
        if "SHIFT1" in row["keterangan"]:  # Override Shift 1 dengan profil 3 bulan
            sp.at[idx, "avg_share"] = p3m_match["avg_share"]
    return sp
```

---

## 5. Komponen C: Tiered Day Weighting (Smart Event Classifier)

Ini adalah inti dari Smart Event Classifier. Setiap hari dalam bulan diberi bobot (*day weight*) berdasarkan karakteristiknya. Bobot ini kemudian digunakan untuk mendistribusikan budget bulanan Layer 1 secara proporsional ke setiap hari.

### 5.1 Tujuh Kategori Hari dan Bobotnya

| Kategori | Kondisi | Bobot (`w`) | Contoh |
|---|---|---|---|
| **Factory Shutdown** | `IsShutdown=1` di SQL atau hari besar keagamaan | `0.0` | Idul Fitri, Natal, Tahun Baru |
| **Ramadan Normal** | `is_ramadan=1`, bukan transisi | `weekday_avg × factor_ramadan` | Hari biasa bulan Ramadan |
| **Ramadan Transition** | 2 hari pertama Ramadan | `0.70 × weekday_avg + 0.30 × (weekday_avg × factor_ramadan)` | Hari 1–2 Ramadan |
| **Hangover Weekday** | H+1 atau H+2 setelah shutdown, hari kerja | `weekday_avg × 0.08` | Senin setelah Idul Fitri |
| **Hangover Weekend** | H+1 atau H+2 setelah shutdown, akhir pekan | `weekday_avg × 0.24` | Sabtu setelah Natal |
| **Standalone Holiday** | Libur nasional tanpa efek hangover | `weekday_avg × 0.24` | Kemerdekaan 17 Agustus |
| **Akhir Pekan** | Sabtu atau Minggu | `weekday_avg × dow_shares[dow]` | Sabtu, Minggu |
| **Hari Kerja Normal** | Senin–Jumat, bukan libur/Ramadan | `weekday_avg × dow_shares[dow] × 5` | Senin–Jumat reguler |

### 5.2 Implementasi Tiered Weighting

```python
# Konfigurasi Ramadan Transition
RAMADAN_TRANSITION_DAYS   = 2
RAMADAN_TRANSITION_FACTOR = 0.70

# [TASK 2] Tiered day weight (Smart Event Classifier)
if is_shutdown_sql or is_shutdown_library:
    w = 0.0                                          # Pabrik tutup total
elif is_ramadan_transition:
    # Formula eksplisit:
    # w = 0.70 x weekday_avg + 0.30 x (weekday_avg x factor_ramadan)
    # = weekday_avg x (0.70 + 0.30 x factor_ramadan)
    w = RAMADAN_TRANSITION_FACTOR * weekday_avg + (1 - RAMADAN_TRANSITION_FACTOR) * weekday_avg * event_factors["ramadan"]
elif is_hangover:
    if dow >= 5:
        w = weekday_avg * 0.24  # Hangover Weekend
    else:
        w = weekday_avg * 0.08  # Hangover Weekday (sangat sepi)
elif is_holiday:
    w = weekday_avg * 0.24      # Standalone Holiday
elif is_ramadan:
    w = weekday_avg * event_factors["ramadan"]
elif dow >= 5:
    w = weekday_avg * dow_shares[dow]               # Weekend
else:
    w = weekday_avg * dow_shares[dow] * 5           # Weekday normal
```

> **Klarifikasi formula Ramadan Transition**: Blending ini bukan mencampur dua nilai yang sepenuhnya berbeda, melainkan interpolasi linear antara bobot hari kerja normal (`weekday_avg`) dan bobot hari Ramadan (`weekday_avg × factor_ramadan`). Dengan `factor_ramadan` rata-rata sekitar 0.04, formula menghasilkan bobot sekitar `0.70 + 0.30 × 0.04 = 71.2%` dari `weekday_avg` — jauh lebih tinggi dari hari Ramadan biasa, namun lebih rendah dari hari kerja penuh.

### 5.3 Deteksi Factory Shutdown: Dua Lapis Keamanan

Sistem menggunakan dua mekanisme paralel untuk mendeteksi hari pabrik tutup total:

1. **SQL-First**: Membaca kolom `IsShutdown` dari `dbo.OperationalCalendar`. Ini adalah mekanisme utama dan mudah diperbarui oleh administrator.
2. **Library Fallback**: Membaca dari library `holidays.Indonesia` dan memeriksa apakah nama hari libur mengandung kata kunci tertentu (Idul Fitri, Natal, Tahun Baru, Nyepi, dll.).

Mekanisme fallback diperlukan sebagai jaring pengaman jika kolom `IsShutdown` belum diisi untuk hari libur tertentu.

### 5.4 Deteksi Hangover Effect

Periode "hangover" adalah 1-2 hari setelah hari besar keagamaan di mana aktivitas masih sangat rendah meskipun secara teknis sudah hari kerja. Contoh: Senin setelah Natal (25 Desember jatuh Kamis) biasanya memiliki kehadiran sangat rendah.

```python
# Cek apakah hari sebelumnya adalah shutdown day
prev1 = dt - pd.Timedelta(days=1)
prev2 = dt - pd.Timedelta(days=2)
p1_name = id_hols_cache.get(prev1.date())
p2_name = id_hols_cache.get(prev2.date())
p1_shut = any(kw in (p1_name or "") for kw in shutdown_kws)  # shutdown_kws = ["Eid al-Fitr", ...]
p2_shut = any(kw in (p2_name or "") for kw in shutdown_kws)
if (p1_shut or p2_shut) and (is_hol or dow >= 5):
    is_hangover = True
```

Cuti Bersama (*joint leave*) secara eksplisit ditangani sebagai hangover karena secara semantis merupakan extension dari shutdown:

```python
if "Cuti Bersama" in hol_name or "Joint Leave" in hol_name:
    is_hangover = True
```

---

## 6. Proses Distribusi Akhir

Setelah setiap hari dalam bulan mendapatkan bobot masing-masing, distribusi dilakukan dalam dua tahap:

**Tahap 1: Distribusi ke Hari**

```python
tw = cal["day_weight"].sum()  # Total bobot semua hari dalam bulan
cal["day_weight_norm"] = cal["day_weight"] / tw  # Normalisasi ke proporsional

# Budget per hari = total_budget × proporsi_hari
daily_vol = total_budget × day_weight_norm
```

**Tahap 2: Distribusi ke Shift**

```python
# Ambil bobot shift untuk jenis hari ini
sw = get_shift_weights(shift_profile, is_holiday, is_ramadan_flag, is_weekend)

# Budget per shift = budget_hari × bobot_shift
for shift_name, share in sw.items():
    demand_pred = round(daily_vol * share, 2)
```

Hasil akhir adalah DataFrame dengan dimensi: **tanggal × varian × shift** dengan kolom `demand_pred` (float untuk akumulasi akurasi) dan `demand_pred_int` (integer untuk keperluan stok fisik).

---

## 7. Step 9 Override di Layer 2

Jika Layer 1 menggunakan Business Logic Fallback (Step 9) karena bulan Ramadan ekstrem, Layer 2 menerima sinyal ini dan menyesuaikan `event_factors["ramadan"]` menjadi `0.0`:

```python
if budget.get("business_logic", False):
    event_factors["ramadan"] = 0.0
    # Seluruh budget terkonsentrasi ke hari-hari produktif (non-Ramadan)
```

Tanpa override ini, budget yang sudah sangat kecil (hasil Step 9) akan tersebar ke seluruh hari termasuk hari Ramadan, menghasilkan prediksi per hari yang terlalu kecil untuk bermakna. Dengan override, seluruh budget terkonsentrasi pada hari-hari produktif yang memang menjadi basis perhitungan Step 9.

---

## 8. Evaluasi Iteratif: Dari v1.0 ke v2.2

Versi v2.2 adalah hasil dari dua iterasi perbaikan besar:

### v1.0 → v2.1: Perubahan Struktural
- Mengganti distribusi berbasis `fractional_weight` murni dengan **Share-Based DOW Profile**
- Menambahkan **Tiered Event Overlay** (Factory Shutdown = 0, Hangover Effect)
- Menjadikan SQL Calendar sebagai sumber utama (menggantikan hardcode Python)

### v2.1 → v2.2: Smart Event Classifier
- **Sebelum**: 2 Jan 2026 (Cuti Bersama) error +73.8%, karena tidak ditangani sebagai hangover
- **Sesudah**: Error turun ke −5.2% setelah Cuti Bersama terklasifikasi sebagai hangover
- **Sebelum**: 3 Jan 2026 (Sabtu setelah shutdown) error +195%
- **Sesudah**: Error turun ke −2.3% setelah penanganan hangover weekend
- **Holiday accuracy**: Meningkat dari 0% menjadi 100% (3/3 hari libur)
- **Weekend accuracy**: Meningkat dari 64.3% menjadi 92.9% (13/14 akhir pekan)

Secara keseluruhan, WAPE harian turun dari **10.6%** (v2.1) menjadi **3.99%** (v2.2), dan Event Accuracy meningkat dari 52.6% menjadi 89.5%.
