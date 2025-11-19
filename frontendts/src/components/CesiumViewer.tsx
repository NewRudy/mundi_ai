/**
 * CesiumViewer - 3D地球可视化组件
 * 集成CesiumJS用于专业级3D地形和地球渲染
 */

import React, { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

interface CesiumViewerProps {
  // 地形数据配置
  terrainProvider?: {
    url: string;
    requestVertexNormals?: boolean;
    requestWaterMask?: boolean;
  };

  // 初始视角
  initialCamera?: {
    longitude: number;
    latitude: number;
    height: number;
    heading?: number;
    pitch?: number;
    roll?: number;
  };

  // 3D图层数据
  layers?: {
    type: 'terrain' | 'imagery' | '3dtiles' | 'vector';
    url: string;
    name: string;
    visible?: boolean;
    style?: any;
  }[];

  // 监测点数据
  monitoringPoints?: {
    id: string;
    name: string;
    longitude: number;
    latitude: number;
    height: number;
    type: 'hydrology' | 'meteorology' | 'dam' | 'reservoir';
    status: 'normal' | 'warning' | 'danger';
    value?: number;
    unit?: string;
    timestamp?: string;
  }[];

  // 洪水模拟数据
  floodData?: {
    extent: {
      west: number;
      south: number;
      east: number;
      north: number;
    };
    waterLevel: number;
    opacity?: number;
    color?: string;
  };

  // 事件回调
  onCameraChange?: (camera: any) => void;
  onPointClick?: (point: any) => void;
  onReady?: (viewer: any) => void;

  // 样式配置
  className?: string;
  style?: React.CSSProperties;
}

// 监测点图标配置
const MONITORING_POINT_ICONS = {
  hydrology: {
    normal: '🌊',
    warning: '⚠️',
    danger: '🚨'
  },
  meteorology: {
    normal: '🌤️',
    warning: '⛈️',
    danger: '🌪️'
  },
  dam: {
    normal: '🏗️',
    warning: '🏗️',
    danger: '💥'
  },
  reservoir: {
    normal: '🏞️',
    warning: '🌊',
    danger: '🌊'
  }
};

// 状态颜色配置
const STATUS_COLORS = {
  normal: Cesium.Color.GREEN,
  warning: Cesium.Color.YELLOW,
  danger: Cesium.Color.RED
};

const CesiumViewer: React.FC<CesiumViewerProps> = ({
  terrainProvider,
  initialCamera,
  layers = [],
  monitoringPoints = [],
  floodData,
  onCameraChange,
  onPointClick,
  onReady,
  className,
  style
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 初始化Cesium Viewer
  useEffect(() => {
    const initViewer = async () => {
      if (!containerRef.current) return;

      try {
        // Cesium配置
        const cesiumConfig: any = {
        terrainProvider: await Cesium.createWorldTerrainAsync({
          requestVertexNormals: true,
          requestWaterMask: true
        }),
        imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 }), // Sentinel-2
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        animation: false,
        timeline: false,
        fullscreenButton: false,
        vrButton: false,
        infoBox: true,
        selectionIndicator: true,
        shadows: true,
        terrainShadows: Cesium.ShadowMode.ENABLED
      };

      // 如果提供了自定义地形
      if (terrainProvider) {
        cesiumConfig.terrainProvider = new Cesium.CesiumTerrainProvider({
          url: terrainProvider.url,
          requestVertexNormals: terrainProvider.requestVertexNormals,
          requestWaterMask: terrainProvider.requestWaterMask
        });
      }

      // 创建Viewer
      const viewer = new Cesium.Viewer(containerRef.current, cesiumConfig);
      viewerRef.current = viewer;

      // 设置初始相机位置
      if (initialCamera) {
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(
            initialCamera.longitude,
            initialCamera.latitude,
            initialCamera.height
          ),
          orientation: {
            heading: Cesium.Math.toRadians(initialCamera.heading || 0),
            pitch: Cesium.Math.toRadians(initialCamera.pitch || -90),
            roll: Cesium.Math.toRadians(initialCamera.roll || 0)
          }
        });
      } else {
        // 默认视角：三峡大坝
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(111.006, 30.827, 10000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0
          }
        });
      }

      // 添加光照效果
      viewer.scene.light = new Cesium.DirectionalLight({
        direction: new Cesium.Cartesian3(0.354, -0.890, -0.288),
        color: new Cesium.Color(1.0, 1.0, 1.0, 1.0),
        intensity: 2.0
      });

      // 监听相机变化
      if (onCameraChange) {
        viewer.camera.changed.addEventListener(() => {
          const camera = viewer.camera;
          const cartographic = Cesium.Cartographic.fromCartesian(camera.position);
          onCameraChange({
            longitude: Cesium.Math.toDegrees(cartographic.longitude),
            latitude: Cesium.Math.toDegrees(cartographic.latitude),
            height: cartographic.height,
            heading: Cesium.Math.toDegrees(camera.heading),
            pitch: Cesium.Math.toDegrees(camera.pitch),
            roll: Cesium.Math.toDegrees(camera.roll)
          });
        });
      }

        setIsLoading(false);
        onReady?.(viewer);

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Cesium初始化失败');
        setIsLoading(false);
      }
    };

    initViewer();

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
      }
    };
  }, []);

  // 添加监测点
  useEffect(() => {
    if (!viewerRef.current || monitoringPoints.length === 0) return;

    const viewer = viewerRef.current;
    const entities = viewer.entities;

    // 清除现有监测点
    entities.removeAll();

    // 添加监测点
    monitoringPoints.forEach((point) => {
      const entity = entities.add({
        id: point.id,
        name: point.name,
        position: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, point.height),
        point: {
          pixelSize: 12,
          color: STATUS_COLORS[point.status],
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        },
        label: {
          text: `${point.name}\n${point.value || ''} ${point.unit || ''}`,
          font: '12px sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -20)
        },
        description: `
          <div style="padding: 10px;">
            <h3>${point.name}</h3>
            <p>类型: ${point.type}</p>
            <p>状态: ${point.status}</p>
            ${point.value ? `<p>数值: ${point.value} ${point.unit || ''}</p>` : ''}
            ${point.timestamp ? `<p>时间: ${new Date(point.timestamp).toLocaleString()}</p>` : ''}
          </div>
        `
      });

      // 点击事件
      if (onPointClick) {
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((movement: any) => {
          const picked = viewer.scene.pick(movement.position);
          if (Cesium.defined(picked) && picked.id === entity) {
            onPointClick(point);
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
      }
    });
  }, [monitoringPoints, onPointClick]);

  // 添加洪水淹没效果
  useEffect(() => {
    if (!viewerRef.current || !floodData) return;

    const viewer = viewerRef.current;
    const { extent, waterLevel, opacity = 0.7, color = '#0066CC' } = floodData;

    // 创建洪水实体
    const floodEntity = viewer.entities.add({
      name: '洪水淹没区域',
      polygon: {
        hierarchy: Cesium.Cartesian3.fromDegreesArray([
          extent.west, extent.south,
          extent.east, extent.south,
          extent.east, extent.north,
          extent.west, extent.north
        ]),
        material: new Cesium.ColorMaterialProperty(
          Cesium.Color.fromCssColorString(color).withAlpha(opacity)
        ),
        height: waterLevel,
        extrudedHeight: waterLevel + 1,
        outline: true,
        outlineColor: Cesium.Color.BLUE,
        outlineWidth: 2
      }
    });

    return () => {
      viewer.entities.remove(floodEntity);
    };
  }, [floodData]);

  // 添加3D图层
  useEffect(() => {
    if (!viewerRef.current || layers.length === 0) return;

    const viewer = viewerRef.current;

    layers.forEach((layer) => {
      switch (layer.type) {
        case '3dtiles':
          const tileset = new Cesium.Cesium3DTileset({
            url: layer.url,
            show: layer.visible !== false
          });
          viewer.scene.primitives.add(tileset);
          break;

        case 'imagery':
          const imageryProvider = new Cesium.UrlTemplateImageryProvider({
            url: layer.url
          });
          viewer.imageryLayers.addImageryProvider(imageryProvider);
          break;
      }
    });
  }, [layers]);

  // 获取当前屏幕截图
  const captureScreenshot = () => {
    if (!viewerRef.current) return null;

    const canvas = viewerRef.current.scene.canvas;
    return canvas.toDataURL('image/png');
  };

  // 导出供父组件使用
  React.useImperativeHandle(
    React.useRef(),
    () => ({
      captureScreenshot,
      getViewer: () => viewerRef.current
    })
  );

  if (error) {
    return (
      <div className={`cesium-viewer-error ${className || ''}`} style={style}>
        <div className="error-content">
          <h3>❌ Cesium加载失败</h3>
          <p>{error}</p>
          <p>请检查Cesium Ion token和网络连接</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`cesium-viewer-container ${className || ''}`} style={style}>
      {isLoading && (
        <div className="cesium-loading">
          <div className="loading-spinner"></div>
          <p>正在加载3D地球...</p>
        </div>
      )}
      <div
        ref={containerRef}
        className="cesium-viewer"
        style={{ width: '100%', height: '100%' }}
      />

      {/* 控制面板 */}
      <div className="cesium-controls">
        <div className="control-panel">
          <h4>🌍 3D地球控制</h4>
          <div className="control-buttons">
            <button
              onClick={() => {
                if (viewerRef.current) {
                  viewerRef.current.camera.flyHome(2);
                }
              }}
              className="cesium-button"
            >
              🏠 重置视角
            </button>
            <button
              onClick={() => {
                if (viewerRef.current) {
                  viewerRef.current.scene.globe.show = !viewerRef.current.scene.globe.show;
                }
              }}
              className="cesium-button"
            >
              🌐 切换地形
            </button>
            <button
              onClick={captureScreenshot}
              className="cesium-button"
            >
              📸 截图
            </button>
          </div>

          {/* 监测点统计 */}
          {monitoringPoints.length > 0 && (
            <div className="monitoring-stats">
              <h5>监测点统计</h5>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">正常</span>
                  <span className="stat-value normal">
                    {monitoringPoints.filter(p => p.status === 'normal').length}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">警告</span>
                  <span className="stat-value warning">
                    {monitoringPoints.filter(p => p.status === 'warning').length}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">危险</span>
                  <span className="stat-value danger">
                    {monitoringPoints.filter(p => p.status === 'danger').length}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CesiumViewer;