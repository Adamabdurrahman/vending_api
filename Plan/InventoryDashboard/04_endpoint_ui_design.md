# Poin 4 — Desain Endpoint & UI (Inventory Dashboard DSS)

## 4.1 Endpoint Specifications

### Endpoint 1: `GET /api/v1/inventory/dashboard`

```
GET /api/v1/inventory/dashboard?year=2026&quarter=3
```

| Aspek | Detail |
|-------|--------|
| **Method** | GET |
| **Auth** | Tidak (sesuai pattern existing) |
| **Query Params** | `year` (int, optional), `quarter` (int 1-4, optional) |
| **Default** | year=tahun ini, quarter=kuartal berikutnya |
| **Pre-process** | Auto-sync OUT dari stocking events (Alur B) |
| **Response** | JSON lengkap (lihat 03_data_response.md Section 3.1) |
| **Error 404** | Jika prediksi tidak tersedia → `has_prediction_data: false` |

**Server-side flow:**
1. Parse params → determine target quarter
2. Run auto-sync (watermark-based OUT deduction)
3. Query ForecastResults_Layer1 for predictions
4. Query warehouse_stock for current balances
5. Query manage_restok + mapping for VM stock
6. Calculate DSS per variant
7. If past quarter → calculate history_summary
8. Build available_quarters list
9. Return JSON

---

### Endpoint 2: `GET /api/v1/inventory/movements`

```
GET /api/v1/inventory/movements?page=1&per_page=10&variant=Coklat&type=IN
```

| Aspek | Detail |
|-------|--------|
| **Method** | GET |
| **Query Params** | `page` (int, default 1), `per_page` (int, default 10, max 50) |
| **Filter Params** | `variant` (string, optional), `type` (IN/OUT, optional) |
| **Response** | Paginated list (lihat 03_data_response.md Section 3.2) |
| **Sort** | `created_at DESC` (terbaru dulu) |

**Server-side flow:**
1. Build WHERE clause from filters
2. Count total matching rows
3. Calculate total_pages
4. Query with OFFSET/FETCH (pagination SQL Server)
5. Format dates to Indonesian
6. Return paginated JSON

---

### Endpoint 3: `POST /api/v1/inventory/stock-in`

```
POST /api/v1/inventory/stock-in
Content-Type: application/json
```

| Aspek | Detail |
|-------|--------|
| **Method** | POST |
| **Body** | `{ items: [{variant_name, qty}], note }` |
| **Validasi** | variant_name valid, qty >= 0, minimal 1 qty > 0 |
| **Response** | Success dengan detail per varian (lihat 03_data_response.md Section 3.3) |
| **Side effect** | Insert IN entries ke warehouse_stock |

**Server-side flow:**
1. Validate request body
2. Filter items where qty > 0
3. For each item:
   a. Get latest balance for variant
   b. Calculate new balance
   c. Insert row in warehouse_stock
4. Return success with results

---

## 4.2 Backend File Structure

### File baru di `vending_api/`:

```
vending_api/
├── inventory_service.py        ← [NEW] Semua logika bisnis inventory
├── main.py                     ← [MODIFY] Tambah 3 endpoint inventory
└── setup_forecast_tables.py    ← [MODIFY] Tambah CREATE TABLE warehouse_stock
```

### `inventory_service.py` — Functions

| Function | Keterangan |
|----------|------------|
| `sync_warehouse_out(db)` | Auto-sync: detect stocking events → insert OUT |
| `get_latest_balance(db, variant)` | Ambil balance_after terakhir per varian |
| `get_vm_stock_by_variant(db)` | Query manage_restok → mapping → SUM per varian |
| `get_warehouse_stock_all(db)` | Saldo gudang semua varian |
| `get_inventory_dashboard(db, year, quarter)` | Main DSS calculation |
| `get_stock_movements(db, page, per_page, variant, type)` | Paginated movements |
| `add_stock_in(db, items, note)` | Batch insert IN entries |
| `get_available_quarters(db)` | List kuartal yang ada datanya |
| `get_history_summary(db, year, quarter)` | Rekap kuartal lalu |

### `main.py` — Endpoint Registration

```python
# === INVENTORY DASHBOARD ===
@app.get("/api/v1/inventory/dashboard")
def inventory_dashboard(year: int = None, quarter: int = None, db = Depends(get_db)):
    ...

@app.get("/api/v1/inventory/movements")
def inventory_movements(page: int = 1, per_page: int = 10, 
                         variant: str = None, type: str = None,
                         db = Depends(get_db)):
    ...

@app.post("/api/v1/inventory/stock-in")
def inventory_stock_in(request: StockInRequest, db = Depends(get_db)):
    ...
```

