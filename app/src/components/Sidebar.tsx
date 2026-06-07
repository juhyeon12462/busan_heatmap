import { Calendar } from '@/components/ui/calendar';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SCENARIO_OPTIONS } from '@/config/cities';
import type { CityInfo, DistrictInfo, ScenarioType } from '@/types';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Search } from 'lucide-react';

interface SidebarProps {
  cities: CityInfo[];
  districts: DistrictInfo[];
  availableDates?: string[];
  availableHours?: number[];
  selectedCity: string;
  selectedDistrict: string;
  selectedScenario: ScenarioType;
  selectedDate: Date;
  selectedHour: number;
  onCityChange: (city: string) => void;
  onDistrictChange: (district: string) => void;
  onScenarioChange: (scenario: ScenarioType) => void;
  onDateChange: (date: Date) => void;
  onHourChange: (hour: number) => void;
  onApply: () => void;
  loading?: boolean;
}

const DEFAULT_HOURS = Array.from({ length: 24 }, (_, hour) => hour);
const FALLBACK_MAX_DATE = new Date();
FALLBACK_MAX_DATE.setDate(FALLBACK_MAX_DATE.getDate() + 7);
const FALLBACK_MIN_DATE = new Date(FALLBACK_MAX_DATE.getFullYear() - 1, 0, 1);

