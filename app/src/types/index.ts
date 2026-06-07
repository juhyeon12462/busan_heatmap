import type { MultiPolygon, Polygon } from 'geojson';

export type ScenarioType = 'past' | 'current' | 'future_7d';
export type SpatialGeometry = Polygon | MultiPolygon;

export interface DistrictInfo {
  code: string;
  name: string;
  name_ko: string;
}

export interface CityInfo {
  code: string;
  name: string;
  name_ko: string;
  center: [number, number];
  zoom: number;
  bounds?: [[number, number], [number, number]];
  districts?: DistrictInfo[];
}

export interface SpatialUnit {
  district_code: string;
  district_name: string;
  district_name_ko: string;
  center: [number, number];
  bbox: [number, number, number, number];
  geometry: SpatialGeometry;
  building_density: number;
  ndvi_mean: number;
  area_ratio_urban: number;
  area_ratio_forest: number;
  area_ratio_green: number;
  grid_count: number;
}

export interface HeatmapCell {
  block_id: string;
  district_code: string;
  district_name: string;
  district_name_ko: string;
  center: [number, number];
  bbox: [number, number, number, number];
  geometry: SpatialGeometry;
  row_index: number;
  col_index: number;
  lst_value: number;
  building_density: number;
  ndvi_mean: number;
  area_ratio_urban: number;
  area_ratio_forest: number;
  area_ratio_green: number;
}

export interface WeatherSignature {
  air_temp: number;
  wind_speed: number;
  humidity: number;
  solar_radiation: number;
  source_type?: string;
  source_detail?: string | null;
}

export interface HeatmapSummary {
  avg_lst: number;
  min_lst: number;
  max_lst: number;
  hotspot_count: number;
  cell_count: number;
  hottest_block_id?: string | null;
  hottest_district_code?: string | null;
  hottest_district_name_ko?: string | null;
}

export interface HeatmapData {
  city: string;
  district?: string | null;
  scenario: ScenarioType;
  datetime: string;
  districts?: SpatialUnit[];
  cells: HeatmapCell[];
  weather?: WeatherSignature;
  summary?: HeatmapSummary;
  source_crs?: string;
  spatial_mode?: string;
  generated_at?: string;
}

export interface ScenarioOption {
  value: ScenarioType;
  label: string;
  label_ko: string;
  color: string;
}

export interface CitiesMetadata {
  cities: CityInfo[];
  availableDates: string[];
  availableHours: number[];
  supportedScenarios?: ScenarioType[];
}
