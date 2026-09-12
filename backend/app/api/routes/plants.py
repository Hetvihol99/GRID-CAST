"""Plants API routes — CRUD for renewable generation plants."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.database.models import Plant
from app.schemas.plant import PlantCreate, PlantUpdate, PlantResponse, PlantSummary
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/plants", tags=["Plants"])


@router.get("/", response_model=List[PlantSummary])
def list_plants(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all plants. Use active_only=false to include decommissioned plants."""
    query = db.query(Plant)
    if active_only:
        query = query.filter(Plant.is_active == True)
    return query.all()


@router.get("/{plant_id}", response_model=PlantResponse)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    """Get full details for a specific plant."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")
    return plant


@router.post("/", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
def create_plant(payload: PlantCreate, db: Session = Depends(get_db)):
    """Create a new renewable plant."""
    plant = Plant(**payload.model_dump())
    db.add(plant)
    db.commit()
    db.refresh(plant)
    logger.info(f"Created plant: {plant.name} ({plant.plant_type})")
    return plant


@router.patch("/{plant_id}", response_model=PlantResponse)
def update_plant(
    plant_id: int,
    payload: PlantUpdate,
    db: Session = Depends(get_db),
):
    """Update plant details (partial update)."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plant, field, value)

    db.commit()
    db.refresh(plant)
    return plant


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_plant(plant_id: int, db: Session = Depends(get_db)):
    """Deactivate a plant (soft delete — preserves historical data)."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")
    plant.is_active = False
    db.commit()
    logger.info(f"Deactivated plant {plant_id}")
