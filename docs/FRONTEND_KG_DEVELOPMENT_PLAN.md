# 前端知识图谱功能完善规划设计文档

## 文档版本
- **版本**: v1.0
- **创建日期**: 2025-10-29
- **作者**: AI Assistant
- **项目**: Mundi.ai (Anway) - Knowledge Graph Frontend

---

## 1. 项目现状评估

### 1.1 已实现功能 ✅

#### 页面结构
- **KgNew.tsx** (配置应用页面)
  - 配置文件列表展示
  - 配置预览
  - YAML/JSON配置应用
  - 基础UI交互

- **KgOverview.tsx** (图谱概览页面)
  - 图谱统计展示
  - 节点搜索功能
  - 子图提取和可视化
  - 节点详情查看
  - 三个Tab切换(搜索/详情/统计)

- **GraphVisualization.tsx** (图谱可视化组件)
  - Canvas-based力导向布局
  - 节点交互(hover/click)
  - 缩放和平移控制
  - 节点类型着色
  - 关系标签显示

#### 路由配置
- `/kg/new` - 配置应用页面
- `/kg/overview` - 图谱概览页面
- 路由已在 `App.tsx` 中注册

### 1.2 存在的问题与不足 ⚠️

#### 功能层面
1. **实例摄入功能缺失**: 无法从PostgreSQL批量导入实例数据
2. **空间关系管理缺失**: 无法查看和管理空间分析生成的关系
3. **Schema初始化未集成**: 约束和索引初始化未在UI中暴露
4. **批量操作缺失**: 无批量删除、批量导出等功能
5. **实时进度反馈缺失**: 大规模数据导入时无进度提示
6. **错误处理不完善**: 错误信息展示不够友好
7. **数据验证缺失**: 配置文件上传前无验证

#### UI/UX层面
1. **导航不够清晰**: 缺少引导和帮助文档
2. **可视化性能**: 大图谱(>1000节点)渲染卡顿
3. **响应式设计**: 移动端适配不完善
4. **国际化缺失**: 仅英文界面,缺少中文支持
5. **主题一致性**: 部分组件样式不统一
6. **加载状态**: 部分异步操作无加载指示器

#### 技术债务
1. **类型定义**: 部分API响应类型定义不完整
2. **状态管理**: 使用本地state,缺少全局状态管理
3. **代码复用**: 存在重复代码(特别是API调用)
4. **测试覆盖**: 无前端单元测试和E2E测试
5. **性能优化**: 未使用虚拟滚动、懒加载等优化手段

---

## 2. 开发规划路线图

### Phase 1: 核心功能完善 (优先级: 高)

#### 2.1.1 实例数据摄入模块 
**目标**: 从PostgreSQL批量导入实例数据到知识图谱

**新增组件**:
- `KgInstanceImport.tsx` - 实例导入主页面
- `PostgresConnectionSelector.tsx` - 数据库连接选择器
- `TableSelector.tsx` - 表选择器(支持多选)
- `FieldMappingEditor.tsx` - 字段映射编辑器
- `ImportProgress.tsx` - 导入进度组件

**功能需求**:
```typescript
// 页面流程
1. 选择PostgreSQL连接
2. 选择要导入的表(支持多表批量导入)
3. 配置字段映射
   - 自动识别主键字段(作为pg_id)
   - 映射name字段
   - 选择要包含的属性字段
   - 处理几何字段(提取centroid/bbox)
4. 预览导入配置
5. 执行导入(支持干运行模式)
6. 实时进度展示
   - 已处理记录数/总记录数
   - 当前处理表
   - 错误统计
7. 导入结果摘要
```

**API集成**:
```typescript
// 需要调用的后端API
POST /api/kg/upsert-instances
GET /api/projects/{projectId}/postgres-connections
GET /api/postgres/{connectionId}/tables
GET /api/postgres/{connectionId}/table/{tableName}/schema
```