export function Sidebar({
  cities,
  districts,
  availableDates,
  availableHours,
  selectedCity,
  selectedDistrict,
  selectedScenario,
  selectedDate,
  selectedHour,
  onCityChange,
  onDistrictChange,
  onScenarioChange,
  onDateChange,
  onHourChange,
  onApply,
  loading = false
}: SidebarProps) {
  const selectedCityInfo = cities.find((city) => city.code === selectedCity);
  const selectedDistrictInfo = districts.find((district) => district.code === selectedDistrict);
  const selectedScenarioInfo = SCENARIO_OPTIONS.find((scenario) => scenario.value === selectedScenario);
  const hourOptions = availableHours?.length ? availableHours : DEFAULT_HOURS;
  const availableDateSet = availableDates?.length ? new Set(availableDates) : null;

  return (
    <Card className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white py-0 text-slate-900 shadow-sm">
      <CardHeader className="space-y-3 border-b border-slate-200 px-4 pt-4 pb-3">
        <div className="space-y-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Control Panel
          </div>
          <CardTitle className="[font-family:var(--font-display)] text-[22px] font-semibold tracking-tight text-slate-900">
            조회 조건
          </CardTitle>
          <p className="text-[13px] leading-5 text-slate-600">
            시 선택 후 구를 지정하면 구 경계선과 블록별 2D 열분포가 바로 갱신됩니다.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">공간 단위</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">구 경계 + 블록 2D</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">상태</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">{loading ? '데이터 조회 중' : '조회 가능'}</div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
        <section className="space-y-2.5">
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              시 선택
            </Label>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
              {selectedCityInfo?.name_ko || '부산광역시'}
            </div>
          </div>
          <Select value={selectedCity} onValueChange={onCityChange}>
            <SelectTrigger className="h-10 w-full rounded-xl border-slate-300 bg-white text-slate-900 shadow-none">
              <SelectValue placeholder="시를 선택하세요" />
            </SelectTrigger>
            <SelectContent className="border-slate-200 bg-white text-slate-900 shadow-lg">
              {cities.map((city) => (
                <SelectItem
                  key={city.code}
                  value={city.code}
                  className="rounded-lg text-slate-900 focus:bg-slate-100 focus:text-slate-900"
                >
                  {city.name_ko}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </section>

        <section className="space-y-2.5">
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              구 선택
            </Label>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
              {selectedDistrictInfo?.name_ko || '부산 전체'}
            </div>
          </div>
          <Select value={selectedDistrict} onValueChange={onDistrictChange}>
            <SelectTrigger className="h-10 w-full rounded-xl border-slate-300 bg-white text-slate-900 shadow-none">
              <SelectValue placeholder="구를 선택하세요" />
            </SelectTrigger>
            <SelectContent className="border-slate-200 bg-white text-slate-900 shadow-lg">
              <SelectItem value="all" className="rounded-lg text-slate-900 focus:bg-slate-100 focus:text-slate-900">
                부산 전체
              </SelectItem>
              {districts.map((district) => (
                <SelectItem
                  key={district.code}
                  value={district.code}
                  className="rounded-lg text-slate-900 focus:bg-slate-100 focus:text-slate-900"
                >
                  {district.name_ko}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </section>

        <section className="space-y-2.5">
          <div className="flex items-center justify-between gap-3">
            <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              날짜 선택
            </Label>
            <div className="text-[11px] font-medium text-slate-600">
              {format(selectedDate, 'yyyy.MM.dd', { locale: ko })}
            </div>
          </div>

          <div className="grid grid-cols-[1fr_auto] gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-900">
                {format(selectedDate, 'yyyy.MM.dd (EEE)', { locale: ko })}
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                기준 시간 {selectedHour.toString().padStart(2, '0')}:00
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-right">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">시점</div>
              <div className="mt-1 text-[11px] font-semibold text-slate-900">{selectedScenarioInfo?.label_ko}</div>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white px-2.5 py-2.5">
            <Calendar
              mode="single"
              navLayout="around"
              selected={selectedDate}
              onSelect={(date) => date && onDateChange(date)}
              className="w-full rounded-[18px] bg-transparent p-0 text-slate-900 [--cell-size:1.95rem] [--rdp-nav_button-width:1.75rem] [--rdp-nav_button-height:1.75rem] [--rdp-nav-height:2rem]"
              classNames={{
                root: 'w-full',
                months: 'w-full',
                month: 'relative w-full',
                month_grid: 'w-full border-separate border-spacing-1',
                month_caption: 'flex h-8 items-center justify-center px-0',
                caption_label: 'text-sm font-semibold tracking-[0.01em] text-slate-900',
                button_previous: 'h-7 w-7 rounded-lg border border-slate-200 bg-white p-0 text-slate-700 hover:bg-slate-100',
                button_next: 'h-7 w-7 rounded-lg border border-slate-200 bg-white p-0 text-slate-700 hover:bg-slate-100',
                weekdays: '',
                weekday: 'h-7 w-9 p-0 text-center align-middle text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400',
                weeks: '',
                week: '',
                day: 'h-9 w-9 p-0 text-center align-middle',
                day_button: 'mx-auto inline-flex h-8.5 w-8.5 items-center justify-center rounded-lg border border-transparent p-0 text-[12px] font-medium text-slate-700 hover:bg-slate-100 hover:text-slate-900 data-[selected-single=true]:border-[#1d4f91] data-[selected-single=true]:bg-[#1d4f91] data-[selected-single=true]:text-white data-[range-middle=true]:bg-slate-100 data-[range-middle=true]:text-slate-900',
                today: 'text-[#1d4f91] font-semibold',
                outside: 'text-slate-300 opacity-90',
                disabled: 'text-slate-300 opacity-45',
              }}
              disabled={(candidateDate) => {
                const formatted = format(candidateDate, 'yyyy-MM-dd');
                if (availableDateSet) {
                  return !availableDateSet.has(formatted);
                }
                return candidateDate > FALLBACK_MAX_DATE || candidateDate < FALLBACK_MIN_DATE;
              }}
            />
          </div>
        </section>

        <section className="space-y-2.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            시간 선택
          </Label>
          <div className="grid grid-cols-4 gap-2">
            {hourOptions.map((hour) => (
              <Button
                key={hour}
                variant="ghost"
                size="sm"
                onClick={() => onHourChange(hour)}
                className={`h-8.5 rounded-lg border px-0 text-[11px] ${
                  selectedHour === hour
                    ? 'border-[#1d4f91] bg-[#1d4f91] text-white hover:bg-[#1d4f91]'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                {hour.toString().padStart(2, '0')}:00
              </Button>
            ))}
          </div>
        </section>

        <section className="space-y-2.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            시점 선택
          </Label>
          <RadioGroup
            value={selectedScenario}
            onValueChange={(value) => onScenarioChange(value as ScenarioType)}
            className="grid gap-2"
          >
            {SCENARIO_OPTIONS.map((scenario) => (
              <label
                key={scenario.value}
                htmlFor={scenario.value}
                className={`flex cursor-pointer items-center gap-2.5 rounded-lg border px-3 py-2 transition ${
                  selectedScenario === scenario.value
                    ? 'border-[#1d4f91] bg-[#eff6ff]'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <RadioGroupItem value={scenario.value} id={scenario.value} className="size-3.5 border-slate-300 text-[#1d4f91]" />
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: scenario.color }} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12px] font-medium text-slate-900">{scenario.label_ko}</div>
                </div>
              </label>
            ))}
          </RadioGroup>
        </section>

        <div className="mt-auto pt-2">
          <Button
            onClick={onApply}
            disabled={loading}
            className="h-10 w-full rounded-lg bg-[#1d4f91] text-[14px] font-semibold text-white shadow-sm hover:bg-[#163d71]"
          >
            <Search className="mr-2 h-4 w-4" />
            {loading ? '조회 중...' : '현재 조건 새로고침'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
