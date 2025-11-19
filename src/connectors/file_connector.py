"""
文件数据连接器
支持CSV/JSON/Excel文件数据加载
"""

import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_connector import BaseConnector


class FileConnector(BaseConnector):
    """文件数据连接器"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.supported_formats = ['csv', 'json', 'xlsx', 'xls']

    async def connect(self, **kwargs) -> bool:
        """连接（文件连接器始终可用）"""
        return True

    async def load_csv(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """加载CSV文件"""
        try:
            df = pd.read_csv(file_path, **kwargs)
            data = self._process_dataframe(df)

            return {
                'status': 'success',
                'format': 'csv',
                'file_path': file_path,
                'data': data,
                'rows': len(df),
                'columns': list(df.columns),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"CSV文件加载失败: {e}")
            return {'status': 'error', 'message': str(e)}

    async def load_json(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                'status': 'success',
                'format': 'json',
                'file_path': file_path,
                'data': data,
                'size': len(str(data)),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"JSON文件加载失败: {e}")
            return {'status': 'error', 'message': str(e)}

    async def load_excel(self, file_path: str, sheet_name: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """加载Excel文件"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

            if isinstance(df, dict):
                # 多个sheet
                data = {
                    sheet_name: self._process_dataframe(sheet_df)
                    for sheet_name, sheet_df in df.items()
                }
                sheet_count = len(df)
            else:
                # 单个sheet
                data = self._process_dataframe(df)
                sheet_count = 1

            return {
                'status': 'success',
                'format': 'excel',
                'file_path': file_path,
                'sheet_name': sheet_name,
                'sheet_count': sheet_count,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Excel文件加载失败: {e}")
            return {'status': 'error', 'message': str(e)}

    def _process_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """处理DataFrame"""
        # 自动检测时间列
        time_columns = []
        for col in df.columns:
            if 'time' in str(col).lower() or 'date' in str(col).lower():
                try:
                    pd.to_datetime(df[col])
                    time_columns.append(col)
                except:
                    pass

        # 数值列统计
        numeric_columns = list(df.select_dtypes(include=['int64', 'float64']).columns)

        stats = {}
        for col in numeric_columns:
            stats[col] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'missing': int(df[col].isnull().sum())
            }

        return {
            'rows': len(df),
            'columns': list(df.columns),
            'data_types': df.dtypes.astype(str).to_dict(),
            'time_columns': time_columns,
            'numeric_columns': numeric_columns,
            'sample_data': df.head(5).to_dict('records'),
            'statistics': stats
        }

    async def detect_file_format(self, file_path: str) -> str:
        """检测文件格式"""
        path = Path(file_path)
        extension = path.suffix.lower()

        format_mapping = {
            '.csv': 'csv',
            '.json': 'json',
            '.xlsx': 'excel',
            '.xls': 'excel'
        }

        return format_mapping.get(extension, 'unknown')

    async def auto_load(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """自动检测并加载文件"""
        file_format = await self.detect_file_format(file_path)

        if file_format == 'csv':
            return await self.load_csv(file_path, **kwargs)
        elif file_format == 'json':
            return await self.load_json(file_path, **kwargs)
        elif file_format == 'excel':
            return await self.load_excel(file_path, **kwargs)
        else:
            return {
                'status': 'error',
                'message': f'不支持的文件格式: {file_format}'
            }