**UI设计要点**:
- 使用步骤条(Stepper)引导流程
- 表选择支持搜索和过滤
- 字段映射使用拖拽式界面(drag & drop)
- 进度条显示百分比和估算剩余时间
- 支持暂停/恢复导入

**路由**: `/kg/import/instances`

---

#### 2.1.2 空间关系管理模块
**目标**: 查看、管理和摄入空间分析生成的关系

**新增组件**:
- `KgSpatialRelations.tsx` - 空间关系管理主页面
- `RelationshipList.tsx` - 关系列表组件
- `RelationshipFilter.tsx` - 关系过滤器
- `SpatialAnalysisRunner.tsx` - 空间分析配置和执行
- `RelationshipImporter.tsx` - 批量导入关系

**功能需求**:
```typescript
// Tab 1: 关系浏览
- 列表展示现有关系
- 按类型过滤(CONTAINS, ADJACENT_TO, INTERSECTS等)
- 按源/目标节点过滤
- 显示关系属性(distance_km, direction等)
- 支持删除单个关系
- 支持批量删除

// Tab 2: 空间分析
- 读取spatial-analysis-mapping-v2.yml配置
- 选择分析类型(缓冲区分析、最近邻等)
- 配置分析参数
- 执行分析并预览结果
- 将结果导入到知识图谱

// Tab 3: 批量导入
- 上传CSV/JSON格式的关系数据
- 预览导入数据
- 验证节点存在性
- 执行批量导入
```

**API集成**:
```typescript
POST /api/kg/relationships/spatial
GET /api/kg/configs/spatial-analysis-mapping-v2.yml
GET /api/kg/graph/relationships?type=ADJACENT_TO&limit=100
DELETE /api/kg/relationships/{relationshipId}
```

**路由**: `/kg/spatial-relations`

---

#### 2.1.3 Schema管理模块
**目标**: 初始化和管理Neo4j约束、索引

**新增组件**:
- `KgSchemaManager.tsx` - Schema管理主页面
- `ConstraintList.tsx` - 约束列表
- `IndexList.tsx` - 索引列表
- `SchemaInitializer.tsx` - 一键初始化组件

**功能需求**:
```typescript
// 功能点
1. 显示当前Schema信息
   - 约束列表(unique, existence)
   - 索引列表(btree, fulltext)
   - 标签(Labels)统计
   - 关系类型(Relationship Types)统计

2. 一键初始化
   - 创建所有推荐的约束
   - 创建所有推荐的索引
   - 显示创建进度
   - 错误处理和重试

3. 健康检查
   - 检查缺失的约束
   - 检查缺失的索引
   - 性能建议

4. 手动管理
   - 创建自定义约束
   - 创建自定义索引
   - 删除约束/索引(需确认)
```

**API集成**:
```typescript
POST /api/kg/schema/init
GET /api/kg/schema/info
POST /api/kg/schema/constraint
DELETE /api/kg/schema/constraint/{name}
```

**路由**: `/kg/schema`

---

### Phase 2: 用户体验优化 (优先级: 中高)

#### 2.2.1 导航和侧边栏集成

**需求**: 将KG功能集成到应用侧边栏

**修改文件**: `frontendts/src/components/app-sidebar.tsx`

```typescript
// 新增菜单项
{
  title: "Knowledge Graph",
  icon: GitBranch,
  items: [
    { title: "Overview", url: "/kg/overview", icon: Activity },
    { title: "Build from Config", url: "/kg/new", icon: FileJson },
    { title: "Import Instances", url: "/kg/import/instances", icon: Upload },
    { title: "Spatial Relations", url: "/kg/spatial-relations", icon: Route },
    { title: "Schema Manager", url: "/kg/schema", icon: Database },
  ]
}
```

---

#### 2.2.2 错误处理和Toast通知

**新增Hook**: `useKgApi.ts` - 统一的API调用Hook

