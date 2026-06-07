import { useState, useEffect, useCallback } from 'react';
import type { HeatmapData, ScenarioType } from '@/types';
import { loadHeatmapData } from '@/services/dataService';

interface UseHeatmapDataProps {
  city: string;
  district: string;
  scenario: ScenarioType;
  date: string;
  hour: number;
}

interface UseHeatmapDataReturn {
  data: HeatmapData | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useHeatmapData({
  city,
  district,
  scenario,
  date,
  hour
}: UseHeatmapDataProps): UseHeatmapDataReturn {
  const [data, setData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await loadHeatmapData(city, district, scenario, date, hour);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [city, district, scenario, date, hour]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refresh };
}
