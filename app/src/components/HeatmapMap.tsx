import { useEffect, useMemo, useRef, useState } from 'react';
import Map, { Layer, NavigationControl, Popup, Source, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre';
import maplibregl, {
  type FillLayerSpecification,
  type LineLayerSpecification,
  type StyleSpecification,
} from 'maplibre-gl';
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson';

import type { HeatmapCell, HeatmapData, SpatialUnit } from '@/types';
import 'maplibre-gl/dist/maplibre-gl.css';

interface HeatmapMapProps {
  data: HeatmapData | null;
  center: [number, number];
  zoom: number;
}

interface BlockFeatureProperties {
  block_id: string;
  district_code: string;
  district_name: string;
  district_name_ko: string;
  lst_value: number;
  building_density: number;
  ndvi_mean: number;
  row_index: number;
  col_index: number;
}

interface DistrictFeatureProperties {
  district_code: string;
  district_name: string;
  district_name_ko: string;
}

type SourceScopedFillLayer = Omit<FillLayerSpecification, 'source'>;
type SourceScopedLineLayer = Omit<LineLayerSpecification, 'source'>;

const BASE_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors'
    }
  },
  layers: [
    {
      id: 'osm-base',
      type: 'raster',
      source: 'osm'
    }
  ]
};

const blockFillLayer: SourceScopedFillLayer = {
  id: 'block-fill',
  type: 'fill',
  paint: {
    'fill-color': [
      'step',
      ['get', 'lst_value'],
      '#2b6cb0',
      18, '#2b6cb0',
      22, '#4f8fc9',
      26, '#83b96b',
      30, '#d7b74b',
      34, '#e8903a',
      38, '#cf5b3e',
      42, '#a03232'
    ],
    'fill-opacity': 0.8
  }
};

const blockLineLayer: SourceScopedLineLayer = {
  id: 'block-outline',
  type: 'line',
  paint: {
    'line-color': 'rgba(255,255,255,0.45)',
    'line-width': 0.25
  }
};

const districtLineLayer: SourceScopedLineLayer = {
  id: 'district-boundary',
  type: 'line',
  paint: {
    'line-color': '#0f172a',
    'line-opacity': 0.75,
    'line-width': 1.45
  }
};

function createBlockGeoJSON(
  data: HeatmapData | null
): FeatureCollection<Polygon | MultiPolygon, BlockFeatureProperties> | null {
  if (!data?.cells?.length) return null;

  return {
    type: 'FeatureCollection',
    features: data.cells.map(
      (cell: HeatmapCell): Feature<Polygon | MultiPolygon, BlockFeatureProperties> => ({
        type: 'Feature',
        properties: {
          block_id: cell.block_id,
          district_code: cell.district_code,
          district_name: cell.district_name,
          district_name_ko: cell.district_name_ko,
          lst_value: cell.lst_value,
          building_density: cell.building_density,
          ndvi_mean: cell.ndvi_mean,
          row_index: cell.row_index,
          col_index: cell.col_index
        },
        geometry: cell.geometry
      })
    )
  };
}

function createDistrictGeoJSON(
  districts: SpatialUnit[] | undefined
): FeatureCollection<Polygon | MultiPolygon, DistrictFeatureProperties> | null {
  if (!districts?.length) return null;

  return {
    type: 'FeatureCollection',
    features: districts.map(
      (district): Feature<Polygon | MultiPolygon, DistrictFeatureProperties> => ({
        type: 'Feature',
        properties: {
          district_code: district.district_code,
          district_name: district.district_name,
          district_name_ko: district.district_name_ko
        },
        geometry: district.geometry
      })
    )
  };
}

