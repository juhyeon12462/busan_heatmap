from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import CITY_CONFIGS, PROVIDED_DATA_DIR

MISSING_VALUES = {"", "-9", "-9.0", "-9.00", "-99", "-99.0", "-99.00"}
OBSERVATION_INDEX = {
    "wind_speed": 3,
    "air_temp": 11,
    "humidity": 13,
    "solar_mj": 34,
}
FIELD_LIMITS = {
    "air_temp": (-25.0, 45.0),
    "wind_speed": (0.0, 20.0),
    "humidity": (5.0, 100.0),
    "solar_radiation": (0.0, 1200.0),
}


@dataclass(frozen=True)
class WeatherRow:
    timestamp: datetime
    city_code: str
    station_id: int
    air_temp: float | None
    wind_speed: float | None
    humidity: float | None
    solar_radiation: float | None
    source_type: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Complete KMA weather collection and forecasting pipeline")
    parser.add_argument("--city", default="busan")
    parser.add_argument("--station-id", type=int, default=None)
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2026-04-13")
    parser.add_argument("--forecast-hours", type=int, default=24 * 7)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--timeout-sec", type=int, default=25)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--api-key", default=os.environ.get("KMA_API_KEY"))
    parser.add_argument("--history-out", default=None)
    parser.add_argument("--forecast-out", default=None)
    parser.add_argument("--mode", choices=("history", "forecast", "all"), default="all")
    return parser.parse_args()


def build_output_path(city: str, explicit_path: str | None, suffix: str) -> Path:
    if explicit_path:
        return Path(explicit_path)
    return PROVIDED_DATA_DIR / f"weather_{suffix}_{city}.csv"


def iter_hourly_range(start_date: str, end_date: str) -> list[datetime]:
    start = datetime.combine(date.fromisoformat(start_date), dt_time(hour=0))
    end = datetime.combine(date.fromisoformat(end_date), dt_time(hour=23))
    if start > end:
        raise ValueError("start-date must be earlier than or equal to end-date")

    timestamps: list[datetime] = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += timedelta(hours=1)
    return timestamps


def build_request_url(api_key: str, station_id: int, timestamp: datetime) -> str:
    query = urlencode(
        {
            "tm": timestamp.strftime("%Y%m%d%H00"),
            "stn": station_id,
            "help": 0,
            "authKey": api_key,
        }
    )
    return f"https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php?{query}"


def parse_optional_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped in MISSING_VALUES:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def mj_to_watts_per_square_meter(solar_mj: float | None) -> float | None:
    if solar_mj is None:
        return None
    return round(solar_mj * 277.778, 1)


def find_payload_line(response_text: str) -> str | None:
    stripped = response_text.lstrip()
    if stripped.startswith("{"):
        raise ValueError(stripped[:200])

    for line in response_text.splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("#"):
            return candidate
    return None


def parse_hourly_response(city: str, station_id: int, timestamp: datetime, response_text: str) -> WeatherRow:
    payload_line = find_payload_line(response_text)
    if payload_line is None:
        return WeatherRow(
            timestamp=timestamp,
            city_code=city,
            station_id=station_id,
            air_temp=None,
            wind_speed=None,
            humidity=None,
            solar_radiation=None,
            source_type="observed",
        )

    parts = payload_line.split()
    if len(parts) <= OBSERVATION_INDEX["solar_mj"]:
        raise ValueError(f"Unexpected KMA response format for {timestamp.isoformat()}: {payload_line}")

    air_temp = parse_optional_float(parts[OBSERVATION_INDEX["air_temp"]])
    wind_speed = parse_optional_float(parts[OBSERVATION_INDEX["wind_speed"]])
    humidity = parse_optional_float(parts[OBSERVATION_INDEX["humidity"]])
    solar_radiation = mj_to_watts_per_square_meter(parse_optional_float(parts[OBSERVATION_INDEX["solar_mj"]]))

    # Night-time hourly rows frequently omit solar even when the row itself is valid.
    if solar_radiation is None and any(value is not None for value in (air_temp, wind_speed, humidity)):
        if timestamp.hour <= 6 or timestamp.hour >= 19:
            solar_radiation = 0.0

    return WeatherRow(
        timestamp=timestamp,
        city_code=city,
        station_id=station_id,
        air_temp=None if air_temp is None else round(air_temp, 1),
        wind_speed=None if wind_speed is None else round(wind_speed, 1),
        humidity=None if humidity is None else round(humidity, 1),
        solar_radiation=solar_radiation,
        source_type="observed",
    )