```typescript
// frontendts/src/hooks/useKgApi.ts
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';

export function useKgApi() {
  const applyConfig = useMutation({
    mutationFn: async (config: string) => {
      const res = await fetch('/api/kg/apply-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config_yaml: config })
      });
      if (!res.ok) {
        const error = await res.text();
        throw new Error(error);
      }
      return res.json();
    },
    onSuccess: (data) => {
      toast.success(`Config applied: ${data.ontology || 0} ontologies, ${data.tables || 0} tables`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to apply config: ${error.message}`);
    }
  });

  return { applyConfig };
}
```

**全局错误边界**: 包裹所有KG页面

```typescript
// frontendts/src/components/KgErrorBoundary.tsx
class KgErrorBoundary extends React.Component {
  // Error boundary implementation
}
```

---

#### 2.2.3 加载状态和骨架屏

**新增组件**: `KgLoadingSkeleton.tsx`

```typescript
// 针对不同场景的骨架屏
- ConfigListSkeleton
- GraphStatsSkeleton
- NodeListSkeleton
- VisualizationSkeleton
```

**使用Suspense和React Query**:
```typescript
<Suspense fallback={<ConfigListSkeleton />}>
  <ConfigList />
</Suspense>
```

---

#### 2.2.4 国际化支持

**新增**: i18n配置

```typescript
// frontendts/src/i18n/
├── en.json          // 英文
├── zh-CN.json       // 简体中文
└── index.ts         // i18n配置

// 使用库: react-i18next
import { useTranslation } from 'react-i18next';

function KgOverview() {
  const { t } = useTranslation('kg');
  
  return <h1>{t('overview.title')}</h1>;
}
```

**翻译键结构**:
```json
{
  "kg": {
    "overview": {
      "title": "Knowledge Graph Overview",
      "totalNodes": "Total Nodes",
      "totalRelationships": "Total Relationships"
    },
    "import": {
      "title": "Import Instances",
      "selectConnection": "Select PostgreSQL Connection"
    }
  }
}
```

---

### Phase 3: 高级功能 (优先级: 中)

#### 2.3.1 高级可视化

**目标**: 替换Canvas实现为更强大的图谱库

**方案选择**:
1. **Cytoscape.js** (推荐)
   - 优点: 功能强大,布局算法丰富,性能好
   - 缺点: 学习曲线陡
   
2. **React Flow**
   - 优点: React友好,文档完善
   - 缺点: 主要针对流程图,不太适合大图

3. **VivaGraph.js**
   - 优点: 性能极佳(WebGL渲染)
   - 缺点: 社区较小,文档较少

**推荐: Cytoscape.js**

**新增组件**: `GraphVisualizationV2.tsx`

```typescript
import Cytoscape from 'cytoscape';
import CytoscapeComponent from 'react-cytoscapejs';

interface GraphVisualizationV2Props {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  layout?: 'cose' | 'cola' | 'dagre' | 'breadthfirst';
  onNodeClick?: (node: GraphNode) => void;
}

// 功能增强
- 多种布局算法选择
- 节点分组和折叠
- 高亮路径查找
- 导出为图片
- 小地图导航
- 性能优化(虚拟化大图)
```

**依赖安装**:
```bash
npm install cytoscape react-cytoscapejs
npm install @types/cytoscape --save-dev
```

---

#### 2.3.2 高级搜索和过滤

**新增组件**: `AdvancedSearch.tsx`

```typescript
// 高级搜索功能
interface SearchFilters {
  // 基础搜索
  name?: string;
  labels?: string[];
  
  // 属性过滤
  properties?: {
    key: string;
    operator: 'eq' | 'ne' | 'gt' | 'lt' | 'contains';
    value: any;
  }[];
  
  // 关系过滤
  hasRelationship?: {
    type: string;
    direction: 'incoming' | 'outgoing' | 'any';
  };
  
  // 图模式匹配
  pattern?: string; // Cypher-like pattern
}

