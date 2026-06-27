import datetime
import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
import models
import schemas

load_dotenv()

EMAIL_LOG_PATH = "email_log.txt"

# ============================================================
# KONFIGURASI GMAIL SMTP UTK KIRIM EMAIL ASLI
# ============================================================
# Baca dari file .env — salin .env.example ke .env dan isi.
# Sandi yang digunakan adalah "Sandi Aplikasi" 16-Digit dari Google.
SENDER_EMAIL = os.getenv("EMAIL_SENDER", "")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def log_mock_email(to_email: str, subject: str, body: str):
    """
    Simulates sending an email by writing it to email_log.txt 
    and printing it to standard output.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
============================================================
DATE: {timestamp}
TO: {to_email}
SUBJECT: {subject}
------------------------------------------------------------
{body}
============================================================
"""
    # Write to file with explicit UTF-8 encoding
    with open(EMAIL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # Print to console safely, replacing non-ASCII characters to avoid Windows encoding crashes
    print(log_entry.encode('ascii', 'replace').decode('ascii'))


def send_email(to_email: str, subject: str, body: str):
    """
    Sends a real email using Gmail SMTP if configured, 
    otherwise falls back gracefully to log_mock_email.
    """
    is_placeholder = (
        SENDER_EMAIL == "your.capstone.email@gmail.com" or 
        SENDER_PASSWORD == "your-16-character-app-password" or
        not SENDER_EMAIL.strip() or 
        not SENDER_PASSWORD.strip()
    )

    if is_placeholder:
        print("\n[NOTICE] SMTP credentials are not configured. Falling back to Mock Email Log.")
        log_mock_email(to_email, subject, body)
        return

    try:
        print(f"\n[SMTP] Attempting to send real email to: {to_email}...")
        
        # Setup MIME email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Connect & login to Gmail SMTP Server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure connection with TLS
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Send
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        
        print(f"[SMTP] Email sent successfully to {to_email}!")
    except Exception as e:
        print(f"\n[SMTP ERROR] Failed to send real email: {e}")
        print("[SMTP FALLBACK] Gracefully falling back to Mock Email Log.")
        log_mock_email(to_email, subject, body)




def register_user(db: Session, req: schemas.RegisterRequest):
    # Cek apakah username sudah terpakai
    existing_user = db.query(models.User).filter(models.User.UserName == req.username).first()
    if existing_user:
        raise ValueError("Username sudah terpakai")
    
    # Cek apakah email sudah terpakai
    existing_email = db.query(models.User).filter(models.User.email_primary == req.email_primary).first()
    if existing_email:
        raise ValueError("Email sudah terdaftar")

    # Generate id_recnum_mur if not automatically incremented
    max_id = db.execute(text("SELECT ISNULL(MAX(id_recnum_mur), 0) FROM dbo.master_user")).scalar()
    new_id_recnum = max_id + 1

    # Generate Id string automatically (e.g. "adam_abdurrahman_9")
    clean_username = "".join(c for c in req.username.lower() if c.isalnum() or c == " ").replace(" ", "_")
    if not clean_username:
        clean_username = "user"
    generated_id = f"{clean_username}_{new_id_recnum}"

    new_user = models.User(
        id_recnum_mur=new_id_recnum,
        Id=generated_id,
        UserName=req.username,
        Password=req.password, # Disimpan plain-text sesuai dengan sample data Superadmin
        level_user=req.level_user,
        email_primary=req.email_primary,
        email_secondary=req.email_secondary,
        nohp=req.nohp,
        register_time=datetime.datetime.now(),
        update_time=datetime.datetime.now(),
        approve_by=None,
        status_active="P", # Pending Approval
        photo_url=None
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "pending",
        "message": "Akun berhasil dibuat. Menunggu persetujuan Superadmin.",
        "user_id": new_user.Id
    }


def get_pending_users(db: Session):
    users = db.query(models.User).filter(models.User.status_active == "P").all()
    # Format register_time to string
    result = []
    for u in users:
        reg_time_str = u.register_time.strftime("%d %b %Y %H:%M") if u.register_time else None
        result.append({
            "id_recnum_mur": u.id_recnum_mur,
            "Id": u.Id,
            "UserName": u.UserName,
            "email_primary": u.email_primary,
            "nohp": u.nohp,
            "register_time": reg_time_str
        })
    return result


def approve_user(db: Session, target_user_id: str, admin_id: str):
    user = db.query(models.User).filter(models.User.Id == target_user_id).first()
    if not user:
        raise ValueError("User tidak ditemukan")
    
    if user.status_active != "P":
        raise ValueError("Akun tidak dalam status pending persetujuan")

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)

    user.status_active = "T" # Pending Token verification
    user.approve_by = admin_id
    user.security_token = otp
    user.token_expiry = expiry
    user.update_time = datetime.datetime.now()

    db.commit()

    # Send mock email
    subject = "Token Keamanan Aktivasi Akun Anda"
    body = f"""Halo {user.UserName},

Pendaftaran akun Anda telah DISETUJUI oleh Superadmin ({admin_id}).

Berikut adalah 6-digit token keamanan Anda untuk mengaktifkan akun:
👉 {otp} 👈

Token ini berlaku selama 15 menit. Silakan masukkan token ini di halaman verifikasi aplikasi Android Anda.

Salam,
Sistem Vending Machine Capstone"""

    send_email(user.email_primary, subject, body)

    return {
        "status": "success",
        "message": "User disetujui, OTP telah dikirim ke email.",
        "otp_test_debug": otp # Mengembalikan OTP untuk mempermudah testing/debug
    }


