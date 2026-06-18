"""
Slot Service Module
Menangani business logic untuk manage_map_slot_number
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
from fastapi import HTTPException, status


def get_all_slots(db: Session, vm_id: int = None):
    query = db.query(models.SlotNumber)

    if vm_id is not None:
        query = query.filter(models.SlotNumber.id_recnum_mav == vm_id)

    slots = query.order_by(models.SlotNumber.id_recnum_mav, models.SlotNumber.slot_name).all()
    total_slots = len(slots)
    total_capacity = sum(slot.slot_number_max for slot in slots)

    return {
        "total": total_slots,
        "data": slots,
        "total_capacity": total_capacity,
    }


def get_slot_by_id(db: Session, slot_id: int):
    slot = db.query(models.SlotNumber).filter(models.SlotNumber.id_recnum_msn == slot_id).first()
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot number dengan ID {slot_id} tidak ditemukan"
        )
    return slot


def get_slots_by_vm(db: Session, vm_id: int):
    slots = db.query(models.SlotNumber).filter(models.SlotNumber.id_recnum_mav == vm_id).order_by(models.SlotNumber.slot_name).all()
    if not slots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tidak ada slot untuk VM ID {vm_id}"
        )
    total_capacity = sum(slot.slot_number_max for slot in slots)
    return {
        "id_recnum_mav": vm_id,
        "total_rows": len(slots),
        "total_slots": total_capacity,
        "slots": slots,
    }


def create_slot(db: Session, request: schemas.SlotCreateRequest):
    if request.slot_number_max < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jumlah slot maximum tidak boleh negatif"
        )
    if not request.slot_name or len(request.slot_name) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama slot tidak valid"
        )

    slot = models.SlotNumber(
        id_recnum_mav=request.id_recnum_mav,
        slot_name=request.slot_name,
        slot_number_max=request.slot_number_max,
        id_recnum_variant=request.id_recnum_variant,
        user_input=request.user_input,
        update_time=datetime.now(),
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def update_slot(db: Session, slot_id: int, request: schemas.SlotUpdateRequest):
    slot = get_slot_by_id(db, slot_id)

    if request.slot_name is not None:
        slot.slot_name = request.slot_name
    if request.slot_number_max is not None:
        if request.slot_number_max < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jumlah slot maximum tidak boleh negatif"
            )
        slot.slot_number_max = request.slot_number_max
    if request.id_recnum_variant is not None:
        slot.id_recnum_variant = request.id_recnum_variant
    if request.user_input is not None:
        slot.user_input = request.user_input

    slot.update_time = datetime.now()
    db.commit()
    db.refresh(slot)
    return slot


def delete_slot(db: Session, slot_id: int):
    slot = get_slot_by_id(db, slot_id)
    db.delete(slot)
    db.commit()
    return {"status": "success", "message": f"Slot number {slot.slot_name} untuk VM {slot.id_recnum_mav} berhasil dihapus"}
