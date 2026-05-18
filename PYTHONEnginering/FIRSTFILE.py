import pyodbc
import pandas as pd
import warnings

# Matikan warning agar output bersih
warnings.filterwarnings('ignore')

# --- 1. KONFIGURASI KONEKSI (Sesuai kredensial Anda) ---
server = r'ADAM123\SQLEXPRESS' 
database = 'db_vending_machine' 
username = 'sa' 
password = '07Mei2005' 
driver = '{ODBC Driver 17 for SQL Server}' 

connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

print("🚀 MEMULAI PROSES TARIK DATA TRANSAKSI MENTAH...")

try:
    conn = pyodbc.connect(connection_string)
    print("✅ Terhubung ke Database!")

    # --- 2. SQL QUERY SEDERHANA (NO JOIN, NO HEADACHE) ---
    # Kita ambil semua kolom (*) dari tabel transaksi
    # Syaratnya cuma satu: status_transaksi = '1'
    query = """
    SELECT *
    FROM dbo.monitor_log_datatransaksi
    WHERE status_transaksi = '1'
    ORDER BY update_time DESC
    """

    print("⏳ Sedang menarik data (Select *)...")
    
    # Masukkan ke Pandas DataFrame
    df = pd.read_sql(query, conn)
    conn.close()

    print(f"📊 Data berhasil ditarik! Total baris: {len(df)}")

    # --- 3. SIMPAN KE CSV ---
    filename = 'master_dataset_vending.csv'
    df.to_csv(filename, index=False)
    
    print(f"\n🎉 FILE AMAN: {filename}")
    print("   Sekarang Anda punya semua data transaksi di CSV ini.")
    print("   Kita bisa melakukan mapping rasa menggunakan Python nanti (lebih mudah di-debug).")
    
    # Tampilkan kolom apa saja yang kita dapat
    print("\nKolom yang tersedia:")
    print(df.columns.tolist())
    
    print("\nContoh Data:")
    print(df.head())

except Exception as e:
    print(f"\n❌ ERROR: {e}")


import pandas as pd

# 1. Load CSV Master yang baru saja Anda buat
filename = 'master_dataset_vending.csv'
try:
    df = pd.read_csv(filename)
    print(f"✅ Berhasil memuat {len(df)} baris data.")
except FileNotFoundError:
    print("❌ File tidak ditemukan. Pastikan nama filenya benar.")

# 2. Cek Variasi Unik di kolom 'slot_number'
if 'slot_number' in df.columns:
    print("\n🔍 DAFTAR VARIASI SLOT NUMBER (UNIQUE VALUES):")
    unique_slots = df['slot_number'].unique()
    print(unique_slots)
    
    print(f"\n📊 Total ada {len(unique_slots)} jenis penulisan slot berbeda.")

    # 3. Cek Frekuensi (Untuk melihat mana yang aneh/jarang muncul)
    print("\n📈 20 Slot Paling Sering Muncul:")
    print(df['slot_number'].value_counts().head(20))
    
    print("\n📉 20 Slot Paling Jarang Muncul (Potensi Anomali/Typo):")
    print(df['slot_number'].value_counts().tail(20))
    
    # 4. Cek apakah ada Spasi Tersembunyi? (Common Issue)
    # Kadang 'B1' dan 'B1 ' dianggap beda
    sample = df['slot_number'].astype(str).iloc[0]
    print(f"\n🕵️‍♂️ Cek Spasi pada data pertama ('{sample}'):")
    print(f"   Panjang karakter: {len(sample)}")
    if len(sample) != len(sample.strip()):
        print("   ⚠️ WARNING: Terdeteksi spasi di depan/belakang! Perlu dibersihkan (trim).")
    else:
        print("   ✅ Data terlihat bersih dari spasi (setidaknya sampel awal).")

else:
    print("❌ Kolom 'slot_number' tidak ditemukan di CSV.")


import pandas as pd
import pyodbc

# --- 1. SETUP KONEKSI (Hanya untuk ambil tabel referensi VM) ---
# Kita definisikan ulang connection string agar script ini bisa jalan mandiri
server = r'ADAM123\SQLEXPRESS'
database = 'db_vending_machine'
username = 'sa'
password = '07Mei2005'
driver = '{ODBC Driver 17 for SQL Server}'
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

print("🚀 MEMULAI PROSES MAPPING NAMA VM...")