export function HeatmapMap({ data, center, zoom }: HeatmapMapProps) {
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const mapRef = useRef<MapRef | null>(null);

  const blockGeoJSON = useMemo(() => createBlockGeoJSON(data), [data]);
  const districtGeoJSON = useMemo(() => createDistrictGeoJSON(data?.districts), [data?.districts]);
  const selectedCell = useMemo<HeatmapCell | null>(() => {
    if (!selectedBlockId || !data?.cells?.length) return null;
    return data.cells.find((cell) => cell.block_id === selectedBlockId) || null;
  }, [data, selectedBlockId]);

  const selectedOutlineLayer = useMemo<SourceScopedLineLayer>(() => ({
    id: 'block-selected-outline',
    type: 'line',
    filter: ['==', ['get', 'block_id'], selectedBlockId || ''],
    paint: {
      'line-color': '#111827',
      'line-width': 1.35,
      'line-opacity': 0.95
    }
  }), [selectedBlockId]);

  useEffect(() => {
    if (!mapRef.current) return;

    if (!data?.cells?.length) {
      mapRef.current.flyTo({ center, zoom, duration: 800 });
      return;
    }

    const bounds = data.cells.reduce<[number, number, number, number]>(
      (acc, cell) => [
        Math.min(acc[0], cell.bbox[0]),
        Math.min(acc[1], cell.bbox[1]),
        Math.max(acc[2], cell.bbox[2]),
        Math.max(acc[3], cell.bbox[3])
      ],
      [Infinity, Infinity, -Infinity, -Infinity]
    );

    mapRef.current.fitBounds(
      [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]]
      ],
      {
        padding: { top: 48, right: 48, bottom: 48, left: 48 },
        duration: 900,
        pitch: 0,
        bearing: 0
      }
    );
  }, [data, center, zoom]);

  const handleMapClick = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0];
    const properties = feature?.properties as Partial<BlockFeatureProperties> | undefined;

    if (!feature || !properties) {
      setSelectedBlockId(null);
      return;
    }

    setSelectedBlockId(String(properties.block_id || ''));
  };

  const popupLng = selectedCell ? selectedCell.center[0] : null;
  const popupLat = selectedCell ? selectedCell.center[1] : null;

  return (
    <div className="relative h-full w-full">
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col gap-2 px-3 pt-3 sm:flex-row sm:items-start sm:justify-between sm:px-4 sm:pt-4">
        <div className="max-w-full rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:px-4">
          <div className="text-[11px] font-medium text-slate-500">표시 정보</div>
          <div className="mt-1 text-xs font-semibold text-slate-900 sm:text-sm">
            {data ? `${data.datetime.replace('T', ' ')} · ${data.spatial_mode || 'district_outline_block_fill_2d'}` : '데이터 준비 중'}
          </div>
        </div>
        <div className="max-w-full self-start rounded-lg border border-slate-200 bg-white px-3 py-2 text-left shadow-sm sm:px-4 sm:text-right">
          <div className="text-[11px] font-medium text-slate-500">좌표계</div>
          <div className="mt-1 text-xs font-semibold text-slate-900 sm:text-sm">{data?.source_crs || 'EPSG:4326'}</div>
        </div>
      </div>

      <Map
        ref={mapRef}
        mapLib={maplibregl}
        initialViewState={{
          longitude: center[0],
          latitude: center[1],
          zoom,
          pitch: 0,
          bearing: 0
        }}
        reuseMaps
        style={{ width: '100%', height: '100%' }}
        mapStyle={BASE_MAP_STYLE}
        interactiveLayerIds={['block-fill']}
        onClick={handleMapClick}
      >
        <NavigationControl position="bottom-right" />

        {blockGeoJSON && (
          <Source id="block-data" type="geojson" data={blockGeoJSON}>
            <Layer {...blockFillLayer} />
            <Layer {...blockLineLayer} />
            <Layer {...selectedOutlineLayer} />
          </Source>
        )}

        {districtGeoJSON && (
          <Source id="district-data" type="geojson" data={districtGeoJSON}>
            <Layer {...districtLineLayer} />
          </Source>
        )}

        {selectedCell && popupLng !== null && popupLat !== null && (
          <Popup
            longitude={popupLng}
            latitude={popupLat}
            closeButton
            onClose={() => setSelectedBlockId(null)}
            closeOnClick={false}
          >
            <div className="min-w-[220px] max-w-[280px] bg-white px-4 py-4 sm:min-w-[260px]">
              <div className="mb-1 text-[11px] font-medium text-slate-500">
                선택 블록 정보
              </div>
              <div className="text-sm font-semibold text-slate-900">
                {selectedCell.district_name_ko} / Block {selectedCell.block_id}
              </div>
              <div className="mt-1 text-xs text-slate-500">{selectedCell.district_name}</div>
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                <div className="flex justify-between gap-4">
                  <span>지표면 온도 (LST)</span>
                  <span className="font-semibold text-[#b45309]">{selectedCell.lst_value.toFixed(1)}°C</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>건축밀도</span>
                  <span className="font-medium">{(selectedCell.building_density * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>NDVI</span>
                  <span className="font-medium">{selectedCell.ndvi_mean.toFixed(3)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>격자 위치</span>
                  <span className="font-medium">[{selectedCell.row_index}, {selectedCell.col_index}]</span>
                </div>
              </div>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}
