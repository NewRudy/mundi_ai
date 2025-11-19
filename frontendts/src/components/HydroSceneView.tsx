/**
 * HydroSceneView - 水电专业场景主视图组件
 * 集成所有3D可视化、场景管理和多屏控制功能
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
  Globe,
  Map,
  BarChart3,
  Settings,
  Play,
  Pause,
  RotateCcw,
  Download,
  Share2,
  Maximize2
} from 'lucide-react';

// 导入所有组件
import CesiumViewer from './CesiumViewer';
import SceneController from './SceneController';
import Scene3DViewer from './Scene3DViewer';
import MultiScreenController from './MultiScreenController';
import { useSceneStore, SceneType } from '../store/useSceneStore';

interface HydroSceneViewProps {
  projectId: string;
  className?: string;
  onSceneChange?: (scene: SceneType) => void;
  // 3D场景数据
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
  projectId,
  className,
  onSceneChange,
  hydroScene
}) => {
  // 使用传入的3D场景数据或使用默认值
  const currentScene = hydroScene?.currentScene || 'normal';
  const [activeTab, setActiveTab] = useState<'2d' | '3d' | 'charts' | 'control'>('2d');
  const [isAnimating, setIsAnimating] = useState(hydroScene?.animationEnabled || false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(hydroScene?.currentTimeIndex || 0);
  const [showMultiScreen, setShowMultiScreen] = useState(false);
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

  // 根据当前场景生成数据
  const sceneData = generateMockData(currentScene as SceneType);

  // 获取场景配置
  const getSceneConfig = useCallback((scene: SceneType) => {
    switch (scene) {
      case 'normal':
        return { name: '普通模式', defaultView: '2d', color: '#6b7280' };
      case 'inspection':
        return { name: '智能巡检', defaultView: '2d', color: '#10b981' };
      case 'emergency':
        return { name: '应急响应', defaultView: '3d', color: '#ef4444' };
      case 'dispatch':
        return { name: '调度决策', defaultView: 'charts', color: '#f59e0b' };
      case 'analysis':
        return { name: '数据分析', defaultView: 'charts', color: '#8b5cf6' };
      default:
        return { name: '普通模式', defaultView: '2d', color: '#6b7280' };
    }
  }, []);

  const currentConfig = getSceneConfig(currentScene as SceneType);

  // 处理场景变化
  const handleSceneChange = useCallback((scene: SceneType, context?: any) => {
    console.log(`场景切换到: ${scene}`, context);
    onSceneChange?.(scene);

    // 根据场景类型自动选择最佳视图
    const config = getSceneConfig(scene);
    if (config.defaultView) {
      setActiveTab(config.defaultView as any);
    }
  }, [onSceneChange, getSceneConfig]);

  // 处理时间轴变化
  const handleTimeChange = useCallback((timeIndex: number) => {
    setCurrentTimeIndex(timeIndex);
  }, []);

  // 处理视角变化
  const handleViewportChange = useCallback((newViewport: any) => {
    setViewport(newViewport);
  }, []);

  // 渲染2D地图视图
  const render2DMap = () => (
    <div className="relative w-full h-full">
      {/* 这里可以集成现有的MapLibreMap组件 */}
      <div className="w-full h-full bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <Map className="h-16 w-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-600">2D地图视图</h3>
          <p className="text-sm text-gray-500">集成MapLibre GL JS</p>
          <p className="text-xs text-gray-400 mt-2">当前场景: {currentConfig.name}</p>
        </div>
      </div>

      {/* 场景特定的2D覆盖层 */}
      {currentScene === 'inspection' && sceneData.monitoringPoints && (
        <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-4">
          <h4 className="font-medium mb-2">监测点概览</h4>
          <div className="space-y-2">
            {sceneData.monitoringPoints.map((point: any) => (
              <div key={point.id} className="flex items-center gap-2 text-sm">
                <div className={`w-3 h-3 rounded-full ${
                  point.status === 'normal' ? 'bg-green-500' :
                  point.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                <span>{point.name}</span>
                <span className="text-gray-500">{point.value}{point.unit}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

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
          showControls={true}
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
          showControls={true}
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
      />
    );
  };

  // 渲染数据分析视图
  const renderCharts = () => (
    <div className="w-full h-full bg-white p-4">
      <div className="grid grid-cols-2 gap-4 h-full">
        {/* 水位趋势图 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              水位趋势
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-4rem)]">
            <div className="w-full h-full bg-gray-50 rounded flex items-center justify-center">
              <span className="text-gray-500">水位趋势图表</span>
            </div>
          </CardContent>
        </Card>

        {/* 流量分析图 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              流量分析
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-4rem)]">
            <div className="w-full h-full bg-gray-50 rounded flex items-center justify-center">
              <span className="text-gray-500">流量分析图表</span>
            </div>
          </CardContent>
        </Card>

        {/* 发电效率图 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              发电效率
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-4rem)]">
            <div className="w-full h-full bg-gray-50 rounded flex items-center justify-center">
              <span className="text-gray-500">发电效率图表</span>
            </div>
          </CardContent>
        </Card>

        {/* 异常检测图 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              异常检测
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-4rem)]">
            <div className="w-full h-full bg-gray-50 rounded flex items-center justify-center">
              <span className="text-gray-500">异常检测图表</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  // 渲染控制面板
  const renderControlPanel = () => (
    <div className="w-full h-full">
      <SceneController onSceneChange={handleSceneChange} />
    </div>
  );

  // 渲染工具栏
  const renderToolbar = () => (
    <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
      {/* 动画控制（仅在洪水模拟时显示） */}
      {currentScene === 'emergency' && (
        <Button
          size="sm"
          onClick={() => setIsAnimating(!isAnimating)}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {isAnimating ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
      )}

      {/* 视角重置 */}
      <Button
        size="sm"
        variant="outline"
        onClick={() => setViewport({
          longitude: 111.0,
          latitude: 30.8,
          zoom: 8,
          pitch: 0,
          bearing: 0
        })}
      >
        <RotateCcw className="h-4 w-4" />
      </Button>

      {/* 多屏控制 */}
      <Button
        size="sm"
        variant="outline"
        onClick={() => setShowMultiScreen(!showMultiScreen)}
        className={showMultiScreen ? 'bg-blue-100' : ''}
      >
        <Maximize2 className="h-4 w-4" />
      </Button>

      {/* 导出功能 */}
      <Button size="sm" variant="outline">
        <Download className="h-4 w-4" />
      </Button>

      {/* 分享功能 */}
      <Button size="sm" variant="outline">
        <Share2 className="h-4 w-4" />
      </Button>
    </div>
  );

  return (
    <div className={`hydro-scene-view w-full h-full relative ${className || ''}`}>
      {/* 状态栏 */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-blue-600 to-blue-700 text-white p-3 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">{currentConfig.icon}</div>
            <div>
              <h2 className="text-lg font-semibold">{currentConfig.name}</h2>
              <p className="text-sm opacity-90">{currentConfig.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`${currentConfig.bgColor} text-white border-none`}>
              {currentConfig.name}
            </Badge>
            <Badge variant="outline" className="text-white border-white/30">
              项目: {projectId}
            </Badge>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="pt-20 h-full">
        {/* 多屏控制面板（可折叠） */}
        {showMultiScreen && (
          <div className="absolute top-20 left-4 right-4 z-20">
            <MultiScreenController className="shadow-xl" />
          </div>
        )}

        {/* 视图切换标签 */}
        <div className="h-full flex flex-col">
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="flex-1">
            <div className="px-4 border-b bg-white/80 backdrop-blur-sm">
              <TabsList className="grid grid-cols-4 w-full max-w-md">
                <TabsTrigger value="2d" className="flex items-center gap-2">
                  <Map className="h-4 w-4" />
                  2D地图
                </TabsTrigger>
                <TabsTrigger value="3d" className="flex items-center gap-2">
                  <Globe className="h-4 w-4" />
                  3D场景
                </TabsTrigger>
                <TabsTrigger value="charts" className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  数据分析
                </TabsTrigger>
                <TabsTrigger value="control" className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  场景控制
                </TabsTrigger>
              </TabsList>
            </div>

            {/* 工具栏 */}
            {renderToolbar()}

            {/* 内容区域 */}
            <div className="flex-1 p-4">
              <TabsContent value="2d" className="mt-0 h-full">
                {render2DMap()}
              </TabsContent>

              <TabsContent value="3d" className="mt-0 h-full">
                {render3DScene()}
              </TabsContent>

              <TabsContent value="charts" className="mt-0 h-full">
                {renderCharts()}
              </TabsContent>

              <TabsContent value="control" className="mt-0 h-full">
                {renderControlPanel()}
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default HydroSceneView;