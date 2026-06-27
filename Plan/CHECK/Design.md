# 📐 Design System — CapstoneProject Android
> **Benchmark:** Operational Calendar (`activity_operational_calendar.xml`)
> **Tujuan:** Menyeragamkan UI/UX semua sub-menu "Module" agar clean, konsisten, dan setara standar Kalender Operasional.

---

## 1. Warna (Color Palette)

### 1.1 Warna Global (`colors.xml`)
| Token Name               | Hex         | Keterangan                            |
|--------------------------|-------------|---------------------------------------|
| `black`                  | `#FF000000` | Teks utama / judul tebal              |
| `white`                  | `#FFFFFFFF` | Background card, header, navbar       |
| `primary_blue`           | `#1A73E8`   | Biru primer (legacy)                  |
| `light_blue`             | `#E3F2FD`   | Background chip biru muda             |
| `text_grey`              | `#757575`   | Teks sekunder, label, sub-info        |
| `dashboard_bg`           | `#F5F6F8`   | Background halaman utama (abu terang) |
| `sidebar_bg`             | `#1A2132`   | Background sidebar gelap              |
| `sidebar_item_selected`  | `#2563EB`   | Warna item aktif sidebar, FAB         |
| `sidebar_text_inactive`  | `#BDC3D1`   | Teks menu sidebar yang tidak aktif    |
| `sidebar_logout`         | `#EF4444`   | Merah tombol logout / hapus           |
| `accuracy_green`         | `#10B981`   | Hijau status aktif / sukses           |
| `verified_bg`            | `#D1FAE5`   | Background chip hijau muda            |
| `delete_red`             | `#EF4444`   | Merah tombol delete                   |
| `chart_blue`             | `#2563EB`   | Biru grafik / stripe card             |
| `chart_grey`             | `#94A3B8`   | Abu grafik / teks muted               |

### 1.2 Warna Inline Penting (Hardcoded, dipakai berulang)
| Warna                  | Hex       | Dipakai di                                      |
|------------------------|-----------|-------------------------------------------------|
| **Brand Indigo**       | `#818CF8` | Ikon header, FAB tambah, indicator loading, chevron navigasi |
| **Deep Indigo**        | `#8B5CF6` | Teks Ramadan legend, accent purple              |
| **Slate Dark**         | `#1E293B` | Background card item shift (dark mode card)     |
| **Slate Medium**       | `#334155` | Nilai angka dalam grid detail variant           |
| **Slate Light**        | `#64748B` | Label UPPERCASE kecil (PREDIKSI, GUDANG, dll.)  |
| **Slate Muted**        | `#94A3B8` | Teks keterangan muted di dark card              |
| **Sky Blue**           | `#38BDF8` | Jam/waktu shift di dark card                    |
| **Divider**            | `#F1F5F9` | Garis pemisah dalam card                        |
| **Card Stroke**        | `#E2E8F0` | Border luar MaterialCardView                    |
| **Card Stroke Alt**    | `#E5E7EB` | Border alternatif card                          |
| **Badge Green BG**     | `#D1FAE5` | Background badge ACTIVE                         |
| **Badge Green Text**   | `#059669` | Teks badge ACTIVE (hijau tua)                   |
| **Badge Blue BG**      | `#EFF6FF` | Background badge Beli/Qty (biru pucat)          |
| **Badge Blue Text**    | `#2563EB` | Teks badge Beli/Qty                             |
| **Month Header**       | `#2B3674` | Nama bulan di kartu kalender (biru tua legam)   |
| **Day Header Grey**    | `#4B5563` | Label hari kerja (Sen–Jum)                      |
| **Weekend Red**        | `#EF4444` | Label Sabtu & Minggu                            |
| **Loading Overlay**    | `#CC0F172A` | Overlay background loading (80% opacity navy) |
| **Loading Text**       | `#E2E8F0` | Teks loading utama                              |
| **Loading SubText**    | `#94A3B8` | Teks loading sekunder                           |

---

