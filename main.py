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
import dashboard_service
import calendar_service
import manual_insert_service
import retrain_log_service
import user_auth_service
import variant_service
import restock_service
import slot_service
import machine_service
import shift_service
import inventory_service

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

    # Validasi status_active
    if user.status_active != '1':
        if user.status_active == 'P':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Akun Anda masih pending persetujuan Superadmin"
            )
        elif user.status_active == 'T':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail={
                    "error_code": "PENDING_OTP",
                    "message": "Akun Anda menunggu verifikasi token email",
                    "user_id": user.Id
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Akun Anda tidak aktif atau dinonaktifkan"
            )

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


# ========================================================
# KUMPULAN ENDPOINT DASHBOARD SUMMARY (GROUP: DASHBOARD)
# ========================================================

@app.get("/api/v1/dashboard/metrics", tags=["Dashboard Summary"])
def api_dashboard_metrics(start_date: str, end_date: str, shift_id: str = "ALL", db: Session = Depends(get_db)):
    return dashboard_service.get_metrics_data(db, start_date, end_date, shift_id)

@app.get("/api/v1/dashboard/consumption-chart", tags=["Dashboard Summary"])
def api_consumption_chart(start_date: str, end_date: str, shift_id: str = "ALL", db: Session = Depends(get_db)):
    return dashboard_service.get_consumption_chart(db, start_date, end_date, shift_id)

@app.get("/api/v1/dashboard/sales-analytics", tags=["Dashboard Summary"])
def api_sales_analytics(start_date: str, end_date: str, shift_id: str = "ALL", db: Session = Depends(get_db)):
    return dashboard_service.get_sales_analytics(db, start_date, end_date, shift_id)

@app.get("/api/v1/dashboard/latest-transactions", tags=["Dashboard Summary"])
def api_latest_transactions(start_date: str, end_date: str, shift_id: str = "ALL", db: Session = Depends(get_db)):
    return dashboard_service.get_latest_transactions(db, start_date, end_date, shift_id)


# ========================================================
# KUMPULAN ENDPOINT PREDICTION DASHBOARD (GROUP: PREDICTION)
# ========================================================

@app.get("/api/v1/prediction/summary", tags=["Prediction Dashboard"])
def api_prediction_summary(year: int = 2026, quarter: int = 1, db: Session = Depends(get_db)):
    return dashboard_service.get_prediction_summary(db, year, quarter)

@app.get("/api/v1/prediction/variant-errors", tags=["Prediction Dashboard"])
def api_variant_errors(year: int = 2026, quarter: int = 1, db: Session = Depends(get_db)):
    return dashboard_service.get_variant_errors(db, year, quarter)

@app.get("/api/v1/prediction/shift-errors", tags=["Prediction Dashboard"])
def api_shift_errors(year: int = 2026, quarter: int = 1, db: Session = Depends(get_db)):
    return dashboard_service.get_shift_errors(db, year, quarter)

@app.get("/api/v1/prediction/daily-logs", tags=["Prediction Dashboard"])
def api_daily_logs(year: int = 2026, quarter: int = 1, db: Session = Depends(get_db)):
    return dashboard_service.get_daily_logs(db, year, quarter)

@app.get("/api/v1/prediction/chart-data", tags=["Prediction Dashboard"])
def api_prediction_chart_data(year: int = 2026, quarter: int = 1, db: Session = Depends(get_db)):
    return dashboard_service.get_chart_data(db, year, quarter)


# ========================================================
# KUMPULAN ENDPOINT OPERATIONAL CALENDAR (GROUP: CALENDAR)
# ========================================================

@app.get("/api/v1/calendar", tags=["Calendar"])
def api_get_calendar(year: int = 2026, db: Session = Depends(get_db)):
    return calendar_service.get_calendar_year_data(db, year)

class CalendarDayUpdate(BaseModel):
    date: str
    day_category: str
    is_working_day: bool
    is_ramadan: bool
    is_shutdown: bool

