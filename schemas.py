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