try:
    # A. LOAD CSV MASTER (Data Transaksi yang sudah ditarik sebelumnya)
    print("📂 Membaca file 'master_dataset_vending.csv'...")
    df_transaksi = pd.read_csv('master_dataset_vending.csv')
    print(f"✅ Data Transaksi dimuat: {len(df_transaksi)} baris.")

    # B. TARIK TABEL MASTER VM DARI SQL
    print("📥 Menarik data Master VM dari Database...")
    conn = pyodbc.connect(connection_string)
    
    # Kita hanya butuh ID dan Nama-nya saja
    query_vm = "SELECT id_recnum_mav, nama_vm FROM dbo.master_alat_vm"
    df_vm = pd.read_sql(query_vm, conn)
    conn.close()
    print(f"✅ Master VM dimuat: {len(df_vm)} mesin ditemukan.")

    # C. PROSES MERGE (VLOOKUP ala Python)
    # Menggabungkan df_transaksi dengan df_vm berdasarkan 'id_recnum_mav'
    print("🔄 Menggabungkan kolom 'nama_vm' ke dataset transaksi...")
    
    df_updated = pd.merge(df_transaksi, df_vm, on='id_recnum_mav', how='left')

    # D. REORDERING KOLOM (Opsional - Agar nama_vm ada di samping id_recnum_mav)
    # Kita pindahkan kolom 'nama_vm' supaya posisinya enak dilihat
    cols = df_updated.columns.tolist()
    if 'nama_vm' in cols:
        cols.remove('nama_vm') # Hapus dulu dari posisi belakang
        # Cari indeks id_recnum_mav
        target_index = cols.index('id_recnum_mav') + 1 
        # Masukkan nama_vm tepat setelahnya
        cols.insert(target_index, 'nama_vm')
        df_updated = df_updated[cols]

    # E. SIMPAN KEMBALI (Update CSV)
    output_filename = 'master_dataset_vending_updated.csv'
    df_updated.to_csv(output_filename, index=False)

    print(f"\n🎉 SUKSES! File baru '{output_filename}' telah dibuat.")
    print("   Kolom 'nama_vm' sudah ditambahkan di samping 'id_recnum_mav'.")
    
    # Cek hasilnya
    print("\nContoh 5 Data Teratas (Setelah Update):")
    print(df_updated[['id_recnum_mav', 'nama_vm', 'slot_number']].head())

except Exception as e:
    print(f"\n❌ TERJADI ERROR: {e}")

import pandas as pd
import pyodbc
import warnings

# Matikan warning
warnings.filterwarnings('ignore')

# --- 1. SETUP KONEKSI SQL (Untuk tarik tabel mapping baru) ---
server = r'ADAM123\SQLEXPRESS'
database = 'db_vending_machine'
username = 'sa'
password = '07Mei2005'
driver = '{ODBC Driver 17 for SQL Server}'
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

print("🚀 MEMULAI PROSES STANDARISASI SLOT NUMBER...")

