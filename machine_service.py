"""
Machine Service Module
Menangani business logic untuk master_alat_vm
"""

from datetime import datetime
from sqlalchemy.orm import Session
import models
import schemas
from fastapi import HTTPException, status


def get_all_machines(db: Session):
    machines = db.query(models.Machine).order_by(models.Machine.id_recnum_mav).all()
    return {
        "total": len(machines),
        "data": machines,
    }


def get_machine_by_id(db: Session, machine_id: int):
    machine = db.query(models.Machine).filter(models.Machine.id_recnum_mav == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine dengan ID {machine_id} tidak ditemukan"
        )
    return machine


def create_machine(db: Session, request: schemas.MachineCreateRequest):
    machine = models.Machine(
        nama_vm=request.nama_vm,
        no_ref=request.no_ref,
        ip_address=request.ip_address,
        user_input=request.user_input,
        update_time=datetime.now(),
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def update_machine(db: Session, machine_id: int, request: schemas.MachineUpdateRequest):
    machine = get_machine_by_id(db, machine_id)

    if request.nama_vm is not None:
        machine.nama_vm = request.nama_vm
    if request.no_ref is not None:
        machine.no_ref = request.no_ref
    if request.ip_address is not None:
        machine.ip_address = request.ip_address
    if request.user_input is not None:
        machine.user_input = request.user_input

    machine.update_time = datetime.now()
    db.commit()
    db.refresh(machine)
    return machine


def delete_machine(db: Session, machine_id: int):
    machine = get_machine_by_id(db, machine_id)
    db.delete(machine)
    db.commit()
    return {"status": "success", "message": f"Machine {machine.nama_vm} berhasil dihapus"}
