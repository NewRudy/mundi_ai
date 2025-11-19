"""
现代化认证授权系统
替代简单的环境变量认证，实现JWT和RBAC
"""

import jwt
import bcrypt
import secrets
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone
from functools import wraps
import json

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    ORGANIZATION_ADMIN = "org_admin"
    PROJECT_OWNER = "project_owner"
    PROJECT_MEMBER = "project_member"
    VIEWER = "viewer"
    GUEST = "guest"

class Permission(Enum):
    """权限枚举"""
    # 系统权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_VIEW = "system:view"

    # 组织权限
    ORG_CREATE = "org:create"
    ORG_DELETE = "org:delete"
    ORG_MANAGE_USERS = "org:manage_users"
    ORG_VIEW = "org:view"

    # 项目权限
    PROJECT_CREATE = "project:create"
    PROJECT_DELETE = "project:delete"
    PROJECT_EDIT = "project:edit"
    PROJECT_VIEW = "project:view"
    PROJECT_SHARE = "project:share"

    # 地图权限
    MAP_CREATE = "map:create"
    MAP_DELETE = "map:delete"
    MAP_EDIT = "map:edit"
    MAP_VIEW = "map:view"
    MAP_SHARE = "map:share"

    # 图层权限
    LAYER_CREATE = "layer:create"
    LAYER_DELETE = "layer:delete"
    LAYER_EDIT = "layer:edit"
    LAYER_VIEW = "layer:view"

    # 数据权限
    DATA_UPLOAD = "data:upload"
    DATA_DELETE = "data:delete"
    DATA_DOWNLOAD = "data:download"
    DATA_QUERY = "data:query"

    # 知识图谱权限
    KG_CREATE = "kg:create"
    KG_DELETE = "kg:delete"
    KG_EDIT = "kg:edit"
    KG_VIEW = "kg:view"
    KG_QUERY = "kg:query"