try:
    # A. LOAD CSV YANG SUDAH ADA NAMA VM
    # Pastikan nama filenya sesuai dengan hasil langkah sebelumnya
    input_csv = 'master_dataset_vending_updated.csv' 
    print(f"📂 Membaca file '{input_csv}'...")
    df = pd.read_csv(input_csv)
    
    # Cek kondisi awal
    print("\n🔍 Kondisi Slot Sebelum Perbaikan:")
    print(f"   Total Unique Slots: {df['slot_number'].nunique()}")
    # Tampilkan sampel data yang angka saja
    angka_saja = df[df['slot_number'].astype(str).str.isdigit()]['slot_number'].unique()
    print(f"   Sampel Slot Angka (yang akan diganti): {angka_saja[:10]} ...")

    # B. TARIK TABEL MAPPING DARI SQL
    print("\n📥 Menarik tabel 'manage_map_new_slot'...")
    conn = pyodbc.connect(connection_string)
    
    # Kita ambil ID dan Target Slot-nya (A1, A2, dst)
    query_map = "SELECT id_recnum_newslot, slot_number FROM dbo.manage_map_new_slot"
    df_map_new = pd.read_sql(query_map, conn)
    conn.close()
    
    print(f"✅ Mapping dimuat: {len(df_map_new)} aturan penggantian ditemukan.")

    # C. BUAT KAMUS PENGGANTIAN (DICTIONARY)
    # Logic: id_recnum_newslot (Misal: 3) -> slot_number (Misal: A3)
    # Kita pastikan ID dijadikan string agar cocok dengan data di CSV
    map_dict = dict(zip(df_map_new['id_recnum_newslot'].astype(str), df_map_new['slot_number']))

    # D. EKSEKUSI PENGGANTIAN (CLEANING)
    print("\n🧹 Sedang memperbaiki format slot number...")
    
    # Fungsi kecil untuk cek dan ganti
    def perbaiki_slot(val):
        val_str = str(val).strip() # Ubah ke string dan hapus spasi
        
        # JIKA formatnya ANGKA SAJA (Digit), maka cari di kamus
        if val_str.isdigit():
            # Kembalikan nilai dari map_dict, jika tidak ada biarkan tetap angka
            return map_dict.get(val_str, val_str) 
        
        # JIKA sudah format huruf (A1, B1), biarkan saja
        return val_str

    # Terapkan ke seluruh kolom
    df['slot_number'] = df['slot_number'].apply(perbaiki_slot)

    # E. VALIDASI HASIL
    print("\n✨ Kondisi Slot SETELAH Perbaikan:")
    print(f"   Total Unique Slots: {df['slot_number'].nunique()}")
    
    # Cek apakah masih ada angka tersisa?
    sisa_angka = df[df['slot_number'].astype(str).str.isdigit()]['slot_number'].unique()
    if len(sisa_angka) == 0:
        print("   ✅ CLEAN! Tidak ada lagi slot berupa angka murni.")
    else:
        print(f"   ⚠️ Masih ada sisa angka (mungkin ID-nya tidak ada di tabel mapping): {sisa_angka}")

    # F. SIMPAN FILE FINAL SEMENTARA
    output_filename = 'master_dataset_vending_fixed_slots.csv'
    df.to_csv(output_filename, index=False)
    
    print(f"\n🎉 SUKSES! File tersimpan sebagai: {output_filename}")
    print("   Sekarang kolom 'slot_number' sudah seragam formatnya (A1, B1, dst).")
    print(df[['nama_vm', 'slot_number']].head())

except Exception as e:
    print(f"\n❌ TERJADI ERROR: {e}")


import pandas as pd
import pyodbc
import warnings

warnings.filterwarnings('ignore')

# --- 1. SETUP KONEKSI ---
server = r'ADAM123\SQLEXPRESS'
database = 'db_vending_machine'
username = 'sa'
password = '07Mei2005'
driver = '{ODBC Driver 17 for SQL Server}'
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

print("🚀 MEMULAI PROSES MAPPING RASA (FINAL LOGIC)...")

