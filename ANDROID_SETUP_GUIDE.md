# Android Integration - Setup Guide

Panduan lengkap untuk setup dan menjalankan Android app yang terintegrasi dengan API Vending Machine.

---

## 📁 Struktur Project Android

```
app/src/main/
├── java/com/vending/api/
│   ├── network/
│   │   ├── ApiService.java         # Retrofit API interface
│   │   └── RetrofitClient.java     # Retrofit client configuration
│   ├── models/
│   │   ├── VariantResponse.java
│   │   ├── VariantCreateRequest.java
│   │   ├── VariantUpdateRequest.java
│   │   ├── VariantListResponse.java
│   │   ├── RestockResponse.java
│   │   ├── RestockCreateRequest.java
│   │   ├── RestockUpdateRequest.java
│   │   ├── RestockListResponse.java
│   │   ├── RestockByVMResponse.java
│   │   ├── LowStockAlertResponse.java
│   │   └── ApiMessage.java
│   ├── adapters/
│   │   ├── VariantAdapter.java     # RecyclerView adapter untuk Variant
│   │   ├── RestockAdapter.java     # RecyclerView adapter untuk Restock
│   │   └── ViewPagerAdapter.java   # ViewPager2 adapter
│   └── ui/
│       ├── activities/
│       │   └── MainActivity.java    # Main Activity dengan TabLayout
│       └── fragments/
│           ├── VariantListFragment.java   # List & CRUD Variant
│           └── RestockListFragment.java   # List & CRUD Restock
├── res/
│   ├── layout/
│   │   ├── activity_main.xml
│   │   ├── fragment_variant_list.xml
│   │   ├── fragment_restock_list.xml
│   │   ├── item_variant.xml
│   │   ├── item_restock.xml
│   │   ├── dialog_variant.xml
│   │   └── dialog_restock.xml
│   ├── drawable/
│   │   └── edittext_background.xml
│   ├── values/
│   │   ├── strings.xml
│   │   ├── arrays.xml
│   │   └── themes.xml
│   └── AndroidManifest.xml
└── build.gradle
```

---

## ⚙️ Setup Langkah-Langkah

### 1. **Clone/Copy Project ke Android Studio**

```bash
# Copy folder android_integration ke project Android Studio Anda
cp -r android_integration ~/AndroidStudioProjects/VendingAPI
```

### 2. **Update Base URL di RetrofitClient.java**

Buka file: `app/src/main/java/com/vending/api/network/RetrofitClient.java`

Ubah base URL sesuai IP backend Anda:

```java
private static final String BASE_URL = "http://YOUR_IP:8000/";
```

**Contoh:**
- Local: `http://127.0.0.1:8000/`
- Network: `http://192.168.1.100:8000/`

### 3. **Sync Gradle**

Di Android Studio:
1. Buka `build.gradle` (Module: app)
2. Klik "Sync Now" (atau File > Sync Project with Gradle Files)

### 4. **Pastikan Permissions di AndroidManifest.xml**

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

### 5. **Run App**

```
1. Hubungkan device Android atau buka emulator
2. Klik Run > Run 'app' (atau tekan Shift+F10)
3. Pilih device target
```

---

## 📦 Dependencies yang Digunakan

### build.gradle (Module: app)

```gradle
dependencies {
    // AndroidX
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    implementation 'androidx.recyclerview:recyclerview:1.3.1'
    implementation 'androidx.fragment:fragment:1.6.1'
    implementation 'androidx.viewpager2:viewpager2:1.0.0'
    
    // Material Design
    implementation 'com.google.android.material:material:1.9.0'
    
    // Retrofit
    implementation 'com.squareup.retrofit2:retrofit:2.10.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.10.0'
    
    // Gson
    implementation 'com.google.code.gson:gson:2.10.1'
    
    // Glide for image loading
    implementation 'com.github.bumptech.glide:glide:4.15.1'
    annotationProcessor 'com.github.bumptech.glide:compiler:4.15.1'
    
    // OkHttp
    implementation 'com.squareup.okhttp3:okhttp:4.11.0'
    
    // Logging
    implementation 'com.squareup.okhttp3:logging-interceptor:4.11.0'
}
```

