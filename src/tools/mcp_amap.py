# MCP AMap client (HTTP shim)
# Tries to call an external MCP server that exposes AMap tools via simple HTTP.
# Expected env:
# - AMAP_MCP_BASE_URL (e.g. https://amap-mcp.local)
# - AMAP_MCP_TOKEN (optional) -> sends Authorization: Bearer <token>

import os
from typing import Any, Dict, List, Tuple
import httpx


class McpError(Exception):
    pass


async def mcp_place_around(
    lon: float,
    lat: float,
    keywords: str,
    radius_m: int = 3000,
    page_size: int = 5,
) -> List[Tuple[float, float, str]]:
    base = os.environ.get("AMAP_MCP_BASE_URL")
    if not base:
        raise McpError("AMAP_MCP_BASE_URL not set")

    url = base.rstrip("/") + "/tools/place_around"
    headers = {}
    token = os.environ.get("AMAP_MCP_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "lon": lon,
        "lat": lat,
        "keywords": keywords,
        "radius_m": radius_m,
        "page_size": page_size,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=15.0)
        data: Dict[str, Any] = {}
        try:
            data = r.json()
        except Exception:
            pass
        if r.status_code != 200:
            raise McpError(f"place_around failed {r.status_code}: {data}")

    pois = []
    for item in (data.get("pois") or []):
        try:
            pois.append((float(item["lon"]), float(item["lat"]), str(item.get("name") or "POI")))
        except Exception:
            continue
    return pois[:page_size]


async def mcp_plan_route(
    mode: str,
    origin_lon: float,
    origin_lat: float,
    dest_lon: float,
    dest_lat: float,
) -> List[Dict[str, Any]]:
    base = os.environ.get("AMAP_MCP_BASE_URL")
    if not base:
        raise McpError("AMAP_MCP_BASE_URL not set")

    url = base.rstrip("/") + "/tools/plan_route"
    headers = {}
    token = os.environ.get("AMAP_MCP_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "mode": mode,
        "origin": {"lon": origin_lon, "lat": origin_lat},
        "destination": {"lon": dest_lon, "lat": dest_lat},
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=20.0)
        data: Dict[str, Any] = {}
        try:
            data = r.json()
        except Exception:
            pass
        if r.status_code != 200:
            raise McpError(f"plan_route failed {r.status_code}: {data}")

    routes_out: List[Dict[str, Any]] = []
    for rt in (data.get("routes") or []):
        coords = rt.get("coords") or []
        try:
            coords = [(float(x), float(y)) for (x, y) in coords]
        except Exception:
            continue
        routes_out.append(
            {
                "coords": coords,
                "distance_m": rt.get("distance_m"),
                "duration_s": rt.get("duration_s"),
            }
        )
    return routes_out