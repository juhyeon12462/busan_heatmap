from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import CitiesResponseModel, HealthResponseModel, HeatmapDataModel, ScenarioType, SpatialUnitModel
from .service import build_cities_response, build_spatial_units, generate_heatmap, load_weather_csv


def _auto_fetch_weather() -> None:
    api_key = os.environ.get("KMA_API_KEY", "r1nJwUHtTKWZycFB7QylFQ")
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "fetch_kma_weather.py"
    if not script_path.exists():
        print(f"[Weather] 스크립트 없음: {script_path}")
        return
    try:
        print("[Weather] 기상 데이터 자동 업데이트 시작...")
        result = subprocess.run(
            [sys.executable, str(script_path), "--api-key", api_key, "--incremental"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[Weather] 오류: {result.stderr}")
        else:
            load_weather_csv.cache_clear()
            print("[Weather] 기상 데이터 업데이트 완료!")
    except Exception as e:
        print(f"[Weather] 자동 수집 실패: {e}")


app = FastAPI(
    title="Urban Heat Island Backend",
    version="0.2.0",
    description="부산 구 단위 도시열섬 히트맵 백엔드",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    thread = threading.Thread(target=_auto_fetch_weather, daemon=True)
    thread.start()


@app.get("/api/health", response_model=HealthResponseModel)
def health_check() -> HealthResponseModel:
    return HealthResponseModel(status="ok")


@app.get("/api/cities", response_model=CitiesResponseModel)
def get_cities() -> CitiesResponseModel:
    return build_cities_response()


@app.get("/api/spatial-units/{city}", response_model=list[SpatialUnitModel])
def get_spatial_units(city: str) -> list[SpatialUnitModel]:
    try:
        return build_spatial_units(city)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/heatmap", response_model=HeatmapDataModel)
def get_heatmap(
    city: str = Query(default="busan"),
    district: str = Query(default="all"),
    scenario: ScenarioType = Query(default="current"),
    date: str = Query(default="2026-04-17"),
    hour: int = Query(default=15),
) -> HeatmapDataModel:
    try:
        return generate_heatmap(city, district, scenario, date, hour)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
