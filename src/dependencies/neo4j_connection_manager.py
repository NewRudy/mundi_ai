# Copyright (C) 2025 Bunting Labs, Inc.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urlparse, urlunparse
import ipaddress

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession  # type: ignore
    from neo4j.exceptions import ServiceUnavailable, AuthError  # type: ignore
    NEO4J_AVAILABLE = True
except Exception:
    AsyncGraphDatabase = None  # type: ignore
    AsyncDriver = Any  # type: ignore
    AsyncSession = Any  # type: ignore

    class ServiceUnavailable(Exception):
        ...

    class AuthError(Exception):
        ...

    NEO4J_AVAILABLE = False

from src.structures import get_async_db_connection


class Neo4jConfigurationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class Neo4jConnectionURIError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


_ALLOWED_NEO4J_SCHEMES = {
    "neo4j",
    "neo4j+s",
    "neo4j+ssc",
    "bolt",
    "bolt+s",
    "bolt+ssc",
}


def _get_localhost_policy() -> str:
    # Prefer explicit NEO4J policy; else fall back to POSTGIS for consistency
    policy = os.environ.get("NEO4J_LOCALHOST_POLICY") or os.environ.get("POSTGIS_LOCALHOST_POLICY")
    if not policy:
        # Keep same behavior as PostGIS when missing: treat as configuration error
        raise Neo4jConfigurationError("Unknown NEO4J_LOCALHOST_POLICY: None")
    if policy not in {"disallow", "docker_rewrite", "allow"}:
        raise Neo4jConfigurationError(f"Unknown NEO4J_LOCALHOST_POLICY: {policy}")
    return policy


def verify_neo4j_uri(connection_uri: str) -> tuple[str, bool]:
    """
    Validate Neo4j URI and apply localhost policy if needed.
    Returns (processed_uri, was_rewritten)
    Raises Neo4jConnectionURIError or Neo4jConfigurationError
    """
    uri = connection_uri.strip()
    try:
        parsed = urlparse(uri)
    except Exception:
        raise Neo4jConnectionURIError("Invalid Neo4j connection URI format")

    if parsed.scheme not in _ALLOWED_NEO4J_SCHEMES:
        raise Neo4jConnectionURIError(
            "Invalid Neo4j URI scheme. Allowed: neo4j, neo4j+s, neo4j+ssc, bolt, bolt+s, bolt+ssc"
        )

    if not parsed.hostname:
        raise Neo4jConnectionURIError("Neo4j connection URI must include a hostname")

    # Localhost policy handling
    host = parsed.hostname
    is_loopback = False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            is_loopback = True
    except ValueError:
        # Not an IP; literal hostname
        if host.lower() == "localhost":
            is_loopback = True

    if is_loopback:
        policy = _get_localhost_policy()
        if policy == "disallow":
            raise Neo4jConnectionURIError(
                f"Detected a localhost database address ({host}) that cannot be connected to from the app"
            )
        elif policy == "docker_rewrite":
            new_netloc = parsed.netloc.replace(host, "host.docker.internal")
            rewritten = urlunparse(parsed._replace(netloc=new_netloc))
            return rewritten, True
        elif policy == "allow":
            return uri, False

    return uri, False


class Neo4jConnectionManager:
    """Manage external Neo4j connections per project connection_id."""

    def __init__(self) -> None:
        self._drivers: dict[str, AsyncDriver] = {}

    async def get_connection(self, connection_id: str) -> Dict[str, Any]:
        async with get_async_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, project_id, user_id, connection_uri, connection_name,
                       created_at, updated_at, last_error_text, last_error_timestamp,
                       soft_deleted_at
                FROM project_neo4j_connections
                WHERE id = $1
                """,
                connection_id,
            )
            if not row:
                raise Neo4jConnectionURIError(
                    f"Neo4j connection {connection_id} not found"
                )
            return dict(row)

    async def update_error_status(self, connection_id: str, error_text: Optional[str]) -> None:
        async with get_async_db_connection() as conn:
            if error_text:
                await conn.execute(
                    """
                    UPDATE project_neo4j_connections
                    SET last_error_text = $1, last_error_timestamp = $2
                    WHERE id = $3
                    """,
                    error_text,
                    datetime.now(timezone.utc),
                    connection_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE project_neo4j_connections
                    SET last_error_text = NULL, last_error_timestamp = NULL
                    WHERE id = $1
                    """,
                    connection_id,
                )

    async def _ensure_driver(self, connection_id: str) -> AsyncDriver:
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j Python driver is not installed. Please install 'neo4j'.")

        if connection_id in self._drivers:
            return self._drivers[connection_id]

        info = await self.get_connection(connection_id)
        raw_uri: str = info["connection_uri"]
        try:
            processed_uri, _ = verify_neo4j_uri(raw_uri)
        except (Neo4jConnectionURIError, Neo4jConfigurationError) as e:
            await self.update_error_status(connection_id, str(e))
            raise

        parsed = urlparse(processed_uri)
        user = parsed.username
        password = parsed.password
        # Rebuild uri without userinfo if present
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        # Manually assemble URI without userinfo
        uri_no_auth = f"{parsed.scheme}://{netloc}{parsed.path or ''}"
        if parsed.query:
            uri_no_auth += f"?{parsed.query}"
        if parsed.fragment:
            uri_no_auth += f"#{parsed.fragment}"

        try:
            assert AsyncGraphDatabase is not None
            driver: AsyncDriver = AsyncGraphDatabase.driver(
                uri_no_auth,
                auth=(user, password) if user else None,
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
            await driver.verify_connectivity()
            self._drivers[connection_id] = driver
            await self.update_error_status(connection_id, None)
            return driver
        except (ServiceUnavailable, AuthError) as e:
            await self.update_error_status(connection_id, str(e))
            raise

    @asynccontextmanager
    async def session_for_connection(self, connection_id: str) -> AsyncGenerator[AsyncSession, None]:
        driver = await self._ensure_driver(connection_id)
        async with driver.session() as session:  # type: ignore[attr-defined]
            yield session


# Singleton
_neo4j_conn_manager: Neo4jConnectionManager | None = None

def get_neo4j_connection_manager() -> Neo4jConnectionManager:
    global _neo4j_conn_manager
    if _neo4j_conn_manager is None:
        _neo4j_conn_manager = Neo4jConnectionManager()
    return _neo4j_conn_manager
