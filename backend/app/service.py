from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from pyproj import Transformer

from .config import (
    CITY_CONFIGS,
    SOURCE_CRS_CANDIDATES,
    SUPPORTED_DATE_END,
    SUPPORTED_DATE_START,
    SUPPORTED_HOURS,
    SUPPORTED_SCENARIOS,
)
from .models import (
    CitiesResponseModel,
    CityInfoModel,
    DistrictInfoModel,
    HeatmapCellModel,
    HeatmapDataModel,
    HeatmapSummaryModel,
    ScenarioType,
    SpatialUnitModel,
    WeatherSignatureModel,
)

BUSAN_DISTRICTS = [
    {"code": "2611", "name": "Jung-gu",      "name_ko": "중구"},
    {"code": "2614", "name": "Seo-gu",       "name_ko": "서구"},
    {"code": "2617", "name": "Dong-gu",      "name_ko": "동구"},
    {"code": "2620", "name": "Yeongdo-gu",   "name_ko": "영도구"},
    {"code": "2623", "name": "Busanjin-gu",  "name_ko": "부산진구"},
    {"code": "2626", "name": "Dongnae-gu",   "name_ko": "동래구"},
    {"code": "2629", "name": "Nam-gu",       "name_ko": "남구"},
    {"code": "2632", "name": "Buk-gu",       "name_ko": "북구"},
    {"code": "2635", "name": "Haeundae-gu",  "name_ko": "해운대구"},
    {"code": "2638", "name": "Saha-gu",      "name_ko": "사하구"},
    {"code": "2641", "name": "Geumjeong-gu", "name_ko": "금정구"},
    {"code": "2644", "name": "Gangseo-gu",   "name_ko": "강서구"},
    {"code": "2647", "name": "Yeonje-gu",    "name_ko": "연제구"},
    {"code": "2650", "name": "Suyeong-gu",   "name_ko": "수영구"},
    {"code": "2653", "name": "Sasang-gu",    "name_ko": "사상구"},
    {"code": "2671", "name": "Gijang-gun",   "name_ko": "기장군"},
]

