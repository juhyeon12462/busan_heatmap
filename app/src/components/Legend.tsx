import { Thermometer } from 'lucide-react';

import { LST_COLOR_SCALE } from '@/config/cities';
import type { HeatmapData } from '@/types';

interface LegendProps {
  data: HeatmapData | null;
}

export function Legend({ data }: LegendProps) {
  const min = data?.summary?.min_lst ?? 18;
  const max = data?.summary?.max_lst ?? 42;

  return (
    <div className="absolute inset-x-3 top-20 z-20 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:inset-x-auto md:top-auto md:bottom-4 md:left-4 md:w-[272px] md:max-w-[calc(100%-2rem)]">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Thermometer className="h-4 w-4 text-[#1d4f91]" />
            지표면 온도 범례
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {data ? `${data.summary?.cell_count.toLocaleString()}개 블록 표시 중` : '블록 데이터 준비 중'}
          </div>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
        <div className="flex h-4">
          {LST_COLOR_SCALE.map((scale, index) => (
            <div
              key={index}
              className="flex-1"
              style={{
                backgroundColor: `rgb(${scale.color[0]}, ${scale.color[1]}, ${scale.color[2]})`
              }}
            />
          ))}
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>{min.toFixed(1)}°C</span>
        <span>{((min + max) / 2).toFixed(1)}°C</span>
        <span>{max.toFixed(1)}°C</span>
      </div>
      <div className="mt-3 text-[12px] leading-5 text-slate-600">
        부산 구 경계선 위에 블록별 2D 폴리곤을 채색합니다. 블록을 클릭하면 상세 값을 확인할 수 있습니다.
      </div>
    </div>
  );
}
