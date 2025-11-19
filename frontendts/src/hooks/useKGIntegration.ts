/**
 * useKGIntegration - 知识图谱集成Hook
 * 提供松耦合架构下的KG功能集成
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { eventBus, EventType } from '../services/EventBusService';

interface KGIntegrationState {
  isConnected: boolean;
  insights: KGInsight[];
  loading: boolean;
  error: string | null;
  lastUpdate: string | null;
}

interface HydroSceneData {
  sceneId: string;
  location: { lat: number; lng: number };
  viewport: { west: number; south: number; east: number; north: number };
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

interface UseKGIntegrationOptions {
  autoAnalyze?: boolean;
  maxInsights?: number;
  onInsightGenerated?: (insight: KGInsight) => void;
  onError?: (error: Error) => void;
}

export const useKGIntegration = (options: UseKGIntegrationOptions = {}) => {
  const {
    autoAnalyze = true,
    maxInsights = 50,
    onInsightGenerated,
    onError
  } = options;

  const [state, setState] = useState<KGIntegrationState>({
    isConnected: false,
    insights: [],
    loading: false,
    error: null,
    lastUpdate: null
  });

  const autoAnalyzeRef = useRef(autoAnalyze);
  const insightsBuffer = useRef<KGInsight[]>([]);

  // 更新连接状态
  const updateConnectionStatus = useCallback(() => {
    const isConnected = eventBus.isConnected();
    setState(prev => ({ ...prev, isConnected }));
  }, []);

  // 添加洞察到状态
  const addInsight = useCallback((insight: KGInsight) => {
    setState(prev => {
      const newInsights = [insight, ...prev.insights]
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, maxInsights);

      return {
        ...prev,
        insights: newInsights,
        lastUpdate: new Date().toISOString()
      };
    });

    if (onInsightGenerated) {
      onInsightGenerated(insight);
    }
  }, [maxInsights, onInsightGenerated]);

  // 处理水电场景变化
  const handleHydroSceneChange = useCallback(async (sceneData: HydroSceneData) => {
    if (!state.isConnected || !autoAnalyzeRef.current) {
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      // 清空之前的缓冲区
      insightsBuffer.current = [];

      // 执行空间分析
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

        addInsight(spatialInsight);
      }

      // 执行KG分析
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

          addInsight(kgInsight);
        });
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '分析失败';
      setState(prev => ({ ...prev, error: errorMessage }));

      if (onError) {
        onError(error instanceof Error ? error : new Error(errorMessage));
      }

      // 创建错误洞察
      const errorInsight: KGInsight = {
        id: `error_${Date.now()}`,
        type: 'error',
        title: '分析失败',
        description: errorMessage,
        confidence: 0,
        data: { error: errorMessage },
        timestamp: new Date().toISOString()
      };

      addInsight(errorInsight);
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [state.isConnected, addInsight, onError]);

  // 手动触发分析
  const analyzeHydroScene = useCallback((sceneData: HydroSceneData) => {
    return handleHydroSceneChange(sceneData);
  }, [handleHydroSceneChange]);

  // 搜索知识图谱
  const searchKG = useCallback(async (query: string, options: {
    limit?: number;
    includeRelationships?: boolean;
  } = {}) => {
    if (!state.isConnected) {
      throw new Error('知识图谱服务未连接');
    }

    const { limit = 20, includeRelationships = false } = options;

    const response = await eventBus.requestReply(
      EventType.KG_SEARCH_REQUEST,
      {
        query,
        limit,
        include_relationships: includeRelationships
      },
      EventType.KG_SEARCH_COMPLETED,
      10000
    );

    if (!response?.payload?.results) {
      throw new Error('搜索失败或未找到结果');
    }

    return response.payload.results;
  }, [state.isConnected]);

  // 获取可视化数据
  const getVisualizationData = useCallback(async (options: {
    limit?: number;
    nodeTypes?: string[];
    relationshipTypes?: string[];
  } = {}) => {
    if (!state.isConnected) {
      throw new Error('知识图谱服务未连接');
    }

    const { limit = 50 } = options;

    const response = await eventBus.requestReply(
      EventType.KG_ANALYSIS_REQUEST,
      {
        action: 'get_visualization_data',
        limit,
        node_types: options.nodeTypes,
        relationship_types: options.relationshipTypes
      },
      EventType.KG_ANALYSIS_COMPLETED,
      15000
    );

    if (!response?.payload?.data) {
      throw new Error('无法获取可视化数据');
    }

    return response.payload.data;
  }, [state.isConnected]);

  // 发布事件
  const publishEvent = useCallback((eventType: EventType, payload: any) => {
    return eventBus.publishEvent(eventType, payload);
  }, []);

  // 订阅事件
  const subscribeToEvent = useCallback((eventType: EventType, handler: (event: any) => void) => {
    return eventBus.subscribe(eventType, handler);
  }, []);

  // 清除错误
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // 清除洞察
  const clearInsights = useCallback(() => {
    setState(prev => ({ ...prev, insights: [], lastUpdate: null }));
  }, []);

  // 监听连接状态变化
  useEffect(() => {
    const handleStatusChange = () => {
      updateConnectionStatus();
    };

    const unsubscribe = eventBus.subscribe('status_changed', handleStatusChange);
    updateConnectionStatus();

    return () => {
      unsubscribe();
    };
  }, [updateConnectionStatus]);

  // 监听水电场景事件
  useEffect(() => {
    const unsubscribe = eventBus.subscribe(EventType.HYDRO_SCENE_CHANGED, (event) => {
      if (event.payload?.sceneData) {
        handleHydroSceneChange(event.payload.sceneData);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [handleHydroSceneChange]);

  // 监听KG数据更新
  useEffect(() => {
    const unsubscribe = eventBus.subscribe(EventType.KG_DATA_UPDATED, () => {
      // 可以在这里处理数据更新逻辑
    });

    return () => {
      unsubscribe();
    };
  }, []);

  // 更新自动分析设置
  useEffect(() => {
    autoAnalyzeRef.current = autoAnalyze;
  }, [autoAnalyze]);

  return {
    // 状态
    ...state,

    // 方法
    analyzeHydroScene,
    searchKG,
    getVisualizationData,
    publishEvent,
    subscribeToEvent,
    clearError,
    clearInsights,

    // 配置
    setAutoAnalyze: (value: boolean) => {
      // 这个需要通过组件状态管理，hook内部使用ref
    }
  };
};

export default useKGIntegration;