## 2. Tipografi

| Elemen                       | Size  | Style      | Warna              |
|------------------------------|-------|------------|--------------------|
| Judul halaman (header bar)   | 18sp  | bold       | `@color/black`     |
| Judul bulan/section          | 18sp  | bold       | `#2B3674`          |
| Navigasi bulan (tengah)      | 16sp  | bold       | `@color/black`     |
| Nama item utama (card)       | 16sp  | bold       | `@color/black` / `#1E293B` / `#F1F5F9` |
| Sub-info item (NIK, bagian)  | 13sp  | normal     | `@color/text_grey` / `#94A3B8` |
| Jam/waktu shift              | 12sp  | normal     | `#38BDF8`          |
| Label UPPERCASE kecil        | 10-11sp | bold    | `#64748B`          |
| Badge teks                   | 10-11sp | bold    | Sesuai tema badge  |
| Legend/subtitle kecil        | 11-12sp | normal  | `@color/text_grey` |
| Nilai angka besar (grid)     | 15sp  | bold       | `#334155`          |
| Label halaman (spinner)      | 13sp  | normal     | `@color/text_grey` |

---

## 3. Komponen UI

### 3.1 Header Bar (Benchmark: Kalender Operasional)
```
Struktur:
┌─────────────────────────────────────────────┐
│  [← Back]   [Judul Halaman]         [🗓 Ikon] │  ← Row 1: Back + Title + Dekoratif
│  [Label:]  [Spinner Card]  [🗑] [+ Aksi Btn]  │  ← Row 2: Filter/Action Row  (opsional)
│  Total Hari: —                               │  ← Row 3: Info summary (opsional)
└─────────────────────────────────────────────┘
```

**Spesifikasi:**
- Background: `@color/white`
- Elevation: `4dp`
- Padding: `paddingStart/End 16dp`, `paddingTop 16dp`, `paddingBottom 12dp`
- Tombol Back: `ImageView` 36×36dp, padding 6dp, icon `ic_back`, tint `@color/black`
- Judul: `textSize="18sp"`, `textStyle="bold"`, `textColor="@color/black"`
- Ikon dekoratif kanan: 24×24dp, tint `#818CF8`

### 3.2 Toolbar Alternatif (dipakai Employee, dll.)
```
Struktur:
┌─────────────────────────────────────────────┐
│  ☰             [Judul Halaman]          🔍   │
└─────────────────────────────────────────────┘
```
> ⚠️ **Perlu diupgrade** ke format "Header Bar" Kalender Operasional yang lebih clean dan informatif.

### 3.3 MaterialCardView — Item List (Light)
```xml
<MaterialCardView
    cardCornerRadius="12dp"
    cardElevation="2dp"
    strokeColor="#E2E8F0"
    strokeWidth="1dp"
    cardBackgroundColor="@color/white"
    layout_marginHorizontal="16dp"
    layout_marginVertical="8dp" />
```
- Padding dalam: `16dp`
- Divider internal: `#F1F5F9`, height `1dp`, margin atas-bawah `12dp`

### 3.4 MaterialCardView — Item List (Dark / Shift Style)
```xml
<CardView
    cardBackgroundColor="#1E293B"
    cardCornerRadius="14dp"
    cardElevation="4dp"
    layout_marginHorizontal="16dp"
    layout_marginTop="10dp" />
```
- Dipakai untuk item Shift sebagai variasi dark card

### 3.5 Stripe Indicator (Variant Card)
- `View` lebar `6dp`, penuh tinggi card
- Background: `#2563EB` (biru brand)
- Dipasang di sisi kiri card sebagai identitas visual

