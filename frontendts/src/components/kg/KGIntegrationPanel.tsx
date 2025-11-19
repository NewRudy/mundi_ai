/**
 * KGIntegrationPanel - 知识图谱集成面板
 * 松耦合架构下与水电场景集成的主要界面
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Layers, MapPin, BarChart3, AlertTriangle, Info } from 'lucide-react';
import { eventBus, EventType } from '../../services/EventBusService';
import KGSearchPanel from './KGSearchPanel';
import KGVisualizationPanel from './KGVisualizationPanel';

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
  type: 'spatial_analysis' | 'flood_risk' | 'monitoring_stations' | 'spatial_relations';
  title: string;
  description: string;
  confidence: number;
  data: any;
  timestamp: string;
}

interface KGIntegrationPanelProps {
  className?: string;
  hydroSceneData?: HydroSceneData;
  onInsightGenerated?: (insight: KGInsight) => void;
}

export const KGIntegrationPanel: React.FC<KGIntegrationPanelProps> = ({
  className = '',
  hydroSceneData,
  onInsightGenerated
}) => {
  const [activeTab, setActiveTab] = useState<'search' | 'visualization' | 'insights'>('search');
  const [insights, setInsights] = useState<KGInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoAnalysis, setAutoAnalysis] = useState(true);
  const [selectedInsight, setSelectedInsight] = useState<KGInsight | null>(null);

  // 分析水电场景数据
  const analyzeHydroScene = useCallback(async (sceneData: HydroSceneData) => {
    if (!autoAnalysis) return;

    setLoading(true);

    try {
      // 发布空间分析请求
      const spatialResponse = await eventBus.requestReply(
        EventType.SPATIAL_ANALYSIS_REQUEST,
        {
          west: sceneData.viewport.west,
          south: sceneData.viewport.south,
          east: sceneData.viewport.east,
          north: sceneData.viewport.north,
          analysis_type: 'hydro_monitoring',
          max_distance_km: 10
        },
        EventType.SPATIAL_ANALYSIS_COMPLETED,
        10000
      );

      if (spatialResponse?.payload?.results) {
        const spatialInsight: KGInsight = {
          id: `spatial_${Date.now()}`,
          type: 'spatial_analysis',
          title: '空间分析结果',
          description: `在视口范围内发现 ${spatialResponse.payload.results.length} 个相关要素`,
          confidence: 0.85,
          data: spatialResponse.payload,
          timestamp: new Date().toISOString()
        };

        setInsights(prev => [spatialInsight, ...prev]);

        if (onInsightGenerated) {
          onInsightGenerated(spatialInsight);
        }

        // 发布事件通知其他组件
        eventBus.publishEvent(EventType.KG_ANALYSIS_COMPLETED, {
          insight: spatialInsight,
          source: 'spatial_analysis'
        });
      }

      // 请求KG分析
      const kgResponse = await eventBus.requestReply(
        EventType.KG_ANALYSIS_REQUEST,
        {
          action: 'hydro_scene_analysis',
          location: sceneData.location,
          viewport: sceneData.viewport,
          layers: sceneData.activeLayers
        },
        EventType.KG_ANALYSIS_COMPLETED,
        15000
      );

      if (kgResponse?.payload?.insights) {
        kgResponse.payload.insights.forEach((insight: any) => {
          const kgInsight: KGInsight = {
            id: insight.id || `kg_${Date.now()}_${Math.random()}`,
            type: insight.type || 'spatial_relations',
            title: insight.title || 'KG分析结果',
            description: insight.description || '基于知识图谱的分析',
            confidence: insight.confidence || 0.7,
            data: insight.data,
            timestamp: new Date().toISOString()
          };

          setInsights(prev => [kgInsight, ...prev]);

          if (onInsightGenerated) {
            onInsightGenerated(kgInsight);
          }
        });
      }
    } catch (error) {
      console.error('水电场景分析失败:', error);

      // 创建错误洞察
      const errorInsight: KGInsight = {
        id: `error_${Date.now()}`,
        type: 'spatial_analysis',
        title: '分析失败',
        description: '无法获取知识图谱分析结果',
        confidence: 0,
        data: { error: error.message },
        timestamp: new Date().toISOString()
      };

      setInsights(prev => [errorInsight, ...prev]);
    } finally {
      setLoading(false);
    }
  }, [autoAnalysis, onInsightGenerated]);

  // 处理搜索结果选择
  const handleSearchResultSelect = useCallback((result: any) => {
    // 发布事件到水电场景
    eventBus.publishEvent(EventType.HYDRO_SCENE_CHANGED, {
      action: 'focus_on_feature',
      feature: {
        id: result.id,
        name: result.name,
        type: result.type,
        location: result.properties.location || result.properties
      },
      source: 'kg_search'
    });
  }, []);

  // 处理可视化节点选择
  const handleVisualizationNodeSelect = useCallback((node: any) => {
    // 发布事件到水电场景
    eventBus.publishEvent(EventType.HYDRO_SCENE_CHANGED, {
      action: 'show_node_details',
      node: node,
      source: 'kg_visualization'
    });
  }, []);

  // 处理洞察选择
  const handleInsightSelect = useCallback((insight: KGInsight) => {
    setSelectedInsight(insight);

    // 根据洞察类型发布不同事件
    switch (insight.type) {
      case 'flood_risk':
        eventBus.publishEvent(EventType.HYDRO_ALERT_TRIGGERED, {
          alert_type: 'flood_risk',
          severity: 'medium',
          data: insight.data,
          source: 'kg_insight'
        });
        break;
      case 'monitoring_stations':
        eventBus.publishEvent(EventType.HYDRO_DATA_UPDATED, {
          update_type: 'stations_discovered',
          stations: insight.data.stations || [],
          source: 'kg_insight'
        });
        break;
      case 'spatial_analysis':
        eventBus.publishEvent(EventType.HYDRO_VIEWPORT_CHANGED, {
          reason: 'kg_spatial_analysis',
          features: insight.data.results || [],
          source: 'kg_insight'
        });
        break;
    }
  }, []);

  // 监听水电场景变化
  useEffect(() => {
    if (hydroSceneData) {
      analyzeHydroScene(hydroSceneData);
    }
  }, [hydroSceneData, analyzeHydroScene]);

  // 监听KG事件
  useEffect(() => {
    const unsubscribe = eventBus.subscribe(EventType.KG_DATA_UPDATED, (event) => {
      // KG数据更新时重新分析
      if (hydroSceneData) {
        analyzeHydroScene(hydroSceneData);
      }
    });

    return unsubscribe;
  }, [hydroSceneData, analyzeHydroScene]);

  const getInsightIcon = (type: KGInsight['type']) => {
    switch (type) {
      case 'flood_risk':
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'monitoring_stations':
        return <MapPin className="w-4 h-4 text-blue-500" />;
      case 'spatial_analysis':
        return <BarChart3 className="w-4 h-4 text-green-500" />;
      case 'spatial_relations':
        return <Layers className="w-4 h-4 text-purple-500" />;
      default:
        return <Info className="w-4 h-4 text-gray-500" />;
    }
  };

  const getInsightColor = (type: KGInsight['type']) => {
    switch (type) {
      case 'flood_risk':
        return 'border-red-200 bg-red-50';
      case 'monitoring_stations':
        return 'border-blue-200 bg-blue-50';
      case 'spatial_analysis':
        return 'border-green-200 bg-green-50';
      case 'spatial_relations':
        return 'border-purple-200 bg-purple-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
      {/* 头部控制 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-800">知识图谱集成</h2>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoAnalysis}
              onChange={(e) => setAutoAnalysis(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">自动分析</span>
          </label>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              eventBus.isConnected() ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-xs text-gray-500">
              {eventBus.isConnected() ? '已连接' : '未连接'}
            </span>
          </div>
        </div>
      </div>

      {/* 标签页导航 */}
      <div className="flex border-b border-gray-200">
        {[
          { key: 'search', label: '搜索', icon: <Layers className="w-4 h-4" /> },
          { key: 'visualization', label: '可视化', icon: <BarChart3 className="w-4 h-4" /> },
          { key: 'insights', label: '洞察', icon: <Info className="w-4 h-4" /> }
        ].map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* 标签页内容 */}
      <div className="p-4">
        {activeTab === 'search' && (
          <KGSearchPanel
            onResultSelect={handleSearchResultSelect}
            className="w-full"
          />
        )}

        {activeTab === 'visualization' && (
          <KGVisualizationPanel
            onNodeSelect={handleVisualizationNodeSelect}
            height={400}
            className="w-full"
          />
        )}

        {activeTab === 'insights' && (
          <div className="space-y-4">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="flex items-center space-x-2 text-gray-500">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span>正在分析水电场景数据...</span>
                </div>
              </div>
            )}

            {insights.length === 0 && !loading && (
              <div className="text-center py-8 text-gray-500">
                <Info className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <div>暂无分析洞察</div>
                <div className="text-sm mt-1">
                  {autoAnalysis ? '等待水电场景数据...' : '开启自动分析以获取洞察'}
                </div>
              </div>
            )}

            {insights.map((insight) => (
              <div
                key={insight.id}
                onClick={() => handleInsightSelect(insight)}
                className={`p-4 border rounded-lg cursor-pointer transition-all hover:shadow-md ${
                  getInsightColor(insight.type)
                } ${
                  selectedInsight?.id === insight.id ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    {getInsightIcon(insight.type)}
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{insight.title}</div>
                      <div className="text-sm text-gray-600 mt-1">{insight.description}</div>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        <div>置信度: {(insight.confidence * 100).toFixed(0)}%</div>
                        <div>{new Date(insight.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 详细信息（如果选中） */}
                {selectedInsight?.id === insight.id && insight.data && (
                  <div className="mt-4 pt-4 border-t border-current border-opacity-20">
                    <div className="text-sm text-gray-700">
                      <pre className="whitespace-pre-wrap text-xs">
                        {JSON.stringify(insight.data, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default KGIntegrationPanel;