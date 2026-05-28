# Poin 1 — Desain Database (Inventory Dashboard DSS)

## 1.1 Analisis Table yang Sudah Ada

### Table A: `dbo.monitor_log_datatransaksi`

**Fungsi:** Log transaksi vending machine — mencatat setiap event yang terjadi di mesin.

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id_recnum_mld` | INT (PK) | Auto-increment |
| `id_recnum_mav` | INT | ID vending machine |
| `kategori_transaksi` | VARCHAR | `'ambil'` / `'stocking'` / `'transaksigagal'` |
| `slot_number` | VARCHAR | Slot fisik di VM (e.g., `'A7'`, `'B1'`) |
| `rfid` | VARCHAR | RFID karyawan yang melakukan aksi |
| `qty` | INT | Jumlah unit |
| `update_time` | DATETIME | Timestamp event |
| `status_transaksi` | VARCHAR | `'1'` = aktif |
| `keterangan` | VARCHAR | Deskripsi (e.g., `'Proses Restock Qty Oleh Admin'`) |
| `detail_keterangan` | VARCHAR | Detail tambahan (biasanya NULL) |

**Relevansi untuk Inventory DSS:**
- Filter `kategori_transaksi = 'stocking'` → **event restock ke VM** (sumber data auto-deduct OUT)
- Filter `kategori_transaksi = 'ambil'` → **susu diambil karyawan** (sumber data konsumsi untuk histori)
- `keterangan = 'Proses Restock Qty Oleh Admin'` mengidentifikasi event stocking secara spesifik

---

### Table B: `dbo.manage_restok`

**Fungsi:** Snapshot stok per slot di vending machine saat ini (current state, bukan log).

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id_recnum_mrs` | INT (PK) | Auto-increment |
| `id_recnum_mav` | INT | ID vending machine |
| `stok_qty` | INT | Jumlah susu saat ini di slot ini |
| `status_restok` | INT | Status (`1` = aktif) |
| `update_time` | DATETIME | Terakhir diupdate |
| `user_input` | VARCHAR | Siapa yang terakhir update (e.g., `'admin'`) |
| `slot_number` | VARCHAR | Slot fisik (e.g., `'A1'`, `'A2'`) |

**Relevansi untuk Inventory DSS:**
- Digunakan untuk menghitung **stok VM saat ini** per varian
- Perlu di-JOIN dengan `manage_map_slot_number` + `master_variant` untuk mapping slot → varian
- Ini adalah SNAPSHOT — hanya menunjukkan kondisi sekarang, bukan historis

---

### Table C: `dbo.monitor_log_stock`

**Fungsi:** Dirancang untuk rekap stok tahunan per slot (format pivot). **Tidak ada data.**

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id_recnum_mls` | INT (PK) | Auto-increment |
| `id_recnum_mav` | INT | ID vending machine |
| `slot_number` | VARCHAR | Slot fisik |
| `tahun` | INT | Tahun |
| `qm1` – `qm12` | INT? | Data bulanan (fungsi tidak jelas) |
| `qk1` – `qk12` | INT? | Data bulanan lain (fungsi tidak jelas) |

**Keputusan:** Table ini **TIDAK digunakan** untuk Inventory DSS. Strukturnya tidak cocok untuk tracking gudang pusat (memiliki `id_recnum_mav` dan `slot_number` yang spesifik ke VM).

---

### Table Referensi (Mapping Slot → Varian)

Untuk menerjemahkan slot di VM ke nama varian susu, dibutuhkan 2 table referensi:

**`dbo.manage_map_slot_number`:**
| Kolom | Keterangan |
|-------|------------|
| `id_recnum_mav` | ID vending machine |
| `slot_name` | Huruf depan slot (e.g., `'A'`, `'B'`) |
| `id_recnum_variant` | FK ke master_variant |

**`dbo.master_variant`:**
| Kolom | Keterangan |
|-------|------------|
| `id_recnum_variant` | PK |
| `nama_variant` | Nama varian: `'Coklat'`, `'Strawberry'`, `'Moca'`, `'Original (Putih)'` |

**Query mapping slot → varian:**
```sql
SELECT 
    v.nama_variant,
    SUM(r.stok_qty) AS total_vm_stock
FROM dbo.manage_restok r
JOIN dbo.manage_map_slot_number m 
    ON r.id_recnum_mav = m.id_recnum_mav 
    AND SUBSTRING(r.slot_number, 1, 1) = m.slot_name
JOIN dbo.master_variant v 
    ON m.id_recnum_variant = v.id_recnum_variant
