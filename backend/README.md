# Backend

부산시 2D 공간 데이터, 구별 기상 시계열, 블록별 LST 계산 로직을 제공하는 FastAPI 백엔드입니다. 현재 응답 구조는 `구 경계 + 블록별 2D` 기준이며 `past`, `current`, `future_7d` 시나리오를 지원합니다.

## 설치

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

## 실행

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 주요 API

- `GET /api/health`
- `GET /api/cities`
- `GET /api/spatial-units/busan`
- `GET /api/grid-master/busan`
- `GET /api/heatmap?city=busan&district=2632&scenario=current&date=2026-04-17&hour=15`

## 데이터 구조

입력 파일:

- `제공data/busan_density_NDVI.csv`
- `제공data/weather_hourly_busan.csv`
- `제공data/weather_hourly_busan_districts.csv`
- `제공data/weather_forecast_busan.csv`
- `제공data/weather_forecast_busan_districts.csv`

현재 지원 범위:

- 날짜: `2025-04-17 ~ 2026-04-24`
- 시간: `00:00 ~ 23:00`
- 시나리오:
  - `past`
  - `current`
  - `future_7d`

## 실측 CSV 반영

사용자 제공 ASOS 실측 CSV를 기준으로 도시/구별 기상 CSV를 다시 생성하려면:

```bash
.venv/bin/python backend/scripts/update_busan_weather_csv.py
```

자세한 사용법:

- [CSV_업데이트_가이드.md](/mnt/c/Users/hkodi/Desktop/윤한신/CSV_업데이트_가이드.md)
- 전용 입력 폴더: [update_input/busan_observation_csv](/mnt/c/Users/hkodi/Desktop/윤한신/update_input/busan_observation_csv)

이 스크립트는 다음 파일을 생성하거나 갱신합니다.

- `제공data/weather_hourly_busan.csv`
- `제공data/weather_hourly_busan_districts.csv`
- `제공data/weather_forecast_busan_districts.csv`
- `app/public/data/...`
- `app/dist/data/...` (`app/dist`가 있을 때)

## 정적 JSON 생성

프론트 fallback용 정적 JSON을 다시 생성하려면:

```bash
.venv/bin/python backend/scripts/export_static_data.py --city busan --start-date 2026-04-17 --days 1
```

## 검수

스택 검수:

```bash
.venv/bin/python backend/scripts/verify_stack.py
```

검수 항목:

- 백엔드 health/cities/heatmap 응답
- 구 선택 시 서로 다른 기상/블록 결과
- 미래 예측 응답 정상 여부
- 정적 산출물 존재 여부
