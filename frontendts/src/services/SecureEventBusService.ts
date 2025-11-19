/**
 * SecureEventBusService - 安全的事件总线服务
 * 提供带有认证、验证和速率限制的WebSocket事件通信
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
  maxAuthRetries: number;
}

const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
  heartbeatInterval: 30000,
  requestTimeout: 30000,
  maxEventBufferSize: 100,
  rateLimitWindow: 60000, // 1 minute
  maxEventsPerWindow: 100,
  maxAuthRetries: 3
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
  AUTHENTICATING = 'authenticating',
  AUTHENTICATED = 'authenticated',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  RECONNECTING = 'reconnecting'
}

// 认证接口
export interface AuthCredentials {
  token: string;
  clientId: string;
  userId?: string;
  permissions?: string[];
}

// 安全事件接口
export interface SecureEvent extends Event {
  signature?: string;
  nonce?: string;
  userId?: string;
}

// 速率限制器
class RateLimiter {
  private events: Map<string, number[]> = new Map();

  constructor(
    private maxEvents: number,
    private windowMs: number
  ) {}

  isAllowed(identifier: string): boolean {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    if (!this.events.has(identifier)) {
      this.events.set(identifier, []);
    }

    const eventTimes = this.events.get(identifier)!;

    // 移除窗口外的事件
    const validEvents = eventTimes.filter(time => time > windowStart);

    if (validEvents.length >= this.maxEvents) {
      return false;
    }

    validEvents.push(now);
    this.events.set(identifier, validEvents);
    return true;
  }

  reset(identifier: string): void {
    this.events.delete(identifier);
  }
}

// 事件验证器
class EventValidator {
  private static readonly MAX_PAYLOAD_SIZE = 1024 * 1024; // 1MB
  private static readonly MAX_STRING_LENGTH = 1000;
  private static readonly ALLOWED_EVENT_TYPES = Object.values(EventType);

  static validateEvent(event: Partial<SecureEvent>): { valid: boolean; error?: string } {
    // 验证事件类型
    if (!event.type || !this.ALLOWED_EVENT_TYPES.includes(event.type)) {
      return { valid: false, error: 'Invalid event type' };
    }

    // 验证源
    if (!event.source || typeof event.source !== 'string') {
      return { valid: false, error: 'Invalid event source' };
    }

    if (!this.isValidSource(event.source)) {
      return { valid: false, error: 'Source contains invalid characters' };
    }

    // 验证载荷大小
    const payloadSize = JSON.stringify(event.payload || {}).length;
    if (payloadSize > this.MAX_PAYLOAD_SIZE) {
      return { valid: false, error: 'Payload too large' };
    }

    // 验证载荷内容
    if (event.payload && !this.isValidPayload(event.payload)) {
      return { valid: false, error: 'Invalid payload format' };
    }

    return { valid: true };
  }

  static sanitizePayload(payload: any): any {
    if (payload === null || payload === undefined) {
      return payload;
    }

    if (typeof payload === 'string') {
      return this.sanitizeString(payload);
    }

    if (typeof payload === 'object') {
      if (Array.isArray(payload)) {
        return payload.map(item => this.sanitizePayload(item));
      }

      const sanitized: any = {};
      for (const [key, value] of Object.entries(payload)) {
        const sanitizedKey = this.sanitizeString(key);
        sanitized[sanitizedKey] = this.sanitizePayload(value);
      }
      return sanitized;
    }

    return payload;
  }

  private static sanitizeString(str: string): string {
    if (!str || typeof str !== 'string') {
      return str;
    }

    // 限制长度
    if (str.length > this.MAX_STRING_LENGTH) {
      str = str.substring(0, this.MAX_STRING_LENGTH);
    }

    // 移除潜在危险字符
    return str.replace(/[<>'"&]/g, '');
  }

  private static isValidSource(source: string): boolean {
    return /^[a-zA-Z0-9_-]{3,32}$/.test(source);
  }

  private static isValidPayload(payload: any): boolean {
    try {
      JSON.stringify(payload);
      return true;
    } catch {
      return false;
    }
  }
}

// 事件总线服务类
export class SecureEventBusService extends EventEmitter {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private authToken: string | null = null;
  private clientId: string;
  private userId: string | null = null;
  private permissions: string[] = [];
  private connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  private eventBuffer: SecureEvent[] = [];
  private isBuffering = true;
  private reconnectAttempts = 0;
  private authRetries = 0;
  private securityConfig: SecurityConfig;

  // 安全组件
  private rateLimiter: RateLimiter;
  private pendingReplies: Map<string, { resolve: (value: any) => void; reject: (error: any) => void }> = new Map();
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionTimer: NodeJS.Timeout | null = null;

  constructor(
    wsUrl: string = 'ws://localhost:8002/api/events/ws',
    clientId: string = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    authToken: string | null = null,
    securityConfig: Partial<SecurityConfig> = {}
  ) {
    super();
    this.wsUrl = wsUrl;
    this.clientId = clientId;
    this.authToken = authToken;
    this.securityConfig = { ...DEFAULT_SECURITY_CONFIG, ...securityConfig };

    // 初始化安全组件
    this.rateLimiter = new RateLimiter(
      this.securityConfig.maxEventsPerWindow,
      this.securityConfig.rateLimitWindow
    );

    this.setupEventHandlers();
  }

  /**
   * 设置认证令牌
   */
  public setAuthToken(token: string | null): void {
    this.authToken = token;
    if (this.connectionStatus === ConnectionStatus.AUTHENTICATED && !token) {
      this.connectionStatus = ConnectionStatus.CONNECTED;
      this.emit('status_changed', this.connectionStatus);
    }
  }

  /**
   * 连接WebSocket并进行认证
   */
  public async connect(): Promise<void> {
    if (this.connectionStatus === ConnectionStatus.CONNECTING ||
        this.connectionStatus === ConnectionStatus.AUTHENTICATING) {
      return;
    }

    this.connectionStatus = ConnectionStatus.CONNECTING;
    this.emit('status_changed', this.connectionStatus);

    try {
      // 添加查询参数用于认证
      const wsUrl = new URL(this.wsUrl);
      wsUrl.searchParams.set('client_id', this.clientId);
      if (this.authToken) {
        wsUrl.searchParams.set('token', this.authToken);
      }

      this.ws = new WebSocket(wsUrl.toString());

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
    this.cleanup();
    this.connectionStatus = ConnectionStatus.DISCONNECTED;
    this.emit('status_changed', this.connectionStatus);
  }

  /**
   * 安全地发布事件
   */
  public async publishEvent(
    eventType: EventType,
    payload: any,
    source: string = 'frontend',
    correlationId?: string,
    replyTo?: string
  ): Promise<string> {
    // 速率限制检查
    if (!this.rateLimiter.isAllowed(this.clientId)) {
      throw new Error('Rate limit exceeded');
    }

    // 验证和清理事件数据
    const sanitizedPayload = EventValidator.sanitizePayload(payload);

    const event: SecureEvent = {
      id: this.generateEventId(),
      type: eventType,
      source: source,
      timestamp: new Date().toISOString(),
      payload: sanitizedPayload,
      correlation_id: correlationId,
      reply_to: replyTo,
      userId: this.userId
    };

    // 验证事件
    const validation = EventValidator.validateEvent(event);
    if (!validation.valid) {
      throw new Error(`Invalid event: ${validation.error}`);
    }

    if (this.connectionStatus !== ConnectionStatus.AUTHENTICATED) {
      // 缓冲事件
      this.eventBuffer.push(event);
      if (this.eventBuffer.length > this.securityConfig.maxEventBufferSize) {
        this.eventBuffer.shift();
      }
      return event.id;
    }

    try {
      this.ws!.send(JSON.stringify({
        type: 'publish_event',
        event_type: eventType,
        payload: sanitizedPayload,
        source: event.source,
        correlation_id: event.correlation_id,
        reply_to: event.reply_to,
        user_id: event.userId
      }));

      console.log(`📤 发布事件: ${eventType} (ID: ${event.id})`);
      return event.id;

    } catch (error) {
      console.error('❌ 发布事件失败:', error);
      throw error;
    }
  }

  /**
   * 安全地订阅事件
   */
  public subscribe(eventType: EventType, handler: (event: SecureEvent) => void): () => void {
    // 检查权限
    if (!this.hasPermission(`events.${eventType}.subscribe`)) {
      console.warn(`没有权限订阅事件: ${eventType}`);
      return () => {};
    }

    this.on(eventType, handler);

    // 如果已认证，发送订阅消息
    if (this.connectionStatus === ConnectionStatus.AUTHENTICATED && this.ws) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        event_types: [eventType]
      }));
    }

    return () => {
      this.off(eventType, handler);

      if (this.connectionStatus === ConnectionStatus.AUTHENTICATED && this.ws) {
        this.ws.send(JSON.stringify({
          type: 'unsubscribe',
          event_types: [eventType]
        }));
      }
    };
  }

  /**
   * 安全的请求-回复模式
   */
  public async requestReply(
    requestType: EventType,
    requestPayload: any,
    replyType: EventType,
    timeout: number = this.securityConfig.requestTimeout
  ): Promise<SecureEvent | null> {
    return new Promise((resolve) => {
      const correlationId = this.generateEventId();
      let resolved = false;

      // 检查权限
      if (!this.hasPermission(`events.${requestType}.publish`)) {
        console.warn(`没有权限发布事件: ${requestType}`);
        resolve(null);
        return;
      }

      // 设置回复监听器
      const replyHandler = (event: SecureEvent) => {
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
   * 是否为已认证连接
   */
  public isAuthenticated(): boolean {
    return this.connectionStatus === ConnectionStatus.AUTHENTICATED;
  }

  /**
   * 检查权限
   */
  private hasPermission(permission: string): boolean {
    return this.permissions.includes(permission) || this.permissions.includes('*');
  }

  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // 清理待处理的回复
    this.pendingReplies.forEach(({ reject }) => {
      reject(new Error('Connection closed'));
    });
    this.pendingReplies.clear();

    this.rateLimiter.reset(this.clientId);
  }

  /**
   * 刷新事件缓冲区
   */
  private flushEventBuffer(): void {
    if (this.eventBuffer.length === 0) return;

    console.log(`🔄 刷新事件缓冲区: ${this.eventBuffer.length} 个事件`);

    this.eventBuffer.forEach(event => {
      if (this.ws) {
        this.ws.send(JSON.stringify({
          type: 'publish_event',
          event_type: event.type,
          payload: event.payload,
          source: event.source,
          correlation_id: event.correlation_id,
          reply_to: event.reply_to,
          user_id: event.userId
        }));
      }
    });

    this.eventBuffer = [];
  }

  /**
   * 创建安全事件
   */
  private createEvent(
    eventType: EventType,
    payload: any,
    source: string,
    correlationId?: string,
    replyTo?: string
  ): SecureEvent {
    return {
      id: this.generateEventId(),
      type: eventType,
      source,
      timestamp: new Date().toISOString(),
      payload,
      correlation_id: correlationId,
      reply_to: replyTo,
      userId: this.userId
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

    // 认证成功
    this.on('authenticated', (tokenData: any) => {
      console.log('✅ 认证成功');
      this.userId = tokenData.userId;
      this.permissions = tokenData.permissions || [];
      this.flushEventBuffer();
    });

    // 认证失败
    this.on('auth_failed', (reason: string) => {
      console.error('❌ 认证失败:', reason);
      this.authRetries++;

      if (this.authRetries < this.securityConfig.maxAuthRetries) {
        // 尝试重新认证
        setTimeout(() => this.authenticate(), 1000);
      } else {
        this.disconnect();
      }
    });

    // 连接成功
    this.on('connected', () => {
      console.log('✅ 事件总线已连接');
      this.reconnectAttempts = 0;
      this.authRetries = 0;

      // 尝试认证
      this.authenticate();
    });

    // 连接断开
    this.on('disconnected', () => {
      console.log('🔌 事件总线已断开');
      this.cleanup();
      this.scheduleReconnect();
    });

    // 连接错误
    this.on('error', (error: Error) => {
      console.error('❌ 事件总线错误:', error);
    });
  }

  /**
   * 认证连接
   */
  private authenticate(): void {
    if (!this.authToken) {
      this.connectionStatus = ConnectionStatus.AUTHENTICATED;
      this.emit('authenticated', { userId: null, permissions: [] });
      return;
    }

    this.connectionStatus = ConnectionStatus.AUTHENTICATING;
    this.emit('status_changed', this.connectionStatus);

    // 发送认证请求
    this.ws?.send(JSON.stringify({
      type: 'auth_request',
      token: this.authToken,
      client_id: this.clientId
    }));
  }

  /**
   * 处理WebSocket连接打开
   */
  private handleOpen(): void {
    this.connectionStatus = ConnectionStatus.CONNECTED;
    this.emit('connected');
    this.emit('status_changed', this.connectionStatus);
  }

  /**
   * 处理WebSocket消息
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'event') {
        // 事件消息
        const eventData: SecureEvent = data.event;
        console.log(`📨 收到事件: ${eventData.type} (ID: ${eventData.id})`);

        // 验证事件
        const validation = EventValidator.validateEvent(eventData);
        if (validation.valid) {
          this.emit(eventData.type, eventData);
        } else {
          console.warn(`收到无效事件: ${validation.error}`);
        }
      } else if (data.type === 'pong') {
        // 心跳响应
        console.log('💓 心跳响应');
      } else if (data.type === 'auth_success') {
        // 认证成功
        this.connectionStatus = ConnectionStatus.AUTHENTICATED;
        this.emit('status_changed', this.connectionStatus);
        this.emit('authenticated', data.token_data);
      } else if (data.type === 'auth_failed') {
        // 认证失败
        this.emit('auth_failed', data.reason);
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
    this.cleanup();
    this.scheduleReconnect();
  }

  /**
   * 处理WebSocket错误
   */
  private handleError(event: Event): void {
    console.error('❌ WebSocket错误:', event);
    this.emit('error', event);
  }

  /**
   * 处理连接错误
   */
  private handleConnectionError(error: any): void {
    console.error('❌ 连接错误:', error);
    this.connectionStatus = ConnectionStatus.ERROR;
    this.emit('error', error);
    this.emit('status_changed', this.connectionStatus);
    this.scheduleReconnect();
  }

  /**
   * 计划重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.securityConfig.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.securityConfig.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`🔄 计划重连: 第${this.reconnectAttempts}次，延迟${delay}ms`);

    this.connectionTimer = setTimeout(() => {
      this.connectionStatus = ConnectionStatus.RECONNECTING;
      this.emit('status_changed', this.connectionStatus);
      this.connect();
    }, delay);
  }

  /**
   * 发送心跳
   */
  private sendHeartbeat(): void {
    if (this.ws && this.connectionStatus === ConnectionStatus.AUTHENTICATED) {
      this.ws.send(JSON.stringify({ type: 'ping' }));

      // 计划下一次心跳
      this.heartbeatTimer = setTimeout(() => {
        this.sendHeartbeat();
      }, this.securityConfig.heartbeatInterval);
    }
  }
}

// 全局安全事件总线实例
export const secureEventBus = new SecureEventBusService();

// 便捷函数
export const publishEvent = secureEventBus.publishEvent.bind(secureEventBus);
export const subscribeToEvent = secureEventBus.subscribe.bind(secureEventBus);
export const requestReply = secureEventBus.requestReply.bind(secureEventBus);

export default secureEventBus;