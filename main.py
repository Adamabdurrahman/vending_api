import os
import shutil

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

import etl_service
import forecast_service

# Import dari file lokal
import models
import notif_service
import retrain_service
import schemas
from database import engine, get_db

# (Opsi) Membuat tabel jika belum ada, walau di sini tabel sudah ada di db
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vending Machine API",
    description="API untuk jembatan aplikasi Android Vending ke SQL Server ADAM123\\SQLEXPRESS",
    version="1.0.0",
)

# Mount folder static untuk mengakses foto
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.post("/login", tags=["Autentikasi"], response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    # Mencari user berdasarkan UserName (di tabel huruf kapital, di pydantic huruf kecil)
    user = (
        db.query(models.User).filter(models.User.UserName == request.username).first()
    )

    # Validasi apakah user ditemukan
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Username tidak ditemukan"
        )

    # Evaluasi plain text password
    if user.Password != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password salah"
        )

    # Validasi status_active (contoh jika 'Y' berarti aktif, bisa disesuaikan '1' atau 'A')
    # if user.status_active != 'Y':
    #     raise HTTPException(status_code=403, detail="User tidak aktif")

    # Jika sukses
    # return custom map since DB fields are Capitalized and Schema fields might differ
    photo_url = user.photo_url if hasattr(user, "photo_url") else None
    return {
        "id_recnum_mur": user.id_recnum_mur,
        "Id": user.Id,
        "username": user.UserName,
        "email_primary": user.email_primary,
        "level_user": user.level_user,
        "status_active": user.status_active,
        "photo_url": photo_url,
    }


# ========================================================
# KUMPULAN PENGATURAN AKUN (GROUP: AKUN)
# ========================================================