### 3.6 Badge
| Tipe      | BG         | Text Color | Text         | Padding            |
|-----------|------------|------------|--------------|---------------------|
| ACTIVE    | `#D1FAE5`  | `#059669`  | "ACTIVE"     | `8dp H / 2dp V`    |
| AKTIF     | `bg_active_badge` | `#065F46` | "Aktif" | drawable-based    |
| Beli/Qty  | `#EFF6FF`  | `#2563EB`  | "Beli: 605"  | `10dp H / 4dp V`   |
| Working   | `bg_active_badge` | `#166534` | "20 Hari Kerja" | `10dp H / 4dp V` |
| Blocked   | `bg_blocked_badge` | `#EF4444` | hapus icon | drawable-based  |

### 3.7 FAB (Floating Action Button)
```xml
<FloatingActionButton
    backgroundTint="@color/sidebar_item_selected"  <!-- #2563EB -->
    layout_margin="24dp"
    srcCompat="@drawable/ic_add"
    tint="@color/white" />
```
- Ditempatkan di sudut kanan bawah
- Di atas pagination bar

### 3.8 MaterialButton (Aksi Header)
```xml
<MaterialButton
    backgroundTint="#818CF8"
    cornerRadius="8dp"
    height="36dp"
    paddingStart="12dp"
    paddingEnd="12dp"
    textSize="12sp" />
```

### 3.9 Spinner (Pilihan Filter)
- Dibungkus `MaterialCardView` height `36dp`, `cornerRadius="8dp"`, `strokeColor="#E2E8F0"`, `strokeWidth="1dp"`, `cardElevation="2dp"`
- Spinner padding: `paddingStart="12dp"`, `paddingEnd="4dp"`

### 3.10 Loading Overlay (Premium)
```
Overlay penuh: background="#CC0F172A" (80% opacity navy hitam)
Card loading:
  - Background: @drawable/bg_loading_card
  - Width: 200dp, gravity: center
  - Elevation: 16dp, padding: 28dp
  - CircularProgressIndicator: 56×56dp, indicatorColor="#818CF8", trackColor="#30818CF8", thickness=5dp
  - Teks utama: "Memuat..." | 13sp | bold | #E2E8F0 | letterSpacing=0.08
  - Teks sub: "Harap tunggu sebentar" | 11sp | #94A3B8 | marginTop=4dp
```

### 3.11 Chevron Navigasi
- `ImageView` 40×40dp
- `background="?attr/selectableItemBackgroundBorderless"` ← ripple effect tanpa border
- `padding="8dp"`
- `tint="#818CF8"` (indigo)

### 3.12 Action Icon Buttons (di dalam item card)
- `ImageView` 24dp × 24dp (untuk layout lama)
- `ImageView` 36dp × 36dp dengan `padding="6dp"` (standar baru)
- Background: `?attr/selectableItemBackgroundBorderless` (ripple borderless)
- Edit icon: `ic_pencil`, tint `#94A3B8`
- Delete icon: `ic_trash`, tint `#EF4444`
- `clickable="true"`, `focusable="true"`

---

## 4. Layout & Spacing

| Elemen                     | Nilai          |
|----------------------------|----------------|
| Margin horizontal card     | `16dp`         |
| Margin vertikal card       | `8dp` (top 10dp untuk shift) |
| Padding dalam card         | `16dp`         |
| Padding header bar         | `Start/End: 16dp`, `Top: 16dp`, `Bottom: 12dp` |
| Gap antara rows header     | `marginTop: 12dp` |
| Divider margin             | `Top/Bottom: 12dp` |
| Bottom padding RecyclerView | `80dp` (untuk tidak tertutup FAB) |
| Pagination bar height      | `64dp`         |
| Navigation bar height      | `56dp`         |

---

## 5. Background Drawables (Referensi)

| Drawable               | Dipakai di                                  |
|------------------------|---------------------------------------------|
| `bg_active_badge`      | Badge ACTIVE/AKTIF, badge hari kerja        |
| `bg_blocked_badge`     | Background tombol hapus (merah rounded)     |
| `bg_loading_card`      | Card di loading overlay                     |
| `bg_day_working`       | Dot legend hari kerja                       |
| `bg_day_holiday`       | Dot legend libur nasional                   |
| `bg_day_cuti`          | Dot legend cuti bersama                     |
| `bg_day_shutdown`      | Dot legend shutdown                         |
| `circle_background`    | Avatar circle (shift initial, status dot)   |
| `sidebar_item_background` | Pagination halaman aktif                 |

