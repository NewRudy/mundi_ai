/**
 * KGVisualizationPanel - 知识图谱可视化面板
 * 松耦合架构下的轻量级可视化组件
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Maximize2, Minimize2, Download, RefreshCw, AlertCircle } from 'lucide-react';
import { eventBus, EventType } from '../../services/EventBusService';

interface KGNode {
  id: string;
  name: string;
  type: string;
  properties: Record<string, any>;
  x?: number;
  y?: number;
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
  };
}

interface KGVisualizationPanelProps {
  className?: string;
  height?: number;
  onNodeSelect?: (node: KGNode) => void;
  onExport?: (data: KGVisualizationData) => void;
}

export const KGVisualizationPanel: React.FC<KGVisualizationPanelProps> = ({
  className = '',
  height = 400,
  onNodeSelect,
  onExport
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [data, setData] = useState<KGVisualizationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);

  // 简单的力导向布局算法
  const applyForceLayout = useCallback((nodes: KGNode[], relationships: KGRelationship[]) => {
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const iterations = 100;
    const repulsionStrength = 1000;
    const attractionStrength = 0.1;
    const damping = 0.9;

    // 初始化位置
    nodes.forEach((node, index) => {
      if (node.x === undefined || node.y === undefined) {
        const angle = (index / nodes.length) * 2 * Math.PI;
        const radius = 100;
        node.x = 400 + radius * Math.cos(angle);
        node.y = height / 2 + radius * Math.sin(angle);
      }
    });

    // 力导向迭代
    for (let iter = 0; iter < iterations; iter++) {
      // 计算斥力
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x! - nodes[i].x!;
          const dy = nodes[j].y! - nodes[i].y!;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsionStrength / (distance * distance);

          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;

          nodes[i].x! -= fx;
          nodes[i].y! -= fy;
          nodes[j].x! += fx;
          nodes[j].y! += fy;
        }
      }

      // 计算引力（关系）
      relationships.forEach(rel => {
        const source = nodeMap.get(rel.source);
        const target = nodeMap.get(rel.target);
        if (source && target) {
          const dx = target.x! - source.x!;
          const dy = target.y! - source.y!;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = distance * attractionStrength;

          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;

          source.x! += fx;
          source.y! += fy;
          target.x! -= fx;
          target.y! -= fy;
        }
      });

      // 应用阻尼
      nodes.forEach(node => {
        if (node.x !== undefined && node.y !== undefined) {
          node.x = 400 + (node.x - 400) * damping;
          node.y = height / 2 + (node.y - height / 2) * damping;
        }
      });
    }

    return nodes;
  }, [height]);

  // 绘制图形
  const drawGraph = useCallback((visualizationData: KGVisualizationData) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const { nodes, relationships } = visualizationData;
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    // 绘制关系
    relationships.forEach(rel => {
      const source = nodeMap.get(rel.source);
      const target = nodeMap.get(rel.target);
      if (source && target && source.x !== undefined && source.y !== undefined &&
          target.x !== undefined && target.y !== undefined) {

        ctx.strokeStyle = '#94a3b8';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();

        // 绘制关系标签
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        ctx.fillStyle = '#64748b';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(rel.type, midX, midY - 2);
      }
    });

    // 绘制节点
    nodes.forEach(node => {
      if (node.x === undefined || node.y === undefined) return;

      const isSelected = selectedNode?.id === node.id;
      const radius = isSelected ? 8 : 6;

      // 节点颜色基于类型
      let nodeColor = '#3b82f6'; // 默认蓝色
      switch (node.type) {
        case 'Location':
          nodeColor = '#10b981';
          break;
        case 'AdministrativeUnit':
          nodeColor = '#f59e0b';
          break;
        case 'Feature':
          nodeColor = '#ef4444';
          break;
        case 'Dataset':
          nodeColor = '#8b5cf6';
          break;
        default:
          nodeColor = '#3b82f6';
      }

      // 绘制节点圆圈
      ctx.fillStyle = nodeColor;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // 绘制节点标签
      ctx.fillStyle = '#1f2937';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, node.x, node.y - radius - 5);
    });
  }, [selectedNode]);

  // 加载知识图谱数据
  const loadKGData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 发布分析请求事件
      const response = await eventBus.requestReply(
        EventType.KG_ANALYSIS_REQUEST,
        {
          action: 'get_subgraph',
          limit: 50, // 限制节点数量以保持性能
          include_relationships: true
        },
        EventType.KG_ANALYSIS_COMPLETED,
        15000 // 15秒超时
      );

      if (response?.payload?.data) {
        const visualizationData = response.payload.data as KGVisualizationData;

        // 应用力导向布局
        const positionedNodes = applyForceLayout(
          visualizationData.nodes,
          visualizationData.relationships
        );

        const processedData = {
          ...visualizationData,
          nodes: positionedNodes
        };

        setData(processedData);
        drawGraph(processedData);
      } else {
        setError('无法加载知识图谱数据');
      }
    } catch (err) {
      console.error('KG可视化数据加载失败:', err);
      setError('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [applyForceLayout, drawGraph]);

  // 处理画布点击
  const handleCanvasClick = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!data) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 查找点击的节点
    const clickedNode = data.nodes.find(node => {
      if (node.x === undefined || node.y === undefined) return false;
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2);
      return distance <= 8; // 节点半径
    });

    if (clickedNode) {
      setSelectedNode(clickedNode);
      if (onNodeSelect) {
        onNodeSelect(clickedNode);
      }

      // 发布节点选择事件
      eventBus.publishEvent(EventType.KG_ANALYSIS_REQUEST, {
        action: 'node_selected',
        node: clickedNode
      });
    }
  }, [data, onNodeSelect]);

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

  // 监听KG数据更新
  useEffect(() => {
    const unsubscribe = eventBus.subscribe(EventType.KG_DATA_UPDATED, () => {
      loadKGData();
    });

    return unsubscribe;
  }, [loadKGData]);

  // 初始加载
  useEffect(() => {
    loadKGData();
  }, [loadKGData]);

  // 数据变化时重绘
  useEffect(() => {
    if (data) {
      drawGraph(data);
    }
  }, [data, drawGraph]);

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
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
              <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
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
          width={800}
          height={isFullscreen ? 600 : height}
          onClick={handleCanvasClick}
          className="w-full border-0 cursor-pointer"
          style={{ height: isFullscreen ? 600 : height }}
        />

        {/* 选中节点信息 */}
        {selectedNode && (
          <div className="absolute bottom-4 left-4 bg-white bg-opacity-90 p-3 rounded-lg shadow-lg max-w-xs">
            <div className="text-sm font-medium text-gray-900">{selectedNode.name}</div>
            <div className="text-xs text-gray-600 mt-1">类型: {selectedNode.type}</div>
            {Object.keys(selectedNode.properties).length > 0 && (
              <div className="mt-2 text-xs text-gray-700">
                {Object.entries(selectedNode.properties)
                  .slice(0, 3)
                  .map(([key, value]) => (
                    <div key={key}>
                      {key}: {typeof value === 'object' ? JSON.stringify(value) : value}
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* 图例 */}
        <div className="absolute top-4 right-4 bg-white bg-opacity-90 p-3 rounded-lg shadow-lg">
          <div className="text-xs font-medium text-gray-700 mb-2">图例</div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-2" />
              <span>位置</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2" />
              <span>行政区</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-red-500 mr-2" />
              <span>要素</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-purple-500 mr-2" />
              <span>数据集</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-2" />
              <span>其他</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KGVisualizationPanel;