/**
 * MultiScreenController - 多屏联动控制面板
 * 管理监控墙的多屏显示和同步控制
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Switch } from './ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Monitor,
  Layout,
  Link,
  Unlink,
  Play,
  Pause,
  RotateCcw,
  Maximize2,
  Minimize2,
  Settings,
  AlertTriangle,
  CheckCircle,
  Wifi,
  WifiOff,
  Cast,
  Eye,
  EyeOff,
  Grid3X3,
  Square
} from 'lucide-react';

interface Screen {
  id: string;
  name: string;
  url: string;
  status: 'online' | 'offline' | 'syncing' | 'error';
  lastHeartbeat: Date;
  currentLayout: string;
  supportedLayouts: string[];
  resolution: string;
  position?: { x: number; y: number };
}

interface LayoutConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  screens: number;
  arrangement: 'grid' | 'linear' | 'custom';
  config: {
    rows: number;
    cols: number;
    screenIds?: string[];
    positions?: Array<{ x: number; y: number; width: number; height: number }>;
  };
}

interface SyncMode {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const LAYOUT_CONFIGS: LayoutConfig[] = [
  {
    id: '2x2-grid',
    name: '2×2 网格',
    description: '标准四屏监控墙',
    icon: <Grid3X3 className="h-4 w-4" />,
    screens: 4,
    arrangement: 'grid',
    config: { rows: 2, cols: 2 }
  },
  {
    id: '1x3-linear',
    name: '1×3 横向',
    description: '三屏横向排列',
    icon: <Square className="h-4 w-4" />,
    screens: 3,
    arrangement: 'linear',
    config: { rows: 1, cols: 3 }
  },
  {
    id: '1x2-vertical',
    name: '1×2 纵向',
    description: '双屏纵向排列',
    icon: <Square className="h-4 w-4" />,
    screens: 2,
    arrangement: 'linear',
    config: { rows: 2, cols: 1 }
  },
  {
    id: '1+3-mixed',
    name: '1+3 混合',
    description: '主屏+三辅屏',
    icon: <Layout className="h-4 w-4" />,
    screens: 4,
    arrangement: 'custom',
    config: {
      rows: 2,
      cols: 2,
      positions: [
        { x: 0, y: 0, width: 1, height: 1 }, // 主屏
        { x: 1, y: 0, width: 1, height: 1 },
        { x: 0, y: 1, width: 1, height: 1 },
        { x: 1, y: 1, width: 1, height: 1 }
      ]
    }
  },
  {
    id: '1+5-command',
    name: '1+5 指挥模式',
    description: '指挥大厅标准布局',
    icon: <Layout className="h-4 w-4" />,
    screens: 6,
    arrangement: 'custom',
    config: {
      rows: 3,
      cols: 3,
      positions: [
        { x: 0, y: 0, width: 3, height: 2 }, // 主大屏
        { x: 0, y: 2, width: 1, height: 1 },
        { x: 1, y: 2, width: 1, height: 1 },
        { x: 2, y: 2, width: 1, height: 1 },
        { x: 0, y: 3, width: 1, height: 1 },
        { x: 1, y: 3, width: 1, height: 1 }
      ]
    }
  }
];

const SYNC_MODES: SyncMode[] = [
  {
    id: 'independent',
    name: '独立模式',
    description: '各屏幕独立操作',
    icon: <Unlink className="h-4 w-4" />
  },
  {
    id: 'master-slave',
    name: '主从模式',
    description: '主屏控制，从屏跟随',
    icon: <Link className="h-4 w-4" />
  },
  {
    id: 'synchronized',
    name: '完全同步',
    description: '所有屏幕完全同步',
    icon: <Cast className="h-4 w-4" />
  }
];

interface MultiScreenControllerProps {
  className?: string;
  onScreenChange?: (screens: Screen[]) => void;
  onLayoutChange?: (layout: LayoutConfig) => void;
  onSyncModeChange?: (mode: string) => void;
}

const MultiScreenController: React.FC<MultiScreenControllerProps> = ({
  className,
  onScreenChange,
  onLayoutChange,
  onSyncModeChange
}) => {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [selectedLayout, setSelectedLayout] = useState<LayoutConfig>(LAYOUT_CONFIGS[0]);
  const [syncMode, setSyncMode] = useState<string>('independent');
  const [masterScreen, setMasterScreen] = useState<string>('');
  const [isBroadcasting, setIsBroadcasting] = useState<boolean>(false);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');

  // 初始化WebSocket连接
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, []);

  // 模拟屏幕发现（实际应该通过WebSocket或API获取）
  useEffect(() => {
    // 模拟发现已连接的屏幕
    const mockScreens: Screen[] = [
      {
        id: 'screen-001',
        name: '主监控屏',
        url: 'http://localhost:5173?screen_id=screen-001',
        status: 'online',
        lastHeartbeat: new Date(),
        currentLayout: '2x2-grid',
        supportedLayouts: ['2x2-grid', '1x3-linear', '1+3-mixed'],
        resolution: '1920x1080'
      },
      {
        id: 'screen-002',
        name: '数据分析屏',
        url: 'http://localhost:5173?screen_id=screen-002',
        status: 'online',
        lastHeartbeat: new Date(),
        currentLayout: '2x2-grid',
        supportedLayouts: ['2x2-grid', '1x3-linear'],
        resolution: '1920x1080'
      },
      {
        id: 'screen-003',
        name: '3D可视化屏',
        url: 'http://localhost:5173?screen_id=screen-003',
        status: 'online',
        lastHeartbeat: new Date(),
        currentLayout: '2x2-grid',
        supportedLayouts: ['2x2-grid', '1x2-vertical'],
        resolution: '1920x1080'
      },
      {
        id: 'screen-004',
        name: '预警信息屏',
        url: 'http://localhost:5173?screen_id=screen-004',
        status: 'offline',
        lastHeartbeat: new Date(Date.now() - 60000),
        currentLayout: '2x2-grid',
        supportedLayouts: ['2x2-grid'],
        resolution: '1920x1080'
      }
    ];

    setScreens(mockScreens);
    onScreenChange?.(mockScreens);
  }, []);

  // WebSocket连接
  const connectWebSocket = () => {
    setConnectionStatus('connecting');

    try {
      const ws = new WebSocket('ws://localhost:8000/api/advanced-viz/multi-screen/ws');

      ws.onopen = () => {
        setConnectionStatus('connected');
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('WebSocket消息解析失败:', error);
        }
      };

      ws.onclose = () => {
        setConnectionStatus('disconnected');
        setWsConnection(null);
        // 尝试重连
        setTimeout(connectWebSocket, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        setConnectionStatus('disconnected');
      };
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      setConnectionStatus('disconnected');
    }
  };

  // 处理WebSocket消息
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'screen_status':
        updateScreenStatus(message.screenId, message.status);
        break;
      case 'heartbeat':
        updateScreenHeartbeat(message.screenId);
        break;
      case 'layout_update':
        handleLayoutUpdate(message);
        break;
      case 'sync_command':
        handleSyncCommand(message);
        break;
    }
  };

  // 更新屏幕状态
  const updateScreenStatus = (screenId: string, status: string) => {
    setScreens(prev => prev.map(screen =>
      screen.id === screenId ? { ...screen, status: status as Screen['status'] } : screen
    ));
  };

  // 更新屏幕心跳
  const updateScreenHeartbeat = (screenId: string) => {
    setScreens(prev => prev.map(screen =>
      screen.id === screenId ? { ...screen, lastHeartbeat: new Date() } : screen
    ));
  };

  // 处理布局更新
  const handleLayoutUpdate = (message: any) => {
    const layout = LAYOUT_CONFIGS.find(l => l.id === message.layoutId);
    if (layout) {
      setSelectedLayout(layout);
      onLayoutChange?.(layout);
    }
  };

  // 处理同步命令
  const handleSyncCommand = (message: any) => {
    // 处理来自其他屏幕的同步命令
    console.log('收到同步命令:', message);
  };

  // 发送广播命令
  const broadcastCommand = async (command: string, data?: any) => {
    if (!wsConnection || connectionStatus !== 'connected') {
      console.warn('WebSocket未连接，无法发送命令');
      return;
    }

    try {
      wsConnection.send(JSON.stringify({
        type: 'broadcast_command',
        command,
        data,
        timestamp: new Date().toISOString()
      }));
    } catch (error) {
      console.error('发送广播命令失败:', error);
    }
  };

  // 布局切换
  const handleLayoutChange = async (layout: LayoutConfig) => {
    setSelectedLayout(layout);

    try {
      const response = await fetch('/api/advanced-viz/multi-screen/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          layout_id: layout.id,
          screen_ids: screens.filter(s => s.status === 'online').map(s => s.id),
          config: layout.config
        })
      });

      if (response.ok) {
        onLayoutChange?.(layout);
        broadcastCommand('layout_change', { layoutId: layout.id });
      } else {
        console.error('布局切换失败');
      }
    } catch (error) {
      console.error('布局切换错误:', error);
    }
  };

  // 同步模式切换
  const handleSyncModeChange = async (mode: string) => {
    setSyncMode(mode);

    try {
      const response = await fetch('/api/advanced-viz/multi-screen/sync-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          master_screen: mode === 'master-slave' ? masterScreen : undefined
        })
      });

      if (response.ok) {
        onSyncModeChange?.(mode);
        broadcastCommand('sync_mode_change', { mode });
      }
    } catch (error) {
      console.error('同步模式切换错误:', error);
    }
  };

  // 开始广播
  const startBroadcast = () => {
    setIsBroadcasting(true);
    broadcastCommand('start_broadcast', {
      masterScreen,
      currentScene: 'emergency' // 假设当前是应急场景
    });
  };

  // 停止广播
  const stopBroadcast = () => {
    setIsBroadcasting(false);
    broadcastCommand('stop_broadcast');
  };

  // 同步所有屏幕
  const syncAllScreens = () => {
    broadcastCommand('sync_all', {
      viewport: {
        longitude: 111.0,
        latitude: 30.8,
        zoom: 10
      },
      scene: 'emergency'
    });
  };

  // 渲染屏幕列表
  const renderScreenList = () => (
    <div className="space-y-3">
      {screens.map((screen) => (
        <div key={screen.id} className="border rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded ${getStatusColor(screen.status)}`}>
                {screen.status === 'online' ? (
                  <Wifi className="h-4 w-4 text-green-600" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-600" />
                )}
              </div>
              <div>
                <div className="font-medium">{screen.name}</div>
                <div className="text-sm text-gray-500">{screen.resolution}</div>
              </div>
            </div>
            <Badge variant={screen.status === 'online' ? 'default' : 'destructive'}>
              {screen.status}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500">ID:</span> {screen.id}
            </div>
            <div>
              <span className="text-gray-500">布局:</span> {screen.currentLayout}
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">最后心跳:</span> {screen.lastHeartbeat.toLocaleTimeString()}
            </div>
          </div>

          {screen.status === 'online' && (
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => window.open(screen.url, '_blank')}
              >
                <Eye className="h-3 w-3 mr-1" />
                查看
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setMasterScreen(screen.id)}
                disabled={syncMode !== 'master-slave'}
                className={masterScreen === screen.id ? 'bg-blue-100' : ''}
              >
                {masterScreen === screen.id ? (
                  <><CheckCircle className="h-3 w-3 mr-1" />主屏</>
                ) : (
                  <>设为主屏</>
                )}
              </Button>
            </div>
          )}
        </div>
      ))}

      {screens.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Monitor className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>未发现已连接的屏幕</p>
          <p className="text-sm">请确保屏幕已启动并连接到网络</p>
        </div>
      )}
    </div>
  );

  // 渲染布局选择
  const renderLayoutSelector = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3">
        {LAYOUT_CONFIGS.map((layout) => (
          <div
            key={layout.id}
            className={`
              border rounded-lg p-4 cursor-pointer transition-all
              ${selectedLayout.id === layout.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
              }
            `}
            onClick={() => handleLayoutChange(layout)}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gray-100 rounded">{layout.icon}</div>
                <div>
                  <div className="font-medium">{layout.name}</div>
                  <div className="text-sm text-gray-500">{layout.description}</div>
                </div>
              </div>
              <Badge variant="outline">{layout.screens} 屏</Badge>
            </div>

            <div className="text-xs text-gray-600 mb-2">
              排列: {getArrangementName(layout.arrangement)}
            </div>

            {selectedLayout.id === layout.id && (
              <div className="text-xs text-blue-600 font-medium">
                ✓ 当前布局
              </div>
            )}
          </div>
        ))}
      </div>

      {selectedLayout && (
        <div className="bg-gray-50 rounded-lg p-3">
          <h4 className="font-medium mb-2">布局详情</h4>
          <div className="text-sm space-y-1">
            <div>屏幕数: {selectedLayout.screens}</div>
            <div>排列方式: {getArrangementName(selectedLayout.arrangement)}</div>
            <div>配置: {selectedLayout.config.rows}×{selectedLayout.config.cols}</div>
          </div>
        </div>
      )}
    </div>
  );

  // 渲染同步控制
  const renderSyncControl = () => (
    <div className="space-y-4">
      <div className="space-y-3">
        <Label className="font-medium">同步模式</Label>
        <div className="space-y-2">
          {SYNC_MODES.map((mode) => (
            <div
              key={mode.id}
              className={`
                border rounded-lg p-3 cursor-pointer transition-all
                ${syncMode === mode.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
                }
              `}
              onClick={() => handleSyncModeChange(mode.id)}
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gray-100 rounded">{mode.icon}</div>
                <div className="flex-1">
                  <div className="font-medium">{mode.name}</div>
                  <div className="text-sm text-gray-500">{mode.description}</div>
                </div>
                {syncMode === mode.id && (
                  <CheckCircle className="h-5 w-5 text-blue-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {syncMode === 'master-slave' && (
        <div className="space-y-3">
          <Label className="font-medium">主屏设置</Label>
          <Select value={masterScreen} onValueChange={setMasterScreen}>
            <SelectTrigger>
              <SelectValue placeholder="选择主屏" />
            </SelectTrigger>
            <SelectContent>
              {screens.filter(s => s.status === 'online').map((screen) => (
                <SelectItem key={screen.id} value={screen.id}>
                  {screen.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-sm text-gray-500">
            主屏的所有操作将自动同步到其他屏幕
          </p>
        </div>
      )}

      <div className="space-y-3">
        <Label className="font-medium">广播控制</Label>
        <div className="flex gap-2">
          <Button
            onClick={startBroadcast}
            disabled={isBroadcasting || screens.filter(s => s.status === 'online').length === 0}
            className="flex items-center gap-2"
          >
            <Cast className="h-4 w-4" />
            开始广播
          </Button>
          <Button
            onClick={stopBroadcast}
            disabled={!isBroadcasting}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Pause className="h-4 w-4" />
            停止广播
          </Button>
          <Button
            onClick={syncAllScreens}
            disabled={screens.filter(s => s.status === 'online').length === 0}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            同步所有
          </Button>
        </div>
        <div className="text-sm text-gray-500">
          {isBroadcasting ? (
            <span className="flex items-center gap-1 text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              正在广播中...
            </span>
          ) : (
            '未进行广播'
          )}
        </div>
      </div>
    </div>
  );

  // 渲染状态概览
  const renderStatusOverview = () => {
    const onlineScreens = screens.filter(s => s.status === 'online').length;
    const totalScreens = screens.length;

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div className="font-medium text-green-900">在线屏幕</div>
            </div>
            <div className="text-2xl font-bold text-green-700">{onlineScreens}</div>
            <div className="text-sm text-green-600">共 {totalScreens} 屏</div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Link className="h-5 w-5 text-blue-600" />
              <div className="font-medium text-blue-900">同步模式</div>
            </div>
            <div className="text-lg font-bold text-blue-700">{getSyncModeName(syncMode)}</div>
            <div className="text-sm text-blue-600">{getSyncModeDescription(syncMode)}</div>
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Layout className="h-5 w-5 text-purple-600" />
              <div className="font-medium text-purple-900">当前布局</div>
            </div>
            <div className="text-lg font-bold text-purple-700">{selectedLayout.name}</div>
            <div className="text-sm text-purple-600">{selectedLayout.screens} 屏布局</div>
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-gray-600" />
              <div className="font-medium">系统状态</div>
            </div>
            <Badge
              variant={connectionStatus === 'connected' ? 'default' : 'destructive'}
            >
              {connectionStatus === 'connected' ? (
                <><Wifi className="h-3 w-3 mr-1" />已连接</>
              ) : (
                <><WifiOff className="h-3 w-3 mr-1" />未连接</>
              )}
            </Badge>
          </div>
          <div className="text-sm text-gray-600 space-y-1">
            <div>广播状态: {isBroadcasting ? '进行中' : '未开始'}</div>
            <div>主屏: {masterScreen || '未设置'}</div>
            <div>最后更新: {new Date().toLocaleTimeString()}</div>
          </div>
        </div>
      </div>
    );
  };

  // 辅助函数
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-green-100';
      case 'offline': return 'bg-red-100';
      case 'syncing': return 'bg-yellow-100';
      case 'error': return 'bg-red-100';
      default: return 'bg-gray-100';
    }
  };

  const getArrangementName = (arrangement: string) => {
    switch (arrangement) {
      case 'grid': return '网格';
      case 'linear': return '线性';
      case 'custom': return '自定义';
      default: return arrangement;
    }
  };

  const getSyncModeName = (mode: string) => {
    const syncMode = SYNC_MODES.find(m => m.id === mode);
    return syncMode?.name || mode;
  };

  const getSyncModeDescription = (mode: string) => {
    const syncMode = SYNC_MODES.find(m => m.id === mode);
    return syncMode?.description || '';
  };

  return (
    <Card className={`multi-screen-controller ${className || ''}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            多屏控制中心
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={connectionStatus === 'connected' ? 'default' : 'secondary'}
              className={connectionStatus === 'connected' ? 'bg-green-500' : ''}
            >
              {connectionStatus === 'connected' ? (
                <><Wifi className="h-3 w-3 mr-1" />已连接</>
              ) : connectionStatus === 'connecting' ? (
                '连接中...'
              ) : (
                <><WifiOff className="h-3 w-3 mr-1" />未连接</>
              )}
            </Badge>
            {isBroadcasting && (
              <Badge className="bg-red-500 animate-pulse">
                <Cast className="h-3 w-3 mr-1" />广播中
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <Monitor className="h-4 w-4" />
              概览
            </TabsTrigger>
            <TabsTrigger value="screens" className="flex items-center gap-2">
              <Layout className="h-4 w-4" />
              屏幕管理
            </TabsTrigger>
            <TabsTrigger value="layout" className="flex items-center gap-2">
              <Grid3X3 className="h-4 w-4" />
              布局设置
            </TabsTrigger>
            <TabsTrigger value="sync" className="flex items-center gap-2">
              <Link className="h-4 w-4" />
              同步控制
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            {renderStatusOverview()}
          </TabsContent>

          <TabsContent value="screens" className="mt-4">
            {renderScreenList()}
          </TabsContent>

          <TabsContent value="layout" className="mt-4">
            {renderLayoutSelector()}
          </TabsContent>

          <TabsContent value="sync" className="mt-4">
            {renderSyncControl()}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default MultiScreenController;