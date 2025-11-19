/**
 * KGHydroIntegrationExample - KG与水电场景集成示例
 * 展示如何在松耦合架构下集成知识图谱与水电场景
 */

import React, { useState, useEffect, useCallback } from 'react';
import { KGIntegrationPanel } from '../kg';
import { useKGIntegration } from '../../hooks';
import { eventBus, EventType } from '../../services/EventBusService';
import { AlertCircle, CheckCircle, Info } from 'lucide-react';

interface HydroSceneData {
  sceneId: string;
  location: {
    lat: number;
    lng: number;
  };
  viewport: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  activeLayers: string[];
}

interface KGInsight {
  id: string;
  type: string;
  title: string;
  description: string;
  confidence: number;
  data: any;
  timestamp: string;
}

/**
 * KG与水电场景集成示例组件
 * 展示如何使用事件总线实现松耦合集成
 */
export const KGHydroIntegrationExample: React.FC = () => {
  const [currentScene, setCurrentScene] = useState<HydroSceneData | null>(null);
  const [integrationStatus, setIntegrationStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle');
  const [lastInsight, setLastInsight] = useState<KGInsight | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // 使用KG集成Hook
  const {
    isConnected,
    insights,
    loading,
    error,
    analyzeHydroScene,
    searchKG,
    publishEvent,
    subscribeToEvent
  } = useKGIntegration({
    autoAnalyze: true,
    maxInsights: 20,
    onInsightGenerated: (insight) => {
      setLastInsight(insight);
      setNotification(`新洞察: ${insight.title}`);

      // 3秒后清除通知
      setTimeout(() => setNotification(null), 3000);
    },
    onError: (error) => {
      setNotification(`错误: ${error.message}`);
      setTimeout(() => setNotification(null), 5000);
    }
  });

  // 模拟水电场景数据
  const mockHydroSceneData: HydroSceneData = {
    sceneId: 'hydro_scene_001',
    location: {
      lat: 39.9042, // 北京
      lng: 116.4074
    },
    viewport: {
      west: 116.3,
      south: 39.8,
      east: 116.5,
      north: 40.0
    },
    activeLayers: ['hydrology', 'meteorology', 'dem']
  };

  // 初始化集成
  const initializeIntegration = useCallback(async () => {
    setIntegrationStatus('connecting');

    try {
      // 连接事件总线
      await eventBus.connect();
      setIntegrationStatus('connected');

      // 设置当前场景
      setCurrentScene(mockHydroSceneData);

      // 发布场景初始化事件
      await publishEvent(EventType.HYDRO_SCENE_CHANGED, {
        sceneData: mockHydroSceneData,
        action: 'initialized',
        source: 'integration_example'
      });

    } catch (error) {
      setIntegrationStatus('error');
      console.error('集成初始化失败:', error);
    }
  }, [publishEvent]);

  // 处理场景切换
  const handleSceneChange = useCallback(async () => {
    if (!currentScene) return;

    // 模拟场景变化
    const newScene = {
      ...currentScene,
      sceneId: `hydro_scene_${Date.now()}`,
      location: {
        lat: currentScene.location.lat + (Math.random() - 0.5) * 0.1,
        lng: currentScene.location.lng + (Math.random() - 0.5) * 0.1
      }
    };

    setCurrentScene(newScene);

    // 发布场景变化事件
    await publishEvent(EventType.HYDRO_SCENE_CHANGED, {
      sceneData: newScene,
      action: 'location_changed',
      source: 'user_interaction'
    });
  }, [currentScene, publishEvent]);

  // 处理搜索
  const handleSearch = useCallback(async (query: string) => {
    if (!isConnected) {
      setNotification('请先连接知识图谱服务');
      return;
    }

    try {
      const results = await searchKG(query, {
        limit: 10,
        includeRelationships: true
      });

      setNotification(`搜索完成，找到 ${results.length} 个结果`);

      // 发布搜索结果事件
      await publishEvent(EventType.KG_SEARCH_COMPLETED, {
        query,
        results,
        source: 'integration_example'
      });

    } catch (error) {
      setNotification(`搜索失败: ${error.message}`);
    }
  }, [isConnected, searchKG, publishEvent]);

  // 处理警报
  const handleAlert = useCallback(async (alertType: string) => {
    await publishEvent(EventType.HYDRO_ALERT_TRIGGERED, {
      alert_type: alertType,
      severity: 'high',
      location: currentScene?.location,
      source: 'integration_example'
    });

    setNotification(`发布警报: ${alertType}`);
  }, [currentScene, publishEvent]);

  // 监听各种事件
  useEffect(() => {
    // 监听连接状态变化
    const unsubscribeStatus = subscribeToEvent('status_changed', (event) => {
      console.log('连接状态变化:', event.payload);
    });

    // 监听水电场景事件
    const unsubscribeScene = subscribeToEvent(EventType.HYDRO_SCENE_CHANGED, (event) => {
      console.log('水电场景变化:', event.payload);
    });

    // 监听KG搜索事件
    const unsubscribeSearch = subscribeToEvent(EventType.KG_SEARCH_COMPLETED, (event) => {
      console.log('KG搜索完成:', event.payload);
    });

    // 监听警报事件
    const unsubscribeAlert = subscribeToEvent(EventType.HYDRO_ALERT_TRIGGERED, (event) => {
      console.log('警报触发:', event.payload);
    });

    // 监听数据更新
    const unsubscribeData = subscribeToEvent(EventType.HYDRO_DATA_UPDATED, (event) => {
      console.log('数据更新:', event.payload);
    });

    return () => {
      unsubscribeStatus();
      unsubscribeScene();
      unsubscribeSearch();
      unsubscribeAlert();
      unsubscribeData();
    };
  }, [subscribeToEvent]);

  // 初始化
  useEffect(() => {
    if (integrationStatus === 'idle') {
      initializeIntegration();
    }
  }, [integrationStatus, initializeIntegration]);

  return (
    <div className="w-full h-full bg-gray-50 p-6">
      {/* 状态栏 */}
      <div className="mb-6 p-4 bg-white rounded-lg shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-800">KG与水电场景集成示例</h1>
            <div className="flex items-center space-x-2">
              {integrationStatus === 'connected' && isConnected ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="text-sm text-green-600">已连接</span>
                </>
              ) : integrationStatus === 'error' ? (
                <>
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <span className="text-sm text-red-600">连接失败</span>
                </>
              ) : (
                <>
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-blue-600">连接中...</span>
                </>
              )}
            </div>
          </div>

          <div className="text-sm text-gray-500">
            洞察数量: {insights.length}
          </div>
        </div>
      </div>

      {/* 控制面板 */}
      <div className="mb-6 p-4 bg-white rounded-lg shadow-sm">
        <div className="flex flex-wrap gap-4">
          <button
            onClick={handleSceneChange}
            disabled={!isConnected || loading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            模拟场景变化
          </button>

          <button
            onClick={() => handleSearch('水电站')}
            disabled={!isConnected}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            搜索"水电站"
          </button>

          <button
            onClick={() => handleAlert('flood_risk')}
            disabled={!isConnected}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            模拟洪水警报
          </button>

          <button
            onClick={() => {
              setCurrentScene(mockHydroSceneData);
              analyzeHydroScene(mockHydroSceneData);
            }}
            disabled={!isConnected}
            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            重新分析场景
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* 主要集成面板 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：KG集成面板 */}
        <div className="lg:col-span-2">
          <KGIntegrationPanel
            hydroSceneData={currentScene}
            onInsightGenerated={(insight) => {
              console.log('新洞察生成:', insight);
            }}
            className="h-[600px]"
          />
        </div>

        {/* 右侧：状态和信息 */}
        <div className="space-y-4">
          {/* 当前场景信息 */}
          <div className="p-4 bg-white rounded-lg shadow-sm">
            <h3 className="text-lg font-medium text-gray-800 mb-3">当前场景信息</h3>
            {currentScene ? (
              <div className="space-y-2 text-sm">
                <div><span className="font-medium">场景ID:</span> {currentScene.sceneId}</div>
                <div><span className="font-medium">位置:</span> {currentScene.location.lat.toFixed(4)}, {currentScene.location.lng.toFixed(4)}</div>
                <div><span className="font-medium">活动图层:</span> {currentScene.activeLayers.join(', ')}</div>
              </div>
            ) : (
              <div className="text-gray-500">暂无场景数据</div>
            )}
          </div>

          {/* 最新洞察 */}
          <div className="p-4 bg-white rounded-lg shadow-sm">
            <h3 className="text-lg font-medium text-gray-800 mb-3">最新洞察</h3>
            {lastInsight ? (
              <div className="space-y-2">
                <div className="font-medium text-gray-900">{lastInsight.title}</div>
                <div className="text-sm text-gray-600">{lastInsight.description}</div>
                <div className="text-xs text-gray-500">置信度: {(lastInsight.confidence * 100).toFixed(0)}%</div>
              </div>
            ) : (
              <div className="text-gray-500">暂无洞察</div>
            )}
          </div>

          {/* 事件日志 */}
          <div className="p-4 bg-white rounded-lg shadow-sm">
            <h3 className="text-lg font-medium text-gray-800 mb-3">事件日志</h3>
            <div className="text-xs text-gray-500 max-h-32 overflow-y-auto">
              <div>系统初始化完成</div>
              <div>事件总线已连接</div>
              <div>KG服务已就绪</div>
            </div>
          </div>
        </div>
      </div>

      {/* 通知 */}
      {notification && (
        <div className="fixed bottom-4 right-4 p-4 bg-blue-500 text-white rounded-lg shadow-lg max-w-sm">
          <div className="flex items-center">
            <Info className="w-4 h-4 mr-2" />
            <span className="text-sm">{notification}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default KGHydroIntegrationExample;