try:
    # A. LOAD CSV (Hasil Fix Slot Number)
    input_csv = 'master_dataset_vending_fixed_slots.csv'
    print(f"📂 Membaca file '{input_csv}'...")
    df = pd.read_csv(input_csv)
    
    # B. TARIK TABEL REFERENSI DARI SQL
    print("📥 Menarik tabel Mapping & Variant dari Database...")
    conn = pyodbc.connect(connection_string)
    
    # 1. Tabel Mapping Slot (Isinya: ID VM, Slot Name 'A'/'B', ID Variant)
    query_map = "SELECT id_recnum_mav, slot_name, id_recnum_variant FROM dbo.manage_map_slot_number"
    df_map = pd.read_sql(query_map, conn)
    
    # 2. Tabel Master Variant (Isinya: ID Variant, Nama Variant)
    query_var = "SELECT id_recnum_variant, nama_variant FROM dbo.master_variant"
    df_var = pd.read_sql(query_var, conn)
    
    conn.close()
    print(f"✅ Referensi dimuat. Siap melakukan mapping.")

    # C. IMPLEMENTASI LOGIKA ANDA (EKSTRAK HURUF DEPAN)
    print("\n🛠️ Menerapkan Logic: Ambil huruf depan slot (A1 -> A)...")
    
    # Kita buat kolom bantuan sementara 'slot_base'
    # Logika: Ambil karakter pertama dari string slot_number
    # A1 -> A, B10 -> B
    df['slot_base'] = df['slot_number'].astype(str).str[0]
    
    # Pastikan slot_name di DB juga string dan bersih
    df_map['slot_name'] = df_map['slot_name'].astype(str).str.strip()

    # D. MAPPING TAHAP 1: DAPATKAN ID VARIANT
    # Join berdasarkan: ID VM dan Slot Base (Hurufnya saja)
    print("🔄 Mapping Tahap 1: Mencari ID Variant...")
    
    df_step1 = pd.merge(
        df, 
        df_map, 
        left_on=['id_recnum_mav', 'slot_base'], # Kunci dari CSV
        right_on=['id_recnum_mav', 'slot_name'], # Kunci dari DB
        how='left'
    )

    # E. MAPPING TAHAP 2: DAPATKAN NAMA RASA
    # Join berdasarkan: id_recnum_variant
    print("🔄 Mapping Tahap 2: Mencari Nama Rasa...")
    
    df_final = pd.merge(
        df_step1,
        df_var,
        on='id_recnum_variant',
        how='left'
    )

    # F. BERSIH-BERSIH KOLOM
    # Kita hapus kolom bantuan yang tidak perlu masuk CSV Final
    # (slot_base, slot_name dari db, id_recnum_variant kalau tidak mau ditampilkan)
    # Tapi sesuai request, id_recnum_variant dimasukkan setelah update_time
    
    # Kita atur urutan kolom agar rapi
    cols = df_final.columns.tolist()
    keep_cols = [
        'Waktu_Transaksi', 'id_recnum_mav', 'nama_vm', 'slot_number', 
        'id_recnum_variant', 'nama_variant', 'qty', 'status_transaksi', 'Info_Shift'
    ]
    
    # Filter hanya kolom yang ada (jaga-jaga jika nama kolom beda dikit)
    final_cols = [c for c in keep_cols if c in cols]
    
    # Tambahkan sisa kolom lain jika ada yang terlewat
    remaining = [c for c in cols if c not in final_cols and c not in ['slot_base', 'slot_name']]
    final_cols.extend(remaining)
    
    df_final = df_final[final_cols]

    # G. VALIDASI HASIL
    sukses = df_final['nama_variant'].notnull().sum()
    gagal = df_final['nama_variant'].isnull().sum()
    
    print(f"\n📊 HASIL AKHIR:")
    print(f"   ✅ Berhasil Mapping Rasa : {sukses} baris")
    print(f"   ❌ Gagal Mapping Rasa    : {gagal} baris")
    
    if gagal > 0:
        print("\n   ⚠️ CONTOH YANG MASIH GAGAL (Cek apakah mapping di DB lengkap?):")
        print(df_final[df_final['nama_variant'].isnull()][['nama_vm', 'slot_number']].head())

    # H. SIMPAN CSV FINAL
    output_filename = 'master_dataset_vending_FINAL_FULL.csv'
    df_final.to_csv(output_filename, index=False)
    
    print(f"\n🎉 SELESAI! File Final: {output_filename}")
    print(df_final[['nama_vm', 'slot_number', 'nama_variant']].head(10))

except Exception as e:
    print(f"\n❌ TERJADI ERROR: {e}")


import pandas as pd

# 1. LOAD DATA
file_path = 'master_dataset_vending_FINAL_FULL.csv'
df = pd.read_csv(file_path)

print(f"Jumlah data awal: {len(df)} baris")

# --- EKSEKUSI POIN 1: Hapus Proses Restock ---
# Kita hanya mengambil data yang keterangan-nya BUKAN 'Proses Restock Qty Oleh Admin'
df = df[df['keterangan'] != 'Proses Restock Qty Oleh Admin'].reset_index(drop=True)
print(f"Jumlah data setelah menghapus Restock Admin: {len(df)} baris")

# --- EKSEKUSI POIN 5: Hapus kolom detail_keterangan ---
if 'detail_keterangan' in df.columns:
    df.drop(columns=['detail_keterangan'], inplace=True)
    print("Kolom 'detail_keterangan' berhasil dihapus.")

# --- EKSEKUSI POIN 4: Reorder Kolom (id_recnum_mld di awal) ---
# Mengambil daftar kolom yang ada
cols = df.columns.tolist()

# Memastikan id_recnum_mld dipindah ke posisi indeks 0
if 'id_recnum_mld' in cols:
    cols.insert(0, cols.pop(cols.index('id_recnum_mld')))
    df = df[cols]
    print("Kolom 'id_recnum_mld' sekarang berada di posisi pertama.")

# --- FINALISASI & VERIFIKASI ---
print("\n=== VERIFIKASI HASIL AKHIR ===")
print(df.head())

# Cek apakah 'Proses Restock Qty Oleh Admin' masih ada
restock_check = df[df['keterangan'] == 'Proses Restock Qty Oleh Admin']
print(f"\nSisa data Restock Admin: {len(restock_check)}")