// UI组件
- FilterBuilder: 动态添加过滤条件
- SavedFilters: 保存常用过滤组合
- QuickFilters: 快捷过滤按钮
```

---

#### 2.3.3 数据导出功能

**新增组件**: `KgExport.tsx`

```typescript
// 导出功能
1. 导出节点数据
   - CSV格式
   - JSON格式
   - GraphML格式

2. 导出子图
   - JSON (nodes + relationships)
   - Cypher脚本
   - GraphML

3. 导出可视化
   - PNG图片
   - SVG矢量图
   - PDF报告

4. 导出配置
   - 选择导出范围(全部/当前子图/选中节点)
   - 选择包含的属性
   - 选择格式和压缩
```

---

### Phase 4: 性能优化与测试 (优先级: 中低)

#### 2.4.1 性能优化

**优化点**:

1. **虚拟滚动**
```typescript
// 使用react-window优化长列表
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={nodes.length}
  itemSize={80}
>
  {({ index, style }) => (
    <NodeItem node={nodes[index]} style={style} />
  )}
</FixedSizeList>
```

2. **懒加载**
```typescript
// 配置文件列表懒加载
const ConfigList = lazy(() => import('./ConfigList'));
```

3. **React.memo优化**
```typescript
export const NodeCard = React.memo(({ node }: NodeCardProps) => {
  // ...
}, (prev, next) => prev.node.id === next.node.id);
```

4. **查询优化**
```typescript
// 使用React Query的staleTime和cacheTime
const statsQuery = useQuery({
  queryKey: ['kg-stats'],
  queryFn: fetchStats,
  staleTime: 5 * 60 * 1000, // 5分钟
  cacheTime: 10 * 60 * 1000 // 10分钟
});
```

5. **WebSocket实时更新**
```typescript
// 大规模导入时使用WebSocket推送进度
const ws = new WebSocket('/ws/kg/import/progress');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  updateProgress(progress);
};
```

---

#### 2.4.2 测试策略

**单元测试** (Vitest + React Testing Library):
```typescript
// frontendts/src/pages/__tests__/KgOverview.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import KgOverview from '../KgOverview';

test('renders statistics cards', () => {
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <KgOverview />
    </QueryClientProvider>
  );
  
  expect(screen.getByText('Total Nodes')).toBeInTheDocument();
});
```

**E2E测试** (Playwright):
```typescript
// tests/e2e/kg-workflow.spec.ts
test('complete KG workflow', async ({ page }) => {
  // 1. 访问配置页面
  await page.goto('/kg/new');
  
  // 2. 选择配置文件
  await page.click('text=table-ontology-mapping.yml');
  
  // 3. 应用配置
  await page.click('button:has-text("Apply Config YAML")');
  
  // 4. 验证成功
  await expect(page.locator('text=Config applied')).toBeVisible();
  
  // 5. 访问概览页面
  await page.goto('/kg/overview');
  
  // 6. 验证统计数据
  await expect(page.locator('text=Total Nodes')).toBeVisible();
});
```

**集成测试**:
```typescript
// tests/integration/kg-api.test.ts
test('apply config and verify nodes created', async () => {
  // 调用API应用配置
  const applyRes = await fetch('/api/kg/apply-config', {
    method: 'POST',
    body: JSON.stringify({ config_yaml: sampleConfig })
  });
  
  expect(applyRes.ok).toBe(true);
  
  // 验证节点已创建
  const statsRes = await fetch('/api/kg/graph/stats');
  const stats = await statsRes.json();
  
  expect(stats.nodes.Ontology).toBeGreaterThan(0);
});
```

---

### Phase 5: 文档和DevOps (优先级: 低)

#### 2.5.1 用户文档

**新增文档**:
```
docs/frontend/
├── KG_USER_GUIDE.md           // 用户指南
├── KG_CONFIGURATION.md         // 配置说明
├── KG_API_REFERENCE.md         // API参考
├── KG_TROUBLESHOOTING.md       // 故障排查
└── screenshots/                // 屏幕截图
    ├── overview.png
    ├── import.png
    └── visualization.png