---

## 4.3 Android UI Design

### Screen 1: `InventoryDashboardActivity`

```
┌─────────────────────────────────────────┐
│ ← Inventory Dashboard                    │  ← Toolbar + back button
├─────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────────┐     │
│  │ [2026 ▼]  [Q3 (Jul-Sep) ▼]    │     │  ← Spinner tahun + kuartal
│  └─────────────────────────────────┘     │
│                                          │
│  ═══ RINGKASAN ═══════════════════════   │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │ 📊       │  │ 📦       │             │  ← Summary cards (2x2 grid)
│  │ PREDIKSI │  │ GUDANG   │             │
│  │  2,600   │  │   480    │             │
│  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐             │
│  │ 🏭       │  │ 🛒       │             │
│  │ STOK VM  │  │PERLU BELI│             │
│  │   110    │  │  2,010   │ ← accent    │
│  └──────────┘  └──────────┘             │
│                                          │
│  ═══ REKOMENDASI PER VARIAN ════════     │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 🟤 Coklat           Beli: 605   │    │  ← Variant card
│  │──────────────────────────────────│    │
│  │ Prediksi: 850                    │    │
│  │ Gudang:   200  │  VM: 45        │    │
│  │ Tersedia: 245  │  30.1% total   │    │
│  │──────────────────────────────────│    │
│  │ Detail Bulanan:                  │    │  ← Selalu tampil
│  │  ┌────────┬────────┬────────┐   │    │
│  │  │  Juli  │Agustus │  Sept  │   │    │
│  │  │  280   │  290   │  280   │   │    │
│  │  └────────┴────────┴────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 🔴 Strawberry       Beli: 540   │    │
│  │──────────────────────────────────│    │
│  │ Prediksi: 720                    │    │
│  │ Gudang:   150  │  VM: 30        │    │
│  │ Tersedia: 180  │  26.9% total   │    │
│  │──────────────────────────────────│    │
│  │ Detail Bulanan:                  │    │
│  │  ┌────────┬────────┬────────┐   │    │
│  │  │  Juli  │Agustus │  Sept  │   │    │
│  │  │  240   │  250   │  230   │   │    │
│  │  └────────┴────────┴────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ ☕ Moca               Beli: 500  │    │
│  │  ... (sama seperti di atas)      │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ ⬜ Original (Putih)  Beli: 365   │    │
│  │  ... (sama seperti di atas)      │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ═══ PERGERAKAN STOK ═══════════════     │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 28 Mei │ IN  │ Coklat │+200│admin│   │
│  │────────────────────────────────── │   │
│  │ 27 Mei │ OUT │ Straw  │-15 │auto │   │
│  │────────────────────────────────── │   │
│  │ 27 Mei │ OUT │ Coklat │-20 │auto │   │
│  │────────────────────────────────── │   │
│  │ 25 Mei │ IN  │ Moca   │+100│admin│   │
│  │────────────────────────────────── │   │
│  │ ... (10 item per halaman)        │   │
│  │────────────────────────────────── │   │
│  │     [ Muat Lebih Banyak ]        │   │  ← Load more (pagination)
│  └──────────────────────────────────┘    │
│                                          │
│  ═══ HANYA UNTUK KUARTAL LALU ══════    │
│  (Section ini hidden jika kuartal       │
│   aktif/mendatang)                       │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 📋 Ringkasan Histori Q1 2026    │    │
│  │──────────────────────────────────│    │
│  │ Stok Masuk (IN)  :       800    │    │
│  │ Ke VM (OUT)      :       620    │    │
│  │ Diambil Karyawan :       580    │    │
│  │ Prediksi Saat Itu:       600    │    │
│  │ Aktual Konsumsi  :       580    │    │
│  │ Akurasi Prediksi :     96.7%    │    │
│  │──────────────────────────────────│    │
│  │ Per Varian:                      │    │
│  │  Coklat    │ IN:250 OUT:190 ↓175│    │
│  │  Strawberry│ IN:200 OUT:160 ↓155│    │
│  │  Moca      │ IN:180 OUT:145 ↓135│    │
│  │  Original  │ IN:170 OUT:125 ↓115│    │
│  └──────────────────────────────────┘    │
│                                          │
│                                 ┌─────┐  │
│                                 │  +  │  │  ← FAB: Tambah Stok Masuk
│                                 └─────┘  │
└─────────────────────────────────────────┘
```