def fetch_hourly_row(
    city: str,
    station_id: int,
    api_key: str,
    timestamp: datetime,
    timeout_sec: int,
    retries: int,
) -> WeatherRow:
    request_url = build_request_url(api_key, station_id, timestamp)
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            with urlopen(request_url, timeout=timeout_sec) as response:
                response_text = response.read().decode("utf-8", errors="ignore")
            return parse_hourly_response(city, station_id, timestamp, response_text)
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(min(2.5, 0.5 * (attempt + 1)))

    raise RuntimeError(f"Failed to fetch {timestamp.isoformat()} after {retries} attempts") from last_error


def collect_history(
    city: str,
    station_id: int,
    api_key: str,
    start_date: str,
    end_date: str,
    max_workers: int,
    timeout_sec: int,
    retries: int,
) -> list[WeatherRow]:
    timestamps = iter_hourly_range(start_date, end_date)

    print(
        f"Collecting {len(timestamps)} hourly observations for {city} "
        f"from {start_date} to {end_date} with {max_workers} workers",
        flush=True,
    )

    row_by_timestamp: dict[datetime, WeatherRow] = {}
    failed_timestamps: list[datetime] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_hourly_row, city, station_id, api_key, ts, timeout_sec, retries): ts
            for ts in timestamps
        }

        for index, future in enumerate(as_completed(future_map), start=1):
            timestamp = future_map[future]
            try:
                row = future.result()
            except Exception:  # noqa: BLE001
                failed_timestamps.append(timestamp)
                row = WeatherRow(
                    timestamp=timestamp,
                    city_code=city,
                    station_id=station_id,
                    air_temp=None,
                    wind_speed=None,
                    humidity=None,
                    solar_radiation=None,
                    source_type="observed",
                )

            row_by_timestamp[timestamp] = row
            if index % 240 == 0 or index == len(timestamps):
                print(f"  collected {index}/{len(timestamps)} rows", flush=True)

    if failed_timestamps:
        print(f"Retrying {len(failed_timestamps)} failed timestamps sequentially", flush=True)
        for index, timestamp in enumerate(failed_timestamps, start=1):
            try:
                row_by_timestamp[timestamp] = fetch_hourly_row(
                    city,
                    station_id,
                    api_key,
                    timestamp,
                    timeout_sec,
                    max(1, retries),
                )
            except Exception:  # noqa: BLE001
                pass

            if index % 120 == 0 or index == len(failed_timestamps):
                print(f"  retried {index}/{len(failed_timestamps)} failed rows", flush=True)

    return [row_by_timestamp[timestamp] for timestamp in sorted(row_by_timestamp)]


def weather_row_to_csv(row: WeatherRow) -> dict[str, str | int | float]:
    return {
        "datetime": row.timestamp.strftime("%Y-%m-%dT%H:00:00"),
        "city_code": row.city_code,
        "station_id": row.station_id,
        "air_temp": "" if row.air_temp is None else row.air_temp,
        "wind_speed": "" if row.wind_speed is None else row.wind_speed,
        "humidity": "" if row.humidity is None else row.humidity,
        "solar_radiation": "" if row.solar_radiation is None else row.solar_radiation,
        "source_type": row.source_type,
    }


