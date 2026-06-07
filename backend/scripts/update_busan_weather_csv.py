from __future__ import annotations

import argparse
import glob
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import APP_PUBLIC_DATA_DIR, CURRENT_DATE, SUPPORTED_HOURS, SUPPORTED_SCENARIOS
from backend.app.service import export_static_bundle
from backend.scripts.import_busan_observation_csv import ImportSummary, import_observation_csvs

DIST_DATA_DIR = ROOT_DIR / "app" / "dist" / "data"
DEFAULT_INPUT_DIR = ROOT_DIR / "update_input" / "busan_observation_csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild Busan weather CSVs from downloaded observation CSVs and refresh static JSON"
    )
    parser.add_argument("--city", default="busan")
    parser.add_argument(
        "--input",
        nargs="+",
        default=None,
        help=(
            "CSV files, directories, or glob patterns containing downloaded observation CSVs. "
            "If omitted, the dedicated project folder is used."
        ),
    )
    parser.add_argument("--pattern", default="OBS_ASOS_TIM*.csv", help="Filename pattern to scan inside input directories")
    parser.add_argument(
        "--static-date",
        default=None,
        help="Fallback JSON export date in YYYY-MM-DD format. Defaults to the current date.",
    )
    parser.add_argument("--static-days", type=int, default=1, help="Number of consecutive dates to export for static JSON")
    parser.add_argument(
        "--hours",
        default=",".join(str(hour) for hour in SUPPORTED_HOURS),
        help="Comma-separated hour list to export for static JSON",
    )
    parser.add_argument("--skip-static", action="store_true", help="Skip static JSON export")
    parser.add_argument("--skip-dist-sync", action="store_true", help="Skip app/dist/data export even if the folder exists")
    return parser.parse_args()


def resolve_input_paths(raw_inputs: list[str], pattern: str) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()

    for raw_input in raw_inputs:
        candidate = Path(raw_input).expanduser()
        matches: list[Path] = []

        if any(token in raw_input for token in "*?[]"):
            matches = [Path(path) for path in glob.glob(raw_input)]
        elif candidate.is_dir():
            matches = sorted(candidate.glob(pattern))
        elif candidate.is_file():
            matches = [candidate]

        if not matches:
            raise FileNotFoundError(f"No CSV files matched input: {raw_input}")

        for match in matches:
            resolved_match = match.resolve()
            if resolved_match in seen:
                continue
            if resolved_match.suffix.lower() != ".csv":
                continue
            seen.add(resolved_match)
            resolved.append(resolved_match)

    resolved.sort()
    if not resolved:
        raise ValueError("No CSV files were resolved from the provided --input values")
    return resolved


def parse_hours(raw_hours: str) -> list[int]:
    hours = sorted({int(value.strip()) for value in raw_hours.split(",") if value.strip()})
    if not hours:
        raise ValueError("At least one hour must be provided")
    invalid_hours = [hour for hour in hours if hour not in SUPPORTED_HOURS]
    if invalid_hours:
        raise ValueError(f"Unsupported hours: {invalid_hours}")
    return hours


def build_export_dates(start_date: str, days: int) -> list[str]:
    if days < 1:
        raise ValueError("--static-days must be at least 1")

    start = date.fromisoformat(start_date)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def export_static_outputs(city: str, dates: list[str], hours: list[int], *, sync_dist: bool) -> None:
    export_static_bundle(
        city=city,
        dates=dates,
        hours=hours,
        scenarios=SUPPORTED_SCENARIOS,  # type: ignore[arg-type]
        out_dir=APP_PUBLIC_DATA_DIR,
    )
    print(f"Updated static JSON in {APP_PUBLIC_DATA_DIR}")

    if sync_dist and DIST_DATA_DIR.parent.exists():
        export_static_bundle(
            city=city,
            dates=dates,
            hours=hours,
            scenarios=SUPPORTED_SCENARIOS,  # type: ignore[arg-type]
            out_dir=DIST_DATA_DIR,
        )
        print(f"Updated built static JSON in {DIST_DATA_DIR}")


def print_summary(summary: ImportSummary) -> None:
    print(f"Imported observation CSVs for {summary.city}")
    print(f"  input files: {len(summary.input_paths)}")
    print(f"  stations found: {', '.join(str(station_id) for station_id in summary.stations_found)}")
    print(
        "  observed range: "
        f"{summary.observed_start.strftime('%Y-%m-%d %H:%M')} ~ {summary.observed_end.strftime('%Y-%m-%d %H:%M')}"
    )
    print(f"  city history rows: {summary.city_history_rows}")
    print(f"  district history rows: {summary.district_history_rows}")
    print(f"  district forecast rows: {summary.district_forecast_rows}")
    print(f"  wrote: {summary.city_history_path}")
    print(f"  wrote: {summary.district_history_path}")
    print(f"  wrote: {summary.district_forecast_path}")


def main() -> None:
    args = parse_args()
    raw_inputs = args.input or [str(DEFAULT_INPUT_DIR)]
    if args.input is None:
        print(f"Using dedicated input folder: {DEFAULT_INPUT_DIR}")
    input_paths = resolve_input_paths(raw_inputs, args.pattern)
    summary = import_observation_csvs(args.city, input_paths)
    print_summary(summary)

    if args.skip_static:
        print("Skipped static JSON export")
        return

    static_date = args.static_date or CURRENT_DATE.isoformat()
    dates = build_export_dates(static_date, args.static_days)
    hours = parse_hours(args.hours)
    export_static_outputs(summary.city, dates, hours, sync_dist=not args.skip_dist_sync)
    print("If the backend server is already running, restart it to load the refreshed CSV files.")


if __name__ == "__main__":
    main()