---

### Screen 2: `StockInActivity`

Dibuka saat FAB "+" diklik. Menerima data rekomendasi dari dashboard via Intent extras.

```
┌─────────────────────────────────────────┐
│ ← Tambah Stok Masuk                     │
├─────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────────┐     │
│  │ 📦 Input Stok Masuk — Q3 2026  │     │
│  │ Catat kiriman susu dari supplier│     │
│  └─────────────────────────────────┘     │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 🟤 Coklat                        │    │
│  │ Rekomendasi beli: 605 unit       │    │  ← Dari DSS calculation
│  │ Sisa gudang saat ini: 200        │    │  ← Dari warehouse_stock
│  │                                   │    │
│  │ Jumlah masuk:                    │    │
│  │ ┌────────────────────────────┐   │    │
│  │ │  placeholder: 605          │   │    │  ← Hint = to_purchase
│  │ └────────────────────────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 🔴 Strawberry                    │    │
│  │ Rekomendasi beli: 540 unit       │    │
│  │ Sisa gudang saat ini: 150        │    │
│  │                                   │    │
│  │ Jumlah masuk:                    │    │
│  │ ┌────────────────────────────┐   │    │
│  │ │  placeholder: 540          │   │    │
│  │ └────────────────────────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ ☕ Moca                           │    │
│  │ Rekomendasi beli: 500 unit       │    │
│  │ Sisa gudang saat ini: 80         │    │
│  │                                   │    │
│  │ Jumlah masuk:                    │    │
│  │ ┌────────────────────────────┐   │    │
│  │ │  placeholder: 500          │   │    │
│  │ └────────────────────────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ ⬜ Original (Putih)              │    │
│  │ Rekomendasi beli: 365 unit       │    │
│  │ Sisa gudang saat ini: 50         │    │
│  │                                   │    │
│  │ Jumlah masuk:                    │    │
│  │ ┌────────────────────────────┐   │    │
│  │ │  placeholder: 365          │   │    │
│  │ └────────────────────────────┘   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Catatan (opsional):                     │
│  ┌──────────────────────────────┐        │
│  │  e.g. PO-2026-007            │        │
│  └──────────────────────────────┘        │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │     💾  SIMPAN STOK MASUK        │    │  ← MaterialButton, primary color
│  └──────────────────────────────────┘    │
│                                          │
└─────────────────────────────────────────┘
```

**Behavior:**
- Input field = `TextInputEditText` dengan `inputType="number"`
- Placeholder (hint) = angka rekomendasi dari DSS
- Boleh dikosongkan (dianggap 0 → skip)
- Setelah sukses → tampilkan dialog ringkasan → navigasi kembali ke Dashboard (refresh)

---

## 4.4 Android File Structure

### File baru di Android project:

```
app/src/main/java/com/example/capstoneproject/
├── InventoryDashboardActivity.java    ← [MODIFY] Sekarang hub utama
├── StockInActivity.java               ← [NEW] Input stok masuk
├── models/
│   ├── InventoryDashboardResponse.java    ← [NEW] Model utama
│   ├── InventorySummary.java              ← [NEW] Summary cards
│   ├── InventoryVariantItem.java          ← [NEW] Per-variant data
│   ├── InventoryMonthlyItem.java          ← [NEW] Monthly breakdown
│   ├── InventoryHistorySummary.java       ← [NEW] Rekap kuartal lalu
│   ├── InventoryHistoryVariant.java       ← [NEW] Histori per varian
│   ├── StockMovementResponse.java         ← [NEW] Paginated movements
│   ├── StockMovementItem.java             ← [NEW] Single movement
│   ├── StockInRequest.java                ← [NEW] Request body stock-in
│   ├── StockInResponse.java              ← [NEW] Response stock-in
│   └── AvailableQuarter.java             ← [NEW] Quarter dropdown item
├── adapters/
│   └── StockMovementAdapter.java         ← [NEW] RecyclerView adapter
├── network/
│   └── ApiService.java                   ← [MODIFY] Tambah 3 endpoint

app/src/main/res/layout/
├── activity_inventory_dashboard.xml       ← [NEW] Layout dashboard
├── item_variant_card.xml                  ← [NEW] Card per varian
├── item_stock_movement.xml               ← [NEW] Row movement log
├── activity_stock_in.xml                 ← [NEW] Layout input stok
├── item_stock_in_variant.xml             ← [NEW] Row input per varian

app/src/main/res/drawable/
├── bg_card_summary_inventory.xml         ← [NEW] Background card
├── bg_variant_card.xml                   ← [NEW] Background variant card
├── ic_warehouse.xml                      ← [NEW] Icon gudang
├── ic_vending_machine.xml                ← [NEW] Icon VM
├── ic_shopping_cart.xml                  ← [NEW] Icon beli

app/src/main/AndroidManifest.xml          ← [MODIFY] Register StockInActivity
```

