from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    # Kolom Pydantic untuk input (berdasarkan kebiasaan FastAPI, huruf kecil untuk API input)
    username: str
    password: str

class LoginResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    username: str
    email_primary: str
    level_user: int
    status_active: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True

class AccountResponse(BaseModel):
    id_recnum_mur: int
    username: str
    email_primary: str
    email_secondary: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True

class AccountUpdateRequest(BaseModel):
    username: str
    email_primary: str
    email_secondary: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    new_password: str

class RegisterRequest(BaseModel):
    id: Optional[str] = None
    username: str
    password: str
    level_user: int
    email_primary: str
    email_secondary: Optional[str] = None
    nohp: str

class VerifyTokenRequest(BaseModel):
    user_id: str
    token: str

class ApproveUserRequest(BaseModel):
    target_user_id: str
    admin_id: str

class ResetPasswordRequest(BaseModel):
    username: str
    email: str

class ResetPasswordConfirmRequest(BaseModel):
    user_id: str
    token: str
    new_password: str

class PendingUserResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    UserName: str
    email_primary: str
    nohp: str
    register_time: Optional[str] = None

    class Config:
        from_attributes = True

class AdminUpdateUserRequest(BaseModel):
    level_user: int
    new_password: Optional[str] = None

class UserManagementResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    UserName: str
    level_user: int
    email_primary: str
    nohp: str
    status_active: str
    register_time: Optional[str] = None

    class Config:
        from_attributes = True

