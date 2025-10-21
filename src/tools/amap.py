# Copyright (C) 2025 Bunting Labs, Inc.
# Licensed under the AGPLv3 or later.

import os
import math
from typing import Any, Dict, List, Optional, Tuple, Literal

import httpx
from pydantic import BaseModel, Field
from fastapi import UploadFile
from io import BytesIO

from src.tools.pyd import AnwayToolCallMetaArgs
from src.routes.websocket import kue_ephemeral_action
from src.routes.postgres_routes import internal_upload_layer, InternalLayerUploadResponse


AMAP_DRIVING_URL = "https://restapi.amap.com/v5/direction/driving"
AMAP_WALKING_URL = "https://restapi.amap.com/v5/direction/walking"
AMAP_PLACE_AROUND_URL = "https://restapi.amap.com/v5/place/around"


class PlanEvacAmapArgs(BaseModel):
    origin_lon: float = Field(..., description="Origin longitude")
    origin_lat: float = Field(..., description="Origin latitude")
    mode: Literal["walking", "driving"] = Field(..., description="Routing mode")
    dest_lon: Optional[float] = Field(None, description="Destination longitude (optional)")
    dest_lat: Optional[float] = Field(None, description="Destination latitude (optional)")
    dest_ftype: Optional[str] = Field(
        None, description="Facility type e.g. shelter|school|square (optional)"
    )
    current_time_iso: str = Field(
        ..., description="ISO8601 time string or 'now' (not used in MVP)"
    )


def _valid_lon_lat(lon: float, lat: float) -> bool:
    return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0


def _decode_polyline_str(poly: str) -> List[Tuple[float, float]]:
    """AMap step polyline is usually 'lon,lat;lon,lat;...'"""
    pts: List[Tuple[float, float]] = []
    for part in poly.split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            x, y = part.split(",")
            lon = float(x)
            lat = float(y)
            pts.append((lon, lat))
        except Exception:
            continue
    return pts


def _assemble_path_coords(route_obj: Dict[str, Any]) -> List[Tuple[float, float]]:
    # Try direct 'polyline'
    poly = route_obj.get("polyline")
    if isinstance(poly, str) and poly:
        return _decode_polyline_str(poly)

    # Else assemble from steps
    steps = route_obj.get("steps") or route_obj.get("segments")
    coords: List[Tuple[float, float]] = []
    if isinstance(steps, list):
        for st in steps:
            sp = st.get("polyline")
            if isinstance(sp, str) and sp:
                part = _decode_polyline_str(sp)
                if coords and part:
                    # avoid duplicate stitch
                    if coords[-1] == part[0]:
                        coords.extend(part[1:])
                    else:
                        coords.extend(part)
                else:
                    coords.extend(part)
    return coords


