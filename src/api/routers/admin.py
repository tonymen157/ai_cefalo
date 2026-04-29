from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.api.database import get_db
from src.api.models import CreditCode, CalibrationConfig
from src.api.dependencies import get_current_admin
from src.api.services.credit_code_service import generate_codes, get_code_stats
import csv
from io import StringIO

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.post("/generate-codes")
def generate_codes_endpoint(data: dict, db: Session = Depends(get_db)):
    count = int(data.get("count", 10))
    result = generate_codes(db, count)
    return result


@router.get("/codes/stats")
def get_codes_stats(db: Session = Depends(get_db)):
    return get_code_stats(db)


@router.get("/codes/export-csv")
def export_codes_csv(db: Session = Depends(get_db)):
    codes = db.query(CreditCode).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["code", "used", "used_at", "created_at", "batch_id"])
    for c in codes:
        writer.writerow([c.code, c.used, c.used_at, c.created_at, c.batch_id])

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credit_codes.csv"},
    )


@router.get("/scanner-scale")
def get_scanner_scale(db: Session = Depends(get_db)):
    config = (
        db.query(CalibrationConfig)
        .filter(CalibrationConfig.key == "scanner_scale")
        .first()
    )
    if not config:
        return {"value": None, "configured": False}
    return {"value": float(config.value), "configured": True}


@router.post("/scanner-scale")
def set_scanner_scale(data: dict, db: Session = Depends(get_db)):
    value = str(data.get("value", ""))
    if not value:
        raise HTTPException(status_code=400, detail="value required")

    config = (
        db.query(CalibrationConfig)
        .filter(CalibrationConfig.key == "scanner_scale")
        .first()
    )
    if config:
        config.value = value
    else:
        config = CalibrationConfig(key="scanner_scale", value=value)
        db.add(config)
    db.commit()
    return {"message": "Scanner scale updated", "value": float(value)}
