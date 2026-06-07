from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import CITY_CONFIGS, PROVIDED_DATA_DIR, SUPPORTED_DATE_END, SUPPORTED_DATE_START

MISSING_VALUES = {"", "-9", "-9.0", "-9.00", "-99", "-99.0", "-99.00"}
OBSERVATION_INDEX = {
    "wind_speed": 3,
    "air_temp": 11,
    "humidity": 13,
    "solar_mj": 34,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch KMA hourly weather observations and save them as CSV")
    parser.add_argument("--city", default="busan")
    parser.add_argument("--station-id", type=int, default=None)
    parser.add_argument("--start-date", default=SUPPORTED_DATE_START.isoformat())
    parser.add_argument("--end-date", default=SUPPORTED_DATE_END.isoformat())
    parser.add_argument("--api-key", default=os.environ.get("KMA_API_KEY"))
    parser.add_argument("--out-path", default=None)
    parser.add_argument("--delay-ms", type=int, default=120)
    parser.add_argument("--incremental", action="store_true", help="기존 CSV 마지막 날짜 이후 데이터만 추가 수집")
    return parser.parse_args()


def build_output_path(city: str, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path)
    return PROVIDED_DATA_DIR / f"weather_hourly_{city}.csv"


def get_last_datetime_in_csv(path: Path) -> datetime | None:
    """CSV 파일의 마지막 datetime 값을 반환."""
    if not path.exists():
        return None
    last_dt = None
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dt_str = row.get("datetime", "").strip()
            if dt_str:
                try:
                    last_dt = datetime.fromisoformat(dt_str)
                except ValueError:
                    pass
    return last_dt


def iter_hourly_range(start_date: str, end_date: str) -> list[datetime]:
    start = datetime.combine(date.fromisoformat(start_date), dt_time(hour=0))
    end = datetime.combine(date.fromisoformat(end_date), dt_time(hour=23))

    if start > end:
        raise ValueError("start-date must be earlier than or equal to end-date")

    hours: list[datetime] = []
    current = start
    while current <= end:
        hours.append(current)
        current += timedelta(hours=1)

    return hours


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


def find_payload_line(response_text: str) -> str | None:
    for line in response_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


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


def to_watts_per_square_meter(solar_mj: float | None) -> float | None:
    if solar_mj is None:
        return None
    return round(solar_mj * 277.778, 1)


def fetch_hourly_observation(api_key: str, station_id: int, city: str, timestamp: datetime) -> dict[str, object]:
    request_url = build_request_url(api_key, station_id, timestamp)

    with urlopen(request_url, timeout=20) as response:
        response_text = response.read().decode("utf-8", errors="ignore")

    payload_line = find_payload_line(response_text)
    if payload_line is None:
        return {
            "datetime": timestamp.strftime("%Y-%m-%dT%H:00:00"),
            "city_code": city,
            "station_id": station_id,
            "air_temp": "",
            "wind_speed": "",
            "humidity": "",
            "solar_radiation": "",
            "source_type": "observed",
        }

    parts = payload_line.split()
    if len(parts) <= OBSERVATION_INDEX["solar_mj"]:
        raise ValueError(f"Unexpected response format for {timestamp.isoformat()}: {payload_line}")

    air_temp = parse_optional_float(parts[OBSERVATION_INDEX["air_temp"]])
    wind_speed = parse_optional_float(parts[OBSERVATION_INDEX["wind_speed"]])
    humidity = parse_optional_float(parts[OBSERVATION_INDEX["humidity"]])
    solar_radiation = to_watts_per_square_meter(parse_optional_float(parts[OBSERVATION_INDEX["solar_mj"]]))

    return {
        "datetime": timestamp.strftime("%Y-%m-%dT%H:00:00"),
        "city_code": city,
        "station_id": station_id,
        "air_temp": "" if air_temp is None else round(air_temp, 1),
        "wind_speed": "" if wind_speed is None else round(wind_speed, 1),
        "humidity": "" if humidity is None else round(humidity, 1),
        "solar_radiation": "" if solar_radiation is None else solar_radiation,
        "source_type": "observed",
    }


def append_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """기존 CSV에 행 추가 (없으면 새로 생성)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "datetime", "city_code", "station_id",
                "air_temp", "wind_speed", "humidity",
                "solar_radiation", "source_type",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "datetime", "city_code", "station_id",
                "air_temp", "wind_speed", "humidity",
                "solar_radiation", "source_type",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def run_incremental(api_key: str, city: str, station_id: int, out_path: Path, delay_ms: int) -> None:
    """CSV 마지막 시각 이후 현재까지 데이터만 추가 수집."""
    last_dt = get_last_datetime_in_csv(out_path)
    now = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    if last_dt is None:
        print("기존 CSV 없음. 전체 수집을 시작합니다.")
        start_dt = datetime.combine(SUPPORTED_DATE_START, dt_time(hour=0))
    else:
        start_dt = last_dt + timedelta(hours=1)

    if start_dt > now:
        print(f"이미 최신 데이터입니다. (마지막: {last_dt})")
        return

    timestamps = []
    current = start_dt
    while current <= now:
        timestamps.append(current)
        current += timedelta(hours=1)

    print(f"신규 {len(timestamps)}시간 데이터 수집 중... ({start_dt} ~ {now})")

    rows = []
    for index, timestamp in enumerate(timestamps, start=1):
        rows.append(fetch_hourly_observation(api_key, station_id, city, timestamp))
        if index % 24 == 0 or index == len(timestamps):
            print(f"  {index}/{len(timestamps)} hours collected")
        if delay_ms > 0 and index < len(timestamps):
            time.sleep(delay_ms / 1000)

    append_csv(out_path, rows)
    print(f"완료: {out_path.resolve()}")


def main() -> None:
    args = parse_args()
    city = args.city.strip().lower()

    if city not in CITY_CONFIGS:
        raise KeyError(f"Unsupported city: {city}")

    city_config = CITY_CONFIGS[city]
    station_id = args.station_id or getattr(city_config, 'weather_station_id', None) or 159
    if not args.api_key:
        raise ValueError("KMA API key is required. Pass --api-key or set KMA_API_KEY.")

    out_path = build_output_path(city, args.out_path)

    if args.incremental:
        run_incremental(args.api_key, city, station_id, out_path, args.delay_ms)
        return

    timestamps = iter_hourly_range(args.start_date, args.end_date)
    rows: list[dict[str, object]] = []

    print(
        f"Fetching {len(timestamps)} hourly observations for {city} "
        f"({args.start_date} to {args.end_date}) from station {station_id}"
    )

    for index, timestamp in enumerate(timestamps, start=1):
        rows.append(fetch_hourly_observation(args.api_key, station_id, city, timestamp))
        if index % 24 == 0 or index == len(timestamps):
            print(f"  {index}/{len(timestamps)} hours collected")
        if args.delay_ms > 0 and index < len(timestamps):
            time.sleep(args.delay_ms / 1000)

    write_csv(out_path, rows)
    print(f"Saved hourly weather CSV to {out_path.resolve()}")


if __name__ == "__main__":
    main()
