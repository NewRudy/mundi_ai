/**
 * KGSearchPanel - 知识图谱搜索面板
 * 松耦合架构下的安全KG界面组件
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Search, Loader2, AlertCircle, Shield } from 'lucide-react';
import { secureEventBus, EventType } from '../../services/SecureEventBusService';

interface KGSearchResult {
  id: string;
  name: string;
  type: string;
  properties: Record<string, any>;
  score: number;
}

interface KGSearchPanelProps {
  onResultSelect?: (result: KGSearchResult) => void;
  className?: string;
}

export const KGSearchPanel: React.FC<KGSearchPanelProps> = ({
  onResultSelect,
  className = ''
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<KGSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  // 搜索知识图谱
  const searchKG = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    // 输入验证
    if (searchQuery.length > 200) {
      setError('搜索查询过长，请限制在200字符以内');
      return;
    }

    if (!secureEventBus.isAuthenticated()) {
      setError('请先连接知识图谱服务');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 使用安全事件总线发送搜索请求
      const response = await secureEventBus.requestReply(
        EventType.KG_SEARCH_REQUEST,
        {
          query: searchQuery.trim(),
          limit: 20,
          include_relationships: false
        },
        EventType.KG_SEARCH_COMPLETED,
        10000 // 10秒超时
      );

      if (response?.payload?.results) {
        setResults(response.payload.results);

        // 添加到搜索历史
        setSearchHistory(prev => {
          const updated = [searchQuery, ...prev.filter(q => q !== searchQuery)];
          return updated.slice(0, 5); // 保留最近5个搜索
        });
      } else {
        setResults([]);
        setError('未找到相关结果');
      }
    } catch (err) {
      console.error('KG搜索失败:', err);
      setError('搜索失败，请稍后重试');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 处理搜索输入
  const handleSearch = useCallback((value: string) => {
    setQuery(value);
    // 防抖搜索
    const timeoutId = setTimeout(() => {
      searchKG(value);
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [searchKG]);

  // 处理结果选择
  const handleResultSelect = useCallback((result: KGSearchResult) => {
    if (onResultSelect) {
      onResultSelect(result);
    }

    // 发布事件通知其他组件
    secureEventBus.publishEvent(EventType.KG_ANALYSIS_REQUEST, {
      action: 'select_result',
      result: result
    });
  }, [onResultSelect]);

  // 监听KG数据更新事件
  useEffect(() => {
    const unsubscribe = secureEventBus.subscribe(EventType.KG_DATA_UPDATED, (event) => {
      // 如果当前有搜索查询，重新搜索
      if (query.trim()) {
        searchKG(query);
      }
    });

    return unsubscribe;
  }, [query, searchKG]);

  return (
    <div className={`bg-white rounded-lg shadow-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">知识图谱搜索</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            secureEventBus.isAuthenticated() ? 'bg-green-500' : secureEventBus.getConnectionStatus() === 'connected' ? 'bg-yellow-500' : 'bg-red-500'
          }`} />
          <span className="text-xs text-gray-500">
            {secureEventBus.isAuthenticated() ? '已认证' :
             secureEventBus.getConnectionStatus() === 'connected' ? '已连接' : '未连接'}
          </span>
          <Shield className="w-4 h-4 text-blue-500" />
        </div>
      </div>

      {/* 搜索输入框 */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="搜索知识图谱..."
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 text-blue-500 w-4 h-4 animate-spin" />
        )}
      </div>

      {/* 搜索历史 */}
      {searchHistory.length > 0 && !query && (
        <div className="mb-4">
          <div className="text-sm text-gray-600 mb-2">搜索历史:</div>
          <div className="flex flex-wrap gap-2">
            {searchHistory.map((historyQuery, index) => (
              <button
                key={index}
                onClick={() => {
                  setQuery(historyQuery);
                  searchKG(historyQuery);
                }}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
              >
                {historyQuery}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center">
          <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* 搜索结果 */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {results.map((result) => (
          <div
            key={result.id}
            onClick={() => handleResultSelect(result)}
            className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="font-medium text-gray-900">{result.name}</div>
                <div className="text-sm text-gray-500">{result.type}</div>
              </div>
              <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                相关度: {result.score.toFixed(2)}
              </div>
            </div>

            {/* 显示关键属性 */}
            {Object.keys(result.properties).length > 0 && (
              <div className="mt-2 text-xs text-gray-600">
                {Object.entries(result.properties)
                  .slice(0, 3)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(', ')}
              </div>
            )}
          </div>
        ))}

        {results.length === 0 && query && !loading && (
          <div className="text-center py-8 text-gray-500">
            <Search className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <div>未找到相关结果</div>
            <div className="text-sm mt-1">尝试其他关键词</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KGSearchPanel;