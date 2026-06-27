# 🤖 Cross-Check #05b — Dashboard: Prediction (DSS)

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Dashboard prediksi berbasis machine learning (Decision Support System):
1. **Lihat Hasil Prediksi** — Prediksi penjualan per varian per mesin
2. **Retrain Model** — Trigger ulang training model ML (Superadmin)
3. **Lihat Log Retrain** — Riwayat training model
4. **Rekomendasi** — Saran pengisian stok berdasarkan prediksi

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| *(belum dikonfirmasi)* | GET | Ambil hasil prediksi | ⬜ |
| *(belum dikonfirmasi)* | POST | Trigger retrain model | ⬜ |
| *(belum dikonfirmasi)* | GET | Log riwayat retrain | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Class | Fungsi | Terhubung API? | Status |
|----------------|--------|----------------|--------|
| `PredictionDashboardActivity.java` | Dashboard prediksi utama | ⬜ | ⬜ |
| `PredictionViewModel.java` | ViewModel data prediksi | ⬜ | ⬜ |
| `PredictionRepository.java` | Repository panggil API | ⬜ | ⬜ |
| `RetrainLogsActivity.java` | Riwayat log retrain | ⬜ | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Dashboard prediksi loading tanpa error
- [ ] Hasil prediksi per varian tampil
- [ ] Rekomendasi stok tampil
- [ ] Tombol "Retrain" muncul untuk Superadmin
- [ ] Setelah retrain, ada feedback (loading/success)
- [ ] Log retrain (`RetrainLogsActivity`) bisa dibuka
- [ ] Data prediksi relevan dengan data aktual

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
