# Android Integration Complete Setup

Berikut adalah panduan lengkap cara setup dan running Android app dengan Variant & Restock modules.

---

## 📥 STEP 1: Download/Copy Project

Semua file Android sudah ada di folder: `d:\vending_api\android_integration\`

### Struktur Folder:
```
android_integration/
├── app/src/main/
│   ├── java/com/vending/api/          # Java source code
│   ├── res/layout/                    # XML layouts
│   ├── res/drawable/                  # Drawables
│   ├── res/values/                    # Resources
│   └── AndroidManifest.xml
├── build.gradle
└── settings.gradle
```

---

## 🔧 STEP 2: Open di Android Studio

### Option A: Open Existing Project
```
1. Buka Android Studio
2. File > Open...
3. Navigate ke: d:\vending_api\android_integration
4. Klik OK
```

### Option B: Copy ke Project Android Studio Anda
```
1. Copy folder: android_integration/ 
2. Paste ke: ~/AndroidStudioProjects/
3. Rename folder sesuai project name Anda (contoh: VendingAPI)
4. Buka di Android Studio
```

---

## ⚙️ STEP 3: Update Configuration

### A. Update Base URL

**File:** `app/src/main/java/com/vending/api/network/RetrofitClient.java`

**Cari baris:**
```java
private static final String BASE_URL = "http://127.0.0.1:8000/";
```

**Ubah sesuai backend Anda:**
```java
// Jika backend di local
private static final String BASE_URL = "http://127.0.0.1:8000/";

// Jika backend di network
private static final String BASE_URL = "http://192.168.1.100:8000/";

// Jika backend di server
private static final String BASE_URL = "http://api.example.com/";
```

**IMPORTANT:** Jangan lupa trailing slash di akhir URL!

### B. Check Dependencies

**File:** `app/build.gradle`

Pastikan semua dependencies sudah tercantum (sudah ada di file):
```gradle
dependencies {
    // Retrofit untuk API calls
    implementation 'com.squareup.retrofit2:retrofit:2.10.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.10.0'
    
    // Material Design
    implementation 'com.google.android.material:material:1.9.0'
    
    // Image Loading
    implementation 'com.github.bumptech.glide:glide:4.15.1'
    
    // ... dependencies lainnya
}
```

### C. Check Manifest Permissions

**File:** `app/src/main/AndroidManifest.xml`

Pastikan ada permissions untuk internet:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

---

## 🔄 STEP 4: Sync Gradle

Di Android Studio:
```
1. Buka build.gradle (Module: app)
2. Klik tombol "Sync Now" (kuning di top)
   atau
   File > Sync Project with Gradle Files
3. Tunggu sampai selesai (cek status di bawah)
```

Jika ada error:
```
1. Klik "Build" menu
2. Pilih "Clean Project"
3. Kemudian "Rebuild Project"
4. Tunggu process selesai
```

---

## 📱 STEP 5: Setup Emulator / Device

### Option A: Gunakan Emulator

```
1. Tools > Device Manager
2. Klik "Create Device"
3. Pilih device (misal Pixel 5)
4. Pilih API Level (misal API 34)
5. Klik "Next" > "Finish"
6. Klik "Play" untuk launch emulator
```

### Option B: Gunakan Physical Device

```
1. Connect device via USB
2. Enable Developer Mode:
   - Settings > About > tap Build Number 7x
3. Enable USB Debugging:
   - Settings > Developer Options > USB Debugging = ON
4. Accept fingerprint on device
5. Device will appear di Android Studio
```

---

## ▶️ STEP 6: Run App

### Via Android Studio

```
1. Klik menu: Run > Run 'app'
   atau tekan: Shift + F10
2. Pilih target device/emulator
3. Klik OK
4. Tunggu app running (~1-2 menit first time)
```

### Via Command Line

```bash
# Navigate ke project folder
cd ~/AndroidStudioProjects/android_integration

# Build APK
./gradlew build

# Run on emulator/device
./gradlew installDebug
```

---

## ✅ STEP 7: Verifikasi App Berjalan

Setelah app running:

1. **Main Activity muncul** dengan 2 tabs:
   - "Variants" - untuk manage product variants
   - "Restock" - untuk manage stock per slot

2. **Cek Tab Variants:**
   - Klik "Add New" button
   - Isi form: Nama Varian, Image URL (optional), Status
   - Klik "Save"
   - Variant baru harusnya appear di list

3. **Cek Tab Restock:**
   - Klik "Add Restock" button
   - Isi form: VM ID, Slot Number (A1-D10), Quantity
   - Klik "Save"
   - Restock harusnya appear di list

4. **Test Low Stock Alert:**
   - Di tab Restock, klik "Low Stock Alert"
   - Akan tampil stok dengan qty < 10

---

## 🐛 TROUBLESHOOTING

### Error 1: "Failed to connect to /127.0.0.1:8000"

**Penyebab:** Backend tidak running atau URL tidak benar

**Solusi:**
```
1. Pastikan backend (FastAPI) sudah running:
   python main.py
   
2. Pastikan backend accessible di:
   http://127.0.0.1:8000/docs
   