DISTRICT_MAP = {d["code"]: d for d in BUSAN_DISTRICTS}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def stable_noise(a: int, b: int) -> float:
    raw = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return raw - math.floor(raw)


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_int(value: str | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def iter_supported_dates() -> list[str]:
    total = (SUPPORTED_DATE_END - SUPPORTED_DATE_START).days + 1
    return [(SUPPORTED_DATE_START + timedelta(days=i)).isoformat() for i in range(total)]


def validate_city(city: str) -> str:
    if city not in CITY_CONFIGS:
        raise KeyError(f"Unsupported city: {city}")
    return city


def validate_scenario(scenario: str) -> ScenarioType:
    if scenario not in SUPPORTED_SCENARIOS:
        raise KeyError(f"Unsupported scenario: {scenario}")
    return scenario  # type: ignore[return-value]


def validate_hour(hour: int) -> int:
    if hour not in SUPPORTED_HOURS:
        raise ValueError(f"Unsupported hour: {hour}")
    return hour


def validate_date_value(date_value: str) -> date:
    parsed = date.fromisoformat(date_value)
    if parsed < SUPPORTED_DATE_START or parsed > SUPPORTED_DATE_END:
        raise ValueError(
            f"Date must be between {SUPPORTED_DATE_START.isoformat()} and {SUPPORTED_DATE_END.isoformat()}"
        )
    return parsed


@lru_cache(maxsize=1)
def load_weather_csv(city: str = "busan") -> dict[str, dict]:
    city_config = CITY_CONFIGS.get(city)
    if city_config is None or city_config.weather_csv_path is None:
        return {}
    path = city_config.weather_csv_path
    if not path.exists():
        return {}
    weather_map: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dt_str = row.get("datetime", "").strip()
            if dt_str:
                weather_map[dt_str] = row
    return weather_map


@lru_cache(maxsize=2)
def load_spatial_units_cache(city: str) -> list[dict]:
    """spatial_units.json 로드 (구 경계 GeoJSON)."""
    city_config = CITY_CONFIGS[city]
    # APP_DATA_DIR 아래 spatial_units.json
    from .config import APP_DATA_DIR
    path = APP_DATA_DIR / "busan_districts.geojson"
    # fallback: public/data
    from .config import APP_PUBLIC_DATA_DIR
    static_path = APP_PUBLIC_DATA_DIR / city / "spatial_units.json"
    
    if static_path.exists():
        with static_path.open(encoding="utf-8") as f:
            return json.load(f)
    return []


def detect_source_crs(city: str, rows: list[dict]) -> str:
    city_config = CITY_CONFIGS[city]
    ref_lon, ref_lat = city_config.reference_center
    sample_rows = rows[::max(len(rows) // 32, 1)][:32]

    best_crs = SOURCE_CRS_CANDIDATES[0]
    best_score = float("inf")

    for source_crs in SOURCE_CRS_CANDIDATES:
        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        lon_sum = lat_sum = 0.0
        for row in sample_rows:
            cx = (parse_float(row.get("left")) + parse_float(row.get("right"))) / 2
            cy = (parse_float(row.get("top")) + parse_float(row.get("bottom"))) / 2
            lon, lat = transformer.transform(cx, cy)
            lon_sum += lon
            lat_sum += lat
        score = abs(lon_sum / len(sample_rows) - ref_lon) + abs(lat_sum / len(sample_rows) - ref_lat)
        if score < best_score:
            best_score = score
            best_crs = source_crs
    return best_crs


def normalize_building_density(row: dict) -> float:
    density_final = parse_float(row.get("density_final1"))
    density = parse_float(row.get("density"))
    raw = parse_float(row.get("building_density"))
    if density_final > 0:
        normalized = density_final
    elif 0 < raw <= 1:
        normalized = raw
    elif raw > 1:
        normalized = raw / 4.0
    else:
        normalized = density
    return round(clamp(normalized, 0.0, 1.0), 4)


def normalize_ndvi(row: dict) -> float:
    return round(clamp(parse_float(row.get("green_mean")), -1.0, 1.0), 4)


def build_area_ratios(bd: float, ndvi: float) -> tuple[float, float, float]:
    urban = clamp(bd * 0.92 + (1 - max(ndvi, 0)) * 0.12, 0.0, 1.0)
    green = clamp(max(ndvi, 0), 0.0, 1.0)
    forest = clamp(max(ndvi, 0) * 0.72 - bd * 0.18, 0.0, 1.0)
    return round(urban, 4), round(forest, 4), round(green, 4)


def assign_district(lon: float, lat: float, spatial_units: list[dict]) -> dict:
    """간단한 bbox 기반 구 배정."""
    for unit in spatial_units:
        bbox = unit["bbox"]  # [minx, miny, maxx, maxy]
        if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
            return unit
    # fallback: 가장 가까운 구
    if spatial_units:
        return min(spatial_units, key=lambda u: (
            abs((u["bbox"][0] + u["bbox"][2]) / 2 - lon) +
            abs((u["bbox"][1] + u["bbox"][3]) / 2 - lat)
        ))
    return {"district_code": "0000", "district_name": "Unknown", "district_name_ko": "미상"}


@dataclass
class GridRecord:
    grid_id: str
    row_index: int
    col_index: int
    geo_left: float
    geo_right: float
    geo_bottom: float
    geo_top: float
    center_lon: float
    center_lat: float
    building_density: float
    ndvi_mean: float
    area_ratio_urban: float
    area_ratio_forest: float
    area_ratio_green: float
    local_noise: float
    district_code: str
    district_name: str
    district_name_ko: str


@lru_cache(maxsize=4)
def load_grid_records(city: str) -> tuple[str, tuple[GridRecord, ...]]:
    city_config = CITY_CONFIGS[city]
    with city_config.csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    source_crs = detect_source_crs(city, rows)
    transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    spatial_units = load_spatial_units_cache(city)

    records = []
    for row in rows:
        left = parse_float(row.get("left"))
        right = parse_float(row.get("right"))
        top = parse_float(row.get("top"))
        bottom = parse_float(row.get("bottom"))
        row_index = parse_int(row.get("row_index"))
        col_index = parse_int(row.get("col_index"))

        corners = [
            transformer.transform(left, bottom),
            transformer.transform(right, bottom),
            transformer.transform(right, top),
            transformer.transform(left, top),
        ]
        lons = [c[0] for c in corners]
        lats = [c[1] for c in corners]
        geo_left, geo_right = min(lons), max(lons)
        geo_bottom, geo_top = min(lats), max(lats)
        center_lon = (geo_left + geo_right) / 2
        center_lat = (geo_bottom + geo_top) / 2

        bd = normalize_building_density(row)
        ndvi = normalize_ndvi(row)
        urban, forest, green = build_area_ratios(bd, ndvi)

        district = assign_district(center_lon, center_lat, spatial_units)

        records.append(GridRecord(
            grid_id=str(row.get("id") or f"{row_index}-{col_index}"),
            row_index=row_index,
            col_index=col_index,
            geo_left=round(geo_left, 7),
            geo_right=round(geo_right, 7),
            geo_bottom=round(geo_bottom, 7),
            geo_top=round(geo_top, 7),
            center_lon=round(center_lon, 7),
            center_lat=round(center_lat, 7),
            building_density=bd,
            ndvi_mean=ndvi,
            area_ratio_urban=urban,
            area_ratio_forest=forest,
            area_ratio_green=green,
            local_noise=stable_noise(row_index + 1, col_index + 1),
            district_code=district.get("district_code", "0000"),
            district_name=district.get("district_name", "Unknown"),
            district_name_ko=district.get("district_name_ko", "미상"),
        ))

    return source_crs, tuple(records)


def build_cities_response() -> CitiesResponseModel:
    cities = []
    for config in CITY_CONFIGS.values():
        districts = [
            DistrictInfoModel(code=d["code"], name=d["name"], name_ko=d["name_ko"])
            for d in BUSAN_DISTRICTS
        ] if config.code == "busan" else []
        cities.append(CityInfoModel(
            code=config.code,
            name=config.name,
            name_ko=config.name_ko,
            center=config.center,
            zoom=config.zoom,
            bounds=config.bounds,
            districts=districts,
        ))
    return CitiesResponseModel(
        cities=cities,
        availableDates=iter_supported_dates(),
        availableHours=list(SUPPORTED_HOURS),
        supportedScenarios=list(SUPPORTED_SCENARIOS),  # type: ignore[arg-type]
    )


def build_spatial_units(city: str) -> list[SpatialUnitModel]:
    validate_city(city)
    units = load_spatial_units_cache(city)
    return [
        SpatialUnitModel(
            district_code=u["district_code"],
            district_name=u["district_name"],
            district_name_ko=u["district_name_ko"],
            center=tuple(u["center"]),  # type: ignore[arg-type]
            bbox=tuple(u["bbox"]),  # type: ignore[arg-type]
            geometry=u["geometry"],
            building_density=u.get("building_density", 0.0),
            ndvi_mean=u.get("ndvi_mean", 0.0),
            area_ratio_urban=u.get("area_ratio_urban", 0.0),
            area_ratio_forest=u.get("area_ratio_forest", 0.0),
            area_ratio_green=u.get("area_ratio_green", 0.0),
            grid_count=u.get("grid_count", 0),
        )
        for u in units
    ]


def build_weather_signature(target_date: date, hour: int, scenario: ScenarioType, city: str = "busan") -> WeatherSignatureModel:
    scenario_bias = {
        "past":      {"air": -1.7, "wind": 0.2,  "humidity": 4.0,  "solar": -10.0},
        "current":   {"air":  0.0, "wind": 0.0,  "humidity": 0.0,  "solar":   0.0},
        "future_7d": {"air":  2.7, "wind": -0.3, "humidity": -5.5, "solar":  24.0},
    }.get(scenario, {"air": 0.0, "wind": 0.0, "humidity": 0.0, "solar": 0.0})

    # 실측 데이터 조회
    if scenario in ("current", "past"):
        weather_map = load_weather_csv(city)
        dt_key = f"{target_date.isoformat()}T{hour:02d}:00:00"
        if dt_key in weather_map:
            row = weather_map[dt_key]
            return WeatherSignatureModel(
                air_temp=round(parse_float(row.get("air_temp")) + scenario_bias["air"], 1),
                wind_speed=round(clamp(parse_float(row.get("wind_speed")) + scenario_bias["wind"], 0.7, 7.5), 1),
                humidity=round(clamp(parse_float(row.get("humidity")) + scenario_bias["humidity"], 28.0, 94.0), 1),
                solar_radiation=round(max(0.0, parse_float(row.get("solar_radiation")) + scenario_bias["solar"]), 1),
                source_type="observed",
                source_detail="KMA 부산 관측소 실측값",
            )

    # 수식 폴백
    day_of_year = target_date.timetuple().tm_yday
    seasonal = math.sin(((day_of_year - 81) / 365.0) * math.pi * 2)
    daylight = max(0.0, math.sin(((hour - 6) / 12.0) * math.pi))
    diurnal = math.cos(((hour - 15) / 12.0) * math.pi)

    return WeatherSignatureModel(
        air_temp=round(15.5 + seasonal * 10.5 + diurnal * 5.2 + scenario_bias["air"], 1),
        wind_speed=round(clamp(1.8 + (1 - daylight) * 0.9 + abs(seasonal) * 0.6 + scenario_bias["wind"], 0.7, 7.5), 1),
        humidity=round(clamp(74.0 - daylight * 23.0 - seasonal * 7.0 + scenario_bias["humidity"], 28.0, 94.0), 1),
        solar_radiation=round(max(0.0, daylight * (690.0 + seasonal * 150.0 + scenario_bias["solar"])), 1),
        source_type="simulated",
        source_detail=None,
    )


def calculate_lst(record: GridRecord, weather: WeatherSignatureModel, scenario: ScenarioType) -> float:
    surface_bias = {"past": -1.4, "current": 0.0, "future_7d": 2.8}.get(scenario, 0.0)
    urban_heat = record.building_density * 7.8 + record.area_ratio_urban * 2.1
    green_cooling = max(record.ndvi_mean, 0) * 5.5 + record.area_ratio_green * 1.6 + record.area_ratio_forest * 0.9
    solar_storage = weather.solar_radiation / 235.0
    wind_cooling = weather.wind_speed * (0.48 + (1 - record.building_density) * 0.12)
    humidity_effect = (weather.humidity - 55.0) * 0.024
    local_variation = (record.local_noise - 0.5) * 1.6
    lst = (weather.air_temp + solar_storage + urban_heat - green_cooling
           - wind_cooling + humidity_effect + surface_bias + local_variation)
    return round(clamp(lst, 10.0, 50.0), 1)


@lru_cache(maxsize=256)
def generate_heatmap(city: str, district: str, scenario: str, date_value: str, hour: int) -> HeatmapDataModel:
    city_key = validate_city(city)
    scenario_key = validate_scenario(scenario)
    validated_hour = validate_hour(hour)
    parsed_date = validate_date_value(date_value)
    source_crs, records = load_grid_records(city_key)
    weather = build_weather_signature(parsed_date, validated_hour, scenario_key, city_key)
    spatial_units = load_spatial_units_cache(city_key)

    # 구 경계 SpatialUnit 목록 (district 필터링)
    if district == "all":
        district_units = spatial_units
    else:
        district_units = [u for u in spatial_units if u.get("district_code") == district]

    districts_out = [
        SpatialUnitModel(
            district_code=u["district_code"],
            district_name=u["district_name"],
            district_name_ko=u["district_name_ko"],
            center=tuple(u["center"]),  # type: ignore[arg-type]
            bbox=tuple(u["bbox"]),  # type: ignore[arg-type]
            geometry=u["geometry"],
            building_density=u.get("building_density", 0.0),
            ndvi_mean=u.get("ndvi_mean", 0.0),
            area_ratio_urban=u.get("area_ratio_urban", 0.0),
            area_ratio_forest=u.get("area_ratio_forest", 0.0),
            area_ratio_green=u.get("area_ratio_green", 0.0),
            grid_count=u.get("grid_count", 0),
        )
        for u in district_units
    ]

    # 격자 필터링
    target_codes = {u["district_code"] for u in district_units} if district != "all" else None

    cells = []
    for record in records:
        if target_codes and record.district_code not in target_codes:
            continue
        lst = calculate_lst(record, weather, scenario_key)
        cells.append(HeatmapCellModel(
            block_id=f"{record.grid_id}-0-0",
            district_code=record.district_code,
            district_name=record.district_name,
            district_name_ko=record.district_name_ko,
            center=(record.center_lon, record.center_lat),
            bbox=(record.geo_left, record.geo_bottom, record.geo_right, record.geo_top),
            geometry={
                "type": "Polygon",
                "coordinates": [[
                    [record.geo_left,  record.geo_bottom],
                    [record.geo_right, record.geo_bottom],
                    [record.geo_right, record.geo_top],
                    [record.geo_left,  record.geo_top],
                    [record.geo_left,  record.geo_bottom],
                ]]
            },
            row_index=record.row_index,
            col_index=record.col_index,
            lst_value=lst,
            building_density=record.building_density,
            ndvi_mean=record.ndvi_mean,
            area_ratio_urban=record.area_ratio_urban,
            area_ratio_forest=record.area_ratio_forest,
            area_ratio_green=record.area_ratio_green,
        ))

    if not cells:
        raise ValueError("No cells found for the given parameters")

    lst_values = [c.lst_value for c in cells]
    hottest = max(cells, key=lambda c: c.lst_value)
    summary = HeatmapSummaryModel(
        avg_lst=round(sum(lst_values) / len(lst_values), 2),
        min_lst=min(lst_values),
        max_lst=max(lst_values),
        hotspot_count=sum(1 for v in lst_values if v >= 31.0),
        cell_count=len(cells),
        hottest_block_id=hottest.block_id,
        hottest_district_code=hottest.district_code,
        hottest_district_name_ko=hottest.district_name_ko,
    )

    return HeatmapDataModel(
        city=city_key,
        district=district if district != "all" else None,
        scenario=scenario_key,
        datetime=f"{parsed_date.isoformat()}T{validated_hour:02d}:00:00",
        districts=districts_out,
        cells=cells,
        weather=weather,
        summary=summary,
        source_crs=source_crs,
        spatial_mode="district_outline_block_fill_2d",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
