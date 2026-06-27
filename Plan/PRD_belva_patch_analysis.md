# PRD — Analisa Branch `belvatabitha-patch-1`
# Status: DRAFT | Dibuat: 2026-06-19

> **Tujuan dokumen ini:**
> Mendokumentasikan semua swagger baru, perubahan breaking, dan bug yang ditemukan
> di branch `belvatabitha-patch-1` sebelum di-merge ke `main` dan diintegrasikan ke Android Capstone.
>
> **Cara baca:**
> Setiap step diberi status `[ ]` = belum, `[x]` = selesai, `[!]` = ada masalah.
> Update status ini seiring perkembangan pengerjaan.

---

## ══════════════════════════════════════
## STEP 1 — RINGKASAN PERUBAHAN (SELESAI DIANALISA)
## ══════════════════════════════════════
**Status: [x] Analisa selesai**

### File Baru yang Ditambahkan:
| File | Fungsi |
|------|--------|
| `variant_service.py` | Refactor logika CRUD Variant ke service layer |
| `restock_service.py` | Business logic manajemen stok slot VM |
| `slot_service.py` | Business logic konfigurasi slot mesin |
| `machine_service.py` | Business logic data mesin vending |
| `shift_service.py` | Business logic jam shift kerja |
| `inventory_service.py` | Business logic Inventory Dashboard + DSS + Warehouse |
| `setup_manage_restok.sql` | Script SQL tabel `manage_restok` |
| `setup_master_variant.sql` | Script SQL perubahan tabel `master_variant` |
| `ANDROID_QUICK_START.md` | Panduan Android dari teman |
| `ANDROID_SETUP_GUIDE.md` | Setup guide Android dari teman |

### Swagger Group Baru:
| Tag Swagger | Endpoint | Keterangan |
|-------------|----------|------------|
| `Restock Management` | 7 endpoint | CRUD stok slot + low stock alert |
| `Slot Number` | 5 endpoint | CRUD konfigurasi slot mesin |
| `Manage Alat VM` | 5 endpoint | CRUD data mesin vending |
| `Shift Management` | 5 endpoint | CRUD jam shift kerja |
| `Inventory Dashboard` | 2 endpoint | Dashboard inventory + DSS + warehouse |

### Swagger yang Direfactor (sudah ada tapi diubah):
| Tag Swagger | Perubahan |
|-------------|-----------|
| `Varian (Android)` | Logika dipindah ke `variant_service.py`, schema berubah |

---

## ══════════════════════════════════════
## STEP 2 — DAFTAR BUG & MASALAH KRITIS
## ══════════════════════════════════════
**Status: [x] Analisa selesai — perlu diperbaiki sebelum merge**

---

### 🔴 BUG 1 — Breaking Change: Model Variant Berubah Kolom
**Tingkat: KRITIS**

Model `Variant` di `models.py` (branch baru) mengubah nama kolom:

| Kolom Lama (main) | Kolom Baru (patch) | Dampak |
|---|---|---|
| `url_image` | `image_url` | Query ORM lama akan crash |
| `status_variant` | `status` | Query ORM lama akan crash |
| *(tidak ada)* | `created_at` | Kolom baru, DB belum tentu punya |
| *(tidak ada)* | `updated_at` | Kolom baru, DB belum tentu punya |

**Lokasi masalah:**
- `models.py` → class `Variant`
- `main.py` → endpoint lama `/api/v1/variants` masih pakai schema `VariantBase/VariantCreate/VariantUpdate` lama
- `schemas.py` → Schema `VariantBase`, `VariantCreate`, `VariantUpdate` kemungkinan dihapus dan diganti dengan yang baru

**Yang perlu dicek:**
- Apakah `main.py` versi baru sudah mengganti endpoint Variant ke `variant_service.py`?
- Apakah kolom baru (`created_at`, `updated_at`, `image_url`, `status`) sudah ada di DB fisik?
- File `setup_master_variant.sql` perlu dijalankan dulu sebelum API bisa berjalan

---

### 🔴 BUG 2 — Kolom Tidak Dikenal di `ForecastResults_Layer1`
**Tingkat: KRITIS**

`inventory_service.py` query kolom yang kemungkinan TIDAK ADA di DB:

```python
# Di inventory_service.py baris ~100:
sql = text(
    "SELECT PredictedMonth, DemandCoklat, DemandStrawberry, DemandMoca, DemandOriginal, TotalDemand, ActualDemand, ErrorPercent "
    "FROM dbo.ForecastResults_Layer1 ..."
)
```

