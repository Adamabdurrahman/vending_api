"""
Variant Service Module
Menangani business logic untuk CRUD master_variant
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
from fastapi import HTTPException, status


def get_all_variants(db: Session, status_filter: int = None):
    """
    Ambil semua varian dengan opsional filter status
    
    Args:
        db: Database session
        status_filter: Optional, filter by status (0 atau 1)
    
    Returns:
        dict dengan total dan list varian
    """
    query = db.query(models.Variant)
    
    if status_filter is not None:
        query = query.filter(models.Variant.status == status_filter)
    
    variants = query.order_by(models.Variant.id_recnum_variant).all()
    
    return {
        "total": len(variants),
        "data": variants
    }


def get_variant_by_id(db: Session, variant_id: int):
    """
    Ambil varian berdasarkan ID
    
    Args:
        db: Database session
        variant_id: ID varian
    
    Returns:
        Variant object atau raise HTTPException 404
    """
    variant = db.query(models.Variant).filter(
        models.Variant.id_recnum_variant == variant_id
    ).first()
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Varian dengan ID {variant_id} tidak ditemukan"
        )
    
    return variant


def create_variant(db: Session, request: schemas.VariantCreateRequest):
    """
    Buat varian baru
    
    Args:
        db: Database session
        request: VariantCreateRequest
    
    Returns:
        Variant object yang baru dibuat
    """
    # Validasi duplikasi nama
    existing = db.query(models.Variant).filter(
        func.lower(models.Variant.nama_variant) == func.lower(request.nama_variant)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Varian dengan nama '{request.nama_variant}' sudah ada"
        )
    
    # Validasi status
    if request.status not in [0, 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status harus 0 (inactive) atau 1 (active)"
        )
    
    # Buat varian baru
    new_variant = models.Variant(
        nama_variant=request.nama_variant,
        image_url=request.image_url,
        status=request.status,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(new_variant)
    db.commit()
    db.refresh(new_variant)
    
    return new_variant


def update_variant(db: Session, variant_id: int, request: schemas.VariantUpdateRequest):
    """
    Update varian yang ada
    
    Args:
        db: Database session
        variant_id: ID varian yang akan diupdate
        request: VariantUpdateRequest
    
    Returns:
        Variant object yang sudah diupdate
    """
    variant = get_variant_by_id(db, variant_id)
    
    # Validasi nama jika diubah
    if request.nama_variant:
        existing = db.query(models.Variant).filter(
            models.Variant.id_recnum_variant != variant_id,
            func.lower(models.Variant.nama_variant) == func.lower(request.nama_variant)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Varian dengan nama '{request.nama_variant}' sudah ada"
            )
        
        variant.nama_variant = request.nama_variant
    
    # Update image jika ada
    if request.image_url is not None:
        variant.image_url = request.image_url
    
    # Update status dengan validasi
    if request.status is not None:
        if request.status not in [0, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status harus 0 (inactive) atau 1 (active)"
            )
        variant.status = request.status
    
    variant.updated_at = datetime.now()
    
    db.commit()
    db.refresh(variant)
    
    return variant


def delete_variant(db: Session, variant_id: int):
    """
    Hapus varian (hard delete)
    
    Args:
        db: Database session
        variant_id: ID varian yang akan dihapus
    
    Returns:
        Pesan sukses atau raise HTTPException
    """
    variant = get_variant_by_id(db, variant_id)
    
    db.delete(variant)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Varian '{variant.nama_variant}' berhasil dihapus"
    }


def get_active_variants(db: Session):
    """
    Ambil hanya varian yang aktif (status = 1)
    
    Args:
        db: Database session
    
    Returns:
        List varian aktif
    """
    variants = db.query(models.Variant).filter(
        models.Variant.status == 1
    ).order_by(models.Variant.nama_variant).all()
    
    return variants
