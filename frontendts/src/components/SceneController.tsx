/**
 * SceneController - 场景控制器组件
 * 提供三种场景触发方式：手动切换、AI建议、阈值自动
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useSceneStore, SCENE_CONFIGS, SceneType } from '../store/useSceneStore';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  AlertTriangle,
  Brain,
  Settings,
  TrendingUp,
  Search,
  Zap,
  BarChart3,
  Map,
  Eye,
  EyeOff,
  RefreshCw,
  Check,
  X,
  Bell,
  BellOff
} from 'lucide-react';

interface SceneControllerProps {
  className?: string;
  onSceneChange?: (scene: SceneType, context?: any) => void;
}

interface AISuggestion {
  scene: SceneType;
  reason: string;
  confidence: number;
  timestamp: Date;
}

interface ThresholdAlert {
  type: 'water_level' | 'flow_rate' | 'rainfall' | 'anomaly';
  value: number;
  threshold: number;
  severity: 'warning' | 'danger' | 'critical';
  message: string;
  location: string;
  timestamp: Date;
}

const SceneController: React.FC<SceneControllerProps> = ({
  className,
  onSceneChange
}) => {
  const {
    currentScene,
    setScene,
    preferences,
    setPreference,
    sceneData
  } = useSceneStore();

  const [aiSuggestion, setAiSuggestion] = useState<AISuggestion | null>(null);
  const [thresholdAlerts, setThresholdAlerts] = useState<ThresholdAlert[]>([]);
  const [isAutoMode, setIsAutoMode] = useState(true);
  const [lastAutoSwitch, setLastAutoSwitch] = useState<Date | null>(null);

  // AI建议处理
  useEffect(() => {
    const handleAISuggestion = (event: CustomEvent) => {
      const { scene, reason, confidence = 0.8 } = event.detail;

      setAiSuggestion({
        scene,
        reason,
        confidence,
        timestamp: new Date()
      });

      // 自动接受高置信度建议
      if (confidence > 0.9 && preferences.autoSwitchScenes) {
        handleAcceptAISuggestion(scene);
      }
    };

    window.addEventListener('ai-scene-suggestion', handleAISuggestion as EventListener);
    return () => window.removeEventListener('ai-scene-suggestion', handleAISuggestion as EventListener);
  }, [preferences.autoSwitchScenes]);

  // 阈值监控（模拟实时数据）
  useEffect(() => {
    if (!preferences.thresholdAlerts) return;

    const checkThresholds = () => {
      // 模拟实时数据检查
      const mockData = generateMockThresholdData();
      const newAlerts: ThresholdAlert[] = [];

      // 水位检查
      if (mockData.waterLevel > 175.0) {
        newAlerts.push({
          type: 'water_level',
          value: mockData.waterLevel,
          threshold: 175.0,
          severity: mockData.waterLevel > 180 ? 'critical' : 'danger',
          message: `水位超过警戒线：${mockData.waterLevel.toFixed(1)}m`,
          location: '三峡大坝',
          timestamp: new Date()
        });
      }

      // 流量检查
      if (mockData.flowRate > 50000) {
        newAlerts.push({
          type: 'flow_rate',
          value: mockData.flowRate,
          threshold: 50000,
          severity: 'warning',
          message: `流量异常：${mockData.flowRate.toFixed(0)} m³/s`,
          location: '宜昌站',
          timestamp: new Date()
        });
      }

      // 异常检测
      if (mockData.anomalyScore > 0.8) {
        newAlerts.push({
          type: 'anomaly',
          value: mockData.anomalyScore,
          threshold: 0.8,
          severity: mockData.anomalyScore > 0.9 ? 'danger' : 'warning',
          message: `检测到${mockData.anomalyScore > 0.9 ? '严重' : '中度'}异常`,
          location: '监测网络',
          timestamp: new Date()
        });
      }

      if (newAlerts.length > 0) {
        setThresholdAlerts(prev => [...prev, ...newAlerts].slice(-10)); // 保留最近10条

        // 自动切换到应急模式
        if (preferences.autoSwitchScenes) {
          const hasCritical = newAlerts.some(alert => alert.severity === 'critical');
          if (hasCritical && currentScene !== 'emergency') {
            handleAutoSwitch('emergency', '检测到严重异常，自动切换至应急响应模式');
          }
        }
      }
    };

    const interval = setInterval(checkThresholds, 30000); // 30秒检查一次
    return () => clearInterval(interval);
  }, [preferences.thresholdAlerts, preferences.autoSwitchScenes, currentScene]);

  // 场景切换处理
  const handleSceneChange = useCallback(async (scene: SceneType, context?: any) => {
    try {
      await setScene(scene, context);
      onSceneChange?.(scene, context);

      // 清除相关建议/警报
      if (aiSuggestion?.scene === scene) {
        setAiSuggestion(null);
      }
    } catch (error) {
      console.error('场景切换失败:', error);
    }
  }, [setScene, onSceneChange, aiSuggestion]);

  // AI建议处理
  const handleAcceptAISuggestion = (scene: SceneType) => {
    handleSceneChange(scene, { source: 'ai_suggestion', reason: aiSuggestion?.reason });
    setAiSuggestion(null);
  };

  const handleRejectAISuggestion = () => {
    setAiSuggestion(null);
  };

  // 自动切换处理
  const handleAutoSwitch = (scene: SceneType, reason: string) => {
    if (!isAutoMode) return;

    setLastAutoSwitch(new Date());
    handleSceneChange(scene, { source: 'auto_threshold', reason });
  };

  // 手动模式切换
  const toggleAutoMode = () => {
    setIsAutoMode(!isAutoMode);
    if (!isAutoMode) {
      setAiSuggestion(null);
      setThresholdAlerts([]);
    }
  };

  // 清除警报
  const dismissAlert = (index: number) => {
    setThresholdAlerts(prev => prev.filter((_, i) => i !== index));
  };

  // 清除所有警报
  const dismissAllAlerts = () => {
    setThresholdAlerts([]);
  };

  // 生成模拟阈值数据
  const generateMockThresholdData = () => ({
    waterLevel: 174.5 + Math.random() * 2, // 174.5-176.5
    flowRate: 45000 + Math.random() * 15000, // 45000-60000
    rainfall: Math.random() * 50, // 0-50mm
    anomalyScore: Math.random() // 0-1
  });

  // 渲染场景选择器
  const renderSceneSelector = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(SCENE_CONFIGS).map(([sceneType, config]) => {
          const isActive = currentScene === sceneType;
          const isTransitioning = useSceneStore.getState().isTransitioning;

          return (
            <Button
              key={sceneType}
              onClick={() => handleSceneChange(sceneType as SceneType)}
              disabled={isTransitioning}
              className={`
                relative h-20 flex-col items-center justify-center gap-2
                ${isActive
                  ? `${config.bgColor} text-white shadow-lg scale-105`
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }
                ${isTransitioning ? 'opacity-50 cursor-not-allowed' : ''}
                transition-all duration-200
              `}
            >
              <div className="text-2xl">{config.icon}</div>
              <div className="text-xs font-medium text-center leading-tight">
                {config.name}
              </div>
              {isActive && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
              )}
            </Button>
          );
        })}
      </div>

      {/* 当前场景信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="text-lg">{SCENE_CONFIGS[currentScene].icon}</div>
          <div className="font-medium text-blue-900">
            {SCENE_CONFIGS[currentScene].name}
          </div>
          <Badge variant="outline" className="ml-auto">
            当前模式
          </Badge>
        </div>
        <p className="text-sm text-blue-700">
          {SCENE_CONFIGS[currentScene].description}
        </p>
        <div className="flex flex-wrap gap-1 mt-2">
          {SCENE_CONFIGS[currentScene].features.map((feature, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              {feature}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );

  // 渲染AI建议面板
  const renderAISuggestion = () => {
    if (!aiSuggestion) return null;

    const config = SCENE_CONFIGS[aiSuggestion.scene];
    const timeAgo = getTimeAgo(aiSuggestion.timestamp);

    return (
      <Alert className="border-blue-200 bg-blue-50">
        <Brain className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-900">
          💡 AI智能建议
          <span className="text-xs font-normal text-blue-600 ml-2">
            置信度: {(aiSuggestion.confidence * 100).toFixed(0)}%
          </span>
        </AlertTitle>
        <AlertDescription className="text-blue-800">
          <div className="space-y-2">
            <p>{aiSuggestion.reason}</p>
            <div className="flex items-center gap-2">
              <span className="text-sm">建议切换到:</span>
              <Badge className={`${config.bgColor} text-white`}>
                {config.icon} {config.name}
              </Badge>
            </div>
            <div className="flex gap-2 mt-3">
              <Button
                size="sm"
                onClick={() => handleAcceptAISuggestion(aiSuggestion.scene)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Check className="h-3 w-3 mr-1" />
                接受建议
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRejectAISuggestion}
                className="border-blue-200 text-blue-700 hover:bg-blue-100"
              >
                <X className="h-3 w-3 mr-1" />
                忽略
              </Button>
            </div>
          </div>
          <div className="text-xs text-blue-600 mt-2">
            {timeAgo}
          </div>
        </AlertDescription>
      </Alert>
    );
  };

  // 渲染阈值警报
  const renderThresholdAlerts = () => {
    if (thresholdAlerts.length === 0) return null;

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <span className="font-medium text-red-900">阈值警报</span>
            <Badge variant="destructive" className="text-xs">
              {thresholdAlerts.length}
            </Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={dismissAllAlerts}
            className="text-red-600 hover:text-red-700"
          >
            清除全部
          </Button>
        </div>

        <div className="max-h-48 overflow-y-auto space-y-2">
          {thresholdAlerts.map((alert, index) => (
            <Alert
              key={index}
              className={`
                ${getAlertColorClass(alert.severity)}
                border-l-4 ${getAlertBorderColor(alert.severity)}
              `}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <AlertTitle className={getAlertTextColor(alert.severity)}>
                    {getAlertIcon(alert.severity)} {alert.message}
                  </AlertTitle>
                  <AlertDescription className={`text-xs ${getAlertTextColor(alert.severity)} opacity-80`}>
                    <div className="flex flex-wrap gap-2 mt-1">
                      <span>位置: {alert.location}</span>
                      <span>数值: {alert.value.toFixed(2)}</span>
                      <span>阈值: {alert.threshold}</span>
                      <span>{getTimeAgo(alert.timestamp)}</span>
                    </div>
                  </AlertDescription>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => dismissAlert(index)}
                  className={`ml-2 ${getAlertTextColor(alert.severity)} hover:opacity-70`}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </Alert>
          ))}
        </div>
      </div>
    );
  };

  // 渲染控制设置
  const renderControlSettings = () => (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="auto-mode" className="flex items-center gap-2">
            {isAutoMode ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            自动模式
          </Label>
          <Switch
            id="auto-mode"
            checked={isAutoMode}
            onCheckedChange={toggleAutoMode}
          />
        </div>

        {isAutoMode && (
          <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
            自动模式下，系统会根据数据阈值和AI建议自动切换场景
            {lastAutoSwitch && (
              <div className="text-xs text-gray-500 mt-1">
                上次自动切换: {getTimeAgo(lastAutoSwitch)}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <Label className="font-medium">触发方式设置</Label>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="threshold-alerts" className="text-sm">
              <Bell className="h-3 w-3 inline mr-1" />
              阈值警报
            </Label>
            <Switch
              id="threshold-alerts"
              checked={preferences.thresholdAlerts}
              onCheckedChange={(checked) => setPreference('thresholdAlerts', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="ai-suggestions" className="text-sm">
              <Brain className="h-3 w-3 inline mr-1" />
              AI建议
            </Label>
            <Switch
              id="ai-suggestions"
              checked={preferences.aiSuggestions}
              onCheckedChange={(checked) => setPreference('aiSuggestions', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="auto-switch" className="text-sm">
              <RefreshCw className="h-3 w-3 inline mr-1" />
              自动切换
            </Label>
            <Switch
              id="auto-switch"
              checked={preferences.autoSwitchScenes}
              onCheckedChange={(checked) => setPreference('autoSwitchScenes', checked)}
            />
          </div>
        </div>
      </div>

      {/* 当前状态指示 */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">当前状态</span>
          <Badge
            variant={isAutoMode ? "default" : "secondary"}
            className={isAutoMode ? "bg-green-500" : ""}
          >
            {isAutoMode ? "自动" : "手动"}
          </Badge>
        </div>
        <div className="text-xs text-gray-600 space-y-1">
          <div>场景: {SCENE_CONFIGS[currentScene].name}</div>
          <div>触发: {getTriggerStatus()}</div>
          <div>数据: {getDataStatus()}</div>
        </div>
      </div>
    </div>
  );

  // 辅助函数
  const getAlertColorClass = (severity: string) => {
    switch (severity) {
      case 'warning': return 'bg-yellow-50 border-yellow-200';
      case 'danger': return 'bg-orange-50 border-orange-200';
      case 'critical': return 'bg-red-50 border-red-200';
      default: return 'bg-blue-50 border-blue-200';
    }
  };

  const getAlertBorderColor = (severity: string) => {
    switch (severity) {
      case 'warning': return 'border-yellow-400';
      case 'danger': return 'border-orange-400';
      case 'critical': return 'border-red-400';
      default: return 'border-blue-400';
    }
  };

  const getAlertTextColor = (severity: string) => {
    switch (severity) {
      case 'warning': return 'text-yellow-800';
      case 'danger': return 'text-orange-800';
      case 'critical': return 'text-red-800';
      default: return 'text-blue-800';
    }
  };

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'warning': return '⚠️';
      case 'danger': return '🚨';
      case 'critical': return '💥';
      default: return '📊';
    }
  };

  const getTimeAgo = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor(diff / 1000);

    if (seconds < 60) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    return `${Math.floor(minutes / 60)}小时前`;
  };

  const getTriggerStatus = () => {
    const active = [];
    if (preferences.thresholdAlerts) active.push('阈值监控');
    if (preferences.aiSuggestions) active.push('AI建议');
    if (preferences.autoSwitchScenes) active.push('自动切换');
    return active.join('、') || '无';
  };

  const getDataStatus = () => {
    const { sceneData } = useSceneStore.getState();
    const currentData = sceneData[currentScene];

    if (!currentData) return '无数据';

    const hasData = Object.values(currentData).some(value =>
      Array.isArray(value) ? value.length > 0 : Boolean(value)
    );

    return hasData ? '已加载' : '加载中';
  };

  return (
    <Card className={`scene-controller ${className || ''}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            场景控制中心
          </div>
          <Badge
            variant="outline"
            className={`${SCENE_CONFIGS[currentScene].bgColor} text-white`}
          >
            {SCENE_CONFIGS[currentScene].icon} {SCENE_CONFIGS[currentScene].name}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        <Tabs defaultValue="scenes" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="scenes" className="flex items-center gap-2">
              <Map className="h-4 w-4" />
              场景选择
            </TabsTrigger>
            <TabsTrigger value="alerts" className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              警报中心
              {thresholdAlerts.length > 0 && (
                <Badge variant="destructive" className="ml-1 text-xs">
                  {thresholdAlerts.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              设置
            </TabsTrigger>
          </TabsList>

          <TabsContent value="scenes" className="mt-4">
            {renderSceneSelector()}
            {aiSuggestion && renderAISuggestion()}
          </TabsContent>

          <TabsContent value="alerts" className="mt-4">
            {renderThresholdAlerts()}
            {thresholdAlerts.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <BellOff className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>暂无警报信息</p>
                <p className="text-sm">系统正在监控中...</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="settings" className="mt-4">
            {renderControlSettings()}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default SceneController;