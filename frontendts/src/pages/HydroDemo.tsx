/**
 * HydroDemo - 水电专业场景演示页面
 * 展示所有新组件的集成功能
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import HydroSceneView from '../components/HydroSceneView';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Play,
  Settings,
  Monitor,
  Globe,
  BarChart3,
  Map,
  Eye,
  EyeOff,
  Download,
  Share2,
  RotateCcw,
  Zap,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

const HydroDemo: React.FC = () => {
  const navigate = useNavigate();
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentProject] = useState('demo-hydro-001');

  const handleBackToMaps = () => {
    navigate('/');
  };

  const handleSceneChange = (scene: string) => {
    console.log('场景切换到:', scene);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* 头部导航 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                onClick={handleBackToMaps}
                className="flex items-center gap-2"
              >
                <Map className="h-4 w-4" />
                返回地图
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">水电专业场景演示</h1>
                <p className="text-sm text-gray-600">展示多场景、3D可视化、多屏联动功能</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-blue-100 text-blue-800">
                <Zap className="h-3 w-3 mr-1" />
                专业版
              </Badge>
              <Badge variant="outline" className="bg-green-100 text-green-800">
                <CheckCircle className="h-3 w-3 mr-1" />
                已集成
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* 功能说明 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-blue-600 mt-1 flex-shrink-0" />
            <h3 className="text-blue-900 font-semibold">演示说明</h3>
          </div>
          <div className="text-blue-800 ml-6">
            本页面演示了水电专业场景的全部功能，包括：
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>🔍 智能巡检模式 - 自动检测异常，生成巡检报告</li>
              <li>🚨 应急响应模式 - 洪水模拟，疏散路线，多屏联动</li>
              <li>⚙️ 调度决策模式 - 方案对比，参数优化，效益分析</li>
              <li>📊 数据分析模式 - 深度挖掘，模式识别，预测建模</li>
              <li>🌍 Cesium 3D地球 - 高精度地形，专业3D模型</li>
              <li>🎮 Deck.gl 3D场景 - 洪水演进，调度可视化</li>
              <li>📺 多屏联动控制 - 监控墙管理，同步广播</li>
            </ul>
          </div>
        </div>

        {/* 核心功能演示 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-blue-600" />
                3D地球可视化
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-1">
                <li>✅ CesiumJS 3D地球引擎</li>
                <li>✅ 高精度地形渲染</li>
                <li>✅ 监测点3D标注</li>
                <li>✅ 洪水淹没效果</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-green-600" />
                智能场景切换
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-1">
                <li>✅ 阈值自动触发</li>
                <li>✅ AI智能建议</li>
                <li>✅ 手动切换控制</li>
                <li>✅ 多模式协同</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5 text-purple-600" />
                多屏联动
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-1">
                <li>✅ 监控墙布局管理</li>
                <li>✅ 同步广播控制</li>
                <li>✅ 主从模式切换</li>
                <li>✅ 实时状态监控</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* 主要演示区域 */}
        <div className="bg-white rounded-xl shadow-lg border overflow-hidden">
          {/* 控制栏 */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-2xl">🌊</div>
                <div>
                  <h2 className="text-xl font-bold">三峡水电站智能监控系统</h2>
                  <p className="text-blue-100 text-sm">实时监控 · 智能分析 · 专业决策</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowControls(!showControls)}
                  className="text-white border-white/30 hover:bg-white/10"
                >
                  {showControls ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  控制面板
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="text-white border-white/30 hover:bg-white/10"
                >
                  <Download className="h-4 w-4" />
                  导出
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="text-white border-white/30 hover:bg-white/10"
                >
                  <Share2 className="h-4 w-4" />
                  分享
                </Button>
              </div>
            </div>
          </div>

          {/* 主要演示区域 */}
          <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'h-[70vh]'} relative`}>
            <HydroSceneView
              projectId={currentProject}
              onSceneChange={handleSceneChange}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* 技术栈展示 */}
        <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg p-4 border">
            <h3 className="font-medium mb-2 text-gray-900">3D可视化</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>• CesiumJS 1.122.0</div>
              <div>• Deck.gl 9.1.13</div>
              <div>• Three.js集成</div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 border">
            <h3 className="font-medium mb-2 text-gray-900">状态管理</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>• Zustand 4.5.2</div>
              <div>• React Context</div>
              <div>• TanStack Query</div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 border">
            <h3 className="font-medium mb-2 text-gray-900">UI组件</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>• Radix UI</div>
              <div>• Tremor React</div>
              <div>• Tailwind CSS</div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 border">
            <h3 className="font-medium mb-2 text-gray-900">后端集成</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>• FastAPI路由</div>
              <div>• WebSocket实时通信</div>
              <div>• Docker容器化</div>
            </div>
          </div>
        </div>

        {/* 快速操作 */}
        <div className="mt-6 bg-white rounded-lg p-6 border">
          <h3 className="text-lg font-semibold mb-4">快速操作</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Button variant="outline" className="flex items-center gap-2">
              <Play className="h-4 w-4" />
              开始演示
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <RotateCcw className="h-4 w-4" />
              重置场景
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              高级设置
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              导出报告
            </Button>
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <div className="max-w-7xl mx-auto px-4 py-8 text-center text-gray-500">
        <p>© 2024 Mundi.ai - 智能水电监控系统</p>
        <p className="text-sm mt-1">基于AI的空间数据分析和可视化平台</p>
      </div>
    </div>
  );
};

export default HydroDemo;