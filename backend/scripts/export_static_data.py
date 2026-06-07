from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import APP_PUBLIC_DATA_DIR, SUPPORTED_DATE_END, SUPPORTED_HOURS, SUPPORTED_SCENARIOS
from backend.app.service import export_static_bundle


def build_date_range(start_date: str, days: int) -> list[str]:
    anchor = date.fromisoformat(start_date)
    return [(anchor + timedelta(days=index)).isoformat() for index in range(days)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export heatmap JSON files for the frontend")
    parser.add_argument("--city", default="busan")
    parser.add_argument("--start-date", default=SUPPORTED_DATE_END.isoformat())
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--hours", default=",".join(str(hour) for hour in SUPPORTED_HOURS))
    parser.add_argument("--out-dir", default=str(APP_PUBLIC_DATA_DIR))
    args = parser.parse_args()

    dates = build_date_range(args.start_date, args.days)
    hours = [int(value.strip()) for value in args.hours.split(",") if value.strip()]

    export_static_bundle(
        city=args.city,
        dates=dates,
        hours=hours,
        scenarios=SUPPORTED_SCENARIOS,  # type: ignore[arg-type]
        out_dir=Path(args.out_dir),
    )

    print(f"Exported static heatmap bundle to {Path(args.out_dir).resolve()}")


if __name__ == "__main__":
    main()
