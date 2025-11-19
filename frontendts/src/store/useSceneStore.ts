/**
 * 场景状态管理 - Zustand store
 * 管理4种核心场景：智能巡检、应急响应、调度决策、数据分析
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 场景类型定义
export type SceneType =
  | 'inspection'      // 智能巡检
  | 'emergency'       // 应急响应
  | 'dispatch'        // 调度决策
  | 'analysis'        // 数据分析
  | 'normal';         // 普通模式

// 场景配置
export interface SceneConfig {
  name: string;
  description: string;
  icon: string;
  color: string;
  bgColor: string;
  features: string[];
  defaultView: '2d' | '3d' | 'charts';
  autoRefresh: boolean;
  refreshInterval: number;
}

// 场景状态
interface SceneState {
  // 当前状态
  currentScene: SceneType;
  previousScene: SceneType;
  isTransitioning: boolean;

  // 场景配置
  scenes: Record<SceneType, SceneConfig>;

  // 场景数据
  sceneData: {
    inspection: {
      monitoringPoints: any[];
      anomalies: any[];
      lastInspection: string;
    };
    emergency: {
      alerts: any[];
      riskLevel: 'low' | 'medium' | 'high' | 'critical';
      affectedAreas: any[];
      evacuationRoutes: any[];
    };
    dispatch: {
      scenarios: any[];
      currentScenario: string;
      parameters: Record<string, number>;
      optimizationResults: any[];
    };
    analysis: {
      datasets: any[];
      charts: any[];
      insights: any[];
      reports: any[];
    };
  };

  // 用户偏好
  preferences: {
    autoSwitchScenes: boolean;
    aiSuggestions: boolean;
    thresholdAlerts: boolean;
  };
}

// 场景操作
interface SceneActions {
  // 场景切换
  setScene: (scene: SceneType, context?: any) => Promise<void>;
  switchToPreviousScene: () => Promise<void>;

  // 场景数据管理
  updateSceneData: (scene: SceneType, data: any) => void;
  updateCurrentSceneData: (data: any) => void;

  // 偏好设置
  setPreference: (key: keyof SceneState['preferences'], value: boolean) => void;

  // 场景触发
  triggerEmergency: (alert: any) => void;
  suggestScene: (scene: SceneType, reason: string) => void;
  dismissSuggestion: () => void;

  // 工作流执行
  executeWorkflow: (tasks: any[]) => Promise<any>;

  // 重置
  resetToNormal: () => void;
}

// 场景配置定义
const SCENE_CONFIGS: Record<SceneType, SceneConfig> = {
  normal: {
    name: '普通模式',
    description: '基础地图浏览和数据查看',
    icon: '🗺️',
    color: '#6b7280',
    bgColor: 'bg-gray-500',
    features: ['地图浏览', '图层管理', '基础查询'],
    defaultView: '2d',
    autoRefresh: false,
    refreshInterval: 0
  },
  inspection: {
    name: '智能巡检',
    description: '自动化监测点巡检和异常检测',
    icon: '🔍',
    color: '#10b981',
    bgColor: 'bg-emerald-500',
    features: ['自动巡检', '异常检测', '趋势分析', '报告生成'],
    defaultView: '2d',
    autoRefresh: true,
    refreshInterval: 30000 // 30秒
  },
  emergency: {
    name: '应急响应',
    description: '紧急情况下的快速响应和指挥',
    icon: '🚨',
    color: '#ef4444',
    bgColor: 'bg-red-500',
    features: ['预警发布', '疏散路线', '资源调度', '多屏联动'],
    defaultView: '3d',
    autoRefresh: true,
    refreshInterval: 10000 // 10秒
  },
  dispatch: {
    name: '调度决策',
    description: '优化水电调度和资源配置',
    icon: '⚙️',
    color: '#f59e0b',
    bgColor: 'bg-amber-500',
    features: ['方案对比', '参数优化', '效益分析', '风险评估'],
    defaultView: 'charts',
    autoRefresh: true,
    refreshInterval: 60000 // 1分钟
  },
  analysis: {
    name: '数据分析',
    description: '深度数据挖掘和智能分析',
    icon: '📊',
    color: '#8b5cf6',
    bgColor: 'bg-violet-500',
    features: ['数据挖掘', '模式识别', '预测建模', '报告生成'],
    defaultView: 'charts',
    autoRefresh: false,
    refreshInterval: 0
  }
};

// 创建store
export const useSceneStore = create<SceneState & SceneActions>()(
  persist(
    (set, get) => ({
      // 初始状态
      currentScene: 'normal',
      previousScene: 'normal',
      isTransitioning: false,

      scenes: SCENE_CONFIGS,

      sceneData: {
        inspection: {
          monitoringPoints: [],
          anomalies: [],
          lastInspection: ''
        },
        emergency: {
          alerts: [],
          riskLevel: 'low',
          affectedAreas: [],
          evacuationRoutes: []
        },
        dispatch: {
          scenarios: [],
          currentScenario: '',
          parameters: {},
          optimizationResults: []
        },
        analysis: {
          datasets: [],
          charts: [],
          insights: [],
          reports: []
        }
      },

      preferences: {
        autoSwitchScenes: true,
        aiSuggestions: true,
        thresholdAlerts: true
      },

      // 场景切换
      setScene: async (scene: SceneType, context?: any) => {
        const { currentScene, scenes } = get();
        if (currentScene === scene) return;

        set({ isTransitioning: true });

        try {
          // 执行场景切换逻辑
          await executeSceneTransition(currentScene, scene, context);

          set({
            previousScene: currentScene,
            currentScene: scene,
            isTransitioning: false
          });

          // 触发场景初始化
          await initializeScene(scene, context);

        } catch (error) {
          console.error('场景切换失败:', error);
          set({ isTransitioning: false });
          throw error;
        }
      },

      switchToPreviousScene: async () => {
        const { previousScene } = get();
        if (previousScene !== 'normal') {
          await get().setScene(previousScene);
        }
      },

      // 数据管理
      updateSceneData: (scene: SceneType, data: any) => {
        set(state => ({
          sceneData: {
            ...state.sceneData,
            [scene]: {
              ...state.sceneData[scene],
              ...data
            }
          }
        }));
      },

      updateCurrentSceneData: (data: any) => {
        const { currentScene } = get();
        get().updateSceneData(currentScene, data);
      },

      // 偏好设置
      setPreference: (key: keyof SceneState['preferences'], value: boolean) => {
        set(state => ({
          preferences: {
            ...state.preferences,
            [key]: value
          }
        }));
      },

      // 触发器
      triggerEmergency: (alert: any) => {
        const { preferences } = get();

        if (preferences.thresholdAlerts) {
          get().setScene('emergency', { alert });
        }
      },

      suggestScene: (scene: SceneType, reason: string) => {
        const { preferences, currentScene } = get();

        if (preferences.aiSuggestions && currentScene !== scene) {
          // 显示AI建议（由UI组件处理）
          window.dispatchEvent(new CustomEvent('ai-scene-suggestion', {
            detail: { scene, reason }
          }));
        }
      },

      dismissSuggestion: () => {
        window.dispatchEvent(new CustomEvent('dismiss-scene-suggestion'));
      },

      // 工作流执行
      executeWorkflow: async (tasks: any[]) => {
        const results = [];

        for (const task of tasks) {
          try {
            const result = await executeTask(task);
            results.push(result);
          } catch (error) {
            console.error('任务执行失败:', task, error);
            throw error;
          }
        }

        return results;
      },

      // 重置
      resetToNormal: () => {
        set({
          currentScene: 'normal',
          previousScene: 'normal',
          isTransitioning: false
        });
      }
    }),
    {
      name: 'scene-store',
      partialize: (state) => ({
        currentScene: state.currentScene,
        previousScene: state.previousScene,
        sceneData: state.sceneData,
        preferences: state.preferences
      })
    }
  )
);

// 辅助函数：执行场景切换
async function executeSceneTransition(fromScene: SceneType, toScene: SceneType, context?: any) {
  console.log(`场景切换: ${fromScene} → ${toScene}`, context);

  // 模拟切换动画延迟
  await new Promise(resolve => setTimeout(resolve, 500));

  // 可以在这里添加更多切换逻辑
  // 比如：保存当前场景状态、清理资源、预加载新场景数据等
}

// 辅助函数：初始化场景
async function initializeScene(scene: SceneType, context?: any) {
  const config = SCENE_CONFIGS[scene];
  console.log(`初始化场景: ${scene} - ${config.name}`);

  // 根据场景类型执行不同的初始化逻辑
  switch (scene) {
    case 'inspection':
      await initializeInspectionScene(context);
      break;
    case 'emergency':
      await initializeEmergencyScene(context);
      break;
    case 'dispatch':
      await initializeDispatchScene(context);
      break;
    case 'analysis':
      await initializeAnalysisScene(context);
      break;
  }
}

// 场景初始化函数
async function initializeInspectionScene(context?: any) {
  // 加载监测点数据
  const monitoringPoints = await fetchMonitoringPoints();

  useSceneStore.getState().updateSceneData('inspection', {
    monitoringPoints,
    lastInspection: new Date().toISOString()
  });
}

async function initializeEmergencyScene(context?: any) {
  // 加载预警数据
  const alerts = await fetchEmergencyAlerts();

  useSceneStore.getState().updateSceneData('emergency', {
    alerts,
    riskLevel: calculateRiskLevel(alerts),
    affectedAreas: calculateAffectedAreas(alerts)
  });
}

async function initializeDispatchScene(context?: any) {
  // 加载调度方案
  const scenarios = await fetchDispatchScenarios();

  useSceneStore.getState().updateSceneData('dispatch', {
    scenarios,
    currentScenario: scenarios[0]?.id || '',
    parameters: getDefaultDispatchParameters()
  });
}

async function initializeAnalysisScene(context?: any) {
  // 加载分析数据
  const datasets = await fetchAnalysisDatasets();

  useSceneStore.getState().updateSceneData('analysis', {
    datasets,
    charts: generateDefaultCharts(datasets)
  });
}

// 模拟API调用（实际项目中替换为真实API）
async function fetchMonitoringPoints() {
  // 模拟异步数据获取
  return new Promise(resolve => {
    setTimeout(() => {
      resolve([
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
        }
      ]);
    }, 100);
  });
}

async function fetchEmergencyAlerts() {
  return [];
}

async function fetchDispatchScenarios() {
  return [];
}

async function fetchAnalysisDatasets() {
  return [];
}

// 辅助函数
function calculateRiskLevel(alerts: any[]): 'low' | 'medium' | 'high' | 'critical' {
  if (alerts.length === 0) return 'low';

  const hasCritical = alerts.some(alert => alert.severity === 'critical');
  const hasHigh = alerts.some(alert => alert.severity === 'high');

  if (hasCritical) return 'critical';
  if (hasHigh) return 'high';
  return 'medium';
}

function calculateAffectedAreas(alerts: any[]) {
  return [];
}

function getDefaultDispatchParameters() {
  return {
    waterLevelLimit: 175.0,
    dischargeFlow: 25000,
    powerGeneration: 10000
  };
}

function generateDefaultCharts(datasets: any[]) {
  return [];
}

// 任务执行函数
async function executeTask(task: any) {
  console.log('执行任务:', task);

  // 模拟任务执行
  await new Promise(resolve => setTimeout(resolve, 1000));

  return {
    success: true,
    result: `任务完成: ${task.type}`,
    timestamp: new Date().toISOString()
  };
}

// 导出场景配置供组件使用
export { SCENE_CONFIGS };

// 自定义hook：智能场景切换
export const useSmartSceneSwitch = () => {
  const { currentScene, setScene, preferences } = useSceneStore();

  // 监听AI建议
  useEffect(() => {
    const handleAISuggestion = (event: CustomEvent) => {
      const { scene, reason } = event.detail;
      if (preferences.aiSuggestions && currentScene !== scene) {
        // 显示建议确认对话框
        const confirmed = window.confirm(`AI建议切换到${SCENE_CONFIGS[scene].name}模式\n原因：${reason}`);
        if (confirmed) {
          setScene(scene);
        }
      }
    };

    window.addEventListener('ai-scene-suggestion', handleAISuggestion as EventListener);
    return () => window.removeEventListener('ai-scene-suggestion', handleAISuggestion as EventListener);
  }, [currentScene, preferences.aiSuggestions, setScene]);

  return {
    currentScene,
    currentConfig: SCENE_CONFIGS[currentScene],
    switchScene: setScene
  };
};

// 自定义hook：场景数据订阅
export const useSceneData = (scene: SceneType) => {
  const sceneData = useSceneStore(state => state.sceneData[scene]);
  const updateData = useSceneStore(state => state.updateSceneData);

  return {
    data: sceneData,
    updateData: (data: any) => updateData(scene, data)
  };
};