@app.post("/api/v1/calendar/day", tags=["Calendar"])
def api_update_calendar_day(req: CalendarDayUpdate, db: Session = Depends(get_db)):
    return calendar_service.update_calendar_day(
        db, req.date, req.day_category, req.is_working_day, req.is_ramadan, req.is_shutdown
    )

class CalendarYearGenerate(BaseModel):
    year: int

@app.post("/api/v1/calendar/generate", tags=["Calendar"])
def api_generate_calendar_year(req: CalendarYearGenerate, db: Session = Depends(get_db)):
    try:
        return calendar_service.generate_calendar_year(db, req.year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/calendar/year/{year}", tags=["Calendar"])
def api_delete_calendar_year(year: int, db: Session = Depends(get_db)):
    return calendar_service.delete_calendar_year(db, year)


# ========================================================
# KUMPULAN ENDPOINT MANUAL INSERT (GROUP: MANUAL INSERT)
# ========================================================

from fastapi.responses import FileResponse

@app.get("/api/v1/manual-insert/template", tags=["Manual Insert"])
def api_download_template():
    manual_insert_service.ensure_template_exists()
    if not os.path.exists(manual_insert_service.TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="File template tidak ditemukan")
    return FileResponse(manual_insert_service.TEMPLATE_PATH, filename="Template_Insert.xlsx")

@app.post("/api/v1/manual-insert/upload", tags=["Manual Insert"])
async def api_upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    return manual_insert_service.process_excel_upload(db, contents, file.filename)


# ========================================================
# KUMPULAN ENDPOINT RETRAIN LOGS (GROUP: RETRAIN LOGS)
# ========================================================

@app.get("/api/v1/retrain/logs", tags=["Retrain Logs"])
def api_get_retrain_logs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return retrain_log_service.get_retrain_logs_data(db, limit, offset)


# ========================================================
# KUMPULAN ENDPOINT AUTENTIKASI & USER MANAGEMENT (NEW)
# ========================================================

@app.post("/api/v1/auth/register", tags=["Autentikasi & User Management"], status_code=201)
def api_register_user(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.register_user(db, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/api/v1/admin/pending-users", tags=["Autentikasi & User Management"], response_model=list[schemas.PendingUserResponse])
def api_get_pending_users(db: Session = Depends(get_db)):
    return user_auth_service.get_pending_users(db)

@app.post("/api/v1/admin/approve-user", tags=["Autentikasi & User Management"])
def api_approve_user(req: schemas.ApproveUserRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.approve_user(db, req.target_user_id, req.admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/v1/auth/verify-token", tags=["Autentikasi & User Management"])
def api_verify_user_token(req: schemas.VerifyTokenRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.verify_user_token(db, req.user_id, req.token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/v1/auth/reset-password/request", tags=["Autentikasi & User Management"])
def api_request_reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.request_reset_password(db, req.username, req.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@app.post("/api/v1/auth/reset-password/confirm", tags=["Autentikasi & User Management"])
def api_confirm_reset_password(req: schemas.ResetPasswordConfirmRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.confirm_reset_password(db, req.user_id, req.token, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/api/v1/admin/users", tags=["Autentikasi & User Management"], response_model=list[schemas.UserManagementResponse])
def api_get_all_users(db: Session = Depends(get_db)):
    return user_auth_service.get_all_users(db)

@app.put("/api/v1/admin/users/{userId}/update-role-password", tags=["Autentikasi & User Management"])
def api_admin_update_user(userId: str, req: schemas.AdminUpdateUserRequest, db: Session = Depends(get_db)):
    try:
        return user_auth_service.admin_update_user(db, userId, req.level_user, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/v1/admin/users/{userId}", tags=["Autentikasi & User Management"])
def api_admin_reject_user(userId: str, db: Session = Depends(get_db)):
    try:
        return user_auth_service.admin_reject_user(db, userId)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============ VARIANT CRUD ENDPOINTS ============

@app.get("/api/v1/variant", tags=["Variant Management"], response_model=schemas.VariantListResponse)
def get_all_variants(status: int = None, db: Session = Depends(get_db)):
    """
    Ambil daftar semua varian
    
    Query Parameters:
    - status: Optional filter (0=inactive, 1=active)
    """
    result = variant_service.get_all_variants(db, status_filter=status)
    return schemas.VariantListResponse(
        total=result["total"],
        data=result["data"]
    )

@app.get("/api/v1/variant/{variant_id}", tags=["Variant Management"], response_model=schemas.VariantResponse)
def get_variant_detail(variant_id: int, db: Session = Depends(get_db)):
    """
    Ambil detail varian berdasarkan ID
    """
    return variant_service.get_variant_by_id(db, variant_id)

@app.post("/api/v1/variant", tags=["Variant Management"], response_model=schemas.VariantResponse, status_code=status.HTTP_201_CREATED)
def create_new_variant(request: schemas.VariantCreateRequest, db: Session = Depends(get_db)):
    """
    Buat varian baru
    
    Body:
    - nama_variant: Nama varian (required, unique)
    - image_url: URL gambar varian (optional)
    - status: Status varian (0=inactive, 1=active, default=1)
    """
    return variant_service.create_variant(db, request)

@app.put("/api/v1/variant/{variant_id}", tags=["Variant Management"], response_model=schemas.VariantResponse)
def update_existing_variant(variant_id: int, request: schemas.VariantUpdateRequest, db: Session = Depends(get_db)):
    """
    Update varian yang ada
    
    Body (semua field optional):
    - nama_variant: Nama varian baru
    - image_url: URL gambar varian baru
    - status: Status baru (0=inactive, 1=active)
    """
    return variant_service.update_variant(db, variant_id, request)

@app.delete("/api/v1/variant/{variant_id}", tags=["Variant Management"])
def delete_existing_variant(variant_id: int, db: Session = Depends(get_db)):
    """
    Hapus varian berdasarkan ID
    """
    return variant_service.delete_variant(db, variant_id)

@app.get("/api/v1/variant/active", tags=["Variant Management"], response_model=list[schemas.VariantResponse])
def get_active_variants_only(db: Session = Depends(get_db)):
    """
    Ambil hanya varian yang aktif (status = 1)
    """
    return variant_service.get_active_variants(db)


# ============ RESTOCK CRUD ENDPOINTS ============

@app.get("/api/v1/restock", tags=["Restock Management"], response_model=schemas.RestockListResponse)
def get_all_restocks(status: int = None, db: Session = Depends(get_db)):
    """
    Ambil daftar semua restock
    
    Query Parameters:
    - status: Optional filter (0=inactive, 1=active)
    """
    result = restock_service.get_all_restocks(db, status_filter=status)
    return schemas.RestockListResponse(
        total=result["total"],
        data=result["data"]
    )

@app.get("/api/v1/restock/{restock_id}", tags=["Restock Management"], response_model=schemas.RestockResponse)
def get_restock_detail(restock_id: int, db: Session = Depends(get_db)):
    """
    Ambil detail restock berdasarkan ID
    """
    return restock_service.get_restock_by_id(db, restock_id)

@app.get("/api/v1/restock/vm/{vm_id}", tags=["Restock Management"], response_model=schemas.RestockByVMResponse)
def get_restock_by_vm(vm_id: int, db: Session = Depends(get_db)):
    """
    Ambil semua restock untuk vending machine tertentu
    
    Path Parameters:
    - vm_id: ID vending machine
    """
    result = restock_service.get_restock_by_vm(db, vm_id)
    return schemas.RestockByVMResponse(**result)

@app.post("/api/v1/restock", tags=["Restock Management"], response_model=schemas.RestockResponse, status_code=status.HTTP_201_CREATED)
def create_new_restock(request: schemas.RestockCreateRequest, db: Session = Depends(get_db)):
    """
    Buat/Update restock baru untuk slot tertentu
    
    Body:
    - id_recnum_mav: ID vending machine (required)
    - slot_number: Nomor slot (A1, B2, dll) (required)
    - stok_qty: Jumlah stok (required)
    - user_input: Username yang input (default: admin)
    - status_restok: Status (0=inactive, 1=active, default=1)
    
    Note: Jika slot sudah ada, akan di-update. Jika belum ada, akan dibuat baru.
    """
    return restock_service.create_restock(db, request)

@app.put("/api/v1/restock/{restock_id}", tags=["Restock Management"], response_model=schemas.RestockResponse)
def update_existing_restock(restock_id: int, request: schemas.RestockUpdateRequest, db: Session = Depends(get_db)):
    """
    Update restock yang ada
    
    Path Parameters:
    - restock_id: ID restock
    
    Body (semua field optional):
    - stok_qty: Jumlah stok baru
    - status_restok: Status baru (0=inactive, 1=active)
    - user_input: Username yang update
    """
    return restock_service.update_restock(db, restock_id, request)

@app.delete("/api/v1/restock/{restock_id}", tags=["Restock Management"])
def delete_existing_restock(restock_id: int, db: Session = Depends(get_db)):
    """
    Hapus restock berdasarkan ID
    """
    return restock_service.delete_restock(db, restock_id)

@app.put("/api/v1/restock/vm/{vm_id}/slot/{slot_number}", tags=["Restock Management"], response_model=schemas.RestockResponse)
def update_stock_quantity(vm_id: int, slot_number: str, stok_qty: int, user: str = "admin", db: Session = Depends(get_db)):
    """
    Update kuantitas stok untuk slot tertentu (shortcut endpoint)
    
    Path Parameters:
    - vm_id: ID vending machine
    - slot_number: Nomor slot (A1, B2, dll)
    
    Query Parameters:
    - stok_qty: Jumlah stok baru (required)
    - user: Username yang update (default: admin)
    """
    return restock_service.update_stock_qty(db, vm_id, slot_number, stok_qty, user)

@app.get("/api/v1/restock/alerts/low-stock", tags=["Restock Management"])
def get_low_stock_alerts(threshold: int = 10, db: Session = Depends(get_db)):
    """
    Ambil restock dengan stok di bawah threshold (untuk alert sistem)
    
    Query Parameters:
    - threshold: Batas minimal stok (default: 10)
    """
    return restock_service.get_low_stock_alerts(db, threshold)


# ============ SLOT NUMBER CRUD ENDPOINTS ============

@app.get("/api/v1/slot", tags=["Slot Number"], response_model=schemas.SlotByVMResponse)
def get_slots(vm_id: int, db: Session = Depends(get_db)):
    """Ambil daftar slot untuk VM tertentu"""
    return slot_service.get_slots_by_vm(db, vm_id)

@app.get("/api/v1/slot/{slot_id}", tags=["Slot Number"], response_model=schemas.SlotResponse)
def get_slot_detail(slot_id: int, db: Session = Depends(get_db)):
    """Ambil detail slot berdasarkan ID"""
    return slot_service.get_slot_by_id(db, slot_id)

@app.post("/api/v1/slot", tags=["Slot Number"], response_model=schemas.SlotResponse, status_code=status.HTTP_201_CREATED)
def create_new_slot(request: schemas.SlotCreateRequest, db: Session = Depends(get_db)):
    """Buat konfigurasi slot baru untuk mesin"""
    return slot_service.create_slot(db, request)

@app.put("/api/v1/slot/{slot_id}", tags=["Slot Number"], response_model=schemas.SlotResponse)
def update_existing_slot(slot_id: int, request: schemas.SlotUpdateRequest, db: Session = Depends(get_db)):
    """Update konfigurasi slot"""
    return slot_service.update_slot(db, slot_id, request)

@app.delete("/api/v1/slot/{slot_id}", tags=["Slot Number"])
def delete_existing_slot(slot_id: int, db: Session = Depends(get_db)):
    """Hapus konfigurasi slot"""
    return slot_service.delete_slot(db, slot_id)


# ============ MACHINE CRUD ENDPOINTS ============

@app.get("/api/v1/machine", tags=["Manage Alat VM"])
def get_all_machines(db: Session = Depends(get_db)):
    """Ambil semua mesin vending"""
    return machine_service.get_all_machines(db)

@app.get("/api/v1/machine/{machine_id}", tags=["Manage Alat VM"], response_model=schemas.MachineResponse)
def get_machine_detail(machine_id: int, db: Session = Depends(get_db)):
    """Ambil detail mesin berdasarkan ID"""
    return machine_service.get_machine_by_id(db, machine_id)

@app.post("/api/v1/machine", tags=["Manage Alat VM"], response_model=schemas.MachineResponse, status_code=status.HTTP_201_CREATED)
def create_new_machine(request: schemas.MachineCreateRequest, db: Session = Depends(get_db)):
    """Tambah mesin vending baru"""
    return machine_service.create_machine(db, request)

@app.put("/api/v1/machine/{machine_id}", tags=["Manage Alat VM"], response_model=schemas.MachineResponse)
def update_existing_machine(machine_id: int, request: schemas.MachineUpdateRequest, db: Session = Depends(get_db)):
    """Update detail mesin vending"""
    return machine_service.update_machine(db, machine_id, request)

@app.delete("/api/v1/machine/{machine_id}", tags=["Manage Alat VM"])
def delete_existing_machine(machine_id: int, db: Session = Depends(get_db)):
    """Hapus data mesin vending"""
    return machine_service.delete_machine(db, machine_id)


# ============ SHIFT CRUD ENDPOINTS ============

@app.get("/api/v1/shift", tags=["Shift Management"])
def get_all_shifts(db: Session = Depends(get_db)):
    """Ambil semua jam shift"""
    return shift_service.get_all_shifts(db)

@app.get("/api/v1/shift/{shift_id}", tags=["Shift Management"], response_model=schemas.ShiftResponse)
def get_shift_detail(shift_id: int, db: Session = Depends(get_db)):
    """Ambil detail shift berdasarkan ID"""
    return shift_service.get_shift_by_id(db, shift_id)

@app.post("/api/v1/shift", tags=["Shift Management"], response_model=schemas.ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_new_shift(request: schemas.ShiftCreateRequest, db: Session = Depends(get_db)):
    """Buat jam shift baru"""
    return shift_service.create_shift(db, request)

@app.put("/api/v1/shift/{shift_id}", tags=["Shift Management"], response_model=schemas.ShiftResponse)
def update_existing_shift(shift_id: int, request: schemas.ShiftUpdateRequest, db: Session = Depends(get_db)):
    """Update jam shift"""
    return shift_service.update_shift(db, shift_id, request)

@app.delete("/api/v1/shift/{shift_id}", tags=["Shift Management"])
def delete_existing_shift(shift_id: int, db: Session = Depends(get_db)):
    """Hapus data shift"""
    return shift_service.delete_shift(db, shift_id)


# ============ INVENTORY DASHBOARD ENDPOINTS ============

@app.get("/api/v1/inventory/dashboard", tags=["Inventory Dashboard"], response_model=schemas.InventoryDashboardResponse)
def get_inventory_dashboard(
    year: int = None,
    quarter: int = None,
    page: int = 1,
    per_page: int = 10,
    variant: str = None,
    type: str = None,
    db: Session = Depends(get_db),
):
    """Ambil data comprehensive inventory dashboard, termasuk forecasting, stok gudang/VM, pergerakan stok, dan rekomendasi pembelian."""
    return inventory_service.get_inventory_dashboard(db, year, quarter, page, per_page, variant, type)

@app.post("/api/v1/inventory/dashboard", tags=["Inventory Dashboard"], response_model=schemas.InventoryDashboardResponse)
def post_inventory_dashboard(
    request: schemas.StockInRequest,
    year: int = None,
    quarter: int = None,
    page: int = 1,
    per_page: int = 10,
    variant: str = None,
    type: str = None,
    db: Session = Depends(get_db),
):
    """Tambahkan stok masuk ke gudang lalu kembalikan inventory dashboard terbaru dengan hasil stock-in dan pergerakan stok."""
    return inventory_service.get_inventory_dashboard(db, year, quarter, page, per_page, variant, type, request)

