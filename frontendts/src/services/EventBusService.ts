/**
 * EventBusService - 事件总线服务
 * 提供松耦合的事件发布和订阅功能，包含安全认证
 */

import { EventEmitter } from 'events';

// 安全配置
interface SecurityConfig {
  maxReconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval: number;
  requestTimeout: number;
  maxEventBufferSize: number;
  rateLimitWindow: number;
  maxEventsPerWindow: number;
}

const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
  heartbeatInterval: 30000,
  requestTimeout: 30000,
  maxEventBufferSize: 100,
  rateLimitWindow: 60000, // 1 minute
  maxEventsPerWindow: 100
};

// 事件类型定义
export enum EventType {
  // Hydro场景事件
  HYDRO_SCENE_CHANGED = 'hydro:scene_changed',
  HYDRO_DATA_UPDATED = 'hydro:data_updated',
  HYDRO_ALERT_TRIGGERED = 'hydro:alert_triggered',
  HYDRO_VIEWPORT_CHANGED = 'hydro:viewport_changed',

  // KG查询事件
  KG_SEARCH_REQUEST = 'kg:search_request',
  KG_SEARCH_COMPLETED = 'kg:search_completed',
  KG_ANALYSIS_REQUEST = 'kg:analysis_request',
  KG_ANALYSIS_COMPLETED = 'kg:analysis_completed',

  // 空间分析事件
  SPATIAL_ANALYSIS_REQUEST = 'spatial:analysis_request',
  SPATIAL_ANALYSIS_COMPLETED = 'spatial:analysis_completed',

  // 系统事件
  SERVICE_CONNECTED = 'system:connected',
  SERVICE_DISCONNECTED = 'system:disconnected',
  SERVICE_ERROR = 'system:error',

  // 认证事件
  AUTH_REQUEST = 'auth:request',
  AUTH_SUCCESS = 'auth:success',
  AUTH_FAILED = 'auth:failed',
  AUTH_REQUIRED = 'auth:required'
}

// 事件数据结构
export interface Event {
  id: string;
  type: EventType;
  source: string;
  timestamp: string;
  payload: any;
  correlation_id?: string;
  reply_to?: string;
}

// WebSocket连接状态
export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}

// 事件总线服务类
class EventBusService extends EventEmitter {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  private eventBuffer: Event[] = [];
  private isBuffering = true;

  constructor(wsUrl: string = 'ws://localhost:8002/api/events/ws') {
    super();
    this.wsUrl = wsUrl;
    this.setupEventHandlers();
  }

