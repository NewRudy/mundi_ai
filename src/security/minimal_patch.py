"""
最小化安全补丁
最小改动修复SQL注入漏洞
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# SQL注入攻击模式
INJECTION_PATTERNS = [
    r';',
    r'--',
    r'/\*',
    r'\*/',
    r'@@',
    r'union\s+select',
    r'union\s+all\s+select',
    r'exec\s*\(',
    r'execute\s+',
    r'sp_',
    r'xp_',
    r'drop\s+',
    r'truncate\s+',
    r'alter\s+',
    r'create\s+',
    r'delete\s+from',
    r'update\s+[\w-]+\s+set',
    r'insert\s+into',
    r'pg_sleep',
    r'waitfor\s+delay',
    r'benchmark',
    r'information_schema',
    r'pg_',
]

def sanitize_query(query: str) -> str:
    """
    最小化SQL清理 - 仅移除最危险的字符

    Args:
        query: 用户提交的查询

    Returns:
        清理后的查询
    """
    if not query:
        return query

    # 移除注释
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    # 移除堆叠查询（多个分号）
    query = query.strip()
    if ';' in query[:-1]:  # 分号不在末尾
        # 只保留最后一个分号（如果有的话）
        parts = query.split(';')
        query = ';'.join(parts[:-1])  # 移除最后一个分号之后的所有内容

    return query.strip()

def detect_injection_risk(query: str) -> List[str]:
    """
    检测SQL注入风险

    Args:
        query: SQL查询

    Returns:
        发现的风险模式列表
    """
    risks = []
    query_lower = query.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            risks.append(pattern)

    return risks

def sanitize_identifier(identifier: str) -> str:
    """
    清理标识符（表名、列名），移除危险字符

    Args:
        identifier: 标识符

    Returns:
        清理后的安全标识符
    """
    # 只允许字母数字和下划线
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
    # 如果清理后为空，返回默认值
    if not sanitized:
        return 'identifier'
    # 确保不以数字开头
    if sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized

def validate_identifier(identifier: str) -> bool:
    """
    验证标识符（表名、列名）是否安全

    Args:
        identifier: 标识符

    Returns:
        是否安全
    """
    # 只允许字母数字和下划线
    return identifier.replace('_', '').replace('-', '').isalnum()

def safe_query_check(query: str) -> bool:
    """
    快速检查查询是否可能安全

    Args:
        query: SQL查询

    Returns:
        True如果看起来安全，False如果有明显风险
    """
    if not query or not isinstance(query, str):
        return False

    risks = detect_injection_risk(query)
    return len(risks) == 0

# 危险函数黑名单
DANGEROUS_FUNCTIONS = {
    'pg_sleep', 'pg_sleep_for', 'pg_sleep_until',
    'lo_import', 'lo_export', 'lo_unlink',
    'system', 'exec', 'eval',
    'current_database', 'current_schema', 'current_user',
    'session_user', 'inet_server_addr', 'inet_server_port',
    'set_config', 'pg_cancel_backend', 'pg_terminate_backend'
}

def check_dangerous_functions(query: str) -> List[str]:
    """
    检查查询中是否包含危险函数

    Args:
        query: SQL查询

    Returns:
        发现的不安全函数列表
    """
    found = []
    query_lower = query.lower()

    for func in DANGEROUS_FUNCTIONS:
        if func in query_lower:
            found.append(func)

    return found

def apply_minimal_security(query: str, max_length: int = 10000) -> tuple[str, bool, List[str]]:
    """
    应用最小化安全检查

    Args:
        query: SQL查询
        max_length: 最大允许长度

    Returns:
        (处理后查询, 是否通过, 警告列表)
    """
    warnings = []

    # 长度检查
    if len(query) > max_length:
        warnings.append(f"查询超过最大长度({max_length}): {len(query)}")
        return query, False, warnings

    # 清理查询
    cleaned = sanitize_query(query)

    # 检测风险
    risks = detect_injection_risk(cleaned)
    if risks:
        warnings.append(f"检测到潜在风险模式: {risks}")

    # 检查危险函数
    dangerous_funcs = check_dangerous_functions(cleaned)
    if dangerous_funcs:
        warnings.append(f"检测到危险函数: {dangerous_funcs}")

    # 检查标识符
    identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', cleaned)
    for ident in identifiers:
        if len(ident) > 50:  # 标识符过长
            warnings.append(f"标识符过长: {ident}")

    # 简单模式检查 - 只允许SELECT查询
    if not re.match(r'\s*SELECT\s+', cleaned, re.IGNORECASE):
        warnings.append("只允许SELECT查询")

    is_safe = len(warnings) == 0

    return cleaned, is_safe, warnings

# 导出最小化安全函数
__all__ = [
    'sanitize_query',
    'sanitize_identifier',
    'detect_injection_risk',
    'validate_identifier',
    'safe_query_check',
    'check_dangerous_functions',
    'apply_minimal_security'
]
