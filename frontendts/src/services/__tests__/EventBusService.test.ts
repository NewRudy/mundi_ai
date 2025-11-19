/**
 * EventBusService 测试
 * 验证事件总线的核心功能
 */

import { EventBusService, EventType, Event } from '../EventBusService';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    MockWebSocket.instances.push(this);

    // 模拟连接成功
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 100);
  }

  send(data: string) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }

    // 模拟服务器响应
    const message = JSON.parse(data);

    if (message.type === 'ping') {
      setTimeout(() => {
        this.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({ type: 'pong' })
        }));
      }, 50);
    } else if (message.type === 'publish_event') {
      // 模拟事件广播
      setTimeout(() => {
        this.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'event',
            event: {
              id: 'test_event_id',
              type: message.event_type,
              source: 'test_server',
              timestamp: new Date().toISOString(),
              payload: message.payload
            }
          })
        }));
      }, 100);
    }
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }
}

// 替换全局WebSocket
global.WebSocket = MockWebSocket as any;

describe('EventBusService', () => {
  let eventBus: EventBusService;

  beforeEach(() => {
    MockWebSocket.instances = [];
    eventBus = new EventBusService('ws://localhost:8002/api/events/ws');
  });

  afterEach(() => {
    eventBus.disconnect();
    jest.clearAllTimers();
  });

  describe('连接管理', () => {
    test('应该成功连接WebSocket', async () => {
      await eventBus.connect();

      expect(eventBus.getConnectionStatus()).toBe('connected');
      expect(eventBus.isConnected()).toBe(true);
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    test('应该处理连接失败', async () => {
      // 模拟连接失败
      const originalWebSocket = global.WebSocket;
      global.WebSocket = class {
        constructor() {
          throw new Error('Connection failed');
        }
      } as any;

      await expect(eventBus.connect()).rejects.toThrow('Connection failed');
      expect(eventBus.getConnectionStatus()).toBe('error');

      global.WebSocket = originalWebSocket;
    });

    test('应该处理断开连接', async () => {
      await eventBus.connect();

      eventBus.disconnect();

      expect(eventBus.getConnectionStatus()).toBe('disconnected');
      expect(eventBus.isConnected()).toBe(false);
    });
  });

  describe('事件发布', () => {
    test('应该发布事件到服务器', async () => {
      await eventBus.connect();

      const eventId = await eventBus.publishEvent(
        EventType.KG_SEARCH_REQUEST,
        { query: 'test query' }
      );

      expect(eventId).toMatch(/^evt_\d+_[a-z0-9]+$/);
    });

    test('应该缓冲离线时的事件', async () => {
      // 离线状态下发布事件
      const eventId = await eventBus.publishEvent(
        EventType.KG_SEARCH_REQUEST,
        { query: 'offline query' }
      );

      expect(eventId).toMatch(/^evt_\d+_[a-z0-9]+$/);

      // 连接后应该发送缓冲的事件
      await eventBus.connect();

      // 验证事件被发送（通过检查WebSocket调用）
      const ws = MockWebSocket.instances[0];
      expect(ws.readyState).toBe(WebSocket.OPEN);
    });

    test('应该限制事件缓冲区大小', async () => {
      // 发布大量事件
      const promises = [];
      for (let i = 0; i < 150; i++) {
        promises.push(
          eventBus.publishEvent(EventType.KG_SEARCH_REQUEST, { query: `query ${i}` })
        );
      }

      await Promise.all(promises);

      // 连接并验证缓冲区限制
      await eventBus.connect();

      // 缓冲区应该限制在100个事件
      expect(eventBus.eventBuffer.length).toBeLessThanOrEqual(100);
    });
  });

  describe('事件订阅', () => {
    test('应该订阅事件并接收通知', async () => {
      await eventBus.connect();

      const mockHandler = jest.fn();
      const unsubscribe = eventBus.subscribe(EventType.KG_SEARCH_COMPLETED, mockHandler);

      // 发布事件
      await eventBus.publishEvent(EventType.KG_SEARCH_REQUEST, { query: 'test' });

      // 等待事件处理
      await new Promise(resolve => setTimeout(resolve, 200));

      expect(mockHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: EventType.KG_SEARCH_COMPLETED,
          source: 'test_server'
        })
      );

      unsubscribe();
    });

    test('应该正确取消订阅', async () => {
      await eventBus.connect();

      const mockHandler = jest.fn();
      const unsubscribe = eventBus.subscribe(EventType.KG_SEARCH_COMPLETED, mockHandler);

      // 取消订阅
      unsubscribe();

      // 发布事件
      await eventBus.publishEvent(EventType.KG_SEARCH_REQUEST, { query: 'test' });

      // 等待事件处理
      await new Promise(resolve => setTimeout(resolve, 200));

      expect(mockHandler).not.toHaveBeenCalled();
    });

    test('应该处理多个订阅者', async () => {
      await eventBus.connect();

      const mockHandler1 = jest.fn();
      const mockHandler2 = jest.fn();

      const unsubscribe1 = eventBus.subscribe(EventType.KG_SEARCH_COMPLETED, mockHandler1);
      const unsubscribe2 = eventBus.subscribe(EventType.KG_SEARCH_COMPLETED, mockHandler2);

      // 发布事件
      await eventBus.publishEvent(EventType.KG_SEARCH_REQUEST, { query: 'test' });

      // 等待事件处理
      await new Promise(resolve => setTimeout(resolve, 200));

      expect(mockHandler1).toHaveBeenCalled();
      expect(mockHandler2).toHaveBeenCalled();

      unsubscribe1();
      unsubscribe2();
    });
  });

  describe('请求-回复模式', () => {
    test('应该处理请求-回复模式', async () => {
      await eventBus.connect();

      // 设置回复监听器
      const unsubscribe = eventBus.subscribe(EventType.KG_SEARCH_COMPLETED, (event) => {
        // 模拟服务器回复
        if (event.correlation_id) {
          eventBus.publishEvent(EventType.KG_SEARCH_COMPLETED, {
            results: ['result1', 'result2'],
            correlation_id: event.correlation_id
          });
        }
      });

      const response = await eventBus.requestReply(
        EventType.KG_SEARCH_REQUEST,
        { query: 'test query' },
        EventType.KG_SEARCH_COMPLETED,
        5000
      );

      expect(response).not.toBeNull();
      expect(response?.correlation_id).toBeDefined();

      unsubscribe();
    });

    test('应该处理请求超时', async () => {
      await eventBus.connect();

      // 不设置回复监听器，模拟超时
      const response = await eventBus.requestReply(
        EventType.KG_SEARCH_REQUEST,
        { query: 'test query' },
        EventType.KG_SEARCH_COMPLETED,
        100 // 很短的超时时间
      );

      expect(response).toBeNull();
    });

    test('应该处理请求发送失败', async () => {
      // 强制断开连接
      eventBus.disconnect();

      const response = await eventBus.requestReply(
        EventType.KG_SEARCH_REQUEST,
        { query: 'test query' },
        EventType.KG_SEARCH_COMPLETED,
        1000
      );

      expect(response).toBeNull();
    });
  });

  describe('心跳机制', () => {
    test('应该发送心跳消息', async () => {
      await eventBus.connect();

      const ws = MockWebSocket.instances[0];
      const originalSend = ws.send;
      const sendSpy = jest.fn(originalSend);
      ws.send = sendSpy;

      // 等待心跳发送
      await new Promise(resolve => setTimeout(resolve, 35000));

      // 验证心跳消息被发送
      const pingCalls = sendSpy.mock.calls.filter(call => {
        try {
          const data = JSON.parse(call[0]);
          return data.type === 'ping';
        } catch {
          return false;
        }
      });

      expect(pingCalls.length).toBeGreaterThan(0);

      ws.send = originalSend;
    });

    test('应该处理心跳响应', async () => {
      await eventBus.connect();

      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      // 等待心跳和响应
      await new Promise(resolve => setTimeout(resolve, 35000));

      // 验证心跳响应被记录
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('心跳响应'));

      consoleSpy.mockRestore();
    });
  });

  describe('错误处理', () => {
    test('应该处理WebSocket错误', async () => {
      const errorHandler = jest.fn();
      eventBus.on('error', errorHandler);

      await eventBus.connect();

      // 触发错误
      const ws = MockWebSocket.instances[0];
      ws.onerror?.(new Event('error'));

      expect(errorHandler).toHaveBeenCalled();
    });

    test('应该处理消息解析错误', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      await eventBus.connect();

      // 发送无效消息
      const ws = MockWebSocket.instances[0];
      ws.onmessage?.(new MessageEvent('message', { data: 'invalid json' }));

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('消息解析失败'));

      consoleSpy.mockRestore();
    });
  });

  describe('重连机制', () => {
    test('应该尝试重连', async () => {
      await eventBus.connect();

      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      // 模拟连接断开
      const ws = MockWebSocket.instances[0];
      ws.onclose?.(new CloseEvent('close'));

      // 等待重连尝试
      await new Promise(resolve => setTimeout(resolve, 2000));

      // 验证重连被尝试
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('计划重连'));

      consoleSpy.mockRestore();
    });

    test('应该限制重连次数', async () => {
      // 设置较低的最大重连次数以便测试
      (eventBus as any).maxReconnectAttempts = 2;

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      // 模拟多次连接失败
      for (let i = 0; i < 3; i++) {
        await eventBus.connect();
        const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
        ws.onclose?.(new CloseEvent('close'));
        await new Promise(resolve => setTimeout(resolve, 3000));
      }

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('达到最大重连次数'));

      consoleSpy.mockRestore();
    });
  });
});