Kolom `DemandCoklat`, `DemandStrawberry`, `DemandMoca`, `DemandOriginal` **belum pernah disebutkan** di service layer lama (`forecast_service.py`). Jika kolom ini tidak ada di DB, endpoint `GET /api/v1/inventory/dashboard` akan crash dengan SQL error.

**Yang perlu dicek:** Jalankan query ini di SQL Server Management Studio untuk verifikasi:
```sql
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'ForecastResults_Layer1'
```

---

### 🔴 BUG 3 — Tabel `warehouse_stock` Baru, Belum Tentu Ada di DB
**Tingkat: KRITIS**

`inventory_service.py` dan `models.py` mereferensikan tabel `dbo.warehouse_stock` yang merupakan **tabel baru** — tidak ada di versi `main`. Jika tabel ini belum dibuat di SQL Server, **semua endpoint Inventory Dashboard akan crash**.

**Solusi:** Perlu script SQL `CREATE TABLE dbo.warehouse_stock` dijalankan. Cek apakah ada di `setup_manage_restok.sql`.

---

### 🟠 BUG 4 — Sintaks Python 3.10+ yang Tidak Kompatibel
**Tingkat: SEDANG** (tergantung versi Python)

Di `schemas.py` versi baru, banyak menggunakan sintaks union type Python 3.10+:
```python
# Contoh yang bermasalah jika Python < 3.10:
id_recnum_variant: int | None = None   # Harus: Optional[int] = None
total_added: int | None = None          # Harus: Optional[int] = None
slot_name: str | None = None            # Harus: Optional[str] = None
```

Juga di `inventory_service.py`:
```python
def get_inventory_dashboard(
    ...
    year: int | None = None,            # Harus: Optional[int] = None
    quarter: int | None = None,
    variant: str | None = None,
    movement_type: str | None = None,
    request: schemas.StockInRequest | None = None,
):
```

**Yang perlu dicek:** Versi Python yang dipakai (`python --version`). Jika < 3.10, semua `X | Y` harus diganti `Optional[X]`.

---

### 🟠 BUG 5 — `get_all_machines` Tidak Punya `response_model`
**Tingkat: RINGAN**

```python
# Di main.py baru:
@app.get("/api/v1/machine", tags=["Manage Alat VM"])   # ← tidak ada response_model
def get_all_machines(db: Session = Depends(get_db)):
    return machine_service.get_all_machines(db)
```

Semua endpoint GET list lainnya (`/api/v1/restock`, `/api/v1/shift`) juga tidak punya `response_model` untuk endpoint list. Swagger tidak bisa menampilkan schema response yang benar.

---

### 🟡 CATATAN 6 — `Variant.nama_variant` Sekarang `unique=True`
**Tingkat: PERHATIAN**

```python
# models.py baru:
nama_variant = Column(String(100), nullable=False, unique=True)
```

Jika di DB sudah ada data variant dengan nama duplikat, constraint ini akan menyebabkan error saat ORM sync. Perlu verifikasi data di DB sebelum deploy.

---

### 🟡 CATATAN 7 — `SlotNumber` Model Menambah Kolom Baru ke Tabel Lama
**Tingkat: PERHATIAN**

Tabel `manage_map_slot_number` sudah ada di DB (dipakai oleh ETL dan Dashboard). Model baru menambah kolom `id_recnum_msn` sebagai PK dan `slot_number_max`, `user_input`. Jika kolom ini belum ada di tabel DB fisik, CRUD Slot Number akan crash.

---

## ══════════════════════════════════════
## STEP 3 — DAFTAR ENDPOINT BARU LENGKAP
## ══════════════════════════════════════
**Status: [x] Terdokumentasi**

