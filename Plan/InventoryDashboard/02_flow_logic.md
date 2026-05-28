# Poin 2 — Alur Logika / Flow (Inventory Dashboard DSS)

## 2.1 Overview Tiga Alur

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ALUR A: Stok Masuk                ALUR B: Stok Keluar           │
│  (Supplier → Gudang)               (Gudang → VM, Auto)          │
│  Manual oleh admin                  Otomatis dari event stocking │
│         │                                    │                   │
│         ▼                                    ▼                   │
│  ┌──────────────────────────────────────────────┐                │
│  │         warehouse_stock (ledger)              │                │
│  │         IN entries + OUT entries               │                │
│  └──────────────────────┬───────────────────────┘                │
│                         │                                        │
│                         ▼                                        │
│              ┌──────────────────────┐                            │
│              │   ALUR C: DSS Calc   │                            │
│              │   Prediksi − Stok    │                            │
│              │   = Rekomendasi Beli │                            │
│              └──────────────────────┘                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2.2 Alur A: Stok Masuk (Supplier → Gudang) — Manual

### Trigger
Admin menerima kiriman susu dari supplier secara fisik, lalu membuka app untuk mencatat.

### Step-by-Step

```
1. Admin buka Inventory Dashboard
2. Klik FAB "Tambah Stok Masuk"
3. Masuk ke StockInActivity
   - Tampilkan 4 field input (satu per varian)
   - Placeholder: angka rekomendasi beli dari DSS
   - Label: sisa gudang saat ini per varian
4. Admin isi jumlah yang datang per varian
   - Boleh 0 untuk varian yang belum datang
5. Isi catatan opsional (PO number, dll)
6. Klik "Simpan Stok Masuk"
```

### Server-Side Logic (Pseudocode)

```python
def stock_in(items: List[StockInItem], note: str):
    results = []
    
    for item in items:
        if item.qty <= 0:
            continue  # Skip varian yang tidak diisi
        
        # Ambil saldo terakhir
        current_balance = get_latest_balance(item.variant_name)
        if current_balance is None:
            current_balance = 0  # Varian baru pertama kali
        
        new_balance = current_balance + item.qty
        
        # Insert ke ledger
        INSERT INTO warehouse_stock (
            variant_name = item.variant_name,
            movement_type = 'IN',
            qty = item.qty,
            balance_after = new_balance,
            note = note,
            created_by = 'admin'
        )
        
        results.append({
            "variant_name": item.variant_name,
            "qty_added": item.qty,
            "new_balance": new_balance
        })
    
    return {"success": True, "results": results}
```

### Validasi

| Rule | Detail |
|------|--------|
| `variant_name` | Harus salah satu dari: `Coklat`, `Strawberry`, `Moca`, `Original (Putih)` |
| `qty` | Harus integer > 0 (item dengan qty=0 diskip, bukan error) |
| `note` | Opsional, max 200 karakter |
| Minimal 1 varian | Setidaknya satu varian harus qty > 0 |

---

## 2.3 Alur B: Stok Keluar (Gudang → VM) — Auto-Deduct

### Trigger
Dipanggil otomatis saat Endpoint `GET /api/v1/inventory/dashboard` dipanggil (sebelum kalkulasi DSS).

### Mekanisme Watermark

Untuk mengetahui event stocking mana yang **sudah** dan **belum** diproses:

```
Watermark = MAX(created_at) dari warehouse_stock WHERE movement_type = 'OUT'
                                                   AND created_by = 'auto-sync'

Jika belum ada OUT sama sekali → watermark = NULL → proses SEMUA stocking events
```

### Step-by-Step

