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

import ssl
from urllib.parse import urlparse, parse_qs
import asyncpg
from typing import Dict, AsyncGenerator
from contextlib import asynccontextmanager

# Store pools by connection URI
_connection_pools: Dict[str, asyncpg.Pool] = {}


async def get_or_create_pool(connection_uri: str) -> asyncpg.Pool:
    """Get existing pool or create new one for the connection URI"""
    if connection_uri not in _connection_pools:
        parsed = urlparse(connection_uri)
        query = parse_qs(parsed.query)
        sslmode = (query.get("sslmode", [None])[0] or "").lower()

        ssl_param: ssl.SSLContext | bool | None
        if sslmode == "disable":
            ssl_param = False
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_param = ssl_context

        _connection_pools[connection_uri] = await asyncpg.create_pool(
            connection_uri, ssl=ssl_param, min_size=1, max_size=10, command_timeout=60
        )
    return _connection_pools[connection_uri]


@asynccontextmanager
async def get_pooled_connection(
    connection_uri: str,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Context manager that yields a database connection from pool"""
    pool = await get_or_create_pool(connection_uri)
    async with pool.acquire() as connection:
        yield connection