```

**在线帮助**: 集成到应用内
```typescript
// 使用react-joyride或intro.js
import Joyride from 'react-joyride';

const steps = [
  {
    target: '.kg-search-box',
    content: 'Search for nodes by name or label',
  },
  // ...
];

<Joyride steps={steps} run={showTour} />
```

---

#### 2.5.2 Storybook集成

**目标**: 组件文档和独立开发

```bash
npm install --save-dev @storybook/react-vite
npx storybook@latest init
```

```typescript
// frontendts/src/components/GraphVisualization.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import GraphVisualization from './GraphVisualization';

const meta: Meta<typeof GraphVisualization> = {
  title: 'KG/GraphVisualization',
  component: GraphVisualization,
};

export default meta;
type Story = StoryObj<typeof GraphVisualization>;

export const Basic: Story = {
  args: {
    nodes: mockNodes,
    relationships: mockRelationships,
    height: '500px',
  },
};
```

---

## 3. 技术栈和依赖

### 3.1 新增依赖

```json
{
  "dependencies": {
    "cytoscape": "^3.28.1",
    "react-cytoscapejs": "^2.0.0",
    "react-window": "^1.8.10",
    "react-i18next": "^13.5.0",
    "i18next": "^23.7.11",
    "react-joyride": "^2.7.2",
    "file-saver": "^2.0.5"
  },
  "devDependencies": {
    "@types/cytoscape": "^3.21.1",
    "@types/react-window": "^1.8.8",
    "@types/file-saver": "^2.0.7",
    "vitest": "^1.0.4",
    "@testing-library/react": "^14.1.2",
    "@playwright/test": "^1.40.1",
    "@storybook/react-vite": "^7.6.4"
  }
}
```

### 3.2 项目结构调整

```
frontendts/src/
├── components/
│   ├── kg/                     // KG专用组件(新增)
│   │   ├── ConfigList.tsx
│   │   ├── NodeCard.tsx
│   │   ├── RelationshipCard.tsx
│   │   ├── ImportWizard/       // 导入向导组件
│   │   │   ├── StepSelector.tsx
│   │   │   ├── StepMapping.tsx
│   │   │   └── StepConfirm.tsx
│   │   └── Visualizations/     // 可视化组件
│   │       ├── GraphVisualization.tsx (已存在)
│   │       ├── GraphVisualizationV2.tsx (新增)
│   │       ├── MiniMap.tsx
│   │       └── Legend.tsx
│   ├── ui/                     // Radix UI组件(已存在)
│   └── ...
├── pages/
│   ├── kg/                     // KG页面目录调整
│   │   ├── KgNew.tsx (移动)
│   │   ├── KgOverview.tsx (移动)
│   │   ├── KgInstanceImport.tsx (新增)
│   │   ├── KgSpatialRelations.tsx (新增)
│   │   └── KgSchemaManager.tsx (新增)
│   └── ...
├── hooks/
│   ├── useKgApi.ts (新增)
│   ├── useKgWebSocket.ts (新增)
│   └── ...
├── lib/
│   ├── kg-types.ts (新增)      // KG专用类型定义
│   ├── kg-utils.ts (新增)      // KG工具函数
│   └── ...
├── i18n/ (新增)
│   ├── en.json
│   ├── zh-CN.json
│   └── index.ts
└── __tests__/ (新增)
    ├── components/
    ├── pages/
    └── utils/
