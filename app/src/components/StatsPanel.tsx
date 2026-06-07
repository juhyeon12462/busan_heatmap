import { Building2, Droplets, Flame, TreePine, Wind } from 'lucide-react';

import type { HeatmapData } from '@/types';

interface StatsPanelProps {
  data: HeatmapData | null;
}

const SCENARIO_LABELS = {
  past: '과거 7일 평균',
  current: '현재',
  future_7d: '미래 7일 예측'
};

export function StatsPanel({ data }: StatsPanelProps) {
  if (!data?.cells?.length) {
    return (
      <div className="absolute inset-x-3 bottom-3 z-20 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:inset-x-auto md:right-4 md:top-4 md:bottom-auto md:w-[292px] md:max-w-[calc(100%-2rem)]">
        <div className="text-sm font-medium text-slate-600">통계 정보를 계산 중입니다.</div>
      </div>
    );
  }

  const cells = data.cells;
  const lstValues = cells.map((cell) => cell.lst_value);
  const buildingDensities = cells.map((cell) => cell.building_density);
  const ndviValues = cells.map((cell) => cell.ndvi_mean);

  const avgLST = lstValues.reduce((sum, value) => sum + value, 0) / lstValues.length;
  const maxLST = Math.max(...lstValues);
  const minLST = Math.min(...lstValues);
  const avgBuilding = buildingDensities.reduce((sum, value) => sum + value, 0) / buildingDensities.length;
  const avgNDVI = ndviValues.reduce((sum, value) => sum + value, 0) / ndviValues.length;

  const highTempCells = cells.filter((cell) => cell.lst_value >= 31).length;
  const highTempPercent = (highTempCells / cells.length) * 100;
  const hottestCell = cells.reduce((top, cell) => (cell.lst_value > top.lst_value ? cell : top), cells[0]);
  const scenarioLabel = SCENARIO_LABELS[data.scenario];

  return (
    <div className="absolute inset-x-3 bottom-3 z-20 max-h-[34svh] overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:inset-x-auto md:right-4 md:top-4 md:bottom-auto md:max-h-[calc(100%-2rem)] md:w-[300px] md:max-w-[calc(100%-2rem)]">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[11px] font-medium text-slate-500">통계 요약</div>
          <div className="mt-1 [font-family:var(--font-display)] text-lg font-semibold text-slate-900">
            {scenarioLabel}
          </div>
          <div className="mt-1 text-[12px] text-slate-500">{data.datetime.replace('T', ' ')}</div>
        </div>
        <div className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
          블록 단위 요약
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-[11px] font-medium text-slate-500">평균 지표면 온도</div>
            <div className="[font-family:var(--font-display)] mt-2 text-[32px] font-semibold text-slate-900">
              {avgLST.toFixed(1)}°C
            </div>
          </div>
          <div className="rounded-lg bg-[#e8f0fb] p-3 text-[#1d4f91]">
            <Flame className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-slate-500">최소</div>
            <div className="mt-1 font-semibold text-slate-900">{minLST.toFixed(1)}°C</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-slate-500">평균</div>
            <div className="mt-1 font-semibold text-slate-900">{avgLST.toFixed(1)}°C</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-slate-500">최대</div>
            <div className="mt-1 font-semibold text-slate-900">{maxLST.toFixed(1)}°C</div>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>고온 블록 비율 (≥31°C)</span>
          <span className="font-semibold text-slate-800">{highTempCells}개 / {highTempPercent.toFixed(1)}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#f1a34d] via-[#eb7940] to-[#cb4533]"
            style={{ width: `${highTempPercent}%` }}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2.5 text-sm">
          <div className="rounded-lg bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-slate-600">
              <Building2 className="h-4 w-4 text-slate-400" />
              평균 건축밀도
            </div>
            <div className="mt-2 font-semibold text-slate-900">{(avgBuilding * 100).toFixed(1)}%</div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-slate-600">
              <TreePine className="h-4 w-4 text-[#2f8d65]" />
              평균 NDVI
            </div>
            <div className="mt-2 font-semibold text-slate-900">{avgNDVI.toFixed(3)}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-2.5 text-sm text-slate-600">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-[11px] font-medium text-slate-500">기상 요소</div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-2">
                <Wind className="h-4 w-4 text-slate-400" />
                <span>풍속</span>
              </div>
              <div className="mt-2 font-semibold text-slate-900">{data.weather?.wind_speed.toFixed(1)} m/s</div>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-2">
                <Droplets className="h-4 w-4 text-sky-500" />
                <span>습도</span>
              </div>
              <div className="mt-2 font-semibold text-slate-900">{data.weather?.humidity.toFixed(0)}%</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-[11px] font-medium text-slate-500">최고 온도 블록</div>
          <div className="mt-2 flex items-end justify-between">
            <div>
              <div className="text-lg font-semibold text-slate-900">{hottestCell.district_name_ko}</div>
              <div className="mt-1 text-xs text-slate-500">Block {hottestCell.block_id} · {hottestCell.district_name}</div>
            </div>
            <div className="[font-family:var(--font-display)] text-3xl font-semibold text-[#b45309]">
              {hottestCell.lst_value.toFixed(1)}°
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