@app.get(
    "/account/{id_recnum_mur}",
    tags=["Pengaturan Akun"],
    response_model=schemas.AccountResponse,
)
def get_account_detail(id_recnum_mur: int, db: Session = Depends(get_db)):
    """Menarik data akun terbaru berdasarkan ID Numerik User"""
    user = (
        db.query(models.User).filter(models.User.id_recnum_mur == id_recnum_mur).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    return {
        "id_recnum_mur": user.id_recnum_mur,
        "username": user.UserName,
        "email_primary": user.email_primary,
        "email_secondary": user.email_secondary,
        "photo_url": user.photo_url if hasattr(user, "photo_url") else None,
    }


@app.put("/account/{id_recnum_mur}/update", tags=["Pengaturan Akun"])
def update_account_profile(
    id_recnum_mur: int,
    request: schemas.AccountUpdateRequest,
    db: Session = Depends(get_db),
):
    """Memperbarui informasi nama dan email pengguna (Tombol: Save Changes)"""
    user = (
        db.query(models.User).filter(models.User.id_recnum_mur == id_recnum_mur).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    user.UserName = request.username
    user.email_primary = request.email_primary
    user.email_secondary = request.email_secondary

    db.commit()
    db.refresh(user)

    return {"status": "success", "message": "Profil berhasil diperbarui"}


@app.put("/account/{id_recnum_mur}/change-password", tags=["Pengaturan Akun"])
def change_password(
    id_recnum_mur: int,
    request: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    """Fungsi khusus mengganti password (Tombol: Change Password)"""
    user = (
        db.query(models.User).filter(models.User.id_recnum_mur == id_recnum_mur).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    user.Password = request.new_password
    db.commit()

    return {"status": "success", "message": "Password berhasil diubah"}


@app.post("/account/{id_recnum_mur}/upload-photo", tags=["Pengaturan Akun"])
async def upload_profile_photo(
    id_recnum_mur: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Upload foto baru (Tombol Kamera) ke dalam folder /uploads/profiles"""
    user = (
        db.query(models.User).filter(models.User.id_recnum_mur == id_recnum_mur).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # Memastikan ekstensi file (.jpg, .png, dll)
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"user_{id_recnum_mur}{file_extension}"
    file_path = os.path.join("uploads", "profiles", new_filename)

    # Simpan file ke server lokal (PC kamu)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Buat public URL, misal: http://10.0.2.2:8000/uploads/profiles/user_1.jpg
    # Pada praktiknya Android akan mengambil URL ini
    public_url_path = f"/uploads/profiles/{new_filename}"

    # Update kolom photo_url di database SQL Server!
    user.photo_url = public_url_path
    db.commit()

    return {
        "status": "success",
        "message": "Foto berhasil diupload",
        "photo_url": public_url_path,
    }


@app.delete("/account/{id_recnum_mur}/delete", tags=["Pengaturan Akun"])
def delete_account(id_recnum_mur: int, db: Session = Depends(get_db)):
    """Menonaktifkan akun (Soft Delete - status_active = 'N') (Tombol: Delete Account)"""
    user = (
        db.query(models.User).filter(models.User.id_recnum_mur == id_recnum_mur).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    user.status_active = "N"  # Atau '0' tergantung kesepakatan aplikasi kamu
    db.commit()

    return {"status": "success", "message": "Akun telah dinonaktifkan"}


# ========================================================
# KUMPULAN ENDPOINT FORECASTING & ML (GROUP: FORECASTING)
# ========================================================


class ForecastRequest(BaseModel):
    start_year: int
    start_month: int
    end_year: int
    end_month: int


class UpdateActualsRequest(BaseModel):
    month: str


@app.post("/api/v1/forecast/generate", tags=["Forecasting"])
def api_generate_forecast(req: ForecastRequest):
    return forecast_service.generate_forecast(
        req.start_year, req.start_month, req.end_year, req.end_month
    )


@app.post("/api/v1/forecast/update-actuals", tags=["Forecasting"])
def api_update_actuals(req: UpdateActualsRequest):
    return forecast_service.update_actuals(req.month)


@app.post("/api/v1/model/retrain", tags=["Machine Learning"])
def api_retrain_model(background_tasks: BackgroundTasks):
    background_tasks.add_task(retrain_service.run_retrain)
    return {"status": "success", "message": "Retraining started in background"}


@app.get("/api/v1/model/retrain-status", tags=["Machine Learning"])
def api_retrain_status(db: Session = Depends(get_db)):
    """Menampilkan riwayat retraining terakhir dari dbo.RetrainLog."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT TOP 5 Id, RunTimestamp, ModelVersion, MAPE, MAE, RMSE, "
                "TrainingRows, TrainingPeriodEnd, BestParams, Status "
                "FROM dbo.RetrainLog ORDER BY RunTimestamp DESC"
            )
        ).fetchall()

    if not rows:
        return {
            "status": "no_data",
            "message": "Belum ada riwayat retraining. Jalankan POST /api/v1/model/retrain terlebih dahulu.",
        }

    latest = rows[0]
    return {
        "status": "ok",
        "latest": {
            "id": latest[0],
            "run_timestamp": latest[1],
            "model_version": latest[2],
            "mape": latest[3],
            "mae": latest[4],
            "rmse": latest[5],
            "training_rows": latest[6],
            "training_period_end": latest[7],
            "best_params": latest[8],
            "result_status": latest[9],
        },
        "history": [
            {
                "id": r[0],
                "run_timestamp": r[1],
                "mape": r[3],
                "result_status": r[9],
            }
            for r in rows
        ],
    }


@app.get("/api/v1/forecast/history", tags=["Forecasting"])
def api_get_forecast_history(month: str = None, db: Session = Depends(get_db)):
    query = "SELECT PredictedMonth, RunTimestamp, TotalDemand, ActualDemand, ErrorPercent FROM dbo.ForecastResults_Layer1"
    params = {}
    if month:
        query += " WHERE PredictedMonth = :m"
        params["m"] = month
    query += " ORDER BY RunTimestamp DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "month": r[0],
            "timestamp": r[1],
            "predicted": r[2],
            "actual": r[3],
            "error": r[4],
        }
        for r in rows
    ]


@app.post("/etl/run-pipeline", tags=["Data Pipeline"])
def api_run_etl(background_tasks: BackgroundTasks):
    background_tasks.add_task(etl_service.run_etl_pipeline)
    return {"status": "success", "message": "ETL Pipeline started in background"}


# ========================================================
# NOTIFIKASI SISTEM
# ========================================================


@app.get("/api/v1/notifications", tags=["Notifikasi"])
def api_get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    notif_type: str = None,
):
    """
    Ambil daftar notifikasi sistem.
    - unread_only=true  : hanya yang belum dibaca
    - limit             : maksimal baris (default 50)
    - notif_type        : filter by type (ETL / QUARTERLY / RETRAIN / dll)
    """
    query = """
        SELECT TOP :lim
            Id, CreatedAt, NotifType, Severity, Title, Message,
            IsRead, RelatedMonth, RelatedQuarter
        FROM dbo.SystemNotifications
        WHERE 1=1
    """
    params = {"lim": limit}

    if unread_only:
        query += " AND IsRead = 0"
    if notif_type:
        query += " AND NotifType = :ntype"
        params["ntype"] = notif_type

    query += " ORDER BY CreatedAt DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()
        unread_count = conn.execute(
            text("SELECT COUNT(*) FROM dbo.SystemNotifications WHERE IsRead = 0")
        ).scalar()

    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": r[0],
                "created_at": r[1],
                "notif_type": r[2],
                "severity": r[3],
                "title": r[4],
                "message": r[5],
                "is_read": r[6],
                "related_month": r[7],
                "related_quarter": r[8],
            }
            for r in rows
        ],
    }


@app.put("/api/v1/notifications/{notif_id}/read", tags=["Notifikasi"])
def api_mark_read(notif_id: int):
    """Tandai satu notifikasi sebagai sudah dibaca."""
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE dbo.SystemNotifications SET IsRead = 1 WHERE Id = :id"),
            {"id": notif_id},
        )
    return {"status": "success", "id": notif_id}


@app.put("/api/v1/notifications/read-all", tags=["Notifikasi"])
def api_mark_all_read():
    """Tandai semua notifikasi sebagai sudah dibaca."""
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE dbo.SystemNotifications SET IsRead = 1 WHERE IsRead = 0")
        )
    return {"status": "success", "marked_read": result.rowcount}