WHERE r.status_restok = 1
GROUP BY v.nama_variant
```

---

## 1.2 Table Baru: `dbo.warehouse_stock`

### Desain: Ledger (Buku Kas)

Setiap baris = satu pergerakan stok (masuk atau keluar). Saldo dihitung secara running.

### DDL (CREATE TABLE)

```sql
CREATE TABLE [dbo].[warehouse_stock] (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    variant_name    NVARCHAR(50)  NOT NULL,        -- 'Coklat', 'Strawberry', 'Moca', 'Original (Putih)'
    movement_type   NVARCHAR(10)  NOT NULL,        -- 'IN' (dari supplier) atau 'OUT' (ke VM)
    qty             INT           NOT NULL,         -- Jumlah unit (selalu positif)
    balance_after   INT           NOT NULL,         -- Saldo gudang setelah transaksi ini
    note            NVARCHAR(200) NULL,             -- Opsional: PO number, keterangan
    created_by      NVARCHAR(50)  NOT NULL,         -- 'admin' (manual) atau 'auto-sync' (otomatis)
    created_at      DATETIME      NOT NULL DEFAULT GETDATE(),

    -- Constraints
    CONSTRAINT CK_movement_type CHECK (movement_type IN ('IN', 'OUT')),
    CONSTRAINT CK_qty_positive CHECK (qty > 0)
);

-- Index untuk query saldo terakhir per varian
CREATE NONCLUSTERED INDEX IX_warehouse_variant_time 
ON [dbo].[warehouse_stock] (variant_name, created_at DESC);
```

### Contoh Data

| id | variant_name | movement_type | qty | balance_after | note | created_by | created_at |
|----|-------------|---------------|-----|---------------|------|------------|------------|
| 1 | Coklat | IN | 500 | 500 | Stok awal Q1 | admin | 2026-01-02 08:00 |
| 2 | Strawberry | IN | 400 | 400 | Stok awal Q1 | admin | 2026-01-02 08:00 |
| 3 | Coklat | OUT | 20 | 480 | Restock VM #1 | auto-sync | 2026-01-05 10:30 |
| 4 | Coklat | OUT | 15 | 465 | Restock VM #1 | auto-sync | 2026-01-08 14:00 |
| 5 | Coklat | IN | 200 | 665 | PO-2026-003 | admin | 2026-02-01 09:00 |

### Query: Saldo Gudang Saat Ini Per Varian

```sql
-- Ambil balance_after terakhir per varian
SELECT ws.variant_name, ws.balance_after
FROM dbo.warehouse_stock ws
INNER JOIN (
    SELECT variant_name, MAX(id) AS max_id
    FROM dbo.warehouse_stock
    GROUP BY variant_name
) latest ON ws.id = latest.max_id
```

### Query: Total IN / OUT dalam Kuartal Tertentu

```sql
-- Contoh: Q1 2026 (Januari–Maret)
SELECT 
    variant_name,
    movement_type,
    SUM(qty) AS total_qty
FROM dbo.warehouse_stock
WHERE created_at >= '2026-01-01' AND created_at < '2026-04-01'
GROUP BY variant_name, movement_type
```

---

## 1.3 Table Prediksi (Sudah Ada)

### `dbo.ForecastResults_Layer1` — Sumber Utama DSS

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `Id` | INT (PK) | Auto-increment |
| `PredictedMonth` | VARCHAR(7) | e.g., `'2026-07'` |
| `TotalDemand` | INT | Total prediksi semua varian |
| `DemandCoklat` | INT | Prediksi khusus Coklat |
| `DemandMoca` | INT | Prediksi khusus Moca |
| `DemandOriginal` | INT | Prediksi khusus Original |
| `DemandStrawberry` | INT | Prediksi khusus Strawberry |
| `MAPE_Total` | FLOAT | Error rate total |
| `ActualDemand` | INT NULL | Aktual (diisi setelah bulan lewat) |
| `ErrorPercent` | FLOAT NULL | Error % (diisi setelah bulan lewat) |

**Query untuk DSS (1 kuartal = 3 bulan):**

```sql
-- Q3 2026 = Juli, Agustus, September
SELECT 
    PredictedMonth,
    TotalDemand,
    DemandCoklat,
    DemandMoca,
    DemandOriginal,
    DemandStrawberry
FROM dbo.ForecastResults_Layer1
WHERE PredictedMonth IN ('2026-07', '2026-08', '2026-09')
ORDER BY PredictedMonth ASC
```

---

## 1.4 Peta Relasi Lengkap

```
┌─────────────────────────────────┐
│    warehouse_stock (BARU)       │ ← Ledger gudang pusat
│    IN : manual oleh admin       │
│    OUT: auto-sync dari stocking │
└───────────────┬─────────────────┘
                │ OUT otomatis via sync
                ▼
┌─────────────────────────────────┐
│ monitor_log_datatransaksi       │ ← Event log VM (sudah ada)
│ kategori = 'stocking'           │
│ + mapping via:                  │
│   manage_map_slot_number        │
│   master_variant                │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ manage_restok                   │ ← Snapshot stok VM (sudah ada)
│ (stok_qty per slot saat ini)    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ ForecastResults_Layer1          │ ← Prediksi demand per bulan
│ (per varian, sudah agregasi)    │    (sudah ada)
└─────────────────────────────────┘

RUMUS DSS (per varian):
═══════════════════════════════════
Rekomendasi Beli = MAX(0,
    Prediksi Demand 3 bulan
  − Saldo Gudang (warehouse_stock)
  − Sisa VM (manage_restok mapped)
)
═══════════════════════════════════
```