### 3A. Restock Management (`/api/v1/restock`)
| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/v1/restock` | List semua restock, optional filter `?status=0/1` |
| GET | `/api/v1/restock/{restock_id}` | Detail restock by ID |
| GET | `/api/v1/restock/vm/{vm_id}` | Semua restock aktif untuk 1 VM |
| POST | `/api/v1/restock` | Buat/update restock slot (upsert by slot) |
| PUT | `/api/v1/restock/{restock_id}` | Update restock by ID |
| DELETE | `/api/v1/restock/{restock_id}` | Hapus restock |
| PUT | `/api/v1/restock/vm/{vm_id}/slot/{slot_number}` | Shortcut update qty stok slot tertentu |
| GET | `/api/v1/restock/alerts/low-stock` | Alert stok di bawah threshold (default 10) |

**Tabel DB:** `dbo.manage_restok`
**Schema Request (Create):** `id_recnum_mav`, `stok_qty`, `slot_number`, `user_input` (default: admin), `status_restok` (default: 1)

---

### 3B. Slot Number (`/api/v1/slot`)
| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/v1/slot?vm_id={id}` | Ambil slot untuk VM tertentu |
| GET | `/api/v1/slot/{slot_id}` | Detail slot by ID |
| POST | `/api/v1/slot` | Buat konfigurasi slot baru |
| PUT | `/api/v1/slot/{slot_id}` | Update slot |
| DELETE | `/api/v1/slot/{slot_id}` | Hapus slot |

**Tabel DB:** `dbo.manage_map_slot_number`

---

### 3C. Manage Alat VM (`/api/v1/machine`)
| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/v1/machine` | List semua mesin |
| GET | `/api/v1/machine/{machine_id}` | Detail mesin by ID |
| POST | `/api/v1/machine` | Tambah mesin baru |
| PUT | `/api/v1/machine/{machine_id}` | Update mesin |
| DELETE | `/api/v1/machine/{machine_id}` | Hapus mesin |

**Tabel DB:** `dbo.master_alat_vm`

---

### 3D. Shift Management (`/api/v1/shift`)
| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/v1/shift` | List semua shift |
| GET | `/api/v1/shift/{shift_id}` | Detail shift by ID |
| POST | `/api/v1/shift` | Buat shift baru |
| PUT | `/api/v1/shift/{shift_id}` | Update shift |
| DELETE | `/api/v1/shift/{shift_id}` | Hapus shift |

**Tabel DB:** `dbo.master_settime`

---

