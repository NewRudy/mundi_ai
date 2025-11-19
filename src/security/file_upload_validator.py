"""
文件上传安全验证器
提供文件类型检查、病毒扫描、大小限制等安全功能
"""

import os
import re
import hashlib
import tempfile
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import magic
import filetype
from datetime import datetime

logger = logging.getLogger(__name__)

class FileType(Enum):
    """文件类型枚举"""
    VECTOR = "vector"
    RASTER = "raster"
    POINT_CLOUD = "point_cloud"
    CSV = "csv"
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    GEOTIFF = "geotiff"
    UNKNOWN = "unknown"

class ValidationStatus(Enum):
    """验证状态"""
    VALID = "valid"
    INVALID_TYPE = "invalid_type"
    TOO_LARGE = "too_large"
    MALICIOUS = "malicious"
    CORRUPTED = "corrupted"
    UNSUPPORTED = "unsupported"

@dataclass
class FileValidationResult:
    """文件验证结果"""
    status: ValidationStatus
    file_type: FileType
    original_filename: str
    safe_filename: str
    file_size: int
    mime_type: str
    detected_type: str
    extension: str
    checksum: str
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    scan_results: Optional[Dict[str, Any]] = None

class FileUploadValidator:
    """文件上传安全验证器"""

    # 允许的文件扩展名白名单
    ALLOWED_EXTENSIONS = {
        # 矢量数据
        '.geojson', '.json', '.kml', '.kmz', '.gpx', '.osm',
        '.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix',
        '.gdb', '.mdb',

        # 栅格数据
        '.tif', '.tiff', '.geotiff', '.gtiff',
        '.jpg', '.jpeg', '.png', '.bmp', '.gif',
        '.dem', '.dtm', '.dsm',

        # 点云数据
        '.las', '.laz', '.ply', '.xyz', '.pts',

        # CSV数据
        '.csv', '.tsv', '.txt',

        # 压缩格式
        '.zip', '.gz', '.tar', '.7z', '.rar'
    }

    # 危险的文件扩展名黑名单
    DANGEROUS_EXTENSIONS = {
        '.exe', '.dll', '.so', '.bat', '.cmd', '.sh', '.ps1',
        '.js', '.vbs', '.php', '.asp', '.jsp', '.py', '.rb',
        '.jar', '.war', '.ear', '.class',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.pdf', '.swf', '.fla'
    }

    # MIME类型白名单
    ALLOWED_MIME_TYPES = {
        'application/json',
        'application/geo+json',
        'application/vnd.google-earth.kml+xml',
        'application/vnd.google-earth.kmz',
        'application/gpx+xml',
        'text/csv',
        'text/plain',
        'text/tab-separated-values',
        'image/tiff',
        'image/geotiff',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'application/zip',
        'application/gzip',
        'application/x-tar',
        'application/x-7z-compressed',
        'application/x-rar-compressed'
    }

    def __init__(self, max_file_size: int = 100 * 1024 * 1024,  # 100MB
                 enable_virus_scan: bool = False,
                 enable_content_analysis: bool = True):
        self.max_file_size = max_file_size
        self.enable_virus_scan = enable_virus_scan
        self.enable_content_analysis = enable_content_analysis

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除危险字符"""
        if not filename:
            return "unnamed_file"

        # 移除路径遍历攻击
        filename = os.path.basename(filename)

        # 移除危险字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = re.sub(r'_{2,}', '_', filename)

        # 限制长度
        name, ext = os.path.splitext(filename)
        name = name[:50]  # 限制主文件名长度
        filename = name + ext

        return filename.lower()

    def detect_file_type(self, file_path: str, original_filename: str) -> Tuple[FileType, str, str]:
        """检测文件类型"""

        # 1. 基于扩展名初步判断
        _, ext = os.path.splitext(original_filename.lower())

        # 2. 使用magic库检测MIME类型
        try:
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_file(file_path)
        except Exception:
            detected_mime = "application/octet-stream"

        # 3. 使用filetype库进行更详细的检测
        try:
            kind = filetype.guess(file_path)
            if kind:
                detected_type = kind.mime
                detected_extension = kind.extension
            else:
                detected_type = detected_mime
                detected_extension = ext.lstrip('.')
        except Exception:
            detected_type = detected_mime
            detected_extension = ext.lstrip('.')

        # 4. 根据检测结果确定文件类型
        file_type = self._determine_file_type(ext, detected_type, detected_extension)

        return file_type, detected_type, detected_extension

    def _determine_file_type(self, extension: str, detected_mime: str, detected_ext: str) -> FileType:
        """根据多种因素确定文件类型"""

        # 矢量数据格式
        vector_extensions = {'.geojson', '.json', '.kml', '.kmz', '.gpx', '.osm',
                           '.shp', '.shx', '.dbf', '.prj', '.gdb', '.mdb'}
        vector_mimes = {'application/json', 'application/geo+json', 'application/vnd.google-earth.kml+xml'}

        # 栅格数据格式
        raster_extensions = {'.tif', '.tiff', '.geotiff', '.jpg', '.jpeg', '.png', '.dem', '.dtm', '.dsm'}
        raster_mimes = {'image/tiff', 'image/geotiff', 'image/jpeg', 'image/png'}

        # 点云数据格式
        point_cloud_extensions = {'.las', '.laz', '.ply', '.xyz', '.pts'}

        # CSV数据格式
        csv_extensions = {'.csv', '.tsv', '.txt'}
        csv_mimes = {'text/csv', 'text/tab-separated-values', 'text/plain'}

        # 判断逻辑
        if extension in vector_extensions or detected_mime in vector_mimes:
            return FileType.VECTOR
        elif extension in raster_extensions or detected_mime in raster_mimes:
            return FileType.RASTER
        elif extension in point_cloud_extensions:
            return FileType.POINT_CLOUD
        elif extension in csv_extensions or detected_mime in csv_mimes:
            return FileType.CSV
        else:
            return FileType.UNKNOWN

    def calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def scan_for_malicious_content(self, file_path: str) -> Dict[str, Any]:
        """扫描恶意内容"""
        scan_results = {
            "has_malicious_content": False,
            "threats_detected": [],
            "scan_status": "completed"
        }

        try:
            # 1. 检查文件头
            with open(file_path, 'rb') as f:
                header = f.read(512)  # 读取前512字节

                # 检查可执行文件头
                if header.startswith(b'MZ') or header.startswith(b'\x7fELF'):
                    scan_results["has_malicious_content"] = True
                    scan_results["threats_detected"].append("Executable file header detected")

                # 检查脚本签名
                script_signatures = [
                    b'#!/bin/bash',
                    b'#!/bin/sh',
                    b'#!/usr/bin/python',
                    b'#!/usr/bin/perl',
                    b'<script',
                    b'javascript:',
                    b'vbscript:'
                ]

                for signature in script_signatures:
                    if signature in header.lower():
                        scan_results["has_malicious_content"] = True
                        scan_results["threats_detected"].append(f"Script signature detected: {signature}")

            # 2. 内容分析（对于文本文件）
            if self.enable_content_analysis:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(8192)  # 读取前8KB文本内容

                        # 检查危险模式
                        dangerous_patterns = [
                            r'<script[^>]*>.*?</script>',
                            r'javascript:',
                            r'vbscript:',
                            r'onload\s*=',
                            r'onerror\s*=',
                            r'document\.write',
                            r'eval\s*\(',
                            r'exec\s*\(',
                            r'system\s*\(',
                            r'__import__',
                            r'import os',
                            r'subprocess\.'
                        ]

                        for pattern in dangerous_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                scan_results["has_malicious_content"] = True
                                scan_results["threats_detected"].append(f"Dangerous pattern: {pattern}")

                except Exception:
                    # 不是文本文件或无法解码，跳过内容分析
                    pass

        except Exception as e:
            scan_results["scan_status"] = "failed"
            scan_results["scan_error"] = str(e)

        return scan_results

    def perform_virus_scan(self, file_path: str) -> Dict[str, Any]:
        """执行病毒扫描（占位符实现）"""
        if not self.enable_virus_scan:
            return {
                "scan_status": "disabled",
                "threats_detected": [],
                "scan_engine": "none"
            }

        # 这里应该集成实际的病毒扫描引擎
        # 如: ClamAV, Windows Defender, 商业杀毒软件API等

        return {
            "scan_status": "not_implemented",
            "threats_detected": [],
            "scan_engine": "placeholder",
            "note": "Virus scanning requires integration with actual antivirus engine"
        }

    async def validate_file(self, file_path: str, original_filename: str,
                          file_size: int, user_id: str) -> FileValidationResult:
        """完整文件验证流程"""

        errors = []
        warnings = []
        metadata = {}

        try:
            # 1. 文件大小检查
            if file_size > self.max_file_size:
                errors.append(f"文件大小超过限制: {file_size} bytes > {self.max_file_size} bytes")
                return FileValidationResult(
                    status=ValidationStatus.TOO_LARGE,
                    file_type=FileType.UNKNOWN,
                    original_filename=original_filename,
                    safe_filename=self.sanitize_filename(original_filename),
                    file_size=file_size,
                    mime_type="unknown",
                    detected_type="unknown",
                    extension="",
                    checksum="",
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )

            # 2. 文件名清理
            safe_filename = self.sanitize_filename(original_filename)

            # 3. 扩展名检查
            _, extension = os.path.splitext(original_filename.lower())

            if extension in self.DANGEROUS_EXTENSIONS:
                errors.append(f"危险的文件扩展名: {extension}")
                return FileValidationResult(
                    status=ValidationStatus.MALICIOUS,
                    file_type=FileType.UNKNOWN,
                    original_filename=original_filename,
                    safe_filename=safe_filename,
                    file_size=file_size,
                    mime_type="unknown",
                    detected_type="unknown",
                    extension=extension,
                    checksum="",
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )

            if extension not in self.ALLOWED_EXTENSIONS:
                errors.append(f"不允许的文件扩展名: {extension}")
                return FileValidationResult(
                    status=ValidationStatus.INVALID_TYPE,
                    file_type=FileType.UNKNOWN,
                    original_filename=original_filename,
                    safe_filename=safe_filename,
                    file_size=file_size,
                    mime_type="unknown",
                    detected_type="unknown",
                    extension=extension,
                    checksum="",
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )

            # 4. 文件类型检测
            file_type, detected_mime, detected_ext = self.detect_file_type(file_path, original_filename)

            if file_type == FileType.UNKNOWN:
                errors.append(f"无法识别的文件类型: {extension}")
                return FileValidationResult(
                    status=ValidationStatus.UNSUPPORTED,
                    file_type=FileType.UNKNOWN,
                    original_filename=original_filename,
                    safe_filename=safe_filename,
                    file_size=file_size,
                    mime_type=detected_mime,
                    detected_type=detected_ext,
                    extension=extension,
                    checksum="",
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )

            # 5. 计算校验和
            checksum = self.calculate_checksum(file_path)

            # 6. 恶意内容扫描
            malicious_scan = self.scan_for_malicious_content(file_path)
            if malicious_scan["has_malicious_content"]:
                errors.extend(malicious_scan["threats_detected"])
                return FileValidationResult(
                    status=ValidationStatus.MALICIOUS,
                    file_type=file_type,
                    original_filename=original_filename,
                    safe_filename=safe_filename,
                    file_size=file_size,
                    mime_type=detected_mime,
                    detected_type=detected_ext,
                    extension=extension,
                    checksum=checksum,
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata,
                    scan_results=malicious_scan
                )

            # 7. 病毒扫描
            virus_scan = self.perform_virus_scan(file_path)

            # 8. 生成元数据
            metadata = {
                "validation_timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "original_extension": extension,
                "detected_mime_type": detected_mime,
                "file_type_detected": file_type.value,
                "scan_results": {
                    "malicious_scan": malicious_scan,
                    "virus_scan": virus_scan
                }
            }

            # 9. 成功验证
            return FileValidationResult(
                status=ValidationStatus.VALID,
                file_type=file_type,
                original_filename=original_filename,
                safe_filename=safe_filename,
                file_size=file_size,
                mime_type=detected_mime,
                detected_type=detected_ext,
                extension=extension,
                checksum=checksum,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                scan_results={
                    "malicious_scan": malicious_scan,
                    "virus_scan": virus_scan
                }
            )

        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            errors.append(f"验证过程异常: {str(e)}")
            return FileValidationResult(
                status=ValidationStatus.CORRUPTED,
                file_type=FileType.UNKNOWN,
                original_filename=original_filename,
                safe_filename=self.sanitize_filename(original_filename),
                file_size=file_size,
                mime_type="unknown",
                detected_type="unknown",
                extension="",
                checksum="",
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

# 全局文件验证器实例
file_validator = FileUploadValidator()

# 便捷函数
def validate_uploaded_file(file_path: str, original_filename: str,
                         file_size: int, user_id: str) -> FileValidationResult:
    """验证上传的文件"""
    return asyncio.run(file_validator.validate_file(file_path, original_filename, file_size, user_id))

def get_allowed_file_extensions() -> set:
    """获取允许的文件扩展名"""
    return FileUploadValidator.ALLOWED_EXTENSIONS.copy()

def is_dangerous_file_extension(extension: str) -> bool:
    """检查是否为危险文件扩展名"""
    return extension.lower() in FileUploadValidator.DANGEROUS_EXTENSIONS