"""
shift_service.py
Business logic untuk CRUD dbo.master_settime (jam shift kerja).

Struktur tabel asli (terverifikasi dari DB):
  id_recnum_mst  bigint   PK
  nama_shift     varchar
  nama_bagian    varchar
  jam_mulai      time     nullable  ← TIME type, bukan varchar!
  jam_akhir      time     nullable  ← TIME type, bukan varchar!
  status_active  varchar            ← VARCHAR, bukan integer!
  update_time    datetime nullable
  user_input     varchar  nullable
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas


def _parse_time(time_str: str) -> dt.time:
    """Parse string 'HH:MM' atau 'HH:MM:SS' menjadi datetime.time."""
    if not time_str:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    raise HTTPException(
        status_code=400,
        detail=f"Format jam tidak valid: '{time_str}'. Gunakan HH:MM atau HH:MM:SS",
    )


def _serialize(shift: models.Shift) -> dict:
    return {
        "id_recnum_mst": shift.id_recnum_mst,
        "nama_shift": shift.nama_shift,
        "nama_bagian": shift.nama_bagian,
        "jam_mulai": str(shift.jam_mulai)[:5] if shift.jam_mulai else None,  # 'HH:MM'
        "jam_akhir": str(shift.jam_akhir)[:5] if shift.jam_akhir else None,
        "status_active": shift.status_active,
        "update_time": shift.update_time.isoformat() if shift.update_time else None,
        "user_input": shift.user_input,
    }


def get_all_shifts(db: Session) -> dict:
    shifts = db.query(models.Shift).order_by(models.Shift.id_recnum_mst).all()
    return {
        "total": len(shifts),
        "data": [_serialize(s) for s in shifts],
    }


def get_shift_by_id(db: Session, shift_id: int) -> dict:
    shift = (
        db.query(models.Shift).filter(models.Shift.id_recnum_mst == shift_id).first()
    )
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift ID {shift_id} tidak ditemukan",
        )
    return _serialize(shift)


def create_shift(db: Session, request: schemas.ShiftCreateRequest) -> dict:
    if request.status_active not in ("0", "1"):
        raise HTTPException(
            status_code=400,
            detail="status_active harus '0' (inactive) atau '1' (active)",
        )

    shift = models.Shift(
        nama_shift=request.nama_shift,
        nama_bagian=request.nama_bagian,
        jam_mulai=_parse_time(request.jam_mulai),
        jam_akhir=_parse_time(request.jam_akhir),
        status_active=request.status_active,
        user_input=request.user_input,
        update_time=dt.datetime.now(),
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return _serialize(shift)


def update_shift(
    db: Session, shift_id: int, request: schemas.ShiftUpdateRequest
) -> dict:
    shift = (
        db.query(models.Shift).filter(models.Shift.id_recnum_mst == shift_id).first()
    )
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift ID {shift_id} tidak ditemukan",
        )

    if request.nama_shift is not None:
        shift.nama_shift = request.nama_shift
    if request.nama_bagian is not None:
        shift.nama_bagian = request.nama_bagian
    if request.jam_mulai is not None:
        shift.jam_mulai = _parse_time(request.jam_mulai)
    if request.jam_akhir is not None:
        shift.jam_akhir = _parse_time(request.jam_akhir)
    if request.user_input is not None:
        shift.user_input = request.user_input

    if request.status_active is not None:
        if request.status_active not in ("0", "1"):
            raise HTTPException(
                status_code=400,
                detail="status_active harus '0' (inactive) atau '1' (active)",
            )
        shift.status_active = request.status_active

    shift.update_time = dt.datetime.now()
    db.commit()
    db.refresh(shift)
    return _serialize(shift)


def delete_shift(db: Session, shift_id: int) -> dict:
    shift = (
        db.query(models.Shift).filter(models.Shift.id_recnum_mst == shift_id).first()
    )
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift ID {shift_id} tidak ditemukan",
        )
    nama = shift.nama_shift
    db.delete(shift)
    db.commit()
    return {"status": "success", "message": f"Shift '{nama}' berhasil dihapus"}
