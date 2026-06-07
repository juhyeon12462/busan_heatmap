## Frontend Info

- Runtime: `Node.js 22`
- Build tool: `Vite 7`
- Framework: `React 19`
- Styling: `Tailwind CSS`
- Map renderer: `react-map-gl/maplibre`

## 핵심 파일

- `src/App.tsx`
- `src/components/Sidebar.tsx`
- `src/components/HeatmapMap.tsx`
- `src/components/StatsPanel.tsx`
- `src/services/dataService.ts`
- `src/hooks/useHeatmapData.ts`

## 현재 동작 방식

- API 우선 조회
- 실패 시 `public/data` 정적 JSON fallback
- 구 선택 시 백엔드 `district` 파라미터 반영
- 지도는 `구 경계 + 블록별 2D`만 렌더링
