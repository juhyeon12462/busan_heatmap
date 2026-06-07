from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import CITY_CONFIGS, CURRENT_DATE, SUPPORTED_DATE_END, SUPPORTED_DATE_START
from backend.app.service import build_district_weather_signature, load_district_profiles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export hourly district-level weather CSV files")
    parser.add_argument("--city", default="busan")
    parser.add_argument("--history-start-date", default=SUPPORTED_DATE_START.isoformat())
    parser.add_argument("--history-end-date", default=CURRENT_DATE.isoformat())
    parser.add_argument("--forecast-start-date", default=CURRENT_DATE.isoformat())
    parser.add_argument("--forecast-end-date", default=SUPPORTED_DATE_END.isoformat())
    return parser.parse_args()


def iter_hourly_range(start_date: str, end_date: str) -> list[datetime]:
    start = datetime.combine(date.fromisoformat(start_date), dt_time(hour=0))
    end = datetime.combine(date.fromisoformat(end_date), dt_time(hour=23))
    if start > end:
        raise ValueError("start date must be earlier than end date")

    timestamps: list[datetime] = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += timedelta(hours=1)
    return timestamps


def build_rows(city: str, timestamps: list[datetime], *, prefer_forecast: bool) -> list[dict[str, object]]:
    city_config = CITY_CONFIGS[city]
    districts = load_district_profiles(city)
    rows: list[dict[str, object]] = []

    for timestamp in timestamps:
        for district in districts:
            signature = build_district_weather_signature(
                city,
                district,
                timestamp.date(),
                timestamp.hour,
                prefer_forecast=prefer_forecast,
            )
            rows.append(
                {
                    "datetime": timestamp.strftime("%Y-%m-%dT%H:00:00"),
                    "city_code": city,
                    "district_code": district.district_code,
                    "district_name_ko": district.district_name_ko,
                    "station_id": city_config.weather_station_id or "",
                    "air_temp": signature.air_temp,
                    "wind_speed": signature.wind_speed,
                    "humidity": signature.humidity,
                    "solar_radiation": signature.solar_radiation,
                    "source_type": signature.source_type,
                    "source_detail": signature.source_detail or "",
                }
            )

    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "datetime",
                "city_code",
                "district_code",
                "district_name_ko",
                "station_id",
                "air_temp",
                "wind_speed",
                "humidity",
                "solar_radiation",
                "source_type",
                "source_detail",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    city = args.city.strip().lower()
    if city not in CITY_CONFIGS:
        raise KeyError(f"Unsupported city: {city}")

    history_timestamps = iter_hourly_range(args.history_start_date, args.history_end_date)
    forecast_timestamps = iter_hourly_range(args.forecast_start_date, args.forecast_end_date)
    city_config = CITY_CONFIGS[city]

    history_path = city_config.district_weather_csv_path
    forecast_path = city_config.district_weather_forecast_csv_path
    if history_path is None or forecast_path is None:
        raise ValueError(f"District weather CSV paths are not configured for city: {city}")

    if history_path.exists():
        history_path.unlink()
    if forecast_path.exists():
        forecast_path.unlink()

    history_rows = build_rows(city, history_timestamps, prefer_forecast=False)
    forecast_rows = build_rows(city, forecast_timestamps, prefer_forecast=True)

    write_csv(history_path, history_rows)
    write_csv(forecast_path, forecast_rows)

    print(f"Saved {len(history_rows)} district history rows to {history_path}")
    print(f"Saved {len(forecast_rows)} district forecast rows to {forecast_path}")


if __name__ == "__main__":
    main()
