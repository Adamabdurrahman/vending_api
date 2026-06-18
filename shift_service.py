"""
Shift Service Module
Menangani business logic untuk master_settime
"""

from datetime import datetime
from sqlalchemy.orm import Session
import models
import schemas
from fastapi import HTTPException, status


def get_all_shifts(db: Session):
    shifts = db.query(models.Shift).order_by(models.Shift.id_recnum_mst).all()
    return {
        "total": len(shifts),
        "data": shifts,
    }


def get_shift_by_id(db: Session, shift_id: int):
    shift = db.query(models.Shift).filter(models.Shift.id_recnum_mst == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift dengan ID {shift_id} tidak ditemukan"
        )
    return shift


def create_shift(db: Session, request: schemas.ShiftCreateRequest):
    if request.status_active not in [0, 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status harus 0 (inactive) atau 1 (active)"
        )

    shift = models.Shift(
        nama_shift=request.nama_shift,
        nama_bagian=request.nama_bagian,
        jam_mulai=request.jam_mulai,
        jam_akhir=request.jam_akhir,
        status_active=request.status_active,
        user_input=request.user_input,
        update_time=datetime.now(),
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def update_shift(db: Session, shift_id: int, request: schemas.ShiftUpdateRequest):
    shift = get_shift_by_id(db, shift_id)

    if request.nama_shift is not None:
        shift.nama_shift = request.nama_shift
    if request.nama_bagian is not None:
        shift.nama_bagian = request.nama_bagian
    if request.jam_mulai is not None:
        shift.jam_mulai = request.jam_mulai
    if request.jam_akhir is not None:
        shift.jam_akhir = request.jam_akhir
    if request.status_active is not None:
        if request.status_active not in [0, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status harus 0 (inactive) atau 1 (active)"
            )
        shift.status_active = request.status_active
    if request.user_input is not None:
        shift.user_input = request.user_input

    shift.update_time = datetime.now()
    db.commit()
    db.refresh(shift)
    return shift


def delete_shift(db: Session, shift_id: int):
    shift = get_shift_by_id(db, shift_id)
    db.delete(shift)
    db.commit()
    return {"status": "success", "message": f"Shift {shift.nama_shift} berhasil dihapus"}
