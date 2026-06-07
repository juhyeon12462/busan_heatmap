from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"
REMOVED_SOURCE_DETAIL_TEXT = "최근 7일 LST"


def fetch_text(url: str) -> str:
    try:
        with urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"{url} returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"{url} request failed: {error.reason}") from error


def fetch_json(url: str) -> dict[str, object]:
    return json.loads(fetch_text(url))


def heatmap_request(**params: str | int) -> dict[str, object]:
    query = urlencode(params)
    return fetch_json(f"{BACKEND_URL}/api/heatmap?{query}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_frontend_shell() -> list[str]:
    html = fetch_text(FRONTEND_URL)
    assert_true("<div id=\"root\"></div>" in html, "frontend HTML shell is missing root container")
    return ["frontend dev server reachable"]


def verify_health() -> list[str]:
    payload = fetch_json(f"{BACKEND_URL}/api/health")
    assert_true(payload.get("status") == "ok", "backend health endpoint did not return ok")
    return ["backend health ok"]


def verify_metadata() -> list[str]:
    payload = fetch_json(f"{BACKEND_URL}/api/cities")
    cities = payload.get("cities", [])
    assert_true(isinstance(cities, list) and len(cities) == 1, "cities metadata is unexpected")
    city = cities[0]
    districts = city.get("districts", [])
    assert_true(city.get("code") == "busan", "busan city metadata is missing")
    assert_true(len(districts) == 16, "district metadata should contain 16 districts")
    assert_true(payload.get("supportedScenarios") == ["past", "current", "future_7d"], "scenario metadata mismatch")
    return ["metadata ok", "16 districts exposed", "scenario list ok"]


def verify_district_weather_split() -> list[str]:
    north = heatmap_request(city="busan", district="2632", scenario="past", date="2026-04-16", hour=15)
    busanjin = heatmap_request(city="busan", district="2623", scenario="past", date="2026-04-16", hour=15)

    north_weather = north["weather"]
    busanjin_weather = busanjin["weather"]
    north_summary = north["summary"]
    busanjin_summary = busanjin["summary"]

    assert_true(north_weather["source_type"] == "observed", "north district should use observed weather for past scenario")
    assert_true(busanjin_weather["source_type"] == "observed", "busanjin district should use observed weather for past scenario")
    assert_true(north_summary["cell_count"] != busanjin_summary["cell_count"], "district block counts should differ")

    same_weather = (
        north_weather["air_temp"] == busanjin_weather["air_temp"]
        and north_weather["wind_speed"] == busanjin_weather["wind_speed"]
        and north_weather["humidity"] == busanjin_weather["humidity"]
        and north_weather["solar_radiation"] == busanjin_weather["solar_radiation"]
    )
    assert_true(not same_weather, "district-specific weather should differ between districts")
    return ["district-specific weather split ok"]


def verify_future_prediction() -> list[str]:
    payload = heatmap_request(city="busan", district="2632", scenario="future_7d", date="2026-04-23", hour=15)
    weather = payload["weather"]
    summary = payload["summary"]

    assert_true(weather["source_type"] in {"forecast", "simulated"}, "future scenario weather source is invalid")
    assert_true(REMOVED_SOURCE_DETAIL_TEXT not in (weather.get("source_detail") or ""), "removed future source text still exists")
    assert_true(summary["cell_count"] > 0, "future scenario returned no cells")
    return ["future_7d prediction ok", "future source_detail cleaned"]


def verify_static_outputs() -> list[str]:
    checks = [
        ROOT_DIR / "app" / "public" / "data" / "busan" / "current" / "2026-04-17" / "15.json",
        ROOT_DIR / "app" / "public" / "data" / "busan" / "future_7d" / "2026-04-17" / "15.json",
        ROOT_DIR / "app" / "dist" / "data" / "busan" / "current" / "2026-04-17" / "15.json",
        ROOT_DIR / "app" / "dist" / "data" / "busan" / "future_7d" / "2026-04-17" / "15.json",
    ]
    for path in checks:
        assert_true(path.exists(), f"missing static output: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_detail = (payload.get("weather") or {}).get("source_detail", "")
        assert_true(REMOVED_SOURCE_DETAIL_TEXT not in source_detail, f"stale source_detail text remains in {path}")
    return ["static public/dist data ok"]


def main() -> None:
    verifications = [
        ("frontend", verify_frontend_shell),
        ("health", verify_health),
        ("metadata", verify_metadata),
        ("district-weather", verify_district_weather_split),
        ("future", verify_future_prediction),
        ("static", verify_static_outputs),
    ]

    for label, verify in verifications:
        messages = verify()
        print(f"[PASS] {label}: " + ", ".join(messages))

    print("[PASS] overall: stack verification completed")


if __name__ == "__main__":
    main()