# Simpan hasil pembersihan ini untuk tahap berikutnya
output_cleaned = 'master_dataset_vending_CLEANED_P1.csv'
df.to_csv(output_cleaned, index=False)
print(f"\n🎉 File bersih tahap 1 disimpan sebagai: {output_cleaned}")

import pandas as pd

# Load data yang sudah dibersihkan tahap 1
df = pd.read_csv('master_dataset_vending_CLEANED_P1.csv')
df['update_time'] = pd.to_datetime(df['update_time'])
df['tanggal'] = df['update_time'].dt.date # Buat kolom tanggal saja untuk cek hari kosong

print("=== 1. ANALISIS DISTRIBUSI QTY ===")
# Melihat frekuensi nilai Qty yang muncul
qty_counts = df['qty'].value_counts().sort_index()
print("\nFrekuensi Pengambilan (Qty):")
print(qty_counts)

# Analisis Anomali Qty
print("\n--- Detail Anomali ---")
print(f"Jumlah transaksi dengan Qty = 0 : {len(df[df['qty'] == 0])} baris")
print(f"Jumlah transaksi dengan Qty > 10: {len(df[df['qty'] > 10])} baris")

print("\n" + "="*40 + "\n")

print("=== 2. ANALISIS HARI KOSONG (ZERO TRANSACTION DAYS) ===")
# Membuat range tanggal lengkap dari awal sampai akhir data
date_range = pd.date_range(start=df['tanggal'].min(), end=df['tanggal'].max())

# Mencari tanggal yang tidak ada di dataset
hari_ada_transaksi = df['tanggal'].unique()
hari_kosong = [d.date() for d in date_range if d.date() not in hari_ada_transaksi]

print(f"Total rentang waktu: {len(date_range)} hari")
print(f"Jumlah hari tanpa transaksi: {len(hari_kosong)} hari")

if len(hari_kosong) > 0:
    print("\nList Hari Kosong (Contoh 10 pertama):")
    for day in hari_kosong[:10]:
        print(f"- {day}")
else:
    print("Hebat! Tidak ada hari yang kosong sama sekali.")

import pandas as pd
import numpy as np

# 1. LOAD DATA
df = pd.read_csv('master_dataset_vending_CLEANED_P1.csv')
df['update_time'] = pd.to_datetime(df['update_time'])
df['tanggal'] = df['update_time'].dt.date

# 2. AGREGASI HARIAN (Group by Tanggal, Shift, dan Rasa)
# Kita hitung jumlah baris sebagai 'demand' (karena qty selalu 1)
df_daily = df.groupby(['tanggal', 'keterangan', 'nama_variant']).size().reset_index(name='demand')

# 3. MEMBUAT KERANGKA WAKTU LENGKAP (Agar tidak ada hari bolong)
all_dates = pd.date_range(start=df['tanggal'].min(), end=df['tanggal'].max()).date
all_shifts = df['keterangan'].unique()
all_variants = df['nama_variant'].unique()

# Membuat index kombinasi semua Tanggal x Semua Shift x Semua Rasa
multi_index = pd.MultiIndex.from_product(
    [all_dates, all_shifts, all_variants], 
    names=['tanggal', 'keterangan', 'nama_variant']
)
df_template = pd.DataFrame(index=multi_index).reset_index()

# 4. MENGGABUNGKAN DATA ASLI KE TEMPLATE
df_final = pd.merge(df_template, df_daily, on=['tanggal', 'keterangan', 'nama_variant'], how='left')

# 5. MENGISI HARI KOSONG DENGAN 0
df_final['demand'] = df_final['demand'].fillna(0).astype(int)

# 6. MENAMBAHKAN FITUR HOLIDAY (Bukti Pentingnya Fitur ini)
# Jika tanggal tersebut ada di list 106 hari kosong (tidak ada transaksi di data asli), tandai sebagai libur
hari_ada_transaksi = set(df['tanggal'].unique())
df_final['is_holiday'] = df_final['tanggal'].apply(lambda x: 1 if x not in hari_ada_transaksi else 0)

print(f"Jumlah baris setelah agregasi lengkap: {len(df_final)}")
print(df_final.head(10))

# Simpan untuk tahap Feature Engineering berikutnya
df_final.to_csv('vending_daily_aggregated.csv', index=False)

