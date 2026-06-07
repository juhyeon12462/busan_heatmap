# Frontend

부산 구 단위 도시열섬 대시보드 프론트엔드입니다. 좌측 `Control Panel`에서 시/구/날짜/시간/시나리오를 선택하면 우측 2D 지도와 블록 통계가 함께 갱신됩니다.

## 주요 화면 구성

- `시 선택 -> 구 선택`
- `과거 7일 평균 / 현재 / 미래 7일 예측`
- `구 경계 2D + 블록별 2D`
- 반응형 레이아웃
- `Control Panel` 내부 스크롤

## 실행

백엔드:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

프론트:

```bash
cd app
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Vite 개발 서버는 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시합니다.

## 빌드 / 린트

```bash
cd app
npm run lint
npm run build
```

## 데이터 공급 방식

- 우선: 백엔드 API
- fallback: `public/data` 정적 JSON

정적 JSON 생성:

```bash
.venv/bin/python backend/scripts/export_static_data.py --city busan --start-date 2026-04-17 --days 1
```

## 현재 사용 데이터

- 조회 범위: `2025-04-17 ~ 2026-04-24`
- 시나리오:
  - `past`
  - `current`
  - `future_7d`
- 대상 도시: `부산광역시`
