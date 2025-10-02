# backend/app/api/v1/calibration.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Tuple
import math

router = APIRouter(prefix="/v1")

class CalibrationIn(BaseModel):
    # two points in PAGE coordinates (PDF points), known ground distance in ft
    p1: Tuple[float, float]
    p2: Tuple[float, float]
    distance_ft: float

class CalibrationOut(BaseModel):
    points_per_foot: float
    scale_in_equals_ft: float

@router.post("/calibrate", response_model=CalibrationOut)
def calibrate(c: CalibrationIn):
    dx = c.p2[0]-c.p1[0]; dy = c.p2[1]-c.p1[1]
    dist_pts = math.hypot(dx, dy)
    ppf = dist_pts / max(1e-6, c.distance_ft)       # points per foot
    # "1in = X ft" -> X = 72 / ppf
    return CalibrationOut(points_per_foot=ppf, scale_in_equals_ft=72.0/ppf)
