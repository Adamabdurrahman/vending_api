from fastapi.testclient import TestClient
from main import app
from sqlalchemy import text
from database import engine

client = TestClient(app)

print("\n=============================================")
print("TESTING LOGIN: USERNAME OR EMAIL SUPPORT")
print("=============================================\n")

def main():
    # 1. Get primary user details directly from database
    with engine.connect() as conn:
        user_row = conn.execute(
            text("SELECT UserName, Password, email_primary FROM dbo.master_user WHERE id_recnum_mur = 1")
        ).fetchone()
        
    if not user_row:
        print("ERROR: Test user with id_recnum_mur = 1 not found in database.")
        return
        
    username, password, email = user_row[0], user_row[1], user_row[2]
    print(f"Database User Details: UserName='{username}', email_primary='{email}', Password='{password}'\n")
    
    # 2. Test Login using UserName
    print("1. Testing login using UserName...")
    payload_username = {"username": username, "password": password}
    response_un = client.post("/login", json=payload_username)
    print(f"Status Code: {response_un.status_code}")
    print("Response JSON:")
    print(response_un.json())
    assert response_un.status_code == 200
    assert response_un.json()["username"] == username
    print("Login using UserName successful [OK].\n")
    
    # 3. Test Login using Email
    print("2. Testing login using Primary Email...")
    payload_email = {"username": email, "password": password}
    response_em = client.post("/login", json=payload_email)
    print(f"Status Code: {response_em.status_code}")
    print("Response JSON:")
    print(response_em.json())
    assert response_em.status_code == 200
    assert response_em.json()["username"] == username
    assert response_em.json()["email_primary"] == email
    print("Login using Primary Email successful [OK].\n")
    
    # 4. Test Login with wrong password
    print("3. Testing login with wrong password...")
    payload_wrong_pw = {"username": username, "password": "wrong_password_123"}
    response_wpw = client.post("/login", json=payload_wrong_pw)
    print(f"Status Code: {response_wpw.status_code}")
    print("Response JSON:")
    print(response_wpw.json())
    assert response_wpw.status_code == 401
    assert response_wpw.json()["detail"] == "Password salah"
    print("Wrong password check successful [OK].\n")

    # 5. Test Login with non-existent username
    print("4. Testing login with non-existent username/email...")
    payload_non_existent = {"username": "non_existent_user_abc_123", "password": password}
    response_ne = client.post("/login", json=payload_non_existent)
    print(f"Status Code: {response_ne.status_code}")
    print("Response JSON:")
    print(response_ne.json())
    assert response_ne.status_code == 404
    assert response_ne.json()["detail"] == "Username tidak ditemukan"
    print("Non-existent user check successful [OK].\n")
    
    print("ALL LOGIN TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
