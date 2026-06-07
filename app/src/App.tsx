import { useCallback, useEffect, useMemo, useState } from 'react';
import { format } from 'date-fns';
import { CloudSun, Flame, MapPinned, Wind } from 'lucide-react';
import { toast } from 'sonner';

import { HeatmapMap } from '@/components/HeatmapMap';
import { Legend } from '@/components/Legend';
import { Sidebar } from '@/components/Sidebar';
import { StatsPanel } from '@/components/StatsPanel';
import { Toaster } from '@/components/ui/sonner';
import { CITIES } from '@/config/cities';
import { useHeatmapData } from '@/hooks/useHeatmapData';
import { loadCitiesMetadata } from '@/services/dataService';
import type { CitiesMetadata, ScenarioType } from '@/types';

const SCENARIO_LABELS: Record<ScenarioType, string> = {
  past: '과거 7일 평균',
  current: '현재',
  future_7d: '미래 7일 예측'
};

const WEATHER_SOURCE_LABELS: Record<string, string> = {
  observed: 'KMA 관측기반',
  forecast: '예측기상',
  simulated: '합성기상'
};

const TODAY = new Date();

function App() {
  const [selectedCity, setSelectedCity] = useState<string>('busan');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('all');
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('current');
  const [selectedDate, setSelectedDate] = useState<Date>(TODAY);
  const [selectedHour, setSelectedHour] = useState<number>(15);
  const [metadata, setMetadata] = useState<CitiesMetadata | null>(null);
  const selectedDateIso = format(selectedDate, 'yyyy-MM-dd');
  const { data, loading, error, refresh } = useHeatmapData({
    city: selectedCity,
    district: selectedDistrict,
    scenario: selectedScenario,
    date: selectedDateIso,
    hour: selectedHour
  });

  const cityOptions = metadata?.cities?.length ? metadata.cities : CITIES;
  const cityInfo = cityOptions.find((city) => city.code === selectedCity) || cityOptions[0];
  const districtOptions = cityInfo?.districts || [];
  const districtInfo = districtOptions.find((district) => district.code === selectedDistrict);

  const kpis = useMemo(
    () => [
      {
        label: '평균 LST',
        value: data ? `${data.summary?.avg_lst.toFixed(1) ?? '-'}°C` : '-',
        accent: 'border-l-[#1d4f91] bg-[#f8fbff]',
        iconWrap: 'bg-[#e8f0fb] text-[#1d4f91]',
        icon: Flame,
      },
      {
        label: '최고 온도',
        value: data ? `${data.summary?.max_lst.toFixed(1) ?? '-'}°C` : '-',
        accent: 'border-l-[#b45309] bg-[#fffaf3]',
        iconWrap: 'bg-[#fef0d9] text-[#b45309]',
        icon: CloudSun,
      },
      {
        label: '고온 구역',
        value: data ? `${data.summary?.hotspot_count.toLocaleString()}개` : '-',
        accent: 'border-l-[#b42318] bg-[#fff8f7]',
        iconWrap: 'bg-[#fdecea] text-[#b42318]',
        icon: MapPinned,
      },
      {
        label: '풍속',
        value: data?.weather ? `${data.weather.wind_speed.toFixed(1)} m/s` : '-',
        accent: 'border-l-[#0f766e] bg-[#f4fbfa]',
        iconWrap: 'bg-[#ddf4f1] text-[#0f766e]',
        icon: Wind,
      },
    ],
    [data]
  );

  useEffect(() => {
    let cancelled = false;

    loadCitiesMetadata()
      .then((result) => {
        if (cancelled) return;
        setMetadata(result);
      })
      .catch((metadataError) => {
        console.error('Failed to load metadata', metadataError);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleCityChange = useCallback((cityCode: string) => {
    setSelectedCity(cityCode);
    setSelectedDistrict('all');
  }, []);

  const handleApply = useCallback(() => {
    refresh();
    toast.success('히트맵 데이터를 불러왔습니다.', {
      description: `${cityInfo?.name_ko || selectedCity} | ${districtInfo?.name_ko || '부산 전체'} | ${selectedDateIso} ${selectedHour.toString().padStart(2, '0')}:00 | ${SCENARIO_LABELS[selectedScenario]}`
    });
  }, [refresh, cityInfo, districtInfo, selectedCity, selectedDateIso, selectedHour, selectedScenario]);

  return (
    <div className="min-h-screen w-full overflow-y-auto bg-slate-100 lg:h-screen lg:overflow-hidden">
      <div className="flex min-h-screen w-full flex-col gap-3 p-3 lg:h-full lg:min-h-0 lg:flex-row">
        <div className="w-full lg:w-[318px] lg:min-w-[318px] 2xl:w-[330px] 2xl:min-w-[330px]">
          <Sidebar
            cities={cityOptions}
            districts={districtOptions}
            availableDates={metadata?.availableDates}
            availableHours={metadata?.availableHours}
            selectedCity={selectedCity}
            selectedDistrict={selectedDistrict}
            selectedScenario={selectedScenario}
            selectedDate={selectedDate}
            selectedHour={selectedHour}
            onCityChange={handleCityChange}
            onDistrictChange={setSelectedDistrict}
            onScenarioChange={setSelectedScenario}
            onDateChange={setSelectedDate}
            onHourChange={setSelectedHour}
            onApply={handleApply}
            loading={loading}
          />
        </div>

        <div className="min-h-0 min-w-0 flex-1">
          <div className="flex h-full min-h-0 flex-col gap-3">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div className="space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Busan District Urban Heat Monitoring
                  </div>
                  <div className="space-y-1">
                    <h1 className="[font-family:var(--font-display)] text-[23px] font-semibold tracking-tight text-slate-900 lg:text-[28px]">
                      부산 구 단위 도시열섬 모니터링 대시보드
                    </h1>
                    <p className="max-w-3xl text-[13px] leading-5 text-slate-600">
                      {cityInfo?.name_ko || '부산광역시'} 구 경계선과 블록별 2D 분포를 함께 표시하고, 구별 기상 시계열과 최근 7일 LST 창을 사용해 미래 7일을 순차 예측합니다.
                    </p>
                  </div>
                </div>

                <div className="grid gap-2.5 sm:grid-cols-2 xl:w-[470px]">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="text-[11px] font-medium text-slate-500">조회 대상</div>
                    <div className="mt-1 text-[15px] font-semibold text-slate-900">
                      {districtInfo?.name_ko || '부산 전체'}
                    </div>
                    <div className="mt-1 text-[12px] text-slate-600">{SCENARIO_LABELS[selectedScenario]}</div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="text-[11px] font-medium text-slate-500">기상 요약</div>
                    <div className="mt-1 text-[15px] font-semibold text-slate-900">
                      {data?.weather ? `${data.weather.air_temp.toFixed(1)}°C / RH ${data.weather.humidity.toFixed(0)}%` : '데이터 준비 중'}
                    </div>
                    <div className="mt-1 text-[12px] text-slate-600">
                      {data?.weather
                        ? `${WEATHER_SOURCE_LABELS[data.weather.source_type || 'simulated'] || '기상데이터'} · 일사량 ${data.weather.solar_radiation.toFixed(0)} W/m²`
                        : '백엔드 응답 대기'}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map(({ label, value, accent, iconWrap, icon: Icon }) => (
                <div
                  key={label}
                  className={`rounded-xl border border-slate-200 border-l-4 ${accent} p-3.5 shadow-sm`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-[11px] font-medium text-slate-500">{label}</p>
                      <div className="[font-family:var(--font-display)] mt-1.5 text-[25px] font-semibold text-slate-900">
                        {value}
                      </div>
                    </div>
                    <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconWrap}`}>
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                  </div>
                </div>
              ))}
            </section>

            <section className="relative min-h-[68svh] flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:min-h-0">
              <div className="absolute inset-0">
                <HeatmapMap
                  data={data}
                  center={cityInfo?.center || [129.0756, 35.1796]}
                  zoom={cityInfo?.zoom || 10.4}
                />
              </div>

              <Legend data={data} />
              <StatsPanel data={data} />

              {loading && (
                <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-100/70">
                  <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-lg">
                    <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-[#1d4f91]" />
                    <span className="text-sm font-medium text-slate-700">데이터 로딩 중...</span>
                  </div>
                </div>
              )}

              {error && (
                <div className="absolute left-1/2 top-5 z-30 -translate-x-1/2 rounded-2xl border border-red-200 bg-red-50/95 px-5 py-4 shadow-lg">
                  <p className="text-sm font-medium text-red-700">데이터를 불러오는 중 오류가 발생했습니다.</p>
                  <p className="mt-1 text-xs text-red-500">{error}</p>
                </div>
              )}

              {!loading && !error && !data && (
                <div className="absolute left-1/2 top-5 z-30 -translate-x-1/2 rounded-2xl border border-amber-200 bg-amber-50/95 px-5 py-4 shadow-lg">
                  <p className="text-sm font-medium text-amber-700">해당 조건의 데이터가 없습니다.</p>
                  <p className="mt-1 text-xs text-amber-600">다른 날짜/시간을 선택해주세요.</p>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>

      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;
