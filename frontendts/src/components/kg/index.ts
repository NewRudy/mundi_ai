/**
 * 知识图谱组件导出
 * 松耦合架构下的KG UI组件集合
 */

export { default as KGSearchPanel } from './KGSearchPanel';
export { default as KGVisualizationPanel } from './KGVisualizationPanel';
export { default as KGIntegrationPanel } from './KGIntegrationPanel';

export type {
  KGSearchResult,
  KGSearchPanelProps
} from './KGSearchPanel';

export type {
  KGNode,
  KGRelationship,
  KGVisualizationData,
  KGVisualizationPanelProps
} from './KGVisualizationPanel';

export type {
  HydroSceneData,
  KGInsight,
  KGIntegrationPanelProps
} from './KGIntegrationPanel';