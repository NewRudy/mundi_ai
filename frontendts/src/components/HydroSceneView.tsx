/**
 * HydroSceneView - 水电专业场景主视图组件
 * 集成所有3D可视化、场景管理和多屏控制功能
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
  Play,
  Pause,
  RotateCcw,
  Download,
  Share2,
  Maximize2,
  Settings
} from 'lucide-react';

// 导入所有组件
import CesiumViewer from './CesiumViewer';
import SceneController from './SceneController';
import Scene3DViewer from './Scene3DViewer';
import MultiScreenController from './MultiScreenController';
import { useSceneStore, SceneType } from '../store/useSceneStore';
import LayerList from '@/components/LayerList';
import { MicButton } from '@/components/MicButton';
import { BasemapControl } from './BasemapControl';
import { useViewModeToggle } from '@/components/ViewModeToggle';
import { XunfeiIatEngine } from '@/asr/xunfei';

// Types
import type { MapProject, MapData, MapTreeResponse, Conversation, EphemeralAction, ErrorEntry, UploadingFile } from '../lib/types';
import { ReadyState } from 'react-use-websocket';

interface HydroSceneViewProps {
  mapId: string;
  project: MapProject;
  mapData?: MapData | null;
  mapTree: MapTreeResponse | null;
  conversationId: number | null;
  conversations: Conversation[];
  conversationsEnabled: boolean;
  setConversationId: (conversationId: number | null) => void;
  readyState: number;
  openDropzone?: () => void;
  uploadingFiles?: UploadingFile[];
  hiddenLayerIDs: string[];
  toggleLayerVisibility: (layerId: string) => void;
  activeActions: EphemeralAction[];
  setActiveActions: React.Dispatch<React.SetStateAction<EphemeralAction[]>>;
  addError: (message: string, shouldOverrideMessages?: boolean, sourceId?: string) => void;
  dismissError: (errorId: string) => void;
  errors: ErrorEntry[];
  invalidateProjectData: () => void;
  invalidateMapData: () => void;
  className?: string;
  onSceneChange?: (scene: SceneType) => void;
  hydroScene?: any;
}

// 模拟数据生成器
const generateMockData = (sceneType: SceneType) => {
  switch (sceneType) {
    case 'inspection':
      return {
        monitoringPoints: [
          {
            id: 'sanzha_001',
            name: '三峡大坝',
            longitude: 111.006,
            latitude: 30.827,
            height: 185,
            type: 'dam',
            status: 'normal',
            value: 175.2,
            unit: 'm',
            timestamp: new Date().toISOString()
          },
          {
            id: 'danjiangkou_001',
            name: '丹江口水库',
            longitude: 111.516,
            latitude: 32.774,
            height: 162,
            type: 'reservoir',
            status: 'warning',
            value: 168.5,
            unit: 'm',
            timestamp: new Date().toISOString()
          },
          {
            id: 'yichang_001',
            name: '宜昌水文站',
            longitude: 111.286,
            latitude: 30.691,
            height: 45,
            type: 'hydrology',
            status: 'normal',
            value: 32450,
            unit: 'm³/s',
            timestamp: new Date().toISOString()
          }
        ]
      };

    case 'emergency':
      return {
        floodData: {
          extent: {
            west: 110.5,
            south: 30.5,
            east: 111.5,
            north: 31.0
          },
          waterLevels: Array(30).fill(0).map(() =>
            Array(50).fill(0).map(() => Math.random() * 15)
          ),
          timestamps: Array(24).fill(0).map((_, i) =>
            `${String(i).padStart(2, '0')}:00`
          ),
          currentTimeIndex: 12,
          maxWaterLevel: 15,
          animationSpeed: 1
        }
      };

    case 'dispatch':
      return {
        scenarios: [
          {
            id: 'scenario_a',
            name: '方案A - 发电优先',
            waterLevel: 175.0,
            dischargeRate: 20000,
            powerGeneration: 12500,
            efficiency: 85,
            riskLevel: 3,
            color: '#10b981'
          },
          {
            id: 'scenario_b',
            name: '方案B - 防洪优先',
            waterLevel: 150.5,
            dischargeRate: 45000,
            powerGeneration: 8800,
            efficiency: 65,
            riskLevel: 1,
            color: '#ef4444'
          },
          {
            id: 'scenario_c',
            name: '方案C - 均衡调度',
            waterLevel: 165.2,
            dischargeRate: 30000,
            powerGeneration: 10500,
            efficiency: 75,
            riskLevel: 2,
            color: '#f59e0b'
          }
        ],
        selectedScenario: 'scenario_c'
      };

    default:
      return {};
  }
};

const HydroSceneView: React.FC<HydroSceneViewProps> = ({
  mapId,
  project,
  mapData,
  mapTree,
  conversationId,
  conversations,
  conversationsEnabled,
  setConversationId,
  readyState,
  openDropzone,
  uploadingFiles,
  hiddenLayerIDs,
  toggleLayerVisibility,
  activeActions,
  setActiveActions,
  addError,
  dismissError,
  errors,
  invalidateProjectData,
  invalidateMapData,
  className,
  onSceneChange,
  hydroScene
}) => {
  // 使用传入的3D场景数据或使用默认值
  const currentScene = hydroScene?.currentScene || 'normal';
  const [isAnimating, setIsAnimating] = useState(hydroScene?.animationEnabled || false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(hydroScene?.currentTimeIndex || 0);
  const [showMultiScreen, setShowMultiScreen] = useState(false);
  const [showSceneController, setShowSceneController] = useState(false);
  const [viewport, setViewport] = useState<
    { longitude: number; latitude: number; zoom: number; pitch: number; bearing: number }
  >(
    hydroScene?.viewport || {
      longitude: 111.0,
      latitude: 30.8,
      zoom: 8,
      pitch: 0,
      bearing: 0
    }
  );

  // Dummy ref for LayerList since we don't have a MapLibre map
  const mapRef = useRef(null);
  const [zoomHistory, setZoomHistory] = useState<Array<{ bounds: [number, number, number, number] }>>([]);
  const [zoomHistoryIndex, setZoomHistoryIndex] = useState(-1);
  const [layerSymbols, setLayerSymbols] = useState<{ [layerId: string]: JSX.Element }>({});
  const [showAttributeTable, setShowAttributeTable] = useState(false);
  const [selectedLayer, setSelectedLayer] = useState<any>(null);
  const [assistantExpanded, setAssistantExpanded] = useState(false);

  // 初始化ViewModeToggle控件
  useViewModeToggle(null); // Pass null as we don't have a MapLibre instance

  // 根据当前场景生成数据
  const sceneData = generateMockData(currentScene as SceneType);

  // 获取场景配置
  const getSceneConfig = useCallback((scene: SceneType) => {
    switch (scene) {
      case 'normal':
        return { name: '普通模式', color: '#6b7280' };
      case 'inspection':
        return { name: '智能巡检', color: '#10b981' };
      case 'emergency':
        return { name: '应急响应', color: '#ef4444' };
      case 'dispatch':
        return { name: '调度决策', color: '#f59e0b' };
      case 'analysis':
        return { name: '数据分析', color: '#8b5cf6' };
      default:
        return { name: '普通模式', color: '#6b7280' };
    }
  }, []);

  const currentConfig = getSceneConfig(currentScene as SceneType);

  // 处理场景变化
  const handleSceneChange = useCallback((scene: SceneType, context?: any) => {
    console.log(`场景切换到: ${scene}`, context);
    onSceneChange?.(scene);
  }, [onSceneChange]);

  // 处理时间轴变化
  const handleTimeChange = useCallback((timeIndex: number) => {
    setCurrentTimeIndex(timeIndex);
  }, []);

  // 处理视角变化
  const handleViewportChange = useCallback((newViewport: any) => {
    setViewport(newViewport);
  }, []);

  // 渲染3D场景视图
  const render3DScene = () => {
    if (currentScene === 'emergency' && sceneData.floodData) {
      return (
        <Scene3DViewer
          sceneType="flood_simulation"
          viewport={viewport}
          floodData={sceneData.floodData}
          onViewportChange={handleViewportChange}
          onTimeChange={handleTimeChange}
          showControls={false} // Hide internal controls
          animationEnabled={isAnimating}
        />
      );
    }

    if (currentScene === 'dispatch' && sceneData.scenarios) {
      return (
        <Scene3DViewer
          sceneType="dispatch_optimization"
          viewport={viewport}
          dispatchData={sceneData}
          onViewportChange={handleViewportChange}
          onScenarioSelect={(scenarioId) => {
            console.log('选中方案:', scenarioId);
          }}
          showControls={false} // Hide internal controls
        />
      );
    }

    // 默认3D视图（Cesium地球）
    return (
      <CesiumViewer
        initialCamera={{
          longitude: viewport.longitude,
          latitude: viewport.latitude,
          height: 10000,
          pitch: -45
        }}
        monitoringPoints={sceneData.monitoringPoints || []}
        onCameraChange={handleViewportChange}
        showInternalControls={false} // Hide internal controls
      />
    );
  };

  return (
    <div className={`hydro-scene-view w-full h-full relative ${className || ''}`}>
      {/* 3D Scene Background */}
      <div className="absolute inset-0 z-0">
        {render3DScene()}
      </div>

      {/* Top Left - Layer List */}
      <LayerList
        project={project}
        currentMapData={mapData || { project_id: project.id, map_id: mapId, layers: [] }}
        mapRef={mapRef}
        openDropzone={openDropzone || (() => { })}
        activeActions={activeActions}
        readyState={readyState}
        isInConversation={!!conversationId}
        setShowAttributeTable={setShowAttributeTable}
        setSelectedLayer={setSelectedLayer}
        updateMapData={invalidateMapData}
        layerSymbols={layerSymbols}
        zoomHistory={zoomHistory}
        zoomHistoryIndex={zoomHistoryIndex}
        setZoomHistoryIndex={setZoomHistoryIndex}
        uploadingFiles={uploadingFiles}
        demoConfig={{ available: false, description: '' }}
        hiddenLayerIDs={hiddenLayerIDs}
        toggleLayerVisibility={toggleLayerVisibility}
        errors={errors}
      />

      {/* Top Right - Scene Controls & Tools */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
        {/* Scene Mode Badge */}
        <div className="bg-white/90 backdrop-blur-sm rounded-md p-2 shadow-md flex items-center gap-2">
          <Badge className={`${currentConfig.color} text-white border-none`}>
            {currentConfig.name}
          </Badge>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0"
            onClick={() => setShowSceneController(!showSceneController)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>

        {/* Scene Controller Panel (Collapsible) */}
        {showSceneController && (
          <div className="bg-white/90 backdrop-blur-sm rounded-md p-2 shadow-md w-64">
            <SceneController onSceneChange={handleSceneChange} />
          </div>
        )}

        {/* Animation Controls (Emergency Mode) */}
        {currentScene === 'emergency' && (
          <div className="bg-white/90 backdrop-blur-sm rounded-md p-2 shadow-md">
            <Button
              size="sm"
              onClick={() => setIsAnimating(!isAnimating)}
              className="w-full bg-blue-600 hover:bg-blue-700"
            >
              {isAnimating ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              {isAnimating ? '暂停模拟' : '开始模拟'}
            </Button>
          </div>
        )}

        {/* View Controls */}
        <div className="bg-white/90 backdrop-blur-sm rounded-md p-1 shadow-md flex flex-col gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setViewport({
              longitude: 111.0,
              latitude: 30.8,
              zoom: 8,
              pitch: 0,
              bearing: 0
            })}
            title="重置视角"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowMultiScreen(!showMultiScreen)}
            className={showMultiScreen ? 'bg-blue-100' : ''}
            title="多屏控制"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="ghost" title="导出">
            <Download className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="ghost" title="分享">
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Bottom Left - Basemap Control */}
      <div className="absolute bottom-8 left-4 z-10">
        <BasemapControl
          currentBasemap="satellite" // Default to satellite for 3D
          onBasemapChange={(style) => console.log('Basemap changed:', style)}
          availableBasemaps={['satellite', 'streets', 'dark']} // Mock available basemaps
          displayNames={{ satellite: '卫星影像', streets: '街道地图', dark: '暗色模式' }}
        />
      </div>

      {/* Bottom Center - Mic Button */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-20">
        <MicButton
          onStateChange={(state) => console.log('Mic state:', state)}
          onTranscript={(text) => console.log('Transcript:', text)}
          engine={new XunfeiIatEngine()}
        />
      </div>

      {/* Multi-screen Controller Overlay */}
      {showMultiScreen && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-20">
          <MultiScreenController className="shadow-xl" />
        </div>
      )}

      {/* Monitoring Points Overlay (Inspection Mode) */}
      {currentScene === 'inspection' && sceneData.monitoringPoints && (
        <div className="absolute top-20 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-4 shadow-md z-10 max-w-xs">
          <h4 className="font-medium mb-2 text-sm">监测点概览</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {sceneData.monitoringPoints.map((point: any) => (
              <div key={point.id} className="flex items-center gap-2 text-xs p-1 hover:bg-gray-100 rounded cursor-pointer">
                <div className={`w-2 h-2 rounded-full ${point.status === 'normal' ? 'bg-green-500' :
                    point.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                  }`} />
                <span className="font-medium">{point.name}</span>
                <span className="text-gray-500 ml-auto">{point.value}{point.unit}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default HydroSceneView;
