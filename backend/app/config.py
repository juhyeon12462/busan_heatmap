from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PROVIDED_DATA_DIR = BASE_DIR / "제공data"
APP_PUBLIC_DATA_DIR = BASE_DIR / "app" / "public" / "data"
APP_DATA_DIR = BASE_DIR / "backend" / "app" / "data"
CURRENT_DATE = date.today()
ROLLING_HISTORY_DAYS = 365
FORECAST_HORIZON_DAYS = 7
BLOCK_SUBDIVISION = 2

SUPPORTED_SCENARIOS = ("past", "current", "future_7d")
SUPPORTED_HOURS = tuple(range(24))
SUPPORTED_DATE_START = CURRENT_DATE - timedelta(days=ROLLING_HISTORY_DAYS)
SUPPORTED_DATE_END = CURRENT_DATE + timedelta(days=FORECAST_HORIZON_DAYS)
DEFAULT_EXPORT_DATES = (CURRENT_DATE.isoformat(),)
SOURCE_CRS_CANDIDATES = ("EPSG:5179", "EPSG:5181", "EPSG:5186", "EPSG:5187")


@dataclass(frozen=True)
class CityConfig:
    code: str
    name: str
    name_ko: str
    center: tuple[float, float]
    zoom: float
    bounds: tuple[tuple[float, float], tuple[float, float]]
    csv_path: Path
    district_geojson_path: Path
    reference_center: tuple[float, float]
    weather_csv_path: Path | None = None
    weather_forecast_csv_path: Path | None = None
    district_weather_csv_path: Path | None = None
    district_weather_forecast_csv_path: Path | None = None
    weather_station_id: int | None = None


CITY_CONFIGS: dict[str, CityConfig] = {
    "busan": CityConfig(
        code="busan",
        name="Busan",
        name_ko="부산광역시",
        center=(129.0756, 35.1796),
        zoom=10.4,
        bounds=((128.76, 34.88), (129.32, 35.40)),
        csv_path=PROVIDED_DATA_DIR / "busan_density_NDVI.csv",
        district_geojson_path=APP_DATA_DIR / "busan_districts.geojson",
        reference_center=(129.0756, 35.1796),
        weather_csv_path=PROVIDED_DATA_DIR / "weather_hourly_busan.csv",
        weather_forecast_csv_path=PROVIDED_DATA_DIR / "weather_forecast_busan.csv",
        district_weather_csv_path=PROVIDED_DATA_DIR / "weather_hourly_busan_districts.csv",
        district_weather_forecast_csv_path=PROVIDED_DATA_DIR / "weather_forecast_busan_districts.csv",
        weather_station_id=159,
    )
}