  /**
   * 连接WebSocket
   */
  public async connect(): Promise<void> {
    if (this.connectionStatus === ConnectionStatus.CONNECTING ||
        this.connectionStatus === ConnectionStatus.CONNECTED) {
      return;
    }

    this.connectionStatus = ConnectionStatus.CONNECTING;
    this.emit('status_changed', this.connectionStatus);

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);

    } catch (error) {
      this.handleConnectionError(error);
    }
  }

  /**
   * 断开连接
   */
  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connectionStatus = ConnectionStatus.DISCONNECTED;
    this.emit('status_changed', this.connectionStatus);
  }

  /**
   * 发布事件
   */
  public async publishEvent(
    eventType: EventType,
    payload: any,
    source: string = 'frontend',
    correlationId?: string,
    replyTo?: string
  ): Promise<string> {
    if (this.connectionStatus !== ConnectionStatus.CONNECTED) {
      // 如果未连接，先缓冲事件
      const event = this.createEvent(eventType, payload, source, correlationId, replyTo);
      this.eventBuffer.push(event);

      if (this.eventBuffer.length > 100) {
        this.eventBuffer.shift(); // 防止缓冲区过大
      }

      return event.id;
    }

    const event = this.createEvent(eventType, payload, source, correlationId, replyTo);

    try {
      this.ws!.send(JSON.stringify({
        type: 'publish_event',
        event_type: eventType,
        payload: event.payload,
        source: event.source,
        correlation_id: event.correlation_id,
        reply_to: event.reply_to
      }));

      console.log(`📤 发布事件: ${eventType} (ID: ${event.id})`);
      return event.id;

    } catch (error) {
      console.error('❌ 发布事件失败:', error);
      throw error;
    }
  }

  /**
   * 订阅事件
   */
  public subscribe(eventType: EventType, handler: (event: Event) => void): () => void {
    this.on(eventType, handler);

    // 如果已连接，发送订阅消息
    if (this.connectionStatus === ConnectionStatus.CONNECTED && this.ws) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        event_types: [eventType]
      }));
    }

    // 返回取消订阅函数
    return () => {
      this.off(eventType, handler);

      // 发送取消订阅消息
      if (this.connectionStatus === ConnectionStatus.CONNECTED && this.ws) {
        this.ws.send(JSON.stringify({
          type: 'unsubscribe',
          event_types: [eventType]
        }));
      }
    };
  }

  /**
   * 请求-回复模式
   */
  public async requestReply(
    requestType: EventType,
    requestPayload: any,
    replyType: EventType,
    timeout: number = 30000
  ): Promise<Event | null> {
    return new Promise((resolve) => {
      const correlationId = this.generateEventId();
      let resolved = false;

      // 设置回复监听器
      const replyHandler = (event: Event) => {
        if (event.correlation_id === correlationId && !resolved) {
          resolved = true;
          this.off(replyType, replyHandler);
          clearTimeout(timeoutId);
          resolve(event);
        }
      };

      this.subscribe(replyType, replyHandler);

      // 设置超时
      const timeoutId = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          this.off(replyType, replyHandler);
          console.warn(`⏰ 请求超时: ${requestType}`);
          resolve(null);
        }
      }, timeout);

      // 发送请求
      this.publishEvent(requestType, requestPayload, 'frontend', correlationId)
        .catch(error => {
          console.error('请求发送失败:', error);
          if (!resolved) {
            resolved = true;
            this.off(replyType, replyHandler);
            clearTimeout(timeoutId);
            resolve(null);
          }
        });
    });
  }

  /**
   * 获取连接状态
   */
  public getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * 是否为连接状态
   */
  public isConnected(): boolean {
    return this.connectionStatus === ConnectionStatus.CONNECTED;
  }

  /**
   * 刷新缓冲区（连接成功后调用）
   */
  private flushEventBuffer(): void {
    if (this.eventBuffer.length === 0) return;

    console.log(`🔄 刷新事件缓冲区: ${this.eventBuffer.length} 个事件`);

    // 发送缓冲区中的所有事件
    this.eventBuffer.forEach(event => {
      if (this.ws) {
        this.ws.send(JSON.stringify({
          type: 'publish_event',
          event_type: event.type,
          payload: event.payload,
          source: event.source,
          correlation_id: event.correlation_id,
          reply_to: event.reply_to
        }));
      }
    });

    this.eventBuffer = [];
  }

  /**
   * 创建事件
   */
  private createEvent(
    eventType: EventType,
    payload: any,
    source: string,
    correlationId?: string,
    replyTo?: string
  ): Event {
    return {
      id: this.generateEventId(),
      type: eventType,
      source,
      timestamp: new Date().toISOString(),
      payload,
      correlation_id: correlationId,
      reply_to: replyTo
    };
  }

  /**
   * 生成事件ID
   */
  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    // 连接状态变化
    this.on('status_changed', (status: ConnectionStatus) => {
      console.log(`🔗 连接状态变化: ${status}`);
    });

    // 连接成功
    this.on('connected', () => {
      console.log('✅ 事件总线已连接');
      this.flushEventBuffer();
    });

    // 连接断开
    this.on('disconnected', () => {
      console.log('🔌 事件总线已断开');
      // 可以在这里实现重连逻辑
      this.scheduleReconnect();
    });

    // 连接错误
    this.on('error', (error: Error) => {
      console.error('❌ 事件总线错误:', error);
    });
  }

  /**
   * 处理WebSocket连接打开
   */
  private handleOpen(): void {
    this.connectionStatus = ConnectionStatus.CONNECTED;
    this.reconnectAttempts = 0;
    this.emit('connected');
    this.emit('status_changed', this.connectionStatus);

    // 发送心跳
    this.sendHeartbeat();
  }

  /**
   * 处理WebSocket消息
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'event') {
        // 事件消息
        const eventData: Event = data.event;
        console.log(`📨 收到事件: ${eventData.type} (ID: ${eventData.id})`);
        this.emit(eventData.type, eventData);
      } else if (data.type === 'pong') {
        // 心跳响应
        console.log('💓 心跳响应');
      } else if (data.type === 'error') {
        // 错误消息
        console.error('❌ 服务器错误:', data.message);
      }

    } catch (error) {
      console.error('❌ 消息解析失败:', error);
    }
  }

  /**
   * 处理WebSocket连接关闭
   */
  private handleClose(): void {
    this.connectionStatus = ConnectionStatus.DISCONNECTED;
    this.emit('disconnected');
    this.emit('status_changed', this.connectionStatus);

    // 清除WebSocket引用
    this.ws = null;

    // 计划重连
    this.scheduleReconnect();
  }

  /**
   * 处理WebSocket错误
   */
  private handleError(error: Event): void {
    console.error('❌ WebSocket错误:', error);
    this.emit('error', error);
  }

  /**
   * 处理连接错误
   */
  private handleConnectionError(error: any): void {
    console.error('❌ 连接错误:', error);
    this.connectionStatus = ConnectionStatus.ERROR;
    this.emit('error', error);
    this.emit('status_changed', this.connectionStatus);

    // 计划重连
    this.scheduleReconnect();
  }

  /**
   * 计划重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // 指数退避

    console.log(`🔄 计划重连: 第${this.reconnectAttempts}次，延迟${delay}ms`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * 发送心跳
   */
  private sendHeartbeat(): void {
    if (this.ws && this.connectionStatus === ConnectionStatus.CONNECTED) {
      this.ws.send(JSON.stringify({ type: 'ping' }));

      // 定期发送心跳
      setTimeout(() => {
        this.sendHeartbeat();
      }, 30000); // 30秒心跳
    }
  }
}

// 全局事件总线实例
export const eventBus = new EventBusService();

// 便捷函数
export const publishEvent = eventBus.publishEvent.bind(eventBus);
export const subscribeToEvent = eventBus.subscribe.bind(eventBus);
export const requestReply = eventBus.requestReply.bind(eventBus);

export default eventBus;