import { CITIES } from '@/config/cities';
import type { CitiesMetadata, HeatmapData, SpatialUnit } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://busan-heatmap.onrender.com/api';
const STATIC_BASE_URL = '/data';

function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function buildFallbackMetadata(): CitiesMetadata {
  const today = new Date();
  const start = new Date(today);
  start.setFullYear(today.getFullYear() - 1);
  const end = new Date(today);
  end.setDate(today.getDate() + 7);

  return {
    cities: CITIES,
    availableDates: [formatLocalDate(start), formatLocalDate(end)],
    availableHours: Array.from({ length: 24 }, (_, hour) => hour),
    supportedScenarios: ['past', 'current', 'future_7d']
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function fetchWithFallback<T>(apiUrl: string, staticUrl: string): Promise<T> {
  try {
    return await fetchJson<T>(apiUrl);
  } catch (apiError) {
    console.warn(`API request failed for ${apiUrl}. Falling back to static JSON.`, apiError);
    return fetchJson<T>(staticUrl);
  }
}

function filterHeatmapByDistrict(data: HeatmapData, districtCode: string): HeatmapData {
  if (districtCode === 'all') {
    return data;
  }

  const filteredCells = data.cells.filter((cell) => cell.district_code === districtCode);
  if (!filteredCells.length) {
    return data;
  }

  const lstValues = filteredCells.map((cell) => cell.lst_value);
  const hottestCell = filteredCells.reduce((top, cell) => (cell.lst_value > top.lst_value ? cell : top), filteredCells[0]);

  return {
    ...data,
    district: districtCode,
    districts: data.districts?.filter((item) => item.district_code === districtCode) ?? data.districts,
    cells: filteredCells,
    summary: {
      avg_lst: Number((lstValues.reduce((sum, value) => sum + value, 0) / lstValues.length).toFixed(2)),
      min_lst: Math.min(...lstValues),
      max_lst: Math.max(...lstValues),
      hotspot_count: filteredCells.filter((cell) => cell.lst_value >= 31).length,
      cell_count: filteredCells.length,
      hottest_block_id: hottestCell.block_id,
      hottest_district_code: hottestCell.district_code,
      hottest_district_name_ko: hottestCell.district_name_ko
    }
  };
}

export async function loadCitiesMetadata(): Promise<CitiesMetadata> {
  try {
    return await fetchWithFallback<CitiesMetadata>(
      `${API_BASE_URL}/cities`,
      `${STATIC_BASE_URL}/cities.json`
    );
  } catch (error) {
    console.error('Error loading metadata:', error);
    return buildFallbackMetadata();
  }
}

export async function loadCities() {
  const metadata = await loadCitiesMetadata();
  return metadata.cities;
}

export async function loadSpatialUnits(city: string): Promise<SpatialUnit[]> {
  try {
    return await fetchWithFallback<SpatialUnit[]>(
      `${API_BASE_URL}/spatial-units/${city}`,
      `${STATIC_BASE_URL}/${city}/spatial_units.json`
    );
  } catch (error) {
    console.error('Error loading spatial units:', error);
    return [];
  }
}

export async function loadGridMaster(city: string): Promise<SpatialUnit[]> {
  return loadSpatialUnits(city);
}

export async function loadHeatmapData(
  city: string,
  district: string,
  scenario: string,
  date: string,
  hour: number
): Promise<HeatmapData | null> {
  try {
    const hourStr = hour.toString().padStart(2, '0');
    const data = await fetchWithFallback<HeatmapData>(
      `${API_BASE_URL}/heatmap?city=${city}&district=${district}&scenario=${scenario}&date=${date}&hour=${hour}`,
      `${STATIC_BASE_URL}/${city}/${scenario}/${date}/${hourStr}.json`
    );

    return filterHeatmapByDistrict(data, district);
  } catch (error) {
    console.error('Error loading heatmap data:', error);
    return null;
  }
}

export async function loadAvailableDates(): Promise<string[]> {
  try {
    const data = await loadCitiesMetadata();
    return data.availableDates || [];
  } catch (error) {
    console.error('Error loading available dates:', error);
    return buildFallbackMetadata().availableDates;
  }
}

export async function loadAvailableHours(): Promise<number[]> {
  try {
    const data = await loadCitiesMetadata();
    return data.availableHours || Array.from({ length: 24 }, (_, hour) => hour);
  } catch (error) {
    console.error('Error loading available hours:', error);
    return Array.from({ length: 24 }, (_, hour) => hour);
  }
}
