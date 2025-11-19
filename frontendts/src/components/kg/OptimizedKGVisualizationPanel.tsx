/**
 * OptimizedKGVisualizationPanel - 优化的知识图谱可视化面板
 * 使用Canvas 2D和优化的力导向算法实现高性能图可视化
 */

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Maximize2, Minimize2, Download, RefreshCw, AlertCircle, Play, Pause } from 'lucide-react';
import { secureEventBus, EventType, SecureEvent } from '../../services/SecureEventBusService';

// 图数据结构
interface KGNode {
  id: string;
  name: string;
  type: string;
  properties: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;  // 速度x
  vy?: number;  // 速度y
  fx?: number;  // 固定力x
  fy?: number;  // 固定力y
  radius?: number;
  color?: string;
  mass?: number;
  degree?: number;
}

interface KGRelationship {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

interface KGVisualizationData {
  nodes: KGNode[];
  relationships: KGRelationship[];
  metadata: {
    totalNodes: number;
    totalRelationships: number;
    queryTime: number;
    bounds?: {
      minX: number;
      minY: number;
      maxX: number;
      maxY: number;
    };
  };
}

// 渲染优化配置
interface RenderConfig {
  nodeRadius: number;
  edgeWidth: number;
  fontSize: number;
  showLabels: boolean;
  showEdges: boolean;
  animationSpeed: number;
  maxFPS: number;
}

const DEFAULT_RENDER_CONFIG: RenderConfig = {
  nodeRadius: 6,
  edgeWidth: 1,
  fontSize: 10,
  showLabels: true,
  showEdges: true,
  animationSpeed: 0.6,
  maxFPS: 30
};

// 性能监控
class PerformanceMonitor {
  private frameCount = 0;
  private lastTime = performance.now();
  private fps = 0;
  private avgFrameTime = 0;

  recordFrame(): void {
    const now = performance.now();
    const deltaTime = now - this.lastTime;

    this.frameCount++;
    this.avgFrameTime = (this.avgFrameTime * (this.frameCount - 1) + deltaTime) / this.frameCount;

    if (deltaTime >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / deltaTime);
      this.frameCount = 0;
      this.lastTime = now;
    }
  }

  getFPS(): number {
    return this.fps;
  }

  getAverageFrameTime(): number {
    return this.avgFrameTime;
  }

  reset(): void {
    this.frameCount = 0;
    this.lastTime = performance.now();
    this.fps = 0;
    this.avgFrameTime = 0;
  }
}

interface OptimizedKGVisualizationPanelProps {
  className?: string;
  height?: number;
  onNodeSelect?: (node: KGNode) => void;
  onExport?: (data: KGVisualizationData) => void;
  renderConfig?: Partial<RenderConfig>;
  maxNodes?: number;
  enablePerformanceMonitoring?: boolean;
}