### API Service Methods (tambahan di `ApiService.java`)

```java
// Inventory Dashboard
@GET("api/v1/inventory/dashboard")
Call<InventoryDashboardResponse> getInventoryDashboard(
    @Query("year") int year,
    @Query("quarter") int quarter
);

// Stock Movements (paginated)
@GET("api/v1/inventory/movements")
Call<StockMovementResponse> getStockMovements(
    @Query("page") int page,
    @Query("per_page") int perPage
);

// Stock In (batch)
@POST("api/v1/inventory/stock-in")
Call<StockInResponse> addStockIn(
    @Body StockInRequest request
);
```

### Data Flow: Dashboard → StockIn Activity

```java
// Di InventoryDashboardActivity, saat FAB diklik:
Intent intent = new Intent(this, StockInActivity.class);
intent.putExtra("year", currentYear);
intent.putExtra("quarter", currentQuarter);
intent.putExtra("quarter_label", quarterLabel);

// Kirim rekomendasi per varian sebagai JSON string
String variantsJson = new Gson().toJson(variantsList);
intent.putExtra("variants_data", variantsJson);

startActivityForResult(intent, REQUEST_STOCK_IN);

// Di StockInActivity, ambil data:
int year = getIntent().getIntExtra("year", 2026);
String variantsJson = getIntent().getStringExtra("variants_data");
// Parse → set placeholder per varian
```

### Setelah StockIn Berhasil → Refresh Dashboard

```java
// Di StockInActivity, setelah POST sukses:
setResult(RESULT_OK);
finish();

// Di InventoryDashboardActivity:
@Override
protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    if (requestCode == REQUEST_STOCK_IN && resultCode == RESULT_OK) {
        // Refresh dashboard data
        loadDashboardData(currentYear, currentQuarter);
    }
}
```

---

## 4.5 Tema Visual

| Elemen | Style |
|--------|-------|
| **Background** | Dark theme (sesuai existing: `#1A1A2E` atau `#0F0F23`) |
| **Card summary** | Gradient subtle, rounded corners 12dp |
| **Card "Perlu Beli"** | Accent color (indigo/teal) untuk highlight |
| **Variant cards** | `#1E1E3A` background, border left berwarna per varian |
| **Warna varian** | Coklat=#8B4513, Strawberry=#DC143C, Moca=#D2B48C, Original=#F5F5F5 |
| **IN badge** | Green (#4CAF50) |
| **OUT badge** | Orange (#FF9800) |
| **FAB** | Primary color (indigo) |
| **Typography** | Inter / Roboto (sesuai existing) |

---

## 4.6 Ringkasan Implementasi

### Backend (Python/FastAPI)

| # | File | Aksi | Estimasi |
|---|------|------|----------|
| 1 | `setup_forecast_tables.py` | Tambah CREATE TABLE warehouse_stock | Kecil |
| 2 | `inventory_service.py` | Buat baru — semua logika bisnis | Besar |
| 3 | `main.py` | Tambah 3 endpoint | Sedang |

### Android (Java)

| # | File | Aksi | Estimasi |
|---|------|------|----------|
| 1 | Models (9 file) | Buat baru — POJO/Gson | Kecil |
| 2 | `ApiService.java` | Tambah 3 method | Kecil |
| 3 | `activity_inventory_dashboard.xml` | Buat baru — layout utama | Besar |
| 4 | `InventoryDashboardActivity.java` | Buat baru — logic + binding | Besar |
| 5 | `activity_stock_in.xml` | Buat baru — form input | Sedang |
| 6 | `StockInActivity.java` | Buat baru — logic input | Sedang |
| 7 | Adapter + item layouts | Buat baru — RecyclerView | Sedang |
| 8 | Drawables + icons | Buat baru — visual assets | Kecil |
| 9 | `AndroidManifest.xml` | Register activity baru | Kecil |
