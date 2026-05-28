from fastapi.testclient import TestClient
from main import app
import pprint

client = TestClient(app)

print("\n=============================================")
print("TESTING ENDPOINTS: USER AUTHENTICATION & FLOW")
print("=============================================\n")

# Hapus data test jika sudah ada sebelumnya di DB agar tes berjalan lancar
# Untuk mempermudah, kita akan menggunakan ID unik tiap run
import time
unique_suffix = int(time.time())
test_user_id = f"test_id_{unique_suffix}"
test_username = f"test_user_{unique_suffix}"
test_email = f"test_{unique_suffix}@gmail.com"
test_password = "password123"
new_password = "newpassword456"

# 1. Registrasi Akun Baru
print("1. Testing POST /api/v1/auth/register...")
register_data = {
    "id": test_user_id,
    "username": test_username,
    "password": test_password,
    "level_user": 1,
    "email_primary": test_email,
    "nohp": "081234567890"
}
response = client.post("/api/v1/auth/register", json=register_data)
print(f"Status Code: {response.status_code}")
pprint.pprint(response.json())
assert response.status_code == 201
assert response.json()["status"] == "pending"

# 2. Coba login sebelum disetujui (Harus ditolak 403)
print("\n2. Testing POST /login (Sebelum Disetujui)...")
login_data = {
    "username": test_username,
    "password": test_password
}
response = client.post("/login", json=login_data)
print(f"Status Code: {response.status_code}")
print(response.json())
assert response.status_code == 403
assert "pending persetujuan" in response.json()["detail"]

# 3. Superadmin melihat daftar pending users
print("\n3. Testing GET /api/v1/admin/pending-users...")
response = client.get("/api/v1/admin/pending-users")
print(f"Status Code: {response.status_code}")
pending_list = response.json()
print(f"Total user pending: {len(pending_list)}")
# Pastikan user kita ada dalam list
found = False
for u in pending_list:
    if u["Id"] == test_user_id:
        found = True
        break
assert found, "User baru tidak ditemukan di antrean pending"

# 4. Superadmin menyetujui akun baru (Trigger OTP)
print("\n4. Testing POST /api/v1/admin/approve-user...")
approve_data = {
    "target_user_id": test_user_id,
    "admin_id": "superadmin_01"
}
response = client.post("/api/v1/admin/approve-user", json=approve_data)
print(f"Status Code: {response.status_code}")
approve_resp = response.json()
pprint.pprint(approve_resp)
assert response.status_code == 200
otp = approve_resp["otp_test_debug"]
print(f"OTP terdeteksi untuk aktivasi: {otp}")

# 5. Coba login setelah disetujui tapi sebelum memasukkan OTP (Harus ditolak 403)
print("\n5. Testing POST /login (Sebelum Memasukkan OTP)...")
response = client.post("/login", json=login_data)
print(f"Status Code: {response.status_code}")
print(response.json())
assert response.status_code == 403
assert "verifikasi token email" in response.json()["detail"]

# 6. Verifikasi Token OTP Aktivasi Akun
print("\n6. Testing POST /api/v1/auth/verify-token...")
verify_data = {
    "user_id": test_user_id,
    "token": otp
}
response = client.post("/api/v1/auth/verify-token", json=verify_data)
print(f"Status Code: {response.status_code}")
pprint.pprint(response.json())
assert response.status_code == 200
assert response.json()["status"] == "active"

# 7. Coba login setelah aktif (Harus Berhasil 200)
print("\n7. Testing POST /login (Setelah Aktif)...")
response = client.post("/login", json=login_data)
print(f"Status Code: {response.status_code}")
pprint.pprint(response.json())
assert response.status_code == 200
assert response.json()["status_active"] == "1"

# 8. Minta Reset Password (OTP dikirim ke email)
print("\n8. Testing POST /api/v1/auth/reset-password/request...")
reset_req_data = {
    "username": test_username,
    "email": test_email
}
response = client.post("/api/v1/auth/reset-password/request", json=reset_req_data)
print(f"Status Code: {response.status_code}")
reset_req_resp = response.json()
pprint.pprint(reset_req_resp)
assert response.status_code == 200
reset_otp = reset_req_resp["otp_test_debug"]
print(f"OTP terdeteksi untuk reset password: {reset_otp}")

# 9. Konfirmasi OTP & Perbarui Password
print("\n9. Testing POST /api/v1/auth/reset-password/confirm...")
reset_confirm_data = {
    "user_id": test_user_id,
    "token": reset_otp,
    "new_password": new_password
}
response = client.post("/api/v1/auth/reset-password/confirm", json=reset_confirm_data)
print(f"Status Code: {response.status_code}")
pprint.pprint(response.json())
assert response.status_code == 200

# 10. Login dengan password baru (Harus Berhasil)
print("\n10. Testing POST /login (Dengan Password Baru)...")
login_new_data = {
    "username": test_username,
    "password": new_password
}
response = client.post("/login", json=login_new_data)
print(f"Status Code: {response.status_code}")
pprint.pprint(response.json())
assert response.status_code == 200
assert response.json()["status_active"] == "1"

print("\n=============================================")
print("CONGRATULATIONS: ALL ENDPOINTS TESTED SUCCESSFULLY!")
print("=============================================\n")
