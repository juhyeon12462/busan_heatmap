from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import CITY_CONFIGS, CURRENT_DATE, SUPPORTED_DATE_END, SUPPORTED_DATE_START
from backend.app.service import build_synthetic_weather_baseline, load_district_profiles


@dataclass(frozen=True)
class WeatherSample:
    air_temp: float | None
    wind_speed: float | None
    humidity: float | None
    solar_radiation: float | None


STATION_NAMES = {
    159: "부산",
    296: "북부산",
}
REQUIRED_STATION_IDS = (159, 296)

REQUIRED_COLUMNS = {
    "지점",
    "일시",
    "기온(°C)",
    "풍속(m/s)",
    "습도(%)",
    "일사(MJ/m2)",
}

# 북부산(296) 실측을 직접 쓰는 구와 혼합 적용 구만 별도 지정한다.
DISTRICT_STATION_WEIGHTS: dict[str, list[tuple[int, float]]] = {
    "2632": [(296, 1.0)],  # 북구
    "2644": [(296, 1.0)],  # 강서구
    "2653": [(296, 0.7), (159, 0.3)],  # 사상구
}


@dataclass(frozen=True)
class ImportSummary:
    city: str
    input_paths: tuple[Path, ...]
    stations_found: tuple[int, ...]
    observed_start: datetime
    observed_end: datetime
    city_history_path: Path
    district_history_path: Path
    district_forecast_path: Path
    city_history_rows: int
    district_history_rows: int
    district_forecast_rows: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import downloaded Busan observation CSVs and rebuild district weather CSVs")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="Downloaded KMA observation CSV file paths",
    )
    parser.add_argument("--city", default="busan")
    return parser.parse_args()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    last_error: Exception | None = None
    for encoding in ("cp949", "utf-8-sig", "euc-kr", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                fieldnames = [name.strip() for name in (reader.fieldnames or []) if name]
                missing = REQUIRED_COLUMNS - set(fieldnames)
                if missing:
                    raise ValueError(f"CSV is missing required columns {sorted(missing)}: {path}")
                return [dict(row) for row in reader]
        except UnicodeDecodeError as error:
            last_error = error
        except ValueError as error:
            last_error = error
            break

    if last_error is not None:
        raise last_error
    raise ValueError(f"Failed to read CSV: {path}")


def parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def mj_to_watts_per_square_meter(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 277.778, 1)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def weighted_average(pairs: list[tuple[float | None, float]]) -> float | None:
    valid = [(value, weight) for value, weight in pairs if value is not None and weight > 0]
    if not valid:
        return None
    total_weight = sum(weight for _, weight in valid)
    return sum(value * weight for value, weight in valid) / total_weight


def load_station_samples(paths: list[Path]) -> dict[int, dict[datetime, WeatherSample]]:
    station_samples: dict[int, dict[datetime, WeatherSample]] = defaultdict(dict)

    for path in paths:
        for row in load_csv_rows(path):
            station_id = int(row["지점"])
            if station_id not in STATION_NAMES:
                continue

            timestamp = datetime.strptime(row["일시"], "%Y-%m-%d %H:%M")
            solar_radiation = mj_to_watts_per_square_meter(parse_optional_float(row.get("일사(MJ/m2)")))
            if solar_radiation is None and (timestamp.hour <= 6 or timestamp.hour >= 19):
                solar_radiation = 0.0

            station_samples[station_id][timestamp] = WeatherSample(
                air_temp=parse_optional_float(row.get("기온(°C)")),
                wind_speed=parse_optional_float(row.get("풍속(m/s)")),
                humidity=parse_optional_float(row.get("습도(%)")),
                solar_radiation=solar_radiation,
            )

    return dict(station_samples)


def load_city_forecast(path: Path) -> dict[datetime, WeatherSample]:
    forecast: dict[datetime, WeatherSample] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = datetime.fromisoformat(row["datetime"])
            forecast[timestamp] = WeatherSample(
                air_temp=parse_optional_float(row.get("air_temp")),
                wind_speed=parse_optional_float(row.get("wind_speed")),
                humidity=parse_optional_float(row.get("humidity")),
                solar_radiation=parse_optional_float(row.get("solar_radiation")),
            )
    return forecast


def write_city_history_csv(path: Path, city: str, station_samples: dict[int, dict[datetime, WeatherSample]]) -> None:
    rows: list[dict[str, object]] = []
    for timestamp, sample in sorted(station_samples[159].items()):
        rows.append(
            {
                "datetime": timestamp.strftime("%Y-%m-%dT%H:00:00"),
                "city_code": city,
                "station_id": 159,
                "air_temp": "" if sample.air_temp is None else round(sample.air_temp, 1),
                "wind_speed": "" if sample.wind_speed is None else round(sample.wind_speed, 1),
                "humidity": "" if sample.humidity is None else round(sample.humidity, 1),
                "solar_radiation": "" if sample.solar_radiation is None else round(sample.solar_radiation, 1),
                "source_type": "observed",
            }
        )

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
        writer.writerows(rows)


def get_profile_means(districts) -> tuple[float, float, float, float]:
    count = max(len(districts), 1)
    return (
        sum(item.building_density for item in districts) / count,
        sum(item.ndvi_mean for item in districts) / count,
        sum(item.area_ratio_urban for item in districts) / count,
        sum(item.area_ratio_green for item in districts) / count,
    )


def district_station_weights(district_code: str) -> list[tuple[int, float]]:
    return DISTRICT_STATION_WEIGHTS.get(district_code, [(159, 1.0)])


def compute_district_adjustment(district, profile_means: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    avg_building, avg_ndvi, avg_urban, avg_green = profile_means
    urban_anomaly = district.building_density - avg_building
    green_anomaly = district.ndvi_mean - avg_ndvi
    urban_cover_anomaly = district.area_ratio_urban - avg_urban
    green_cover_anomaly = district.area_ratio_green - avg_green

    air_offset = urban_anomaly * 2.5 - green_anomaly * 1.7 + urban_cover_anomaly * 0.8
    humidity_offset = green_anomaly * 12.0 - urban_anomaly * 8.5 + green_cover_anomaly * 4.0
    wind_factor = clamp(1.0 - district.building_density * 0.17 + district.ndvi_mean * 0.06, 0.72, 1.18)
    solar_factor = clamp(1.0 + district.area_ratio_urban * 0.05 - district.area_ratio_green * 0.04, 0.9, 1.08)
    return air_offset, humidity_offset, wind_factor, solar_factor


def describe_weights(weights: list[tuple[int, float]]) -> str:
    return ", ".join(f"{STATION_NAMES[station_id]} {int(weight * 100)}%" for station_id, weight in weights)


def make_weighted_station_sample(
    station_samples: dict[int, dict[datetime, WeatherSample]],
    weights: list[tuple[int, float]],
    timestamp: datetime,
) -> WeatherSample | None:
    air_temp = weighted_average(
        [(station_samples.get(station_id, {}).get(timestamp, WeatherSample(None, None, None, None)).air_temp, weight) for station_id, weight in weights]
    )
    wind_speed = weighted_average(
        [(station_samples.get(station_id, {}).get(timestamp, WeatherSample(None, None, None, None)).wind_speed, weight) for station_id, weight in weights]
    )
    humidity = weighted_average(
        [(station_samples.get(station_id, {}).get(timestamp, WeatherSample(None, None, None, None)).humidity, weight) for station_id, weight in weights]
    )
    solar_radiation = weighted_average(
        [(station_samples.get(station_id, {}).get(timestamp, WeatherSample(None, None, None, None)).solar_radiation, weight) for station_id, weight in weights]
    )

    if all(value is None for value in (air_temp, wind_speed, humidity, solar_radiation)):
        return None

    return WeatherSample(air_temp=air_temp, wind_speed=wind_speed, humidity=humidity, solar_radiation=solar_radiation)


def build_history_rows(
    city: str,
    station_samples: dict[int, dict[datetime, WeatherSample]],
    districts,
    history_start: datetime,
    history_end: datetime,
) -> tuple[list[dict[str, object]], dict[str, dict[datetime, WeatherSample]]]:
    rows: list[dict[str, object]] = []
    district_series: dict[str, dict[datetime, WeatherSample]] = {district.district_code: {} for district in districts}
    profile_means = get_profile_means(districts)
    current = history_start

    while current <= history_end:
        for district in districts:
            weights = district_station_weights(district.district_code)
            base_sample = make_weighted_station_sample(station_samples, weights, current)
            if base_sample is None:
                continue

            air_offset, humidity_offset, wind_factor, solar_factor = compute_district_adjustment(district, profile_means)
            sample = WeatherSample(
                air_temp=None if base_sample.air_temp is None else round(clamp(base_sample.air_temp + air_offset, -25.0, 45.0), 1),
                wind_speed=None
                if base_sample.wind_speed is None
                else round(clamp(base_sample.wind_speed * wind_factor, 0.3, 20.0), 1),
                humidity=None
                if base_sample.humidity is None
                else round(clamp(base_sample.humidity + humidity_offset, 20.0, 100.0), 1),
                solar_radiation=None
                if base_sample.solar_radiation is None
                else round(clamp(base_sample.solar_radiation * solar_factor, 0.0, 1200.0), 1),
            )
            district_series[district.district_code][current] = sample
            rows.append(
                {
                    "datetime": current.strftime("%Y-%m-%dT%H:00:00"),
                    "city_code": city,
                    "district_code": district.district_code,
                    "district_name_ko": district.district_name_ko,
                    "station_id": weights[0][0],
                    "air_temp": "" if sample.air_temp is None else sample.air_temp,
                    "wind_speed": "" if sample.wind_speed is None else sample.wind_speed,
                    "humidity": "" if sample.humidity is None else sample.humidity,
                    "solar_radiation": "" if sample.solar_radiation is None else sample.solar_radiation,
                    "source_type": "observed",
                    "source_detail": f"KMA 실관측 ({describe_weights(weights)}) + 구별 공간보정",
                }
            )
        current += timedelta(hours=1)

    return rows, district_series


def compute_hourly_biases(
    district_series: dict[str, dict[datetime, WeatherSample]],
    city_series: dict[datetime, WeatherSample],
    *,
    lookback_days: int = 60,
) -> tuple[dict[str, list[float]], dict[str, list[float]], dict[str, list[float]], dict[str, list[float]]]:
    end_dt = max(city_series)
    start_dt = end_dt - timedelta(days=lookback_days)
    temp_biases: dict[str, list[list[float]]] = {}
    humidity_biases: dict[str, list[list[float]]] = {}
    wind_biases: dict[str, list[list[float]]] = {}
    solar_ratios: dict[str, list[list[float]]] = {}

    for district_code in district_series:
        temp_biases[district_code] = [[] for _ in range(24)]
        humidity_biases[district_code] = [[] for _ in range(24)]
        wind_biases[district_code] = [[] for _ in range(24)]
        solar_ratios[district_code] = [[] for _ in range(24)]

    for district_code, samples in district_series.items():
        for timestamp, district_sample in samples.items():
            if timestamp < start_dt:
                continue
            city_sample = city_series.get(timestamp)
            if city_sample is None:
                continue
            hour = timestamp.hour
            if district_sample.air_temp is not None and city_sample.air_temp is not None:
                temp_biases[district_code][hour].append(district_sample.air_temp - city_sample.air_temp)
            if district_sample.humidity is not None and city_sample.humidity is not None:
                humidity_biases[district_code][hour].append(district_sample.humidity - city_sample.humidity)
            if district_sample.wind_speed is not None and city_sample.wind_speed is not None:
                wind_biases[district_code][hour].append(district_sample.wind_speed - city_sample.wind_speed)
            if (
                district_sample.solar_radiation is not None
                and city_sample.solar_radiation is not None
                and city_sample.solar_radiation > 0
            ):
                solar_ratios[district_code][hour].append(district_sample.solar_radiation / city_sample.solar_radiation)

    def finalize(container: dict[str, list[list[float]]], default: float) -> dict[str, list[float]]:
        return {
            district_code: [round(sum(values) / len(values), 3) if values else default for values in hour_values]
            for district_code, hour_values in container.items()
        }

    return (
        finalize(temp_biases, 0.0),
        finalize(humidity_biases, 0.0),
        finalize(wind_biases, 0.0),
        finalize(solar_ratios, 1.0),
    )


def build_forecast_rows(
    city: str,
    districts,
    city_series: dict[datetime, WeatherSample],
    city_forecast: dict[datetime, WeatherSample],
    district_series: dict[str, dict[datetime, WeatherSample]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    temp_bias, humidity_bias, wind_bias, solar_ratio = compute_hourly_biases(district_series, city_series)

    current = datetime.combine(CURRENT_DATE, dt_time(hour=0))
    forecast_end = datetime.combine(SUPPORTED_DATE_END, dt_time(hour=23))

    while current <= forecast_end:
        base_forecast = city_forecast.get(current)
        source_type = "forecast"
        source_detail = "KMA 부산 시예보 + 구별 실측 편차 보정"

        if base_forecast is None:
            synthetic = build_synthetic_weather_baseline(current.date(), current.hour)
            base_forecast = WeatherSample(
                air_temp=synthetic.air_temp,
                wind_speed=synthetic.wind_speed,
                humidity=synthetic.humidity,
                solar_radiation=synthetic.solar_radiation,
            )
            source_type = "simulated"
            source_detail = "KMA 시예보 없음 · 합성기상 + 구별 실측 편차 보정"

        for district in districts:
            hour = current.hour
            weights = district_station_weights(district.district_code)

            solar_base = base_forecast.solar_radiation
            if solar_base is None:
                solar_base = build_synthetic_weather_baseline(current.date(), current.hour).solar_radiation

            forecast_sample = WeatherSample(
                air_temp=None
                if base_forecast.air_temp is None
                else round(clamp(base_forecast.air_temp + temp_bias[district.district_code][hour], -25.0, 45.0), 1),
                wind_speed=None
                if base_forecast.wind_speed is None
                else round(clamp(base_forecast.wind_speed + wind_bias[district.district_code][hour], 0.3, 20.0), 1),
                humidity=None
                if base_forecast.humidity is None
                else round(clamp(base_forecast.humidity + humidity_bias[district.district_code][hour], 20.0, 100.0), 1),
                solar_radiation=None
                if solar_base is None
                else round(
                    clamp(
                        solar_base * solar_ratio[district.district_code][hour],
                        0.0,
                        1200.0,
                    ),
                    1,
                ),
            )

            rows.append(
                {
                    "datetime": current.strftime("%Y-%m-%dT%H:00:00"),
                    "city_code": city,
                    "district_code": district.district_code,
                    "district_name_ko": district.district_name_ko,
                    "station_id": weights[0][0],
                    "air_temp": "" if forecast_sample.air_temp is None else forecast_sample.air_temp,
                    "wind_speed": "" if forecast_sample.wind_speed is None else forecast_sample.wind_speed,
                    "humidity": "" if forecast_sample.humidity is None else forecast_sample.humidity,
                    "solar_radiation": "" if forecast_sample.solar_radiation is None else forecast_sample.solar_radiation,
                    "source_type": source_type,
                    "source_detail": source_detail,
                }
            )
        current += timedelta(hours=1)

    return rows


def write_district_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def import_observation_csvs(city: str, input_paths: list[Path]) -> ImportSummary:
    city_key = city.strip().lower()
    if city_key not in CITY_CONFIGS:
        raise KeyError(f"Unsupported city: {city_key}")

    normalized_paths = [path.resolve() for path in input_paths]
    if not normalized_paths:
        raise ValueError("At least one input CSV is required")

    city_config = CITY_CONFIGS[city_key]
    station_samples = load_station_samples(normalized_paths)

    missing_station_ids = [station_id for station_id in REQUIRED_STATION_IDS if station_id not in station_samples]
    if missing_station_ids:
        missing_names = ", ".join(f"{station_id} {STATION_NAMES[station_id]}" for station_id in missing_station_ids)
        raise ValueError(f"Downloaded CSVs are missing required stations: {missing_names}")

    write_city_history_csv(city_config.weather_csv_path, city_key, station_samples)

    districts = load_district_profiles(city_key)
    history_start = datetime.combine(SUPPORTED_DATE_START, dt_time(hour=0))
    observed_end = max(station_samples[159])
    history_end = min(observed_end, datetime.combine(CURRENT_DATE, dt_time(hour=23)))
    history_rows, district_series = build_history_rows(city_key, station_samples, districts, history_start, history_end)

    city_series = station_samples[159]
    city_forecast = load_city_forecast(city_config.weather_forecast_csv_path)
    forecast_rows = build_forecast_rows(city_key, districts, city_series, city_forecast, district_series)

    write_district_csv(city_config.district_weather_csv_path, history_rows)
    write_district_csv(city_config.district_weather_forecast_csv_path, forecast_rows)

    return ImportSummary(
        city=city_key,
        input_paths=tuple(normalized_paths),
        stations_found=tuple(sorted(station_samples)),
        observed_start=min(station_samples[159]),
        observed_end=observed_end,
        city_history_path=city_config.weather_csv_path,
        district_history_path=city_config.district_weather_csv_path,
        district_forecast_path=city_config.district_weather_forecast_csv_path,
        city_history_rows=len(station_samples[159]),
        district_history_rows=len(history_rows),
        district_forecast_rows=len(forecast_rows),
    )


def main() -> None:
    args = parse_args()
    summary = import_observation_csvs(args.city, [Path(path) for path in args.input])

    print(f"Imported observation CSVs for {summary.city}:")
    print(f"  input files: {len(summary.input_paths)}")
    print(f"  stations found: {', '.join(str(station_id) for station_id in summary.stations_found)}")
    print(
        "  observed range: "
        f"{summary.observed_start.strftime('%Y-%m-%d %H:%M')} ~ {summary.observed_end.strftime('%Y-%m-%d %H:%M')}"
    )
    print(f"Saved city history CSV to {summary.city_history_path}")
    print(f"Saved {summary.district_history_rows} district history rows to {summary.district_history_path}")
    print(f"Saved {summary.district_forecast_rows} district forecast rows to {summary.district_forecast_path}")


if __name__ == "__main__":
    main()
