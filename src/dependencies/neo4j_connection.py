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

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from neo4j import AsyncDriver as _AsyncDriver  # noqa: F401
    from neo4j import AsyncSession as _AsyncSession  # noqa: F401


class Neo4jConfig:
    """Neo4j connection configuration"""
    
    def __init__(self):
        self.host = os.getenv("NEO4J_HOST", "localhost")
        self.port = int(os.getenv("NEO4J_PORT", "7687"))
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.uri = f"bolt://{self.host}:{self.port}"
        
    @property
    def auth(self):
        return (self.user, self.password)


class Neo4jConnection:
    """Neo4j database connection manager"""
    
    def __init__(self):
        self.config = Neo4jConfig()
        self.driver: AsyncDriver | None = None
    
    async def connect(self) -> AsyncDriver:
        """Create and return Neo4j driver"""
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j Python driver is not installed. Please install 'neo4j' to enable graph features.")
        if self.driver is None:
            try:
                assert AsyncGraphDatabase is not None
                self.driver = AsyncGraphDatabase.driver(
                    self.config.uri,
                    auth=self.config.auth,
                    max_connection_lifetime=30 * 60,  # 30 minutes
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,  # 60 seconds
                )
                # Test the connection
                await self.driver.verify_connectivity()
                print(f"✅ Connected to Neo4j at {self.config.uri}")
            except (ServiceUnavailable, AuthError) as e:
                print(f"❌ Failed to connect to Neo4j: {e}")
                raise
        return self.driver
    
    async def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            await self.driver.close()
            self.driver = None
            print("🔌 Neo4j connection closed")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create Neo4j session context manager"""
        driver = await self.connect()
        async with driver.session() as session:  # type: ignore[attr-defined]
            yield session


# Global connection instance
neo4j_connection = Neo4jConnection()


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting Neo4j session (default/internal connection)"""
    async with neo4j_connection.session() as session:
        yield session


@asynccontextmanager
async def get_neo4j_session_for_connection(connection_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting Neo4j session for external connection by id"""
    from src.dependencies.neo4j_connection_manager import get_neo4j_connection_manager

    manager = get_neo4j_connection_manager()
    async with manager.session_for_connection(connection_id) as session:
        yield session

async def init_neo4j():
    """Initialize Neo4j connection on startup"""
    try:
        await neo4j_connection.connect()
        print("🚀 Neo4j initialized successfully")
    except Exception as e:
        print(f"⚠️  Neo4j initialization failed: {e}")
        # Don't raise exception - allow app to start without Neo4j


async def cleanup_neo4j():
    """Cleanup Neo4j connection on shutdown"""
    await neo4j_connection.close()