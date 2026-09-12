from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone, timedelta

from app.database.connection import get_db
from app.database.models import GenerationData, Plant, DataSource
from app.schemas.generation import GenerationResponse, GenerationBulkCreate

router = APIRouter(prefix="/generation", tags=["Generation Data"])

@router.get("/plant/{plant_id}", response_model=List[GenerationResponse])
def get_generation(
    plant_id: int,
    hours: int = 48,
    db: Session = Depends(get_db),
):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = (
        db.query(GenerationData)
        .filter(
            GenerationData.plant_id == plant_id,
            GenerationData.timestamp >= cutoff,
        )
        .order_by(GenerationData.timestamp.desc())
        .all()
    )
    return records

@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def ingest_generation_bulk(
    payload: GenerationBulkCreate,
    db: Session = Depends(get_db),
):
    plant = db.query(Plant).filter(Plant.id == payload.plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {payload.plant_id} not found")

    inserted = 0
    flagged = 0

    for record in payload.records:
        is_valid = True
        flag_reason = None

        if record.generation_mw < 0:
            is_valid = False
            flag_reason = "negative_generation"
        elif record.generation_mw > plant.capacity_mw:
            is_valid = False
            flag_reason = "above_capacity"

        gen = GenerationData(
            plant_id=plant.id,
            timestamp=record.timestamp,
            generation_mw=max(0, record.generation_mw),
            is_valid=is_valid,
            flag_reason=flag_reason,
            data_source=DataSource.SIMULATED,
        )
        db.merge(gen)
        inserted += 1
        if not is_valid:
            flagged += 1

    db.commit()
    return {"inserted": inserted, "flagged": flagged}