def verify_user_token(db: Session, user_id: str, token: str):
    user = db.query(models.User).filter(models.User.Id == user_id).first()
    if not user:
        raise ValueError("User tidak ditemukan")
    
    if user.status_active != "T":
        raise ValueError("Akun tidak dalam status menunggu verifikasi token")
    
    if not user.security_token or user.security_token != token:
        raise ValueError("Token verifikasi salah")
    
    if not user.token_expiry or user.token_expiry < datetime.datetime.now():
        raise ValueError("Token verifikasi sudah kadaluarsa")

    # Activate user
    user.status_active = "1" # Active
    user.security_token = None
    user.token_expiry = None
    user.update_time = datetime.datetime.now()

    db.commit()

    return {
        "status": "active",
        "message": "Verifikasi sukses! Akun Anda telah aktif dan siap digunakan."
    }


def request_reset_password(db: Session, username: str, email: str):
    user = db.query(models.User).filter(
        models.User.UserName == username,
        models.User.email_primary == email,
        models.User.status_active == "1"
    ).first()

    if not user:
        raise ValueError("Kombinasi Username dan Email tidak ditemukan atau akun tidak aktif")

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)

    user.security_token = otp
    user.token_expiry = expiry
    user.update_time = datetime.datetime.now()

    db.commit()

    # Send mock email
    subject = "Permintaan Reset Password Anda"
    body = f"""Halo {user.UserName},

Kami menerima permintaan untuk mereset password akun Anda.

Berikut adalah 6-digit OTP reset password Anda:
👉 {otp} 👈

OTP ini berlaku selama 15 menit. Masukkan OTP ini di halaman reset password aplikasi Android untuk membuat password baru.

Jika Anda tidak merasa melakukan permintaan ini, abaikan email ini.

Salam,
Sistem Vending Machine Capstone"""

    send_email(user.email_primary, subject, body)

    return {
        "status": "otp_sent",
        "user_id": user.Id,
        "message": "OTP untuk reset password telah dikirim ke email.",
        "otp_test_debug": otp # Mengembalikan OTP untuk mempermudah testing/debug
    }


def confirm_reset_password(db: Session, user_id: str, token: str, new_password: str):
    user = db.query(models.User).filter(models.User.Id == user_id).first()
    if not user:
        raise ValueError("User tidak ditemukan")
    
    if not user.security_token or user.security_token != token:
        raise ValueError("OTP salah")
    
    if not user.token_expiry or user.token_expiry < datetime.datetime.now():
        raise ValueError("OTP sudah kadaluarsa")

    # Update password
    user.Password = new_password
    user.security_token = None
    user.token_expiry = None
    user.update_time = datetime.datetime.now()

    db.commit()

    return {
        "status": "success",
        "message": "Password Anda berhasil diperbarui. Silakan login kembali dengan password baru."
    }

def get_all_users(db: Session):
    users = db.query(models.User).filter(models.User.status_active != "R").order_by(models.User.id_recnum_mur.desc()).all()
    result = []
    for u in users:
        reg_time_str = u.register_time.strftime("%d %b %Y %H:%M") if u.register_time else None
        result.append({
            "id_recnum_mur": u.id_recnum_mur,
            "Id": u.Id,
            "UserName": u.UserName,
            "level_user": u.level_user,
            "email_primary": u.email_primary,
            "nohp": u.nohp,
            "status_active": u.status_active,
            "register_time": reg_time_str
        })
    return result

def admin_update_user(db: Session, target_user_id: str, level_user: int, new_password: str = None):
    user = db.query(models.User).filter(models.User.Id == target_user_id).first()
    if not user:
        raise ValueError("User tidak ditemukan")
    
    user.level_user = level_user
    if new_password:
        user.Password = new_password
    
    user.update_time = datetime.datetime.now()
    db.commit()
    
    return {
        "status": "success",
        "message": "User berhasil diperbarui oleh Superadmin."
    }

def admin_reject_user(db: Session, target_user_id: str):
    user = db.query(models.User).filter(models.User.Id == target_user_id).first()
    if not user:
        raise ValueError("User tidak ditemukan")
    
    user.status_active = "R" # Reject / Soft delete
    user.update_time = datetime.datetime.now()
    db.commit()
    
    return {
        "status": "success",
        "message": "User berhasil dinonaktifkan/ditolak."
    }