### 3E. Inventory Dashboard (`/api/v1/inventory`)
| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/v1/inventory/dashboard` | Dashboard inventory lengkap + DSS |
| POST | `/api/v1/inventory/dashboard` | Stock-in ke gudang + return dashboard terbaru |

**Parameter GET:**
- `year` (int, opsional) — default: tahun sekarang
- `quarter` (int, opsional) — default: kuartal berikutnya
- `page` (int, default 1) — pagination pergerakan stok
- `per_page` (int, default 10, max 50)
- `variant` (string, opsional) — filter pergerakan by nama varian
- `type` (string, opsional) — filter `IN` atau `OUT`

**Response berisi:**
- `summary`: total predicted, warehouse stock, vm stock, to purchase
- `variants[]`: per-varian (predicted, warehouse, vm, to_purchase, monthly)
- `decision_support`: rekomendasi pembelian, top variant, catatan
- `movements`: riwayat pergerakan stok gudang (paginated)
- `auto_sync_info`: hasil sinkronisasi otomatis stok keluar dari transaksi ambil
- `stock_in_result`: hasil stock-in jika POST

**Tabel DB:** `dbo.warehouse_stock` (BARU), `dbo.ForecastResults_Layer1`, `dbo.manage_restok`

---

## ══════════════════════════════════════
## STEP 4 — CHECKLIST SEBELUM MERGE KE MAIN
## ══════════════════════════════════════
**Status: [x] SELESAI (semua item API side resolved)**

### Temuan Tambahan dari Analisa Lanjutan:

**🔴 BUG BARU — `setup_master_variant.sql` MENGHAPUS DATA EXISTING!**
Script SQL dari teman menggunakan `DROP TABLE dbo.master_variant` sebelum CREATE.
Ini akan **menghapus semua data variant yang sudah ada di DB**!
Script aman (ALTER TABLE) sudah dibuat di: `Plan/sql_safe/safe_alter_master_variant.sql`

**🔴 BUG BARU — Tidak Ada Script untuk Tabel `warehouse_stock`**
Tidak ditemukan script CREATE TABLE untuk `warehouse_stock` di branch teman.
Script sudah dibuat di: `Plan/sql_safe/create_warehouse_stock.sql`

**🟠 TEMUAN BARU — Endpoint Variant Path Berubah**
Path lama: `/api/v1/variants` (plural) → Path baru: `/api/v1/variant` (singular)
Tag Swagger juga berubah: `Varian (Android)` → `Variant Management`
Ini breaking change jika Android sudah pakai path lama.

**✅ BUG 4 TERTUTUP — Python 3.12 Terdeteksi**
Sintaks `int | None` valid di Python 3.12. Tidak ada yang perlu difix.

**✅ BUG 1 SEBAGIAN — Endpoint Variant Sudah Direfactor**
Endpoint `/api/v1/variant` sudah memakai `variant_service.py`. Tidak ada duplikasi.
Sisanya: DB perlu di-update dengan script AMAN (bukan DROP TABLE).

---

Selesaikan semua item berikut sebelum branch ini di-merge ke `main`:

- [SKIP] **4.1** — Tabel `manage_restok` sudah ada di DB sejak awal. Script tidak perlu dijalankan.
- [SKIP] **4.2** — Keputusan final: kolom `master_variant` TIDAK diubah. Tetap pakai `url_image` & `status_variant` (skema DB asli). Script safe_alter TIDAK perlu dijalankan.
- [x] **4.3** — Tabel `warehouse_stock` sudah dibuat oleh user di SSMS. ✅
- [x] **4.4** — User konfirmasi kolom `DemandCoklat/Strawberry/Moca/Original` ada di `ForecastResults_Layer1`. ✅
- [x] **4.5** — Python 3.12 terdeteksi. Sintaks `int | None` valid. TIDAK ADA yang perlu difix. ✅
- [x] **4.6** — Semua kolom `manage_map_slot_number` terverifikasi ada di DB. ✅
- [x] **4.7** — Keputusan final: path `/api/v1/variants` DIPERTAHANKAN (tidak diubah ke singular). Kode teman TIDAK dipakai untuk Variant. ✅
- [x] **4.8** — Semua test passed: 4 swagger baru (27 tests) + Inventory Dashboard (17 tests) = 44/44 PASS. ✅

---

## ══════════════════════════════════════
## STEP 5 — UPDATE API_BUNDLE.md
## ══════════════════════════════════════
**Status: [x] SELESAI**

- [x] Tambahkan section `[NEW] Variant Management` (refactor path lama)
- [x] Tambahkan section `[NEW] Restock Management` dengan endpoint lengkap dari STEP 3A
- [x] Tambahkan section `[NEW] Manage Alat VM` dari STEP 3C
- [x] Tambahkan section `[NEW] Shift Management` dari STEP 3D
- [x] Tambahkan section `[NEW] Slot Number` dari STEP 3B
- [x] Tambahkan section `[NEW] Inventory Dashboard` dari STEP 3E
- [x] Update urutan prioritas eksekusi di Bagian 4 (13 item, BARU diutamakan)

---

## ══════════════════════════════════════
## STEP 6 — INTEGRASI KE ANDROID CAPSTONE
## ══════════════════════════════════════
**Status: [ ] Belum dimulai — tunggu STEP 4 & 5 selesai**

Sub menu yang perlu dibuat di Android (menu "module", sejajar "Management Variant"):

| Sub Menu Android | Swagger Source | Prioritas |
|------------------|---------------|-----------|
| Management Variant | `Varian (Android)` | Sudah ada |
| Restock Management | `Restock Management` | Tinggi |
| Manage Alat VM | `Manage Alat VM` | Tinggi |
| Shift Management | `Shift Management` | Sedang |
| Slot Number | `Slot Number` | Sedang |
| Inventory Dashboard | `Inventory Dashboard` | Tinggi |

---

## ══════════════════════════════════════
## CATATAN TAMBAHAN DARI ANALISA
## ══════════════════════════════════════

1. **Kualitas kode teman secara umum cukup baik** — pattern konsisten, ada validasi input, error handling dengan HTTPException. Yang perlu diperbaiki hanya masalah kompatibilitas Python dan potensi mismatch DB schema.

2. **`inventory_service.py` adalah yang paling kompleks** — menggabungkan forecast data, warehouse stock, VM stock, auto-sync, dan DSS dalam satu response. Perlu pengujian end-to-end setelah DB fix.

3. **Auto-sync logic di Inventory** — setiap kali endpoint dashboard dipanggil, otomatis akan sync transaksi `stocking` dari `monitor_log_datatransaksi` ke `warehouse_stock` sebagai OUT movement. Ini bisa menyebabkan **data dobel** jika endpoint dipanggil berkali-kali tanpa watermark yang benar. Perlu dimonitor.

4. **`POST /api/v1/restock` bersifat upsert** — jika slot sudah ada untuk VM tersebut, data akan di-UPDATE bukan di-INSERT baru. Ini perlu dikomunikasikan ke tim Android agar tidak membingungkan.