---

## 6. Status Module — Kondisi Saat Ini vs Target

| Module                | Layout Saat Ini              | Kondisi Header      | Kondisi Card Item    | Target Redesign |
|-----------------------|------------------------------|---------------------|----------------------|-----------------|
| **Employee**          | `activity_employee.xml`      | ❌ Toolbar lama     | ✅ Light card OK     | Header → Calendar style |
| **Master VM**         | `activity_master_data_user.xml` | ❓ Belum dicek   | ❓ Belum dicek       | Perlu audit     |
| **Master Variant**    | `activity_master_variant.xml` | ❓ Belum dicek    | ✅ Ada stripe, divider | Audit + seragamkan |
| **Shift Mgmt**        | `activity_shift_management.xml` | ❓ Belum dicek  | ✅ Dark card OK      | Header → Calendar style |
| **Slot Mgmt**         | `activity_slot_management.xml` | ❓ Belum dicek   | ❓ Belum dicek       | Perlu audit     |
| **Restock Mgmt**      | `activity_restock_management.xml` | ❓ Belum dicek | ❓ Belum dicek      | Perlu audit     |

**Legend:** ✅ Sudah sesuai | ❌ Perlu ganti | ❓ Perlu dicek

---

## 7. Design Principles (Dari Benchmark)

1. **Hierarchy yang jelas** → Header → Filter Bar → Content List → Pagination/FAB
2. **Warna konsisten** → Indigo `#818CF8` untuk aksen, Biru `#2563EB` untuk aksi utama, Merah `#EF4444` untuk hapus
3. **Elevation bertingkat** → Header `4dp` → Card `2-4dp` → Overlay `16dp`
4. **Ripple effect pada semua tombol** → `?attr/selectableItemBackgroundBorderless`
5. **Loading overlay premium** → Jangan pakai ProgressDialog default Android
6. **Badge status** → Selalu gunakan drawable `bg_active_badge` / `bg_blocked_badge`, bukan background inline
7. **FAB minimal** → Hanya 1 FAB per screen, warna `#2563EB`, di sudut kanan bawah di atas pagination

---

## 8. Rencana Redesign — Checklist Module

### 8.1 Perbaikan Header (Semua Module)
- [ ] Ganti `Toolbar` menjadi `LinearLayout` dengan pattern header Kalender Operasional
- [ ] Pastikan ada Back button (bukan hamburger menu) karena activity ini bukan root
- [ ] Tambahkan ikon dekoratif di kanan header dengan tint `#818CF8`
- [ ] Tambahkan `elevation="4dp"` pada header

### 8.2 Perbaikan Item Card (Per Module)
- [ ] **Employee** → Sudah bagus, hanya perlu pastikan action icon 36dp + ripple borderless
- [ ] **Master VM** → Audit dan tambahkan stripe indicator jika perlu
- [ ] **Master Variant** → Sudah ada stripe & divider, cek konsistensi warna
- [ ] **Shift** → Dark card sudah OK, cek action button size
- [ ] **Slot** → Audit keseluruhan
- [ ] **Restock** → Audit keseluruhan

### 8.3 Standarisasi Loading
- [ ] Semua module harus punya `overlayLoading` yang sama dengan Kalender Operasional
- [ ] Hapus `ProgressDialog` atau spinner inline jika ada

---

## 9. Referensi File Benchmark

| File | Path |
|------|------|
| Layout Benchmark | `activity_operational_calendar.xml` |
| Fragment Benchmark | `fragment_calendar_month.xml` |
| Java Benchmark | `CalendarOperationalActivity.java` |
| Colors | `res/values/colors.xml` |
| Item Employee | `item_employee.xml` |
| Item Shift | `item_shift.xml` |
| Item Variant | `item_variant_card.xml` |
