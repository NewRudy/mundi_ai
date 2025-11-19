/**
 * UnifiedViewContext - 2D/3D统一视图状态管理
 * 实现2D MapLibreMap和3D HydroSceneView的深度融合
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { useSceneStore, SceneType } from '@/store/useSceneStore';
import { useProjects } from './ProjectsContext';
import { toast } from 'sonner';

// 统一图层接口
export interface UnifiedLayer {
  id: string;
  type: 'vector' | 'raster' | 'pointcloud' | 'hydro' | 'geojson' | 'mvt';
  name: string;
  source: {
    type: string;
    url?: string;
    data?: any;
  };

  // 2D MapLibre属性
  maplibreStyle?: {
    type: 'fill' | 'line' | 'symbol' | 'circle' | 'heatmap';
    paint?: Record<string, any>;
    layout?: Record<string, any>;
  };
  visibility2D: boolean;

  // 3D Deck.gl属性
  deckglConfig?: {
    type: string;
    props: Record<string, any>;
  };

  // 3D Cesium属性
  cesiumConfig?: {
    entityType: string;
    position?: [number, number, number];
    properties?: Record<string, any>;
  };

  visibility3D: boolean;
  opacity: number;
  bounds?: [number, number, number, number]; // [west, south, east, north]

  // 专业属性
  hydroProperties?: {
    monitoringType?: 'dam' | 'reservoir' | 'hydrology' | 'weather';
    alertLevel?: 'normal' | 'warning' | 'danger' | 'critical';
    currentValue?: number;
    unit?: string;
    threshold?: number;
  };
}

// 统一视口状态
export interface ViewportState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  height?: number; // 3D高度
}

// 3D场景状态
export interface HydroSceneState {
  currentScene: SceneType;
  sceneData: any;
  isLoading: boolean;
  animationEnabled: boolean;
  currentTimeIndex: number;
}

// 统一视图状态
interface UnifiedViewState {
  viewMode: '2d' | '3d' | 'split';
  isTransitioning: boolean;
  sharedLayers: UnifiedLayer[];
  activeLayerIds: string[];
  viewport: ViewportState;
  hydroScene: HydroSceneState;
  syncEnabled: boolean;
  lastSyncTime: number;
  preferences: {
    autoSwitchScenes: boolean;
    aiSuggestions: boolean;
    thresholdAlerts: boolean;
  };
}

// 动作类型
type UnifiedViewAction =
  | { type: 'SET_VIEW_MODE'; payload: '2d' | '3d' | 'split' }
  | { type: 'SET_TRANSITIONING'; payload: boolean }
  | { type: 'ADD_LAYER'; payload: UnifiedLayer }
  | { type: 'REMOVE_LAYER'; payload: string }
  | { type: 'UPDATE_LAYER'; payload: { id: string; updates: Partial<UnifiedLayer> } }
  | { type: 'SET_ACTIVE_LAYERS'; payload: string[] }
  | { type: 'SET_VIEWPORT'; payload: ViewportState }
  | { type: 'SET_HYDRO_SCENE'; payload: Partial<HydroSceneState> }
  | { type: 'SET_SYNC_ENABLED'; payload: boolean }
  | { type: 'SET_PREFERENCE'; payload: { key: string; value: any } }
  | { type: 'SET_LAST_SYNC_TIME'; payload: number };

// 初始状态
const initialState: UnifiedViewState = {
  viewMode: '2d',
  isTransitioning: false,
  sharedLayers: [],
  activeLayerIds: [],
  viewport: {
    longitude: 111.0,
    latitude: 30.8,
    zoom: 8,
    pitch: 0,
    bearing: 0,
  },
  hydroScene: {
    currentScene: 'normal',
    sceneData: {},
    isLoading: false,
    animationEnabled: false,
    currentTimeIndex: 0,
  },
  syncEnabled: true,
  lastSyncTime: 0,
  preferences: {
    autoSwitchScenes: true,
    aiSuggestions: true,
    thresholdAlerts: true,
  },
};

// Reducer函数
function unifiedViewReducer(state: UnifiedViewState, action: UnifiedViewAction): UnifiedViewState {
  switch (action.type) {
    case 'SET_VIEW_MODE':
      return { ...state, viewMode: action.payload };

    case 'SET_TRANSITIONING':
      return { ...state, isTransitioning: action.payload };

    case 'ADD_LAYER':
      return {
        ...state,
        sharedLayers: [...state.sharedLayers, action.payload]
      };

    case 'REMOVE_LAYER':
      return {
        ...state,
        sharedLayers: state.sharedLayers.filter(layer => layer.id !== action.payload)
      };

    case 'UPDATE_LAYER':
      return {
        ...state,
        sharedLayers: state.sharedLayers.map(layer =>
          layer.id === action.payload.id
            ? { ...layer, ...action.payload.updates }
            : layer
        )
      };

    case 'SET_ACTIVE_LAYERS':
      return { ...state, activeLayerIds: action.payload };

    case 'SET_VIEWPORT':
      return { ...state, viewport: action.payload };

    case 'SET_HYDRO_SCENE':
      return {
        ...state,
        hydroScene: { ...state.hydroScene, ...action.payload }
      };

    case 'SET_SYNC_ENABLED':
      return { ...state, syncEnabled: action.payload };

    case 'SET_PREFERENCE':
      return {
        ...state,
        preferences: {
          ...state.preferences,
          [action.payload.key]: action.payload.value
        }
      };

    case 'SET_LAST_SYNC_TIME':
      return { ...state, lastSyncTime: action.payload };

    default:
      return state;
  }
}

// Context类型
interface UnifiedViewContextType extends UnifiedViewState {
  setViewMode: (mode: '2d' | '3d' | 'split') => void;
  setTransitioning: (transitioning: boolean) => void;
  addUnifiedLayer: (layer: UnifiedLayer) => void;
  removeUnifiedLayer: (layerId: string) => void;
  updateUnifiedLayer: (id: string, updates: Partial<UnifiedLayer>) => void;
  setActiveLayers: (layerIds: string[]) => void;
  setViewport: (viewport: ViewportState) => void;
  updateHydroScene: (updates: Partial<HydroSceneState>) => void;
  setSyncEnabled: (enabled: boolean) => void;
  setPreference: (key: string, value: any) => void;

  // 核心同步函数
  sync2DTo3D: () => void;
  sync3DTo2D: () => void;
  syncViewport2DTo3D: (viewport: ViewportState) => void;
  syncViewport3DTo2D: (viewport: ViewportState) => void;

  // 场景控制
  setActiveScene: (scene: SceneType) => void;
  toggleAnimation: () => void;
  setTimeIndex: (index: number) => void;

  // 智能功能
  handleAICommand: (command: string) => boolean;
  checkThresholdAlerts: (data: any) => void;
}

// Context创建
const UnifiedViewContext = createContext<UnifiedViewContextType | undefined>(undefined);

// Provider组件
export const UnifiedViewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(unifiedViewReducer, initialState);
  const { setScene, sceneData } = useSceneStore();
  const { currentProject } = useProjects();

  // 基础设置函数
  const setViewMode = useCallback((mode: '2d' | '3d' | 'split') => {
    dispatch({ type: 'SET_TRANSITIONING', payload: true });

    // 添加过渡动画
    setTimeout(() => {
      dispatch({ type: 'SET_VIEW_MODE', payload: mode });
      dispatch({ type: 'SET_TRANSITIONING', payload: false });

      toast.success(`已切换到${mode === '2d' ? '2D地图' : mode === '3d' ? '3D场景' : '分屏显示'}`);
    }, 300);
  }, []);

  const setTransitioning = useCallback((transitioning: boolean) => {
    dispatch({ type: 'SET_TRANSITIONING', payload: transitioning });
  }, []);

  const addUnifiedLayer = useCallback((layer: UnifiedLayer) => {
    dispatch({ type: 'ADD_LAYER', payload: layer });
    toast.success(`已添加图层: ${layer.name}`);
  }, []);

  const removeUnifiedLayer = useCallback((layerId: string) => {
    dispatch({ type: 'REMOVE_LAYER', payload: layerId });
    toast.success('图层已移除');
  }, []);

  const updateUnifiedLayer = useCallback((id: string, updates: Partial<UnifiedLayer>) => {
    dispatch({ type: 'UPDATE_LAYER', payload: { id, updates } });
  }, []);

  const setActiveLayers = useCallback((layerIds: string[]) => {
    dispatch({ type: 'SET_ACTIVE_LAYERS', payload: layerIds });
  }, []);

  const setViewport = useCallback((viewport: ViewportState) => {
    dispatch({ type: 'SET_VIEWPORT', payload: viewport });
  }, []);

  const updateHydroScene = useCallback((updates: Partial<HydroSceneState>) => {
    dispatch({ type: 'SET_HYDRO_SCENE', payload: updates });
  }, []);

  const setSyncEnabled = useCallback((enabled: boolean) => {
    dispatch({ type: 'SET_SYNC_ENABLED', payload: enabled });
    toast.info(enabled ? '已启用2D/3D同步' : '已禁用2D/3D同步');
  }, []);

  const setPreference = useCallback((key: string, value: any) => {
    dispatch({ type: 'SET_PREFERENCE', payload: { key, value } });
  }, []);

  // 核心同步函数
  const sync2DTo3D = useCallback(() => {
    if (!state.syncEnabled) return;

    dispatch({ type: 'SET_TRANSITIONING', payload: true });

    try {
      // 转换2D图层为3D格式
      const deckglLayers = convertLayersToDeckGL(state.sharedLayers);
      const cesiumEntities = convertLayersToCesium(state.sharedLayers);

      // 转换2D视口到3D相机位置
      const cesiumCamera = convertMaplibreViewportToCesium(state.viewport);

      // 更新3D场景状态
      updateHydroScene({
        deckglLayers,
        cesiumEntities,
        cameraPosition: cesiumCamera,
        isLoading: false,
      });

      dispatch({ type: 'SET_LAST_SYNC_TIME', payload: Date.now() });

      toast.success('2D到3D同步完成');

    } catch (error) {
      console.error('2D到3D同步失败:', error);
      toast.error('2D到3D同步失败');
    } finally {
      dispatch({ type: 'SET_TRANSITIONING', payload: false });
    }
  }, [state.syncEnabled, state.sharedLayers, state.viewport, updateHydroScene]);

  const sync3DTo2D = useCallback(() => {
    if (!state.syncEnabled) return;

    try {
      // 将3D场景数据转换回2D格式
      const maplibreLayers = convert3DToMaplibre(state.hydroScene);

      // 触发2D地图更新（通过回调）
      // 这里会调用传入的onLayersChange回调

      dispatch({ type: 'SET_LAST_SYNC_TIME', payload: Date.now() });

    } catch (error) {
      console.error('3D到2D同步失败:', error);
      toast.error('3D到2D同步失败');
    }
  }, [state.syncEnabled, state.hydroScene]);

  const syncViewport2DTo3D = useCallback((viewport: ViewportState) => {
    if (!state.syncEnabled) return;

    try {
      // 2D视角同步到3D
      const cesiumCamera = convertMaplibreViewportToCesium(viewport);

      updateHydroScene({
        cameraPosition: cesiumCamera
      });

      dispatch({ type: 'SET_LAST_SYNC_TIME', payload: Date.now() });

    } catch (error) {
      console.error('2D到3D视口同步失败:', error);
    }
  }, [state.syncEnabled, updateHydroScene]);

  const syncViewport3DTo2D = useCallback((viewport: ViewportState) => {
    if (!state.syncEnabled) return;

    try {
      // 3D视角同步到2D
      const maplibreViewport = convertCesiumViewportToMaplibre(viewport);

      setViewport(maplibreViewport);

      dispatch({ type: 'SET_LAST_SYNC_TIME', payload: Date.now() });

    } catch (error) {
      console.error('3D到2D视口同步失败:', error);
    }
  }, [state.syncEnabled, setViewport]);

  // 场景控制函数
  const setActiveScene = useCallback((scene: SceneType) => {
    setScene(scene);
    updateHydroScene({ currentScene: scene, isLoading: true });

    // 根据场景类型自动调整视图
    const config = sceneData.scenes[scene];
    if (config.defaultView === '3d' && state.viewMode === '2d') {
      setViewMode('3d');
    }

    toast.success(`已切换到${config.name}模式`);
  }, [setScene, sceneData.scenes, state.viewMode, setViewMode, updateHydroScene]);

  const toggleAnimation = useCallback(() => {
    updateHydroScene({
      animationEnabled: !state.hydroScene.animationEnabled
    });
  }, [state.hydroScene.animationEnabled, updateHydroScene]);

  const setTimeIndex = useCallback((index: number) => {
    updateHydroScene({ currentTimeIndex: index });
  }, [updateHydroScene]);

  // AI命令处理 - 增强版
  const handleAICommand = useCallback((command: string): boolean => {
    const lowerCommand = command.toLowerCase();
    let handled = false;

    // 3D视图相关命令
    if (lowerCommand.includes('3d') || lowerCommand.includes('三维') || lowerCommand.includes('立体')) {
      if (state.viewMode !== '3d') {
        setViewMode('3d');
        toast.success('已切换到3D视图');
        handled = true;
      } else {
        toast.info('当前已在3D视图模式');
      }
    }

    // 2D视图相关命令
    if (lowerCommand.includes('2d') || lowerCommand.includes('二维') || lowerCommand.includes('平面')) {
      if (state.viewMode !== '2d') {
        setViewMode('2d');
        toast.success('已切换到2D视图');
        handled = true;
      } else {
        toast.info('当前已在2D视图模式');
      }
    }

    // 分屏相关命令
    if (lowerCommand.includes('分屏') || lowerCommand.includes('split') || lowerCommand.includes('并排')) {
      setViewMode('split');
      toast.success('已切换到分屏模式');
      handled = true;
    }

    // 场景切换命令
    const sceneCommands = {
      '应急': 'emergency',
      '洪水': 'emergency',
      '灾害': 'emergency',
      '调度': 'dispatch',
      '巡检': 'inspection',
      '巡查': 'inspection',
      '分析': 'analysis',
      '数据': 'analysis',
      '普通': 'normal',
      '常规': 'normal',
      '默认': 'normal',
    };

    for (const [keyword, scene] of Object.entries(sceneCommands)) {
      if (lowerCommand.includes(keyword)) {
        setActiveScene(scene as SceneType);
        handled = true;
        break;
      }
    }

    // 动画控制命令
    if (lowerCommand.includes('动画') || lowerCommand.includes('播放') || lowerCommand.includes('动态')) {
      toggleAnimation();
      toast.success(state.hydroScene.animationEnabled ? '已启用动画' : '已禁用动画');
      handled = true;
    }

    // 同步控制命令
    if (lowerCommand.includes('同步')) {
      if (lowerCommand.includes('开启') || lowerCommand.includes('启用')) {
        setSyncEnabled(true);
        toast.success('已启用2D/3D同步');
        handled = true;
      } else if (lowerCommand.includes('关闭') || lowerCommand.includes('禁用')) {
        setSyncEnabled(false);
        toast.success('已禁用2D/3D同步');
        handled = true;
      } else {
        // 手动触发同步
        sync2DTo3D();
        toast.success('正在同步2D/3D数据');
        handled = true;
      }
    }

    // 视角控制命令
    if (lowerCommand.includes('视角') || lowerCommand.includes('视图') || lowerCommand.includes('相机')) {
      if (lowerCommand.includes('俯视') || lowerCommand.includes('顶部')) {
        setViewport({ ...state.viewport, pitch: 0, bearing: 0 });
        toast.success('已切换到俯视图');
        handled = true;
      } else if (lowerCommand.includes('侧视') || lowerCommand.includes('侧面')) {
        setViewport({ ...state.viewport, pitch: 45 });
        toast.success('已切换到侧视图');
        handled = true;
      } else if (lowerCommand.includes('重置') || lowerCommand.includes('默认')) {
        setViewport({ ...state.viewport, pitch: 0, bearing: 0, zoom: 8 });
        toast.success('已重置视角');
        handled = true;
      }
    }

    // 图层控制命令
    if (lowerCommand.includes('图层') || lowerCommand.includes('layer')) {
      if (lowerCommand.includes('显示') || lowerCommand.includes('开启')) {
        toast.info('图层显示功能需要在图层管理面板中操作');
        handled = true;
      } else if (lowerCommand.includes('隐藏') || lowerCommand.includes('关闭')) {
        toast.info('图层隐藏功能需要在图层管理面板中操作');
        handled = true;
      } else if (lowerCommand.includes('添加') || lowerCommand.includes('增加')) {
        toast.info('图层添加功能需要上传数据文件');
        handled = true;
      }
    }

    // 专业功能命令
    if (lowerCommand.includes('告警') || lowerCommand.includes('预警')) {
      setPreference('thresholdAlerts', !state.preferences.thresholdAlerts);
      toast.success(state.preferences.thresholdAlerts ? '已启用阈值告警' : '已禁用阈值告警');
      handled = true;
    }

    if (lowerCommand.includes('自动切换')) {
      setPreference('autoSwitchScenes', !state.preferences.autoSwitchScenes);
      toast.success(state.preferences.autoSwitchScenes ? '已启用自动场景切换' : '已禁用自动场景切换');
      handled = true;
    }

    if (lowerCommand.includes('ai建议') || lowerCommand.includes('智能建议')) {
      setPreference('aiSuggestions', !state.preferences.aiSuggestions);
      toast.success(state.preferences.aiSuggestions ? '已启用AI建议' : '已禁用AI建议');
      handled = true;
    }

    // 如果处理了命令，显示反馈
    if (handled) {
      console.log(`AI命令已处理: ${command}`);
    }

    return handled; // 返回是否处理了命令
  }, [
    state.viewMode,
    state.hydroScene.animationEnabled,
    state.preferences.thresholdAlerts,
    state.preferences.autoSwitchScenes,
    state.preferences.aiSuggestions,
    state.viewport,
    setViewMode,
    setActiveScene,
    toggleAnimation,
    setSyncEnabled,
    sync2DTo3D,
    setViewport,
    setPreference
  ]);

  // 阈值告警检查
  const checkThresholdAlerts = useCallback((data: any) => {
    if (!state.preferences.thresholdAlerts) return;

    // 检查是否有超阈值的数据
    const alerts = [];

    // 这里可以添加具体的阈值检查逻辑
    // 例如：水位、流量、雨量等

    if (alerts.length > 0 && state.preferences.autoSwitchScenes) {
      // 自动切换到应急模式
      setActiveScene('emergency');
      toast.warning('检测到异常，已自动切换到应急响应模式');
    }
  }, [state.preferences, setActiveScene]);

  // 自动同步逻辑
  useEffect(() => {
    if (state.syncEnabled && state.sharedLayers.length > 0) {
      const timer = setTimeout(() => {
        sync2DTo3D();
      }, 500); // 防抖处理

      return () => clearTimeout(timer);
    }
  }, [state.sharedLayers, state.syncEnabled, sync2DTo3D]);

  // 项目变化时的处理
  useEffect(() => {
    if (currentProject) {
      // 根据项目类型判断是否启用3D功能
      const isHydroProject = currentProject.title?.toLowerCase().includes('hydro') ||
                           currentProject.title?.toLowerCase().includes('水电') ||
                           currentProject.id?.startsWith('hydro-');

      if (isHydroProject && state.viewMode === '2d') {
        // 自动提示用户是否切换到3D
        toast.info('检测到水电项目，是否切换到3D专业视图？', {
          action: {
            label: '切换',
            onClick: () => setViewMode('3d')
          }
        });
      }
    }
  }, [currentProject, state.viewMode, setViewMode]);

  const contextValue: UnifiedViewContextType = {
    ...state,
    setViewMode,
    setTransitioning,
    addUnifiedLayer,
    removeUnifiedLayer,
    updateUnifiedLayer,
    setActiveLayers,
    setViewport,
    updateHydroScene,
    setSyncEnabled,
    setPreference,
    sync2DTo3D,
    sync3DTo2D,
    syncViewport2DTo3D,
    syncViewport3DTo2D,
    setActiveScene,
    toggleAnimation,
    setTimeIndex,
    handleAICommand,
    checkThresholdAlerts,
  };

  return (
    <UnifiedViewContext.Provider value={contextValue}>
      {children}
    </UnifiedViewContext.Provider>
  );
};

// Hook函数
export const useUnifiedView = () => {
  const context = useContext(UnifiedViewContext);
  if (context === undefined) {
    throw new Error('useUnifiedView must be used within a UnifiedViewProvider');
  }
  return context;
};

// 辅助函数 - 图层转换
function convertLayersToDeckGL(layers: UnifiedLayer[]): any[] {
  return layers
    .filter(layer => layer.visibility3D && layer.deckglConfig)
    .map(layer => {
      const baseConfig = {
        id: layer.id,
        visible: true,
        opacity: layer.opacity,
        ...layer.deckglConfig?.props
      };

      // 根据图层类型添加特定配置
      switch (layer.type) {
        case 'vector':
          return {
            ...baseConfig,
            type: 'GeoJsonLayer',
            data: layer.source.data || layer.source.url,
            filled: true,
            stroked: true,
            pickable: true,
            getFillColor: layer.maplibreStyle?.paint?.['fill-color'] || [255, 140, 0, 180],
            getLineColor: layer.maplibreStyle?.paint?.['line-color'] || [255, 140, 0, 255],
            getLineWidth: layer.maplibreStyle?.paint?.['line-width'] || 1,
          };

        case 'pointcloud':
          return {
            ...baseConfig,
            type: 'PointCloudLayer',
            data: layer.source.data || layer.source.url,
            getPosition: d => d.position,
            getColor: d => d.color || [255, 255, 255, 255],
            pointSize: 2,
          };

        case 'raster':
          return {
            ...baseConfig,
            type: 'BitmapLayer',
            bounds: layer.bounds,
            image: layer.source.url,
          };

        default:
          return baseConfig;
      }
    });
}

function convertLayersToCesium(layers: UnifiedLayer[]): any[] {
  return layers
    .filter(layer => layer.visibility3D && layer.cesiumConfig)
    .map(layer => {
      const baseConfig = {
        id: layer.id,
        show: true,
        ...layer.cesiumConfig
      };

      // 根据实体类型添加特定配置
      switch (layer.cesiumConfig?.entityType) {
        case 'point':
          return {
            ...baseConfig,
            position: Cesium.Cartesian3.fromDegrees(...(layer.cesiumConfig.position || [0, 0, 0])),
            point: {
              pixelSize: 10,
              color: Cesium.Color.ORANGE,
              ...layer.cesiumConfig.properties
            }
          };

        case 'polygon':
          return {
            ...baseConfig,
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(layer.cesiumConfig.properties?.positions || []),
              material: Cesium.Color.ORANGE.withAlpha(layer.opacity || 0.8),
              ...layer.cesiumConfig.properties
            }
          };

        case 'model':
          return {
            ...baseConfig,
            position: Cesium.Cartesian3.fromDegrees(...(layer.cesiumConfig.position || [0, 0, 0])),
            model: {
              uri: layer.source.url,
              scale: 1.0,
              ...layer.cesiumConfig.properties
            }
          };

        default:
          return baseConfig;
      }
    });
}

function convert3DToMaplibre(hydroScene: HydroSceneState): any[] {
  // 将3D场景数据转换回2D格式
  // 这里需要根据具体的数据结构实现
  // 返回MapLibre样式层配置
  return [];
}

// 视口转换函数
function convertMaplibreViewportToCesium(viewport: ViewportState) {
  return {
    destination: Cesium.Cartesian3.fromDegrees(
      viewport.longitude,
      viewport.latitude,
      viewport.height || (10000 / Math.pow(2, viewport.zoom - 8))
    ),
    orientation: {
      heading: Cesium.Math.toRadians(viewport.bearing || 0),
      pitch: Cesium.Math.toRadians(viewport.pitch || -90),
      roll: 0.0
    }
  };
}

function convertCesiumViewportToMaplibre(cameraPosition: any): ViewportState {
  const cartographic = Cesium.Cartographic.fromCartesian(cameraPosition.position);
  return {
    longitude: Cesium.Math.toDegrees(cartographic.longitude),
    latitude: Cesium.Math.toDegrees(cartographic.latitude),
    zoom: Math.log2(10000 / (cartographic.height || 10000)) + 8,
    pitch: Cesium.Math.toDegrees(cameraPosition.pitch || -90),
    bearing: Cesium.Math.toDegrees(cameraPosition.heading || 0),
    height: cartographic.height
  };
}