---

## 🎯 Fitur & Navigasi

### Tab 1: Variants (Product Management)

**Fitur:**
- ✅ List semua varian produk
- ✅ Add varian baru (modal dialog)
- ✅ Edit varian (ubah nama, image, status)
- ✅ Delete varian
- ✅ Filter by status (active/inactive)

**Cara Pakai:**
1. Buka tab "Variants"
2. Klik "Add New" untuk menambah varian
3. Isi form (Nama Varian, Image URL, Status)
4. Klik "Save"
5. Swipe item untuk Edit/Delete

### Tab 2: Restock (Stock Management)

**Fitur:**
- ✅ List semua restock per slot
- ✅ Add restock baru (VM ID, Slot, Qty)
- ✅ Edit restock
- ✅ Delete restock
- ✅ Quick update qty (tanpa modal)
- ✅ Low stock alerts (< 10 units)

**Cara Pakai:**
1. Buka tab "Restock"
2. Klik "Add Restock" untuk menambah stok
3. Isi form (VM ID, Slot Number, Quantity)
4. Klik "Save"
5. Update qty langsung di list item dengan "New Qty" field
6. Klik "Low Stock Alert" untuk melihat stok rendah

---

## 🔧 Struktur Code

### RetrofitClient.java - Konfigurasi API

```java
public class RetrofitClient {
    private static Retrofit retrofit;
    private static final String BASE_URL = "http://127.0.0.1:8000/";
    
    public static ApiService getApiService() {
        return getRetrofitInstance().create(ApiService.class);
    }
}
```

**Cara Pakai:**
```java
ApiService apiService = RetrofitClient.getApiService();
apiService.getAllVariants(null).enqueue(callback);
```

### ApiService.java - API Interface

```java
public interface ApiService {
    @GET("api/v1/variant")
    Call<VariantListResponse> getAllVariants(@Query("status") Integer status);
    
    @POST("api/v1/variant")
    Call<VariantResponse> createVariant(@Body VariantCreateRequest request);
    
    @GET("api/v1/restock/vm/{vm_id}")
    Call<RestockByVMResponse> getRestockByVM(@Path("vm_id") int vmId);
    
    // ... dan endpoint lainnya
}
```

### VariantListFragment.java - Fragment untuk List Variant

```java
public class VariantListFragment extends Fragment 
        implements VariantAdapter.OnVariantClickListener {
    
    private void loadVariants() {
        apiService.getAllVariants(null).enqueue(new Callback<VariantListResponse>() {
            @Override
            public void onResponse(Call<VariantListResponse> call, 
                                   Response<VariantListResponse> response) {
                // Handle success
                variantList.clear();
                variantList.addAll(response.body().getData());
                adapter.notifyDataSetChanged();
            }
            
            @Override
            public void onFailure(Call<VariantListResponse> call, Throwable t) {
                // Handle error
                Toast.makeText(getContext(), "Error: " + t.getMessage(), 
                               Toast.LENGTH_SHORT).show();
            }
        });
    }
}
```

---

## 🎨 UI Components

### VariantAdapter - RecyclerView Adapter

```java
public class VariantAdapter extends RecyclerView.Adapter<VariantAdapter.ViewHolder> {
    private List<VariantResponse> variantList;
    private OnVariantClickListener listener;
    
    @Override
    public void onBindViewHolder(ViewHolder holder, int position) {
        VariantResponse variant = variantList.get(position);
        holder.tvVariantName.setText(variant.getNamaVariant());
        holder.tvStatus.setText(variant.getStatusLabel());
        
        // Load image with Glide
        Glide.with(context)
             .load(variant.getImageUrl())
             .placeholder(R.drawable.ic_placeholder)
             .into(holder.ivVariantImage);
    }
}
```

### RestockAdapter - RecyclerView Adapter untuk Restock

