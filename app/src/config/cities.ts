import type { CityInfo, ScenarioOption } from '@/types';

const BUSAN_DISTRICTS = [
  { code: '2611', name: 'Jung-gu', name_ko: '중구' },
  { code: '2614', name: 'Seo-gu', name_ko: '서구' },
  { code: '2617', name: 'Dong-gu', name_ko: '동구' },
  { code: '2620', name: 'Yeongdo-gu', name_ko: '영도구' },
  { code: '2623', name: 'Busanjin-gu', name_ko: '부산진구' },
  { code: '2626', name: 'Dongnae-gu', name_ko: '동래구' },
  { code: '2629', name: 'Nam-gu', name_ko: '남구' },
  { code: '2632', name: 'Buk-gu', name_ko: '북구' },
  { code: '2635', name: 'Haeundae-gu', name_ko: '해운대구' },
  { code: '2638', name: 'Saha-gu', name_ko: '사하구' },
  { code: '2641', name: 'Geumjeong-gu', name_ko: '금정구' },
  { code: '2644', name: 'Gangseo-gu', name_ko: '강서구' },
  { code: '2647', name: 'Yeonje-gu', name_ko: '연제구' },
  { code: '2650', name: 'Suyeong-gu', name_ko: '수영구' },
  { code: '2653', name: 'Sasang-gu', name_ko: '사상구' },
  { code: '2671', name: 'Gijang-gun', name_ko: '기장군' }
];

export const CITIES: CityInfo[] = [
  {
    code: 'busan',
    name: 'Busan',
    name_ko: '부산광역시',
    center: [129.0756, 35.1796],
    zoom: 10.4,
    bounds: [[128.76, 34.88], [129.32, 35.4]],
    districts: BUSAN_DISTRICTS
  }
];

export const SCENARIO_OPTIONS: ScenarioOption[] = [
  { value: 'past', label: 'Trailing Week', label_ko: '과거 7일 평균', color: '#64748b' },
  { value: 'current', label: 'Current', label_ko: '현재', color: '#148f77' },
  { value: 'future_7d', label: 'Next Week Forecast', label_ko: '미래 7일 예측', color: '#d97706' }
];

export const LST_COLOR_SCALE = [
  { threshold: 18, color: [28, 117, 132] },
  { threshold: 22, color: [70, 167, 161] },
  { threshold: 26, color: [238, 215, 128] },
  { threshold: 30, color: [244, 161, 79] },
  { threshold: 34, color: [232, 102, 58] },
  { threshold: 38, color: [192, 52, 42] },
  { threshold: 42, color: [122, 21, 34] }
];