def _parse_routes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of candidate routes with keys: coords, distance_m, duration_s."""
    routes: List[Dict[str, Any]] = []

    # v5: sometimes 'routes': [ { 'distance':.., 'duration':.., 'polyline':.. } ]
    if isinstance(data.get("routes"), list) and data["routes"]:
        for r in data["routes"]:
            coords = _assemble_path_coords(r)
            dist = r.get("distance") or (r.get("cost") or {}).get("distance")
            dur = r.get("duration") or (r.get("cost") or {}).get("duration")
            try:
                distance_m = float(dist) if dist is not None else math.nan
            except Exception:
                distance_m = math.nan
            try:
                duration_s = float(dur) if dur is not None else math.nan
            except Exception:
                duration_s = math.nan
            if coords:
                routes.append(
                    {"coords": coords, "distance_m": distance_m, "duration_s": duration_s}
                )

    # v3-like: 'route': { 'paths': [ { 'distance':, 'duration':, 'steps':[{'polyline':..}] } ] }
    if not routes and isinstance(data.get("route"), dict):
        route = data["route"]
        paths = route.get("paths")
        if isinstance(paths, list) and paths:
            for p in paths:
                coords = _assemble_path_coords(p)
                dist = p.get("distance")
                dur = p.get("duration")
                try:
                    distance_m = float(dist) if dist is not None else math.nan
                except Exception:
                    distance_m = math.nan
                try:
                    duration_s = float(dur) if dur is not None else math.nan
                except Exception:
                    duration_s = math.nan
                if coords:
                    routes.append(
                        {"coords": coords, "distance_m": distance_m, "duration_s": duration_s}
                    )

    # Sort by duration then distance
    routes.sort(key=lambda r: (r.get("duration_s", math.inf), r.get("distance_m", math.inf)))
    return routes


async def _amap_place_around(
    client: httpx.AsyncClient,
    key: str,
    lon: float,
    lat: float,
    keywords: str,
    radius_m: int = 3000,
    page_size: int = 5,
) -> List[Tuple[float, float, str]]:
    params = {
        "location": f"{lon},{lat}",
        "keywords": keywords,
        "key": key,
        "radius": str(radius_m),
        "page_size": str(page_size),
    }
    r = await client.get(AMAP_PLACE_AROUND_URL, params=params, timeout=10.0)
    try:
        data = r.json()
    except Exception:
        data = {}

    pois = []
    # Try v5 style: data["pois"][{ "name", "location": "lon,lat" }]
    for item in (data.get("pois") or []):
        loc = item.get("location")
        name = item.get("name") or "POI"
        if isinstance(loc, str) and "," in loc:
            try:
                x, y = loc.split(",")
                pois.append((float(x), float(y), str(name)))
            except Exception:
                continue

    # Fallback other structures if needed
    return pois[:page_size]


def _coords_to_geojson_line(coords: List[Tuple[float, float]], props: Dict[str, Any]) -> bytes:
    import json

    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": props,
            }
        ],
    }
    return json.dumps(fc, ensure_ascii=False).encode("utf-8")


async def plan_evac_amap(args: PlanEvacAmapArgs, mundi: AnwayToolCallMetaArgs) -> Dict[str, Any]:
    """Use AMap to plan evacuation route from origin to destination (or nearest facility).

    - If dest_lon/lat provided, route directly.
    - Else if dest_ftype provided, use AMap place-around to find nearby candidates and route to each, pick best.
    - Create an unattached vector layer for the best route (GeoJSON LineString).
    """
    key = os.environ.get("AMAP_API_KEY")
    if not key:
        return {"status": "error", "error": "AMAP_API_KEY 未配置 / not configured"}

    if not _valid_lon_lat(args.origin_lon, args.origin_lat):
        return {"status": "error", "error": "起点经纬度无效/Invalid origin lon/lat"}

    if args.dest_lon is not None and args.dest_lat is not None:
        if not _valid_lon_lat(args.dest_lon, args.dest_lat):
            return {"status": "error", "error": "终点经纬度无效/Invalid destination lon/lat"}
        dests = [(args.dest_lon, args.dest_lat, "destination")]
    else:
        # Build keywords
        ftype = (args.dest_ftype or "").lower().strip()
        if ftype == "shelter":
            keywords = "避难所|应急避难|shelter"
        elif ftype == "school":
            keywords = "学校|中学|小学|幼儿园|school"
        elif ftype == "square":
            keywords = "广场|空地|运动场|square"
        else:
            keywords = "学校|广场|空地|避难所|应急避难|school|square|shelter"

        # Try MCP first
        pois = []
        try:
            from src.tools.mcp_amap import mcp_place_around as _mcp_place_around  # lazy import
            if os.environ.get("AMAP_MCP_BASE_URL"):
                pois = await _mcp_place_around(args.origin_lon, args.origin_lat, keywords)
        except Exception:
            pois = []
        if not pois:
            async with httpx.AsyncClient() as client:
                pois = await _amap_place_around(
                    client, key, args.origin_lon, args.origin_lat, keywords
                )
        if not pois:
            return {"status": "error", "error": "附近未找到候选目的地 / no nearby facilities"}
        dests = [(x, y, name) for (x, y, name) in pois]

    # Fetch routes
    mode = args.mode
    base_url = AMAP_WALKING_URL if mode == "walking" else AMAP_DRIVING_URL

    async with kue_ephemeral_action(
        mundi.conversation_id, f"规划{ '步行' if mode=='walking' else '驾车' }路线…"
    ):
        async with httpx.AsyncClient() as client:
            candidates = []
            for (dx, dy, dname) in dests:
                # Try MCP first for routing
                routes = []
                try:
                    from src.tools.mcp_amap import mcp_plan_route as _mcp_plan_route  # lazy import
                    if os.environ.get("AMAP_MCP_BASE_URL"):
                        routes = await _mcp_plan_route(mode, args.origin_lon, args.origin_lat, dx, dy)
                except Exception:
                    routes = []
                if not routes:
                    params = {
                        "origin": f"{args.origin_lon},{args.origin_lat}",
                        "destination": f"{dx},{dy}",
                        "key": key,
                        # Ask v5 to include polyline and cost if supported
                        "show_fields": "cost,polyline",
                    }
                    try:
                        r = await client.get(base_url, params=params, timeout=10.0)
                        data = r.json()
                    except Exception:
                        data = {}
                    routes = _parse_routes(data)
                for rt in routes:
                    if rt.get("coords"):
                        candidates.append(
                            {
                                "coords": rt["coords"],
                                "distance_m": rt.get("distance_m"),
                                "duration_s": rt.get("duration_s"),
                                "dest": {"name": dname, "lon": dx, "lat": dy},
                            }
                        )

    if not candidates:
        return {"status": "error", "error": "未获取到可用路线 / no route"}

    # sort by duration then distance
    candidates.sort(
        key=lambda c: (
            c.get("duration_s") if c.get("duration_s") is not None else math.inf,
            c.get("distance_m") if c.get("distance_m") is not None else math.inf,
        )
    )

    best = candidates[0]
    # Upload best as a line layer
    dist = best.get("distance_m")
    dur = best.get("duration_s")
    dest_name = best["dest"].get("name")
    props = {
        "mode": mode,
        "distance_m": dist,
        "duration_s": dur,
        "dest_name": dest_name,
        "dest_lon": best["dest"].get("lon"),
        "dest_lat": best["dest"].get("lat"),
    }
    gj_bytes = _coords_to_geojson_line(best["coords"], props)

    layer_name = (
        f"Evac route ({'步行' if mode=='walking' else '驾车'}) to {dest_name}"
        if dest_name
        else f"Evac route ({'步行' if mode=='walking' else '驾车'})"
    )
    upload = UploadFile(filename="route.geojson", file=BytesIO(gj_bytes))
    uploaded: InternalLayerUploadResponse = await internal_upload_layer(
        map_id=mundi.map_id,
        file=upload,
        layer_name=layer_name,
        add_layer_to_map=False,
        user_id=mundi.user_uuid,
        project_id=mundi.project_id,
    )

    # Prepare alternatives summary
    alts = []
    for c in candidates[1:3]:
        alts.append(
            {
                "dest": c.get("dest"),
                "distance_m": c.get("distance_m"),
                "duration_s": c.get("duration_s"),
            }
        )

    return {
        "status": "success",
        "layer_id": uploaded.id,
        "message": f"已生成疏散路线（未挂载）：{layer_name}",
        "alternatives": alts,
        "kue_instructions": (
            "使用 add_layer_to_map 将该路线显示在地图上，并为其设置一个清晰的中文名称。"
        ),
    }