# 🖥️ Cross-Check #04a — Master VM (Mesin Vending)

**Status:** 📋 Analisis Selesai — Menunggu Validasi Kamu
**Tanggal Analisis:** 2026-06-30
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul Master VM mencakup CRUD lengkap untuk data mesin vending:
- Lihat semua mesin (list + count)
- Tambah mesin baru (Superadmin only)
- Edit data mesin
- Hapus mesin

> 📝 **Catatan:** Module Employee di-hide dari sidebar (visibility=gone) — data tidak dihapus, bisa diaktifkan kembali kapanpun.

---

## 🔧 API Side (vending_api)

**Base path:** `/api/v1/machine/...`
**File:** `machine_service.py`
**Tabel DB:** `dbo.master_alat_vm`

| # | Endpoint | Method | Deskripsi | Status |
|---|----------|--------|-----------|--------|
| 1 | `/api/v1/machine` | GET | Ambil semua mesin | ✅ Ada |
| 2 | `/api/v1/machine/{id}` | GET | Detail 1 mesin | ✅ Ada |
| 3 | `/api/v1/machine` | POST | Tambah mesin baru | ✅ Ada |
| 4 | `/api/v1/machine/{id}` | PUT | Update data mesin | ✅ Ada |
| 5 | `/api/v1/machine/{id}` | DELETE | Hapus mesin | ✅ Ada |

### Response Fields dari API

```python
{
  "id_recnum_mav": int,
  "nama_vm": str,
  "no_ref": str | null,
  "ip_address": str | null,
  "update_time": str | null,   # ISO format datetime
  "user_input": str | null
}
```

### Response `GET /api/v1/machine` (getAll)

⚠️ **PENTING:** API GET All mengembalikan object wrapper, bukan array langsung:
```json
{
  "total": 5,
  "data": [ {...}, {...} ]
}
```

---

## 📱 Android Side (CapstoneProject)

| Method | Fungsi | Endpoint | Status |
|--------|--------|----------|--------|
| `fetchMachines()` | Load semua mesin | `GET /api/v1/machine` | ⚠️ Lihat catatan |
| `callCreateMachine(body)` | Tambah mesin | `POST /api/v1/machine` | ✅ OK |
| `callUpdateMachine(id, body)` | Edit mesin | `PUT /api/v1/machine/{id}` | ✅ OK |
| `onDelete()` + `deleteMachine(id)` | Hapus mesin | `DELETE /api/v1/machine/{id}` | ✅ OK |

### ⚠️ BUG KRITIS: Response Mismatch di `fetchMachines()`

**Android memanggil:**
```java
RetrofitClient.getApiService().getAllMachines()
// Return type: Call<List<MachineResponse>>  ← mengharapkan array langsung
```

**Tapi API mengembalikan:**
```json
{ "total": 5, "data": [ {...} ] }   // ← object wrapper, BUKAN array
```

Ini akan menyebabkan **Gson parsing gagal** → list mesin tidak tampil / crash.

**Fix yang diperlukan:**
Buat wrapper class baru atau ubah return type di ApiService dan fetchMachines().

---

## 🔍 Temuan Lengkap

| # | Level | Temuan | Rekomendasi |
|---|-------|--------|-------------|
| 1 | ❌ **BUG** | `getAllMachines()` return `List<MachineResponse>` tapi API return `{total, data:[]}` | Buat `MachineListResponse` wrapper atau ubah API return jadi array langsung |
| 2 | ✅ OK | Create, Update, Delete endpoint path sudah sesuai | — |
| 3 | ✅ OK | Model `MachineResponse` field names sudah cocok dengan API (`nama_vm`, `no_ref`, `ip_address`, dll) | — |
| 4 | ✅ OK | FAB Add Machine hanya muncul untuk Superadmin (level 9) | — |
| 5 | ✅ OK | Dialog form punya validasi: nama, no_ref, ip_address wajib diisi | — |
| 6 | ✅ OK | SwipeRefresh berfungsi untuk reload data | — |
| 7 | ✅ OK | Empty state (layout kosong) sudah ada | — |
| 8 | ⚠️ Minor | `user_input` di-set dari `sessionManager.getUsername()` — perlu pastikan field ini tidak null saat login | — |
| 9 | ⚠️ Minor | Tidak ada validasi format IP Address (bebas input string apapun) | Tambahkan regex validasi IP |

---

## 🔧 Fix yang Harus Dilakukan (Sebelum Testing)

### Fix 1 — Buat Wrapper Model `MachineListResponse`

Buat file baru `MachineListResponse.java`:
```java
public class MachineListResponse {
    @SerializedName("total")
    public int total;

    @SerializedName("data")
    public List<MachineResponse> data;
}
```

### Fix 2 — Update `ApiService.java`

```java
// SEBELUM (salah):
@GET("api/v1/machine")
Call<List<MachineResponse>> getAllMachines();

// SESUDAH (benar):
@GET("api/v1/machine")
Call<MachineListResponse> getAllMachines();
```

### Fix 3 — Update `fetchMachines()` di `MachineManagementActivity.java`

```java
RetrofitClient.getApiService().getAllMachines().enqueue(new Callback<MachineListResponse>() {
    @Override
    public void onResponse(..., Response<MachineListResponse> response) {
        if (response.isSuccessful() && response.body() != null) {
            machineList.clear();
            machineList.addAll(response.body().data);   // ← akses .data
            ...
        }
    }
});
```

---

## ✅ Checklist Validasi (Diisi setelah Fix diterapkan + cek di device)

- [ ] Halaman Master VM terbuka tanpa crash
- [ ] List mesin tampil dengan benar
- [ ] Total mesin di header sesuai
- [ ] SwipeRefresh berfungsi
- [ ] Tambah mesin baru berhasil (Superadmin)
- [ ] Edit data mesin berhasil
- [ ] Hapus mesin berhasil + dialog konfirmasi muncul
- [ ] FAB tidak muncul untuk user non-Superadmin

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** 📋 Ada 1 bug kritis yang harus difix dulu sebelum testing