def write_csv(path: Path, rows: Iterable[WeatherRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "datetime",
                "city_code",
                "station_id",
                "air_temp",
                "wind_speed",
                "humidity",
                "solar_radiation",
                "source_type",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(weather_row_to_csv(row))


def read_csv(path: Path) -> list[WeatherRow]:
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[WeatherRow] = []
        for record in reader:
            rows.append(
                WeatherRow(
                    timestamp=datetime.fromisoformat(record["datetime"]),
                    city_code=record["city_code"],
                    station_id=int(record["station_id"]),
                    air_temp=parse_optional_float(record.get("air_temp")),
                    wind_speed=parse_optional_float(record.get("wind_speed")),
                    humidity=parse_optional_float(record.get("humidity")),
                    solar_radiation=parse_optional_float(record.get("solar_radiation")),
                    source_type=record.get("source_type", "observed") or "observed",
                )
            )
        return rows


def fill_interior_gaps(values: list[float | None]) -> list[float]:
    if not values:
        return []

    filled = list(values)
    valid_indexes = [index for index, value in enumerate(filled) if value is not None]
    if not valid_indexes:
        return [0.0 for _ in filled]

    first_valid = valid_indexes[0]
    first_value = filled[first_valid]
    assert first_value is not None
    for index in range(0, first_valid):
        filled[index] = first_value

    for left_index, right_index in zip(valid_indexes, valid_indexes[1:]):
        left_value = filled[left_index]
        right_value = filled[right_index]
        assert left_value is not None
        assert right_value is not None
        gap = right_index - left_index
        if gap > 1:
            for offset in range(1, gap):
                ratio = offset / gap
                filled[left_index + offset] = left_value + (right_value - left_value) * ratio

    last_valid = valid_indexes[-1]
    last_value = filled[last_valid]
    assert last_value is not None
    for index in range(last_valid + 1, len(filled)):
        filled[index] = last_value

    return [0.0 if value is None else float(value) for value in filled]


def prepare_training_rows(rows: list[WeatherRow]) -> list[WeatherRow]:
    cutoff_index = -1
    for index, row in enumerate(rows):
        if any(value is not None for value in (row.air_temp, row.wind_speed, row.humidity)):
            cutoff_index = index

    if cutoff_index < 0:
        raise ValueError("No observed rows available for forecasting")

    observed_rows = rows[: cutoff_index + 1]
    air_temp = fill_interior_gaps([row.air_temp for row in observed_rows])
    wind_speed = fill_interior_gaps([row.wind_speed for row in observed_rows])
    humidity = fill_interior_gaps([row.humidity for row in observed_rows])
    solar_radiation = fill_interior_gaps([row.solar_radiation for row in observed_rows])

    cleaned_rows: list[WeatherRow] = []
    for index, row in enumerate(observed_rows):
        cleaned_rows.append(
            WeatherRow(
                timestamp=row.timestamp,
                city_code=row.city_code,
                station_id=row.station_id,
                air_temp=round(air_temp[index], 1),
                wind_speed=round(wind_speed[index], 1),
                humidity=round(humidity[index], 1),
                solar_radiation=round(solar_radiation[index], 1),
                source_type=row.source_type,
            )
        )
    return cleaned_rows


def get_value(record_by_time: dict[datetime, WeatherRow], target: datetime, field: str) -> float | None:
    row = record_by_time.get(target)
    if row is None:
        return None
    return getattr(row, field)


def mean(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def weighted_average(values: list[tuple[float | None, float]]) -> float | None:
    valid = [(value, weight) for value, weight in values if value is not None]
    if not valid:
        return None
    total_weight = sum(weight for _, weight in valid)
    return sum(value * weight for value, weight in valid) / total_weight


def get_recent_same_hour_values(
    record_by_time: dict[datetime, WeatherRow],
    target: datetime,
    field: str,
    *,
    day_step: int,
    count: int,
) -> list[float | None]:
    values: list[float | None] = []
    for multiplier in range(1, count + 1):
        values.append(get_value(record_by_time, target - timedelta(days=day_step * multiplier), field))
    return values


def estimate_scalar_field(
    record_by_time: dict[datetime, WeatherRow],
    target: datetime,
    field: str,
) -> float:
    last_hour = get_value(record_by_time, target - timedelta(hours=1), field)
    lag_24 = get_value(record_by_time, target - timedelta(hours=24), field)
    lag_48 = get_value(record_by_time, target - timedelta(hours=48), field)
    lag_168 = get_value(record_by_time, target - timedelta(hours=168), field)
    same_hour_3 = mean(get_recent_same_hour_values(record_by_time, target, field, day_step=1, count=3))
    same_hour_14 = mean(get_recent_same_hour_values(record_by_time, target, field, day_step=1, count=14))

    trend_sources = [
        get_value(record_by_time, target - timedelta(hours=offset), field)
        for offset in range(1, 7)
    ]
    trend = 0.0
    if all(value is not None for value in trend_sources[:3]):
        trend = ((trend_sources[0] or 0.0) - (trend_sources[2] or 0.0)) / 2.0

    estimate = weighted_average(
        [
            (lag_24, 0.42),
            (lag_48, 0.18),
            (lag_168, 0.18),
            (same_hour_3, 0.12),
            (same_hour_14, 0.06),
            (last_hour, 0.04),
        ]
    )
    if estimate is None:
        estimate = mean([lag_24, lag_48, lag_168, same_hour_14, last_hour]) or 0.0

    if field == "air_temp":
        estimate += clamp(trend * 0.25, -1.8, 1.8)
    elif field == "humidity":
        estimate -= clamp(trend * 0.9, -4.0, 4.0)
    elif field == "wind_speed":
        estimate += clamp(trend * 0.08, -0.6, 0.6)

    lower, upper = FIELD_LIMITS[field]
    return round(clamp(estimate, lower, upper), 1)


def estimate_solar_radiation(record_by_time: dict[datetime, WeatherRow], target: datetime) -> float:
    daylight_factor = max(0.0, math.sin(((target.hour - 6) / 12.0) * math.pi))
    if daylight_factor == 0.0:
        return 0.0

    lag_24 = get_value(record_by_time, target - timedelta(hours=24), "solar_radiation")
    lag_48 = get_value(record_by_time, target - timedelta(hours=48), "solar_radiation")
    lag_168 = get_value(record_by_time, target - timedelta(hours=168), "solar_radiation")
    same_hour_14 = mean(get_recent_same_hour_values(record_by_time, target, "solar_radiation", day_step=1, count=14))

    estimate = weighted_average(
        [
            (lag_24, 0.5),
            (lag_48, 0.2),
            (lag_168, 0.2),
            (same_hour_14, 0.1),
        ]
    )
    if estimate is None:
        estimate = 850.0 * daylight_factor

    return round(clamp(estimate * daylight_factor, 0.0, FIELD_LIMITS["solar_radiation"][1]), 1)


def build_forecast_rows(rows: list[WeatherRow], forecast_hours: int) -> list[WeatherRow]:
    training_rows = prepare_training_rows(rows)
    record_by_time = {row.timestamp: row for row in training_rows}
    last_observed = training_rows[-1]
    current_time = last_observed.timestamp
    forecast_rows: list[WeatherRow] = []

    for _ in range(forecast_hours):
        current_time += timedelta(hours=1)
        air_temp = estimate_scalar_field(record_by_time, current_time, "air_temp")
        wind_speed = estimate_scalar_field(record_by_time, current_time, "wind_speed")
        humidity = estimate_scalar_field(record_by_time, current_time, "humidity")
        prior_day_temp = get_value(record_by_time, current_time - timedelta(hours=24), "air_temp")
        if prior_day_temp is not None:
            humidity = round(
                clamp(humidity - clamp((air_temp - prior_day_temp) * 1.4, -5.0, 5.0), *FIELD_LIMITS["humidity"]),
                1,
            )
        humidity = round(
            clamp(humidity, *FIELD_LIMITS["humidity"]),
            1,
        )
        solar_radiation = estimate_solar_radiation(record_by_time, current_time)

        forecast_row = WeatherRow(
            timestamp=current_time,
            city_code=last_observed.city_code,
            station_id=last_observed.station_id,
            air_temp=air_temp,
            wind_speed=wind_speed,
            humidity=humidity,
            solar_radiation=solar_radiation,
            source_type="forecast",
        )
        forecast_rows.append(forecast_row)
        record_by_time[current_time] = forecast_row

    return forecast_rows


def main() -> None:
    args = parse_args()
    city = args.city.strip().lower()
    if city not in CITY_CONFIGS:
        raise KeyError(f"Unsupported city: {city}")

    city_config = CITY_CONFIGS[city]
    station_id = args.station_id or city_config.weather_station_id
    if station_id is None:
        raise ValueError(f"No weather station configured for city: {city}")

    history_path = build_output_path(city, args.history_out, "hourly")
    forecast_path = build_output_path(city, args.forecast_out, "forecast")

    history_rows: list[WeatherRow] = []

    if args.mode in {"history", "all"}:
        if not args.api_key:
            raise ValueError("KMA API key is required. Pass --api-key or set KMA_API_KEY.")
        history_rows = collect_history(
            city=city,
            station_id=station_id,
            api_key=args.api_key,
            start_date=args.start_date,
            end_date=args.end_date,
            max_workers=max(1, args.max_workers),
            timeout_sec=max(5, args.timeout_sec),
            retries=max(1, args.retries),
        )
        write_csv(history_path, history_rows)
        print(f"Saved observed history to {history_path.resolve()}", flush=True)

    if args.mode in {"forecast", "all"}:
        if not history_rows:
            if not history_path.exists():
                raise FileNotFoundError(f"History CSV not found: {history_path}")
            history_rows = read_csv(history_path)

        forecast_rows = build_forecast_rows(history_rows, max(1, args.forecast_hours))
        write_csv(forecast_path, forecast_rows)
        print(f"Saved forecast horizon to {forecast_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