```
1. Dashboard API dipanggil
2. Ambil watermark (timestamp OUT terakhir yang auto-sync)
3. Query stocking events baru:

   SELECT 
       t.id_recnum_mld,
       t.slot_number,
       t.qty,
       t.update_time,
       t.id_recnum_mav
   FROM dbo.monitor_log_datatransaksi t
   WHERE t.kategori_transaksi = 'stocking'
     AND t.status_transaksi = '1'
     AND t.update_time > @watermark   -- hanya event baru
   ORDER BY t.update_time ASC

4. Untuk setiap event, mapping slot → varian:

   slot_number = 'A7'
   slot_base = 'A'                    -- huruf pertama
   
   SELECT v.nama_variant
   FROM manage_map_slot_number m
   JOIN master_variant v ON m.id_recnum_variant = v.id_recnum_variant
   WHERE m.id_recnum_mav = @id_recnum_mav
     AND m.slot_name = @slot_base
   
   → Hasil: 'Coklat'

5. Agregasi per varian:
   
   aggregated = {
       'Coklat': 35,       -- total qty dari semua event stocking Coklat
       'Strawberry': 20,
   }

6. Insert OUT entries ke warehouse_stock:

   Untuk setiap varian dalam aggregated:
       current_balance = get_latest_balance(variant)
       new_balance = current_balance - aggregated[variant]
       
       INSERT INTO warehouse_stock (
           variant_name = variant,
           movement_type = 'OUT',
           qty = aggregated[variant],
           balance_after = new_balance,
           note = f'Auto-sync: {count} event stocking',
           created_by = 'auto-sync'
       )

7. Lanjut ke kalkulasi DSS (Alur C)
```

### Edge Cases

| Situasi | Handling |
|---------|----------|
| Balance jadi negatif | Tetap simpan (indikasi: ada stocking dari stok yang belum di-input IN). Tampilkan warning di UI. |
| Mapping slot tidak ditemukan | Skip event tersebut, log warning di server |
| Tidak ada event baru | Skip sync, langsung ke DSS calc |
| Watermark NULL (pertama kali) | Proses semua stocking events sejak awal. **PENTING:** Ini bisa menghasilkan balance negatif besar jika belum ada IN. Admin perlu input saldo awal dulu. |

### Rekomendasi: Saldo Awal

Saat pertama kali deploy, admin harus **input saldo awal gudang** (Alur A) sebelum auto-sync mulai berjalan. Tanpa ini, semua OUT akan membuat balance negatif.

---

## 2.4 Alur C: Kalkulasi DSS (Inti)

### Trigger
Dipanggil setelah Alur B (sync) selesai, sebagai bagian dari `GET /api/v1/inventory/dashboard`.

### Step-by-Step

```
Input: year (int), quarter (int)

STEP 0: Jalankan Alur B (auto-sync OUT)
        ↓
STEP 1: Tentukan 3 bulan target
        Q3 → month_1='2026-07', month_2='2026-08', month_3='2026-09'
        ↓
STEP 2: Cek apakah prediksi tersedia
        SELECT COUNT(*) FROM ForecastResults_Layer1
        WHERE PredictedMonth IN (@m1, @m2, @m3)
        
        Jika 0 → return has_prediction_data: false
        ↓
STEP 3: Ambil prediksi per bulan per varian dari Layer1
        SELECT PredictedMonth, 
               DemandCoklat, DemandMoca, 
               DemandOriginal, DemandStrawberry
        FROM ForecastResults_Layer1
        WHERE PredictedMonth IN (@m1, @m2, @m3)
        ORDER BY PredictedMonth ASC
        
        Agregasi per varian:
        predicted = {
            'Coklat': sum(DemandCoklat across 3 months),
            'Strawberry': sum(DemandStrawberry),
            'Moca': sum(DemandMoca),
            'Original (Putih)': sum(DemandOriginal)
        }
        ↓
STEP 4: Ambil saldo gudang per varian
        (Query dari 01_database_design.md Section 1.2)
        
        warehouse = {
            'Coklat': 200,
            'Strawberry': 150,
            'Moca': 80,
            'Original (Putih)': 50
        }
        ↓
STEP 5: Ambil stok VM per varian
        (Query mapping dari 01_database_design.md Section 1.1)
        
        vm_stock = {
            'Coklat': 45,
            'Strawberry': 30,
            'Moca': 20,
            'Original (Putih)': 15
        }
        ↓
STEP 6: Hitung rekomendasi per varian
        Untuk setiap varian:
            total_available = warehouse[v] + vm_stock[v]
            to_purchase = max(0, predicted[v] - total_available)
            purchase_pct = to_purchase / sum(all to_purchase) * 100
        ↓
STEP 7: Jika kuartal sudah lewat, hitung history_summary
        - Total IN: SUM(qty) dari warehouse_stock WHERE type='IN' AND dalam kuartal
        - Total OUT: SUM(qty) dari warehouse_stock WHERE type='OUT' AND dalam kuartal
        - Total consumed: COUNT(*) dari monitor_log_datatransaksi 
                         WHERE kategori='ambil' AND dalam kuartal
        - Prediksi vs Aktual: dari ForecastResults_Layer1 
                              (ActualDemand, ErrorPercent)
        ↓
STEP 8: Susun response JSON
        (Struktur lengkap di 03_data_response.md)
```

