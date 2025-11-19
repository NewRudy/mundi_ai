/**
 * Scene3DViewer - Deck.gl 3D场景可视化组件
 * 专门用于水电场景的3D数据可视化：洪水演进、地形分析、调度模拟
 */

import React, { useEffect, useRef, useState, useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import {
  GeoJsonLayer,
  PathLayer,
  ScatterplotLayer,
  PolygonLayer,
  ColumnLayer,
  PointCloudLayer
} from '@deck.gl/layers';
import { LightingEffect, AmbientLight, _SunLight as SunLight } from '@deck.gl/core';
import { MapView } from '@deck.gl/core';
import * as d3 from 'd3';

interface Scene3DViewerProps {
  // 场景类型
  sceneType: 'flood_simulation' | 'dispatch_optimization' | 'terrain_analysis' | 'reservoir_modeling';

  // 基础数据
  viewport: {
    longitude: number;
    latitude: number;
    zoom: number;
    pitch: number;
    bearing: number;
  };

  // 洪水模拟数据
  floodData?: {
    extent: {
      west: number;
      south: number;
      east: number;
      north: number;
    };
    waterLevels: number[][]; // 网格水位数据 [row][col]
    timestamps: string[];
    currentTimeIndex: number;
    maxWaterLevel: number;
    animationSpeed?: number;
  };

  // 地形数据
  terrainData?: {
    elevationData: string; // 地形URL或base64
    bounds: [number, number, number, number]; // [west, south, east, north]
    elevationDecoder: {
      rScaler: number;
      gScaler: number;
      bScaler: number;
      offset: number;
    };
    meshMaxError: number;
  };

  // 调度数据
  dispatchData?: {
    scenarios: Array<{
      id: string;
      name: string;
      waterLevel: number;
      dischargeRate: number;
      powerGeneration: number;
      efficiency: number;
      riskLevel: number;
      color: string;
    }>;
    selectedScenario: string;
    parameters: Record<string, number>;
  };

  // 水库模型数据
  reservoirData?: {
    dam: {
      position: [number, number];
      height: number;
      width: number;
      modelUrl?: string;
    };
    waterLevel: number;
    maxWaterLevel: number;
    inflow: number;
    outflow: number;
  };

  // 监测点数据
  monitoringPoints?: Array<{
    id: string;
    position: [number, number];
    altitude: number;
    type: 'hydrology' | 'meteorology' | 'dam';
    status: 'normal' | 'warning' | 'danger';
    value: number;
    unit: string;
    timestamp: string;
  }>;

  // 事件回调
  onViewportChange?: (viewport: any) => void;
  onTimeChange?: (timeIndex: number) => void;
  onScenarioSelect?: (scenarioId: string) => void;
  onPointClick?: (point: any) => void;

  // 样式配置
  className?: string;
  style?: React.CSSProperties;
  showControls?: boolean;
  animationEnabled?: boolean;
}

// 光照效果配置
const lightingEffect = new LightingEffect({
  ambientLight: new AmbientLight({
    color: [255, 255, 255],
    intensity: 1.0
  }),
  sunLight: new SunLight({
    timestamp: Date.now(),
    color: [255, 255, 255],
    intensity: 2.0,
    _shadow: true
  })
});

const Scene3DViewer: React.FC<Scene3DViewerProps> = ({
  sceneType,
  viewport,
  floodData,
  terrainData,
  dispatchData,
  reservoirData,
  monitoringPoints = [],
  onViewportChange,
  onTimeChange,
  onScenarioSelect,
  onPointClick,
  className,
  style,
  showControls = true,
  animationEnabled = true
}) => {
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [animationSpeed, setAnimationSpeed] = useState(1);
  const [selectedScenario, setSelectedScenario] = useState(dispatchData?.selectedScenario || '');
  const animationRef = useRef<NodeJS.Timeout | null>(null);

  // 生成洪水淹没图层
  const floodLayer = useMemo(() => {
    if (!floodData) return null;

    const { extent, waterLevels, currentTimeIndex, maxWaterLevel } = floodData;
    const currentWaterLevel = waterLevels[currentTimeIndex] || [];

    // 创建网格数据
    const gridWidth = currentWaterLevel[0]?.length || 50;
    const gridHeight = currentWaterLevel.length || 30;
    const cellWidth = (extent.east - extent.west) / gridWidth;
    const cellHeight = (extent.north - extent.south) / gridHeight;

    const polygons = [];
    for (let row = 0; row < gridHeight; row++) {
      for (let col = 0; col < gridWidth; col++) {
        const waterLevel = currentWaterLevel[row]?.[col] || 0;
        if (waterLevel > 0) {
          const west = extent.west + col * cellWidth;
          const south = extent.south + row * cellHeight;
          const east = west + cellWidth;
          const north = south + cellHeight;

          const intensity = waterLevel / maxWaterLevel;
          const color = d3.interpolateBlues(0.3 + intensity * 0.7);

          polygons.push({
            polygon: [
              [west, south],
              [east, south],
              [east, north],
              [west, north],
              [west, south]
            ],
            elevation: waterLevel,
            color,
            opacity: 0.6 + intensity * 0.4
          });
        }
      }
    }

    return new PolygonLayer({
      id: 'flood-inundation',
      data: polygons,
      extruded: true,
      wireframe: false,
      filled: true,
      getPolygon: d => d.polygon,
      getElevation: d => d.elevation,
      getFillColor: d => {
        const rgb = d3.rgb(d.color);
        return [rgb.r, rgb.g, rgb.b, Math.round(d.opacity * 255)];
      },
      getLineColor: [255, 255, 255, 100],
      getLineWidth: 1,
      material: {
        ambient: 0.35,
        diffuse: 0.6,
        shininess: 32,
        specularColor: [255, 255, 255]
      }
    });
  }, [floodData]);

  // 生成地形图层
  const terrainLayer = useMemo(() => {
    if (!terrainData) return null;

    return new TerrainLayer({
      id: 'terrain',
      elevationData: terrainData.elevationData,
      bounds: terrainData.bounds,
      elevationDecoder: terrainData.elevationDecoder,
      meshMaxError: terrainData.meshMaxError,
      material: {
        ambient: 0.4,
        diffuse: 0.7,
        shininess: 16,
        specularColor: [255, 255, 255]
      }
    });
  }, [terrainData]);

  // 生成调度方案对比图层
  const dispatchLayers = useMemo(() => {
    if (!dispatchData) return [];

    const layers = [];

    // 柱状图显示各方案参数
    dispatchData.scenarios.forEach((scenario, index) => {
      const height = (scenario.waterLevel / 200) * 5000; // 标准化高度
      const position = [111.0 + index * 0.01, 30.8]; // 横向排列

      layers.push(
        new ColumnLayer({
          id: `dispatch-scenario-${scenario.id}`,
          data: [{
            position,
            height,
            color: scenario.color,
            scenario: scenario.name,
            efficiency: scenario.efficiency,
            riskLevel: scenario.riskLevel
          }],
          diskResolution: 12,
          radius: 500,
          extruded: true,
          pickable: true,
          elevationScale: 1,
          getPosition: d => d.position,
          getElevation: d => d.height,
          getFillColor: d => {
            const rgb = d3.rgb(d.color);
            const alpha = selectedScenario === scenario.id ? 255 : 180;
            return [rgb.r, rgb.g, rgb.b, alpha];
          },
          getLineColor: [255, 255, 255, 200],
          getLineWidth: selectedScenario === scenario.id ? 3 : 1,
          onClick: (info) => {
            onScenarioSelect?.(scenario.id);
            setSelectedScenario(scenario.id);
          }
        })
      );
    });

    return layers;
  }, [dispatchData, selectedScenario, onScenarioSelect]);

  // 生成水库3D模型图层
  const reservoirLayers = useMemo(() => {
    if (!reservoirData) return [];

    const layers = [];

    // 大坝3D模型
    if (reservoirData.dam.modelUrl) {
      layers.push(
        new ScenegraphLayer({
          id: 'dam-3d-model',
          data: [reservoirData.dam],
          scenegraph: reservoirData.dam.modelUrl,
          getPosition: d => d.position,
          getOrientation: [0, 0, 90],
          sizeScale: 100,
          _lighting: 'pbr'
        })
      );
    } else {
      // 简单的大坝几何体
      layers.push(
        new ColumnLayer({
          id: 'dam-structure',
          data: [{
            position: reservoirData.dam.position,
            height: reservoirData.dam.height,
            radius: reservoirData.dam.width / 2
          }],
          diskResolution: 8,
          radius: reservoirData.dam.width / 2,
          extruded: true,
          getPosition: d => d.position,
          getElevation: d => d.height,
          getFillColor: [100, 100, 100, 255],
          getLineColor: [150, 150, 150, 255],
          getLineWidth: 2
        })
      );
    }

    // 水面效果
    const waterLevel = reservoirData.waterLevel;
    const maxLevel = reservoirData.maxWaterLevel;
    const waterIntensity = waterLevel / maxLevel;

    layers.push(
      new PolygonLayer({
        id: 'reservoir-water',
        data: [{
          polygon: [
            [reservoirData.dam.position[0] - 0.01, reservoirData.dam.position[1] - 0.01],
            [reservoirData.dam.position[0] + 0.01, reservoirData.dam.position[1] - 0.01],
            [reservoirData.dam.position[0] + 0.01, reservoirData.dam.position[1] + 0.01],
            [reservoirData.dam.position[0] - 0.01, reservoirData.dam.position[1] + 0.01]
          ],
          elevation: waterLevel,
          intensity: waterIntensity
        }],
        extruded: true,
        wireframe: false,
        getPolygon: d => d.polygon,
        getElevation: d => d.elevation * 1000, // 转换为米
        getFillColor: d => {
          const blue = Math.round(100 + d.intensity * 100);
          const alpha = Math.round(0.6 * 255);
          return [0, 100, blue, alpha];
        },
        material: {
          ambient: 0.3,
          diffuse: 0.7,
          shininess: 64,
          specularColor: [255, 255, 255]
        }
      })
    );

    return layers;
  }, [reservoirData]);

  // 生成监测点图层
  const monitoringLayer = useMemo(() => {
    if (monitoringPoints.length === 0) return null;

    return new ScatterplotLayer({
      id: 'monitoring-points',
      data: monitoringPoints,
      pickable: true,
      opacity: 0.8,
      stroked: true,
      filled: true,
      radiusScale: 6,
      radiusMinPixels: 3,
      radiusMaxPixels: 30,
      lineWidthMinPixels: 1,
      getPosition: d => [...d.position, d.altitude || 0],
      getRadius: d => {
        switch (d.status) {
          case 'danger': return 15;
          case 'warning': return 10;
          default: return 8;
        }
      },
      getFillColor: d => {
        switch (d.status) {
          case 'danger': return [255, 0, 0, 255];
          case 'warning': return [255, 165, 0, 255];
          default: return [0, 255, 0, 255];
        }
      },
      getLineColor: [255, 255, 255, 255],
      onClick: (info) => {
        if (info.object) {
          onPointClick?.(info.object);
        }
      }
    });
  }, [monitoringPoints, onPointClick]);

  // 组合所有图层
  const layers = useMemo(() => {
    const allLayers = [];

    // 基础地形
    if (terrainLayer) allLayers.push(terrainLayer);

    // 根据场景类型添加特定图层
    switch (sceneType) {
      case 'flood_simulation':
        if (floodLayer) allLayers.push(floodLayer);
        break;

      case 'dispatch_optimization':
        allLayers.push(...dispatchLayers);
        break;

      case 'reservoir_modeling':
        allLayers.push(...reservoirLayers);
        break;
    }

    // 通用监测点
    if (monitoringLayer) allLayers.push(monitoringLayer);

    return allLayers;
  }, [terrainLayer, floodLayer, dispatchLayers, reservoirLayers, monitoringLayer, sceneType]);

  // 动画控制
  useEffect(() => {
    if (!floodData || !animationEnabled) return;

    if (isAnimating) {
      const animate = () => {
        setCurrentTimeIndex(prev => {
          const next = (prev + 1) % floodData.timestamps.length;
          onTimeChange?.(next);
          return next;
        });
      };

      const interval = Math.max(100, 1000 / animationSpeed);
      animationRef.current = setInterval(animate, interval);
    } else {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
    }

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isAnimating, animationSpeed, floodData, animationEnabled, onTimeChange]);

  // 初始化
  useEffect(() => {
    if (floodData) {
      setCurrentTimeIndex(floodData.currentTimeIndex || 0);
    }
    if (dispatchData) {
      setSelectedScenario(dispatchData.selectedScenario || '');
    }
  }, [floodData, dispatchData]);

  // 渲染控制面板
  const renderControls = () => {
    if (!showControls) return null;

    return (
      <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg p-4 shadow-lg max-w-sm">
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          🌊 3D场景控制
        </h3>

        {sceneType === 'flood_simulation' && floodData && (
          <div className="space-y-3 mb-4">
            <label className="block text-sm font-medium">洪水演进控制</label>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">动画播放</span>
                <button
                  onClick={() => setIsAnimating(!isAnimating)}
                  className={`px-3 py-1 rounded text-sm ${
                    isAnimating
                      ? 'bg-red-500 text-white'
                      : 'bg-green-500 text-white'
                  }`}
                >
                  {isAnimating ? '暂停' : '播放'}
                </button>
              </div>

              <div className="space-y-1">
                <label className="text-xs">速度: {animationSpeed}x</label>
                <input
                  type="range"
                  min="0.5"
                  max="5"
                  step="0.5"
                  value={animationSpeed}
                  onChange={(e) => setAnimationSpeed(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div className="text-xs text-gray-600">
                时间: {floodData.timestamps[currentTimeIndex]}
              </div>
            </div>
          </div>
        )}

        {sceneType === 'dispatch_optimization' && dispatchData && (
          <div className="space-y-3 mb-4">
            <label className="block text-sm font-medium">调度方案</label>
            <select
              value={selectedScenario}
              onChange={(e) => {
                setSelectedScenario(e.target.value);
                onScenarioSelect?.(e.target.value);
              }}
              className="w-full p-2 border rounded text-sm"
            >
              {dispatchData.scenarios.map(scenario => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name} (效率: {scenario.efficiency}%)
                </option>
              ))}
            </select>

            {selectedScenario && (
              <div className="text-xs text-gray-600 space-y-1">
                {(() => {
                  const scenario = dispatchData.scenarios.find(s => s.id === selectedScenario);
                  return scenario ? (
                    <>
                      <div>水位: {scenario.waterLevel}m</div>
                      <div>泄洪: {scenario.dischargeRate} m³/s</div>
                      <div>发电: {scenario.powerGeneration} MW</div>
                      <div>风险: {scenario.riskLevel}/10</div>
                    </>
                  ) : null;
                })()}
              </div>
            )}
          </div>
        )}

        <div className="space-y-2">
          <label className="block text-sm font-medium">视角控制</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                // 重置到默认视角
                onViewportChange?.({
                  ...viewport,
                  longitude: 111.0,
                  latitude: 30.8,
                  zoom: 10,
                  pitch: 45,
                  bearing: 0
                });
              }}
              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              重置视角
            </button>
            <button
              onClick={() => {
                // 俯视图
                onViewportChange?.({
                  ...viewport,
                  pitch: 0,
                  bearing: 0
                });
              }}
              className="px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              俯视图
            </button>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t text-xs text-gray-500">
          场景: {sceneType.replace('_', ' ').toUpperCase()}
          <br />
          图层: {layers.length} 层
          <br />
          监测点: {monitoringPoints.length} 个
        </div>
      </div>
    );
  };

  // 渲染时间轴（洪水模拟专用）
  const renderTimeline = () => {
    if (!floodData || sceneType !== 'flood_simulation') return null;

    return (
      <div className="absolute bottom-4 left-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div className="text-sm font-medium">洪水演进时间轴</div>
          <div className="flex-1">
            <input
              type="range"
              min="0"
              max={floodData.timestamps.length - 1}
              value={currentTimeIndex}
              onChange={(e) => {
                const index = Number(e.target.value);
                setCurrentTimeIndex(index);
                onTimeChange?.(index);
              }}
              className="w-full"
            />
          </div>
          <div className="text-sm text-gray-600 min-w-[120px]">
            {floodData.timestamps[currentTimeIndex]}
          </div>
        </div>
      </div>
    );
  };

  // 渲染图例
  const renderLegend = () => {
    const legends = [];

    if (sceneType === 'flood_simulation') {
      legends.push(
        <div key="flood" className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3">
          <h4 className="text-sm font-medium mb-2">洪水淹没图例</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-200 rounded" />
              <span>浅水区</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded" />
              <span>中等水深</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-800 rounded" />
              <span>深水区</span>
            </div>
          </div>
        </div>
      );
    }

    if (monitoringPoints.length > 0) {
      legends.push(
        <div key="monitoring" className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3">
          <h4 className="text-sm font-medium mb-2">监测点状态</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span>正常</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded-full" />
              <span>警告</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <span>危险</span>
            </div>
          </div>
        </div>
      );
    }

    return legends;
  };

  // 计算最终图层
  const finalLayers = useMemo(() => {
    const allLayers = [];

    // 基础图层
    if (terrainLayer) allLayers.push(terrainLayer);
    if (floodLayer) allLayers.push(floodLayer);
    allLayers.push(...dispatchLayers);
    allLayers.push(...reservoirLayers);
    if (monitoringLayer) allLayers.push(monitoringLayer);

    return allLayers;
  }, [terrainLayer, floodLayer, dispatchLayers, reservoirLayers, monitoringLayer]);

  // 处理视角变化
  const handleViewStateChange = useCallback(({ viewState }) => {
    onViewportChange?.(viewState);
    return viewState;
  }, [onViewportChange]);

  return (
    <div className={`scene-3d-viewer relative w-full h-full ${className || ''}`} style={style}>
      <DeckGL
        initialViewState={viewport}
        controller={true}
        layers={finalLayers}
        effects={[lightingEffect]}
        onViewStateChange={handleViewStateChange}
        getTooltip={({ object }) => {
          if (!object) return null;

          // 洪水数据提示
          if (object.elevation !== undefined) {
            return {
              html: `
                <div class="p-2 text-sm">
                  <div class="font-medium">洪水淹没</div>
                  <div>水深: ${object.elevation.toFixed(1)}m</div>
                  <div>强度: ${(object.opacity * 100).toFixed(0)}%</div>
                </div>
              `
            };
          }

          // 监测点提示
          if (object.type) {
            return {
              html: `
                <div class="p-2 text-sm">
                  <div class="font-medium">${object.name || '监测点'}</div>
                  <div>类型: ${object.type}</div>
                  <div>状态: ${object.status}</div>
                  <div>数值: ${object.value} ${object.unit}</div>
                </div>
              `
            };
          }

          return null;
        }}
      />

      {showControls && renderControls()}
      {renderTimeline()}
      {renderLegend()}

      {/* 场景信息面板 */}
      <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 max-w-xs">
        <h4 className="text-sm font-medium mb-2">场景信息</h4>
        <div className="text-xs text-gray-600 space-y-1">
          <div>类型: {sceneType.replace('_', ' ').toUpperCase()}</div>
          <div>视角: {viewport.pitch.toFixed(0)}°俯仰, {viewport.bearing.toFixed(0)}°方位</div>
          <div>缩放: {viewport.zoom.toFixed(1)}x</div>
          <div>图层: {finalLayers.length} 层</div>
          {isAnimating && (
            <div className="flex items-center gap-1 text-blue-600">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
              动画播放中...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Scene3DViewer;