```java
public class RestockAdapter extends RecyclerView.Adapter<RestockAdapter.ViewHolder> {
    private List<RestockResponse> restockList;
    
    @Override
    public void onBindViewHolder(ViewHolder holder, int position) {
        RestockResponse restock = restockList.get(position);
        holder.tvSlotNumber.setText("Slot: " + restock.getSlotNumber());
        holder.tvStokQty.setText("Stok: " + restock.getStokQty());
        
        // Warning untuk stok rendah
        if (restock.getStokQty() < 10) {
            holder.tvStokQty.setTextColor(Color.RED);
        }
    }
}
```

---

## 🔄 API Calls

### Variant Endpoints

**GET All Variants:**
```java
apiService.getAllVariants(null).enqueue(callback);
apiService.getAllVariants(1).enqueue(callback);  // Filter active
```

**Create Variant:**
```java
VariantCreateRequest req = new VariantCreateRequest("Coklat", "url", 1);
apiService.createVariant(req).enqueue(callback);
```

**Update Variant:**
```java
VariantUpdateRequest req = new VariantUpdateRequest("Coklat Baru", null, 1);
apiService.updateVariant(variantId, req).enqueue(callback);
```

**Delete Variant:**
```java
apiService.deleteVariant(variantId).enqueue(callback);
```

### Restock Endpoints

**GET All Restocks:**
```java
apiService.getAllRestocks(null).enqueue(callback);
```

**GET Restock by VM:**
```java
apiService.getRestockByVM(vmId).enqueue(callback);
```

**Create Restock:**
```java
RestockCreateRequest req = new RestockCreateRequest(1, 50, "A1");
apiService.createRestock(req).enqueue(callback);
```

**Update Stock Qty (Quick):**
```java
apiService.updateStockQty(vmId, "A1", newQty, "mobile").enqueue(callback);
```

**Low Stock Alerts:**
```java
apiService.getLowStockAlerts(10).enqueue(callback);  // threshold: 10
```

---

## 🚨 Error Handling

### Common Issues

**1. Connection Refused**
```
Error: java.net.ConnectException: Failed to connect
```
**Solusi:** 
- Pastikan backend running di `http://127.0.0.1:8000`
- Update base URL di RetrofitClient.java dengan IP yang benar
- Pastikan firewall tidak block port 8000

**2. Invalid URL**
```
Error: java.lang.IllegalArgumentException: Invalid URL
```
**Solusi:** Pastikan format URL benar: `http://IP:PORT/` (dengan trailing slash)

**3. JSON Parse Error**
```
Error: com.google.gson.JsonSyntaxException
```
**Solusi:** Pastikan API response format sesuai dengan model class

**4. Permission Denied**
```
Error: java.net.SocketPermission
```
**Solusi:** Tambahkan permission di AndroidManifest.xml:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

---

## 🧪 Testing

### Test dengan Mock Data

Buat `MockApiService` untuk testing tanpa backend:

```java
public class MockApiService implements ApiService {
    @Override
    public Call<VariantListResponse> getAllVariants(Integer status) {
        List<VariantResponse> data = new ArrayList<>();
        data.add(new VariantResponse(1, "Coklat", null, 1));
        data.add(new VariantResponse(2, "Strawberry", null, 1));
        
        VariantListResponse response = new VariantListResponse(2, data);
        return new Call<VariantListResponse>() {
            // Implement mock call
        };
    }
}
```

---

## 📝 Notes

1. **Image Handling**: Menggunakan Glide untuk loading image dari URL
2. **Form Validation**: Validasi dilakukan di Fragment sebelum send ke API
3. **Error Toast**: Semua error ditampilkan dengan Toast message
4. **Threading**: Retrofit callback otomatis handle di main thread

---

## 🎓 Learning Resources

- [Retrofit Documentation](https://square.github.io/retrofit/)
- [Android Fragments](https://developer.android.com/guide/fragments)
- [RecyclerView Guide](https://developer.android.com/guide/topics/ui/layout/recyclerview)
- [Material Design Components](https://material.io/components)

---

## 📞 Support

Jika ada error atau issue:
1. Cek logcat di Android Studio (View > Tool Windows > Logcat)
2. Pastikan backend API running dan accessible
3. Verify base URL di RetrofitClient
4. Check permissions di AndroidManifest

Enjoy! 🚀