### Penentuan Kuartal Default

```python
import datetime

today = datetime.date.today()
current_quarter = (today.month - 1) // 3 + 1

# Default: kuartal berikutnya
if current_quarter < 4:
    default_quarter = current_quarter + 1
    default_year = today.year
else:
    default_quarter = 1
    default_year = today.year + 1
```

### Penentuan "Kuartal Sudah Lewat"

```python
def is_past_quarter(year, quarter):
    today = datetime.date.today()
    current_year = today.year
    current_quarter = (today.month - 1) // 3 + 1
    
    if year < current_year:
        return True
    if year == current_year and quarter < current_quarter:
        return True
    return False
```

### Available Quarters

```python
# Query kuartal yang tersedia (ada data prediksi)
SELECT DISTINCT 
    LEFT(PredictedMonth, 4) AS year,
    CEILING(CAST(RIGHT(PredictedMonth, 2) AS INT) / 3.0) AS quarter
FROM dbo.ForecastResults_Layer1
ORDER BY year DESC, quarter DESC
```

---

## 2.5 Diagram Sequence Lengkap

```
User                 Android App              Server                    Database
 │                       │                       │                         │
 │  Buka Dashboard       │                       │                         │
 │──────────────────────>│                       │                         │
 │                       │  GET /inventory/      │                         │
 │                       │  dashboard?y=2026&q=3 │                         │
 │                       │──────────────────────>│                         │
 │                       │                       │  [SYNC] Cek watermark   │
 │                       │                       │────────────────────────>│
 │                       │                       │  [SYNC] Query stocking  │
 │                       │                       │  events baru            │
 │                       │                       │────────────────────────>│
 │                       │                       │  [SYNC] Map slot→varian │
 │                       │                       │────────────────────────>│
 │                       │                       │  [SYNC] Insert OUT      │
 │                       │                       │────────────────────────>│
 │                       │                       │                         │
 │                       │                       │  [DSS] Query Layer1     │
 │                       │                       │────────────────────────>│
 │                       │                       │  [DSS] Query warehouse  │
 │                       │                       │────────────────────────>│
 │                       │                       │  [DSS] Query VM stock   │
 │                       │                       │────────────────────────>│
 │                       │                       │  [DSS] Calculate        │
 │                       │                       │                         │
 │                       │  JSON Response        │                         │
 │                       │<──────────────────────│                         │
 │  Tampilkan Dashboard  │                       │                         │
 │<──────────────────────│                       │                         │
 │                       │                       │                         │
 │  Klik "Tambah Stok"   │                       │                         │
 │──────────────────────>│                       │                         │
 │                       │  Buka StockInActivity │                         │
 │  Isi qty per varian   │  (placeholder = DSS)  │                         │
 │──────────────────────>│                       │                         │
 │                       │  POST /inventory/     │                         │
 │                       │  stock-in             │                         │
 │                       │──────────────────────>│                         │
 │                       │                       │  Insert IN entries      │
 │                       │                       │────────────────────────>│
 │                       │  Success response     │                         │
 │                       │<──────────────────────│                         │
 │  Dialog sukses        │                       │                         │
 │<──────────────────────│                       │                         │
```