export const OptimizedKGVisualizationPanel: React.FC<OptimizedKGVisualizationPanelProps> = ({
  className = '',
  height = 400,
  onNodeSelect,
  onExport,
  renderConfig = {},
  maxNodes = 500,
  enablePerformanceMonitoring = true
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number>(0);
  const performanceMonitorRef = useRef<PerformanceMonitor>(new PerformanceMonitor());

  const [data, setData] = useState<KGVisualizationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [isAnimating, setIsAnimating] = useState(true);
  const [performance, setPerformance] = useState({ fps: 0, avgFrameTime: 0 });

  // 合并渲染配置
  const config = useMemo(() => ({ ...DEFAULT_RENDER_CONFIG, ...renderConfig }), [renderConfig]);

  // 颜色映射
  const nodeColors = useMemo(() => ({
    'Location': '#10b981',
    'AdministrativeUnit': '#f59e0b',
    'Feature': '#ef4444',
    'Dataset': '#8b5cf6',
    'Concept': '#06b6d4',
    'TimePeriod': '#84cc16',
    'MonitoringStation': '#3b82f6',
    'FloodRisk': '#dc2626',
    'River': '#0ea5e9',
    'Dam': '#7c3aed',
    'default': '#6b7280'
  }), []);

  // 空间索引 - 用于快速节点查找
  class SpatialIndex {
    private nodes: KGNode[] = [];
    private grid: Map<string, KGNode[]> = new Map();
    private cellSize: number;

    constructor(cellSize: number = 50) {
      this.cellSize = cellSize;
    }

    build(nodes: KGNode[], width: number, height: number): void {
      this.nodes = nodes;
      this.grid.clear();

      nodes.forEach(node => {
        if (node.x !== undefined && node.y !== undefined) {
          const cellKey = this.getCellKey(node.x, node.y);
          if (!this.grid.has(cellKey)) {
            this.grid.set(cellKey, []);
          }
          this.grid.get(cellKey)!.push(node);
        }
      });
    }

    private getCellKey(x: number, y: number): string {
      const cellX = Math.floor(x / this.cellSize);
      const cellY = Math.floor(y / this.cellSize);
      return `${cellX},${cellY}`;
    }

    findNear(x: number, y: number, radius: number): KGNode | null {
      const searchRadius = Math.ceil(radius / this.cellSize);
      const centerCellX = Math.floor(x / this.cellSize);
      const centerCellY = Math.floor(y / this.cellSize);

      let closestNode: KGNode | null = null;
      let closestDistance = Infinity;

      // 搜索周围的格子
      for (let dx = -searchRadius; dx <= searchRadius; dx++) {
        for (let dy = -searchRadius; dy <= searchRadius; dy++) {
          const cellKey = `${centerCellX + dx},${centerCellY + dy}`;
          const nodesInCell = this.grid.get(cellKey);

          if (nodesInCell) {
            for (const node of nodesInCell) {
              if (node.x !== undefined && node.y !== undefined) {
                const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2);
                if (distance < radius && distance < closestDistance) {
                  closestDistance = distance;
                  closestNode = node;
                }
              }
            }
          }
        }
      }

      return closestNode;
    }
  }

  const spatialIndexRef = useRef<SpatialIndex>(new SpatialIndex());

  // 优化的力导向布局算法
  const applyOptimizedForceLayout = useCallback((nodes: KGNode[], relationships: KGRelationship[], width: number, height: number) => {
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const iterations = 300;
    const repulsionStrength = 8000;
    const attractionStrength = 0.01;
    const damping = 0.9;
    const centerForce = 0.001;
    const idealEdgeLength = 100;

    // 初始化节点属性
    nodes.forEach((node, index) => {
      if (node.vx === undefined) node.vx = 0;
      if (node.vy === undefined) node.vy = 0;
      if (node.mass === undefined) node.mass = 1;
      if (node.degree === undefined) node.degree = 0;
      if (node.radius === undefined) node.radius = config.nodeRadius;
      if (node.color === undefined) node.color = nodeColors[node.type] || nodeColors.default;

      // 计算节点度数
      node.degree = relationships.filter(rel =>
        rel.source === node.id || rel.target === node.id
      ).length;

      // 根据度数调整质量
      node.mass = Math.max(1, Math.sqrt(node.degree + 1));
    });

    // 预计算边的理想长度
    const idealLengths = new Map<string, number>();
    relationships.forEach(rel => {
      const sourceNode = nodeMap.get(rel.source);
      const targetNode = nodeMap.get(rel.target);
      if (sourceNode && targetNode) {
        const key = `${rel.source}-${rel.target}`;
        const combinedDegree = (sourceNode.degree || 0) + (targetNode.degree || 0);
        idealLengths.set(key, idealEdgeLength + combinedDegree * 5);
      }
    });

    // 初始化位置（如果不存在）
    nodes.forEach((node, index) => {
      if (node.x === undefined || node.y === undefined) {
        // 使用度数影响初始位置
        const degreeFactor = (node.degree || 0) / Math.max(1, nodes.length);
        const angle = (index / nodes.length) * 2 * Math.PI + degreeFactor;
        const radius = 50 + (node.degree || 0) * 10;
        node.x = width / 2 + radius * Math.cos(angle);
        node.y = height / 2 + radius * Math.sin(angle);
      }
    });

    //  Barnes-Hut 近似算法参数
    const theta = 0.5;
    const maxDepth = 10;

    // 力导向迭代
    for (let iter = 0; iter < iterations; iter++) {
      // 重置力
      nodes.forEach(node => {
        node.fx = 0;
        node.fy = 0;
      });

      // 计算排斥力（使用简化版本以提高性能）
      for (let i = 0; i < nodes.length; i++) {
        const node1 = nodes[i];
        if (node1.x === undefined || node1.y === undefined) continue;

        for (let j = i + 1; j < nodes.length; j++) {
          const node2 = nodes[j];
          if (node2.x === undefined || node2.y === undefined) continue;

          const dx = node2.x - node1.x;
          const dy = node2.y - node1.y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;

          // 避免节点重叠
          const minDistance = (node1.radius || config.nodeRadius) + (node2.radius || config.nodeRadius) + 5;
          if (distance < minDistance) {
            const overlap = minDistance - distance;
            const force = overlap * 10;
            const fx = (dx / distance) * force;
            const fy = (dy / distance) * force;

            node1.fx -= fx;
            node1.fy -= fy;
            node2.fx += fx;
            node2.fy += fy;
            continue;
          }

          // 标准排斥力
          const force = (repulsionStrength * node1.mass! * node2.mass!) / (distance * distance);
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;

          node1.fx -= fx;
          node1.fy -= fy;
          node2.fx += fx;
          node2.fy += fy;
        }
      }

      // 计算吸引力（边力）
      relationships.forEach(rel => {
        const source = nodeMap.get(rel.source);
        const target = nodeMap.get(rel.target);
        if (!source || !target || source.x === undefined || source.y === undefined ||
            target.x === undefined || target.y === undefined) return;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        const key = `${rel.source}-${rel.target}`;
        const idealLength = idealLengths.get(key) || idealEdgeLength;

        const displacement = distance - idealLength;
        const force = displacement * attractionStrength;

        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        source.fx += fx;
        source.fy += fy;
        target.fx -= fx;
        target.fy -= fy;
      });

      // 添加中心力（防止图形漂移）
      const centerX = width / 2;
      const centerY = height / 2;

      nodes.forEach(node => {
        if (node.x === undefined || node.y === undefined) return;
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        node.fx += dx * centerForce;
        node.fy += dy * centerForce;
      });

      // 应用力并更新位置
      nodes.forEach(node => {
        if (node.x === undefined || node.y === undefined || node.fx === undefined || node.fy === undefined) return;

        // 更新速度
        node.vx = (node.vx || 0) * damping + node.fx / node.mass!;
        node.vy = (node.vy || 0) * damping + node.fy / node.mass!;

        // 更新位置
        node.x += node.vx;
        node.y += node.vy;

        // 边界检查
        const radius = node.radius || config.nodeRadius;
        node.x = Math.max(radius, Math.min(width - radius, node.x));
        node.y = Math.max(radius, Math.min(height - radius, node.y));
      });

      // 温度冷却（逐步减少运动）
      if (iter > iterations * 0.8) {
        const coolingFactor = 1 - (iter - iterations * 0.8) / (iterations * 0.2);
        nodes.forEach(node => {
          if (node.vx !== undefined) node.vx *= coolingFactor;
          if (node.vy !== undefined) node.vy *= coolingFactor;
        });
      }
    }

    return nodes;
  }, [config, nodeColors]);

  // 高效的Canvas渲染
  const renderFrame = useCallback((visualizationData: KGVisualizationData, canvas: HTMLCanvasElement) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const startTime = performance.now();

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const { nodes, relationships } = visualizationData;

    // 构建节点映射
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    // 渲染边（如果启用）
    if (config.showEdges) {
      ctx.strokeStyle = '#94a3b8';
      ctx.lineWidth = config.edgeWidth;
      ctx.globalAlpha = 0.6;

      relationships.forEach(rel => {
        const source = nodeMap.get(rel.source);
        const target = nodeMap.get(rel.target);
        if (source && target && source.x !== undefined && source.y !== undefined &&
            target.x !== undefined && target.y !== undefined) {

          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();

          // 渲染边标签（性能允许时）
          if (nodes.length < 100) {
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;
            ctx.fillStyle = '#64748b';
            ctx.font = `${config.fontSize * 0.8}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText(rel.type, midX, midY - 2);
          }
        }
      });

      ctx.globalAlpha = 1.0;
    }

    // 渲染节点
    nodes.forEach(node => {
      if (node.x === undefined || node.y === undefined) return;

      const isSelected = selectedNode?.id === node.id;
      const radius = isSelected ? (node.radius || config.nodeRadius) * 1.3 : (node.radius || config.nodeRadius);

      // 节点阴影（选中时）
      if (isSelected) {
        ctx.shadowColor = '#3b82f6';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
      }

      // 节点圆圈
      ctx.fillStyle = node.color || nodeColors[node.type] || nodeColors.default;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fill();

      // 节点边框
      if (isSelected) {
        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // 重置阴影
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;

      // 节点标签（如果启用且性能允许）
      if (config.showLabels && nodes.length < 200) {
        ctx.fillStyle = '#1f2937';
        ctx.font = `${config.fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(node.name, node.x, node.y - radius - 3);
      }
    });

    // 性能监控
    if (enablePerformanceMonitoring) {
      const renderTime = performance.now() - startTime;
      performanceMonitorRef.current.recordFrame();

      const fps = performanceMonitorRef.current.getFPS();
      const avgFrameTime = performanceMonitorRef.current.getAverageFrameTime();

      setPerformance({ fps, avgFrameTime });

      // 显示性能信息
      ctx.fillStyle = '#6b7280';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`FPS: ${fps}`, 10, 20);
      ctx.fillText(`Frame: ${renderTime.toFixed(1)}ms`, 10, 32);
      ctx.fillText(`Nodes: ${nodes.length}`, 10, 44);
      ctx.fillText(`Edges: ${relationships.length}`, 10, 56);
    }
  }, [config, nodeColors, selectedNode, enablePerformanceMonitoring]);

  // 动画循环
  const animate = useCallback(() => {
    if (!data || !isAnimating) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    // 应用力导向算法的一步
    const newNodes = applyOptimizedForceLayout(data.nodes, data.relationships, canvas.width, canvas.height);

    // 更新数据
    setData(prev => prev ? { ...prev, nodes: newNodes } : null);

    // 渲染
    renderFrame({ ...data, nodes: newNodes }, canvas);

    // 继续动画
    animationRef.current = requestAnimationFrame(animate);
  }, [data, isAnimating, applyOptimizedForceLayout, renderFrame]);

  // 加载知识图谱数据
  const loadKGData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 发布分析请求事件
      const response = await secureEventBus.requestReply(
        EventType.KG_ANALYSIS_REQUEST,
        {
          action: 'get_visualization_data',
          limit: maxNodes,
          include_relationships: true,
          optimization: {
            spatial_index: true,
            degree_centrality: true
          }
        },
        EventType.KG_ANALYSIS_COMPLETED,
        15000
      );

      if (response?.payload?.data) {
        const visualizationData = response.payload.data as KGVisualizationData;

        // 初始化节点属性
        visualizationData.nodes.forEach(node => {
          node.radius = config.nodeRadius;
          node.color = nodeColors[node.type] || nodeColors.default;
        });

        setData(visualizationData);

        // 构建空间索引
        const canvas = canvasRef.current;
        if (canvas) {
          spatialIndexRef.current.build(visualizationData.nodes, canvas.width, canvas.height);
        }

        // 开始动画
        if (isAnimating) {
          animationRef.current = requestAnimationFrame(animate);
        }
      } else {
        setError('无法加载知识图谱数据');
      }
    } catch (err) {
      console.error('KG可视化数据加载失败:', err);
      setError('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [maxNodes, config, nodeColors, isAnimating, animate]);

  // 处理画布点击
  const handleCanvasClick = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!data) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 使用空间索引快速查找
    const clickedNode = spatialIndexRef.current.findNear(x, y, config.nodeRadius * 2);

    if (clickedNode) {
      setSelectedNode(clickedNode);
      if (onNodeSelect) {
        onNodeSelect(clickedNode);
      }

      // 发布节点选择事件
      secureEventBus.publishEvent(EventType.KG_ANALYSIS_REQUEST, {
        action: 'node_selected',
        node: clickedNode
      });
    } else {
      setSelectedNode(null);
    }
  }, [data, onNodeSelect, config.nodeRadius]);

  // 导出数据
  const handleExport = useCallback(() => {
    if (!data) return;

    if (onExport) {
      onExport(data);
    } else {
      // 默认导出为JSON
      const jsonData = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `kg-visualization-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [data, onExport]);

  // 切换动画
  const toggleAnimation = useCallback(() => {
    setIsAnimating(prev => !prev);
  }, []);

  // 监听KG数据更新
  useEffect(() => {
    const unsubscribe = secureEventBus.subscribe(EventType.KG_DATA_UPDATED, () => {
      loadKGData();
    });

    return unsubscribe;
  }, [loadKGData]);

  // 初始加载
  useEffect(() => {
    loadKGData();
  }, [loadKGData]);

  // 动画控制
  useEffect(() => {
    if (isAnimating && data) {
      animationRef.current = requestAnimationFrame(animate);
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isAnimating, data, animate]);

  // 画布大小调整
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (canvas && container) {
        const rect = container.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = isFullscreen ? window.innerHeight - 200 : height;

        // 重新构建空间索引
        if (data) {
          spatialIndexRef.current.build(data.nodes, canvas.width, canvas.height);
        }
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [height, isFullscreen, data]);

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`} ref={containerRef}>
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800">
          知识图谱可视化
          {data && (
            <span className="text-sm font-normal text-gray-500 ml-2">
              ({data.metadata.totalNodes} 节点, {data.metadata.totalRelationships} 关系)
            </span>
          )}
        </h3>
        <div className="flex items-center space-x-2">
          {enablePerformanceMonitoring && (
            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <span>FPS: {performance.fps}</span>
              <span>Frame: {performance.avgFrameTime.toFixed(1)}ms</span>
            </div>
          )}

          <button
            onClick={toggleAnimation}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            title={isAnimating ? "暂停动画" : "播放动画"}
          >
            {isAnimating ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>

          <button
            onClick={loadKGData}
            disabled={loading}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            title="刷新数据"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleExport}
            disabled={!data}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            title="导出数据"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            title={isFullscreen ? "退出全屏" : "全屏"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* 可视化区域 */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-600">加载知识图谱数据中...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <div className="flex items-center">
              <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}

        <canvas
          ref={canvasRef}
          className="w-full border-0 cursor-pointer"
          style={{ height: isFullscreen ? window.innerHeight - 200 : height }}
          onClick={handleCanvasClick}
        />

        {/* 选中节点信息 */}
        {selectedNode && (
          <div className="absolute bottom-4 left-4 bg-white bg-opacity-95 p-4 rounded-lg shadow-lg max-w-sm">
            <div className="text-sm font-medium text-gray-900">{selectedNode.name}</div>
            <div className="text-xs text-gray-600 mt-1">类型: {selectedNode.type}</div>
            <div className="text-xs text-gray-500 mt-1">度数: {selectedNode.degree}</div>
            {Object.keys(selectedNode.properties).length > 0 && (
              <div className="mt-2 text-xs text-gray-700 max-h-20 overflow-y-auto">
                {Object.entries(selectedNode.properties)
                  .slice(0, 5)
                  .map(([key, value]) => (
                    <div key={key}>
                      {key}: {typeof value === 'object' ? JSON.stringify(value) : value}
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* 图例和性能信息 */}
        <div className="absolute top-4 right-4 bg-white bg-opacity-95 p-3 rounded-lg shadow-lg">
          <div className="text-xs font-medium text-gray-700 mb-2">图例</div>
          <div className="space-y-1 text-xs">
            {Object.entries(nodeColors).slice(0, 6).map(([type, color]) => (
              <div key={type} className="flex items-center">
                <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: color }} />
                <span>{type}</span>
              </div>
            ))}
          </div>

          {enablePerformanceMonitoring && (
            <div className="mt-3 pt-2 border-t border-gray-200 text-xs text-gray-500">
              <div>渲染: {performance.avgFrameTime.toFixed(1)}ms</div>
              <div>FPS: {performance.fps}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OptimizedKGVisualizationPanel;