@dataclass
class User:
    """用户数据模型"""
    id: str
    username: str
    email: str
    role: UserRole
    organization_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    last_login: Optional[datetime] = None
    permissions: Set[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.permissions is None:
            self.permissions = set()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class JWTToken:
    """JWT令牌数据"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    user_id: str = ""
    scope: List[str] = None

    def __post_init__(self):
        if self.scope is None:
            self.scope = []

class RolePermissionManager:
    """角色权限管理器"""

    # 角色权限映射
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            Permission.SYSTEM_ADMIN,
            Permission.SYSTEM_VIEW,
            Permission.ORG_CREATE,
            Permission.ORG_DELETE,
            Permission.ORG_MANAGE_USERS,
            Permission.ORG_VIEW,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_EDIT,
            Permission.PROJECT_VIEW,
            Permission.PROJECT_SHARE,
            Permission.MAP_CREATE,
            Permission.MAP_DELETE,
            Permission.MAP_EDIT,
            Permission.MAP_VIEW,
            Permission.MAP_SHARE,
            Permission.LAYER_CREATE,
            Permission.LAYER_DELETE,
            Permission.LAYER_EDIT,
            Permission.LAYER_VIEW,
            Permission.DATA_UPLOAD,
            Permission.DATA_DELETE,
            Permission.DATA_DOWNLOAD,
            Permission.DATA_QUERY,
            Permission.KG_CREATE,
            Permission.KG_DELETE,
            Permission.KG_EDIT,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        },
        UserRole.ORGANIZATION_ADMIN: {
            Permission.ORG_VIEW,
            Permission.ORG_MANAGE_USERS,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_EDIT,
            Permission.PROJECT_VIEW,
            Permission.PROJECT_SHARE,
            Permission.MAP_CREATE,
            Permission.MAP_DELETE,
            Permission.MAP_EDIT,
            Permission.MAP_VIEW,
            Permission.MAP_SHARE,
            Permission.LAYER_CREATE,
            Permission.LAYER_DELETE,
            Permission.LAYER_EDIT,
            Permission.LAYER_VIEW,
            Permission.DATA_UPLOAD,
            Permission.DATA_DELETE,
            Permission.DATA_DOWNLOAD,
            Permission.DATA_QUERY,
            Permission.KG_CREATE,
            Permission.KG_DELETE,
            Permission.KG_EDIT,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        },
        UserRole.PROJECT_OWNER: {
            Permission.PROJECT_EDIT,
            Permission.PROJECT_VIEW,
            Permission.PROJECT_SHARE,
            Permission.MAP_CREATE,
            Permission.MAP_DELETE,
            Permission.MAP_EDIT,
            Permission.MAP_VIEW,
            Permission.MAP_SHARE,
            Permission.LAYER_CREATE,
            Permission.LAYER_DELETE,
            Permission.LAYER_EDIT,
            Permission.LAYER_VIEW,
            Permission.DATA_UPLOAD,
            Permission.DATA_DELETE,
            Permission.DATA_DOWNLOAD,
            Permission.DATA_QUERY,
            Permission.KG_CREATE,
            Permission.KG_DELETE,
            Permission.KG_EDIT,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        },
        UserRole.PROJECT_MEMBER: {
            Permission.PROJECT_VIEW,
            Permission.MAP_CREATE,
            Permission.MAP_EDIT,
            Permission.MAP_VIEW,
            Permission.LAYER_CREATE,
            Permission.LAYER_EDIT,
            Permission.LAYER_VIEW,
            Permission.DATA_UPLOAD,
            Permission.DATA_DOWNLOAD,
            Permission.DATA_QUERY,
            Permission.KG_CREATE,
            Permission.KG_EDIT,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        },
        UserRole.VIEWER: {
            Permission.PROJECT_VIEW,
            Permission.MAP_VIEW,
            Permission.LAYER_VIEW,
            Permission.DATA_DOWNLOAD,
            Permission.DATA_QUERY,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        },
        UserRole.GUEST: {
            Permission.PROJECT_VIEW,
            Permission.MAP_VIEW,
            Permission.LAYER_VIEW,
            Permission.KG_VIEW,
            Permission.KG_QUERY,
        }
    }

    @classmethod
    def get_role_permissions(cls, role: UserRole) -> Set[str]:
        """获取角色的权限集合"""
        return cls.ROLE_PERMISSIONS.get(role, set())

    @classmethod
    def has_permission(cls, user: User, permission: Permission) -> bool:
        """检查用户是否有特定权限"""
        if not user.is_active:
            return False
        return permission.value in user.permissions

    @classmethod
    def has_any_permission(cls, user: User, permissions: List[Permission]) -> bool:
        """检查用户是否有任意一个权限"""
        if not user.is_active:
            return False
        user_perms = user.permissions
        return any(perm.value in user_perms for perm in permissions)

    @classmethod
    def has_all_permissions(cls, user: User, permissions: List[Permission]) -> bool:
        """检查用户是否拥有所有指定权限"""
        if not user.is_active:
            return False
        user_perms = user.permissions
        return all(perm.value in user_perms for perm in permissions)

class JWTManager:
    """JWT令牌管理器"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def generate_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """生成访问令牌"""
        if expires_delta is None:
            expires_delta = timedelta(hours=1)

        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "org_id": user.organization_id,
            "permissions": list(user.permissions),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
            "type": "access"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self, user: User) -> str:
        """生成刷新令牌"""
        expire = datetime.now(timezone.utc) + timedelta(days=30)

        payload = {
            "sub": user.id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(16),
            "type": "refresh"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT令牌已过期")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT令牌解码失败: {e}")
            return None

    def verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> bool:
        """验证令牌类型"""
        return payload.get("type") == expected_type

class AuthenticationManager:
    """认证管理器"""

    def __init__(self, secret_key: str):
        self.jwt_manager = JWTManager(secret_key)
        self.permission_manager = RolePermissionManager()
        self.token_blacklist = set()  # 令牌黑名单

    async def authenticate_user(self, username: str, password: str,
                              user_repository) -> Optional[User]:
        """用户认证"""
        try:
            # 从存储库获取用户信息
            user_data = await user_repository.get_user_by_username(username)
            if not user_data:
                return None

            # 验证密码
            if not self.verify_password(password, user_data.get("password_hash", "")):
                return None

            # 创建用户对象
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=UserRole(user_data.get("role", "viewer")),
                organization_id=user_data.get("organization_id"),
                is_active=user_data.get("is_active", True),
                permissions=set(user_data.get("permissions", []))
            )

            # 如果用户没有显式权限，使用角色权限
            if not user.permissions:
                user.permissions = self.permission_manager.get_role_permissions(user.role)

            return user

        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def generate_tokens(self, user: User) -> JWTToken:
        """生成JWT令牌对"""
        access_token = self.jwt_manager.generate_access_token(user)
        refresh_token = self.jwt_manager.generate_refresh_token(user)

        return JWTToken(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            scope=list(user.permissions)
        )

    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        try:
            payload = self.jwt_manager.decode_token(token)
            if payload:
                self.token_blacklist.add(payload.get("jti"))
                return True
        except Exception as e:
            logger.error(f"令牌撤销失败: {e}")
        return False

    def is_token_revoked(self, payload: Dict[str, Any]) -> bool:
        """检查令牌是否被撤销"""
        return payload.get("jti") in self.token_blacklist

# 认证装饰器
def require_auth(permissions: Optional[List[Permission]] = None):
    """认证装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里应该实现实际的认证逻辑
            # 从请求头获取JWT令牌并验证

            # 简化实现 - 实际应该从请求上下文获取用户
            current_user = kwargs.get('current_user')
            if not current_user:
                raise PermissionError("用户未认证")

            if permissions:
                permission_manager = RolePermissionManager()
                if not permission_manager.has_any_permission(current_user, permissions):
                    raise PermissionError(f"用户没有所需权限: {[p.value for p in permissions]}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(roles: List[UserRole]):
    """角色要求装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise PermissionError("用户未认证")

            if current_user.role not in roles:
                raise PermissionError(f"用户角色不符合要求: {current_user.role.value}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 全局认证管理器实例
auth_manager = AuthenticationManager(
    secret_key=os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
)

# 便捷函数
def create_user(username: str, email: str, password: str, role: UserRole,
                organization_id: Optional[str] = None) -> Dict[str, Any]:
    """创建新用户"""
    password_hash = auth_manager.hash_password(password)
    user_id = f"user_{secrets.token_urlsafe(16)}"

    permissions = list(RolePermissionManager.get_role_permissions(role))

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role.value,
        "organization_id": organization_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "permissions": permissions,
        "metadata": {}
    }

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """验证JWT令牌"""
    try:
        payload = auth_manager.jwt_manager.decode_token(token)
        if payload and not auth_manager.is_token_revoked(payload):
            return payload
        return None
    except Exception as e:
        logger.error(f"JWT令牌验证失败: {e}")
        return None

def get_user_from_token_payload(payload: Dict[str, Any]) -> User:
    """从JWT载荷创建用户对象"""
    return User(
        id=payload["sub"],
        username=payload["username"],
        email=payload["email"],
        role=UserRole(payload["role"]),
        organization_id=payload.get("org_id"),
        is_active=True,
        permissions=set(payload.get("permissions", [])),
        metadata={}
    )