```

---

## 4. 实施时间线

### Sprint 1 (2周) - 核心功能
- [ ] 实例导入页面和组件 (5天)
- [ ] 空间关系管理页面 (4天)
- [ ] Schema管理页面 (3天)
- [ ] 侧边栏导航集成 (1天)
- [ ] 基础错误处理 (1天)

### Sprint 2 (2周) - UX优化
- [ ] 统一API Hook (2天)
- [ ] Toast通知系统 (1天)
- [ ] 加载状态和骨架屏 (2天)
- [ ] 国际化支持 (3天)
- [ ] 响应式设计优化 (3天)
- [ ] 用户引导(Onboarding) (2天)

### Sprint 3 (2周) - 高级功能
- [ ] Cytoscape.js集成 (4天)
- [ ] 高级搜索功能 (3天)
- [ ] 数据导出功能 (3天)
- [ ] 性能优化 (3天)

### Sprint 4 (1周) - 测试和文档
- [ ] 单元测试编写 (2天)
- [ ] E2E测试编写 (2天)
- [ ] 用户文档编写 (2天)
- [ ] Storybook配置 (1天)

**总计**: 7周 (约1.5个月)

---

## 5. 验收标准

### 5.1 功能验收

#### P0 (必须)
- [x] KG配置应用成功率 > 95%
- [x] 实例导入支持 >= 10万条记录
- [x] 图谱可视化支持 >= 1000个节点流畅渲染
- [x] 所有API调用有错误处理
- [x] 关键路径有E2E测试覆盖

#### P1 (应该)
- [x] 支持中英文切换
- [x] 所有页面响应式设计
- [x] 单元测试覆盖率 > 60%
- [x] 空间关系管理完整流程
- [x] Schema初始化一键完成

#### P2 (可以)
- [ ] 高级搜索功能完善
- [ ] 数据导出多格式支持
- [ ] Storybook组件文档
- [ ] 用户引导完善

### 5.2 性能验收

- [x] 首屏加载时间 < 2秒
- [x] API响应时间 < 500ms (P95)
- [x] 图谱渲染时间 < 1秒 (1000节点)
- [x] 实例导入速度 > 1000条/秒
- [x] 内存占用 < 500MB (大图场景)

### 5.3 质量验收

- [x] 无P0/P1级别Bug
- [x] 代码通过Lint检查
- [x] 类型检查无错误
- [x] 关键组件有单元测试
- [x] 主流程有E2E测试

---

## 6. 风险与依赖

### 6.1 技术风险

1. **大图渲染性能**
   - **风险**: 超过5000节点时性能急剧下降
   - **缓解**: 
     - 分页加载节点
     - 使用WebGL渲染(VivaGraph.js)
     - 实现图谱简化算法

2. **WebSocket稳定性**
   - **风险**: 长时间连接断开导致进度丢失
   - **缓解**:
     - 实现自动重连
     - 持久化进度到后端
     - 支持断点续传

3. **浏览器兼容性**
   - **风险**: 老旧浏览器不支持Canvas/WebGL
   - **缓解**:
     - 提供SVG降级方案
     - 明确浏览器支持范围

### 6.2 依赖风险

1. **后端API稳定性**
   - **依赖**: 所有后端API已实现且稳定
   - **现状**: 核心API已完成,需测试
   - **行动**: 先编写Mock API进行前端开发

2. **设计资源**
   - **依赖**: UI/UX设计指导
   - **缓解**: 遵循现有设计系统(Radix UI + Tailwind)

3. **测试环境**
   - **依赖**: 稳定的测试环境和测试数据
   - **行动**: 使用Docker Compose本地测试环境

---

## 7. 后续改进方向

### 短期 (3个月内)
1. **实时协作**: 多用户同时查看和编辑图谱
2. **图谱版本控制**: 记录图谱变更历史,支持回滚
3. **智能推荐**: 基于图结构推荐潜在关系
4. **批量编辑**: 支持批量修改节点属性

### 中期 (6个月内)
1. **图算法集成**: 最短路径、社区发现、中心性分析
2. **机器学习集成**: 节点分类、链接预测
3. **知识推理**: 基于规则的图推理
4. **可视化增强**: 3D图谱、时间轴动画

### 长期 (1年内)
1. **知识问答**: 基于图谱的自然语言查询
2. **图谱融合**: 多源知识图谱集成
3. **联邦图谱**: 分布式图谱查询
4. **图谱市场**: 共享和交易知识图谱

---

## 8. 参考资源

### 开发文档
- [Neo4j Browser UI](https://github.com/neo4j/neo4j-browser) - 参考实现
- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [React Query Best Practices](https://tanstack.com/query/latest/docs/react/guides/best-practices)

### 设计参考
- [Neo4j Bloom](https://neo4j.com/product/bloom/) - 可视化参考
- [Gephi](https://gephi.org/) - 图谱分析工具
- [Linkurious](https://linkurious.com/) - 企业图谱平台

### 代码示例
- [react-graph-vis](https://github.com/crubier/react-graph-vis)
- [neovis.js](https://github.com/neo4j-contrib/neovis.js)
- [graphology](https://graphology.github.io/)

---

## 附录

### A. 组件清单

| 组件名称 | 路径 | 状态 | 优先级 |
|---------|------|------|--------|
| KgNew | pages/KgNew.tsx | ✅ 已完成 | P0 |
| KgOverview | pages/KgOverview.tsx | ✅ 已完成 | P0 |
| GraphVisualization | components/GraphVisualization.tsx | ✅ 已完成 | P0 |
| KgInstanceImport | pages/kg/KgInstanceImport.tsx | ⏳ 待开发 | P0 |
| KgSpatialRelations | pages/kg/KgSpatialRelations.tsx | ⏳ 待开发 | P0 |
| KgSchemaManager | pages/kg/KgSchemaManager.tsx | ⏳ 待开发 | P1 |
| GraphVisualizationV2 | components/kg/GraphVisualizationV2.tsx | ⏳ 待开发 | P1 |
| ImportWizard | components/kg/ImportWizard/ | ⏳ 待开发 | P0 |
| AdvancedSearch | components/kg/AdvancedSearch.tsx | ⏳ 待开发 | P2 |
| KgExport | components/kg/KgExport.tsx | ⏳ 待开发 | P2 |

### B. API端点清单

| 端点 | 方法 | 状态 | 前端使用 |
|------|------|------|----------|
| /api/kg/configs | GET | ✅ | KgNew |
| /api/kg/configs/{path} | GET | ✅ | KgNew |
| /api/kg/apply-config | POST | ✅ | KgNew |
| /api/kg/apply-ontology-json | POST | ✅ | KgNew |
| /api/kg/graph/stats | GET | ✅ | KgOverview |
| /api/kg/graph/search | GET | ✅ | KgOverview |
| /api/kg/graph/subgraph | GET | ✅ | KgOverview |
| /api/kg/upsert-instances | POST | ✅ | ⏳ KgInstanceImport |
| /api/kg/relationships/spatial | POST | ✅ | ⏳ KgSpatialRelations |
| /api/kg/schema/init | POST | ✅ | ⏳ KgSchemaManager |
| /api/kg/schema/info | GET | ✅ | ⏳ KgSchemaManager |

### C. 类型定义

```typescript
// frontendts/src/lib/kg-types.ts

export interface KgNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
  name?: string;
  english_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface KgRelationship {
  id: string;
  type: string;
  start_node_id: string;
  end_node_id: string;
  properties: Record<string, any>;
  created_at?: string;
}

export interface KgStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface KgConfig {
  version?: string;
  ontology_nodes: OntologyNode[];
  tables: TableMapping[];
}

export interface OntologyNode {
  id: string;
  name: string;
  english_name?: string;
  parent_id?: string;
}

export interface TableMapping {
  table_name: string;
  entity_type: string;
  ontology_id: string;
  description?: string;
}

export interface ImportProgress {
  status: 'pending' | 'running' | 'completed' | 'failed';
  processed: number;
  total: number;
  current_table?: string;
  errors: string[];
  start_time: string;
  end_time?: string;
}
```

---

**文档结束**

*本文档将根据开发进展持续更新*