3. Update URL di RetrofitClient.java jika di network:
   http://192.168.1.XX:8000/
   
4. Rebuild app:
   Build > Rebuild Project
```

### Error 2: "Unsupported Content-Type: text/html"

**Penyebab:** Response bukan JSON (mungkin error page)

**Solusi:**
```
1. Check endpoint di backend:
   curl http://127.0.0.1:8000/api/v1/variant
   
2. Pastikan backend response JSON, bukan HTML error
3. Check logs di backend untuk error message
```

### Error 3: "Cannot resolve symbol 'R'"

**Penyebab:** Gradle belum sync atau ada syntax error di resources

**Solusi:**
```
1. Klik File > Sync Project with Gradle Files
2. Wait for sync complete
3. Build > Clean Project
4. Build > Rebuild Project
```

### Error 4: "Permission denied for android.permission.INTERNET"

**Penyebab:** Permission belum ditambahkan

**Solusi:**
```
Buka AndroidManifest.xml, tambahkan:
<uses-permission android:name="android.permission.INTERNET" />
```

### Error 5: Emulator Connection Refused

**Penyebab:** Backend localhost (127.0.0.1) tidak accessible dari emulator

**Solusi:**
```
1. Ganti base URL di RetrofitClient.java:
   private static final String BASE_URL = "http://10.0.2.2:8000/";
   
   (10.0.2.2 adalah alias untuk host machine dari emulator)
   
2. Atau gunakan IP network:
   private static final String BASE_URL = "http://192.168.1.XXX:8000/";
```

---

## 📁 File Structure untuk Reference

```
android_integration/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── java/com/vending/api/
│   │       │   ├── network/
│   │       │   │   ├── ApiService.java ⭐
│   │       │   │   └── RetrofitClient.java ⭐ (UPDATE BASE_URL DI SINI)
│   │       │   ├── models/
│   │       │   │   ├── VariantResponse.java
│   │       │   │   ├── VariantCreateRequest.java
│   │       │   │   ├── RestockResponse.java
│   │       │   │   └── ... (9 model files lainnya)
│   │       │   ├── adapters/
│   │       │   │   ├── VariantAdapter.java
│   │       │   │   ├── RestockAdapter.java
│   │       │   │   └── ViewPagerAdapter.java
│   │       │   └── ui/
│   │       │       ├── activities/
│   │       │       │   └── MainActivity.java
│   │       │       └── fragments/
│   │       │           ├── VariantListFragment.java ⭐
│   │       │           └── RestockListFragment.java ⭐
│   │       ├── res/
│   │       │   ├── layout/
│   │       │   │   ├── activity_main.xml
│   │       │   │   ├── fragment_variant_list.xml
│   │       │   │   ├── fragment_restock_list.xml
│   │       │   │   ├── item_variant.xml
│   │       │   │   ├── item_restock.xml
│   │       │   │   ├── dialog_variant.xml
│   │       │   │   └── dialog_restock.xml
│   │       │   ├── drawable/
│   │       │   │   └── edittext_background.xml
│   │       │   └── values/
│   │       │       ├── strings.xml
│   │       │       ├── arrays.xml
│   │       │       └── themes.xml
│   │       └── AndroidManifest.xml ⭐ (CHECK PERMISSIONS)
│   └── build.gradle ⭐ (CHECK DEPENDENCIES)
├── build.gradle (project level)
└── settings.gradle
```

⭐ = File penting yang mungkin perlu di-update

---

## 🎯 Quick Checklist

Sebelum run app, pastikan sudah done:

- [ ] Base URL sudah di-update di RetrofitClient.java
- [ ] Backend (FastAPI) sudah running di http://127.0.0.1:8000
- [ ] Gradle sudah sync (tidak ada error)
- [ ] AndroidManifest.xml sudah ada permission INTERNET
- [ ] Emulator/Device sudah ready
- [ ] build.gradle sudah punya semua dependencies

---

## 📞 Quick Test

Setelah app running, test setiap feature:

### Tab Variants:
```
1. ✅ List load (jika ada data)
2. ✅ Add button berfungsi
3. ✅ Dialog form muncul
4. ✅ Save variant baru
5. ✅ Edit variant (klik Edit di item)
6. ✅ Delete variant (klik Delete di item)
7. ✅ List refresh setelah action
```

### Tab Restock:
```
1. ✅ List load (jika ada data)
2. ✅ Add Restock button berfungsi
3. ✅ Dialog form muncul dengan 4 field
4. ✅ Save restock baru
5. ✅ Quick update qty (isi etNewQty + klik Update)
6. ✅ Low Stock Alert button berfungsi
7. ✅ Edit & Delete bekerja
```

---

## 🚀 Siap! Enjoy!

App sudah lengkap dengan:
- ✅ 6 Java Model Classes
- ✅ 2 RecyclerView Adapters
- ✅ 2 Fragments dengan CRUD operation
- ✅ 7 XML Layouts
- ✅ Retrofit API Integration
- ✅ Error Handling dengan Toast
- ✅ Image Loading dengan Glide

Happy Coding! 🎉

Untuk dokumentasi lebih detail, lihat: `ANDROID_SETUP_GUIDE.md`
