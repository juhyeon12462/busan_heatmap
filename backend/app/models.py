from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

ScenarioType = Literal["past", "current", "future_7d"]


class DistrictInfoModel(BaseModel):
    code: str
    name: str
    name_ko: str


class CityInfoModel(BaseModel):
    code: str
    name: str
    name_ko: str
    center: tuple[float, float]
    zoom: float
    bounds: tuple[tuple[float, float], tuple[float, float]] | None = None
    districts: list[DistrictInfoModel] = []


class CitiesResponseModel(BaseModel):
    cities: list[CityInfoModel]
    availableDates: list[str]
    availableHours: list[int]
    supportedScenarios: list[ScenarioType]


class SpatialUnitModel(BaseModel):
    district_code: str
    district_name: str
    district_name_ko: str
    center: tuple[float, float]
    bbox: tuple[float, float, float, float]
    geometry: dict[str, Any]
    building_density: float
    ndvi_mean: float
    area_ratio_urban: float
    area_ratio_forest: float
    area_ratio_green: float
    grid_count: int


class HeatmapCellModel(BaseModel):
    block_id: str
    district_code: str
    district_name: str
    district_name_ko: str
    center: tuple[float, float]
    bbox: tuple[float, float, float, float]
    geometry: dict[str, Any]
    row_index: int
    col_index: int
    lst_value: float
    building_density: float
    ndvi_mean: float
    area_ratio_urban: float
    area_ratio_forest: float
    area_ratio_green: float


class WeatherSignatureModel(BaseModel):
    air_temp: float
    wind_speed: float
    humidity: float
    solar_radiation: float
    source_type: str = "observed"
    source_detail: str | None = None


class HeatmapSummaryModel(BaseModel):
    avg_lst: float
    min_lst: float
    max_lst: float
    hotspot_count: int
    cell_count: int
    hottest_block_id: str | None = None
    hottest_district_code: str | None = None
    hottest_district_name_ko: str | None = None


class HeatmapDataModel(BaseModel):
    city: str
    district: str | None = None
    scenario: ScenarioType
    datetime: str
    districts: list[SpatialUnitModel] = []
    cells: list[HeatmapCellModel]
    weather: WeatherSignatureModel
    summary: HeatmapSummaryModel
    source_crs: str
    spatial_mode: str = "district_outline_block_fill_2d"
    generated_at: str


class HealthResponseModel(BaseModel):
    status: str
