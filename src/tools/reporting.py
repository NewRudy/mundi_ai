# Copyright (C) 2025 Bunting Labs, Inc.
# Licensed under the AGPLv3 or later.

from typing import Any, Dict
from datetime import datetime
from io import BytesIO

from pydantic import BaseModel, Field
from fastapi import UploadFile

from src.tools.pyd import AnwayToolCallMetaArgs
from src.routes.websocket import kue_ephemeral_action
from src.routes.postgres_routes import internal_upload_layer, InternalLayerUploadResponse


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _make_point_geojson(lon: float, lat: float, props: Dict[str, Any]) -> bytes:
    import json

    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        ],
    }
    return json.dumps(fc, ensure_ascii=False).encode("utf-8")


class ReportDisasterTextArgs(BaseModel):
    """灾情文本上报工具 / Disaster text reporting tool

    用于将用户在地图上右键位置的文字上报记录为一个未挂载的点图层。\
    Records a text-only disaster report at a clicked lon/lat as an unattached point layer.
    """
    raw_text: str = Field(..., description="User-submitted disaster description text")
    lon: float = Field(..., description="Longitude of the reported location")
    lat: float = Field(..., description="Latitude of the reported location")
    current_time_iso: str = Field(..., description="ISO8601 time string; use 'now' if unknown")


class ReportRoadIssueTextArgs(BaseModel):
    """道路问题文本上报工具 / Road issue text reporting tool

    记录用户在地图上右键位置的道路问题描述为未挂载点图层。\
    Records a text-only road issue at a clicked lon/lat as an unattached point layer.
    """
    raw_text: str = Field(..., description="User-submitted road issue text")
    lon: float = Field(..., description="Longitude of the reported location")
    lat: float = Field(..., description="Latitude of the reported location")
    current_time_iso: str = Field(..., description="ISO8601 time string; use 'now' if unknown")


async def _upload_point_layer(
    mundi: AnwayToolCallMetaArgs,
    name_prefix: str,
    geojson_bytes: bytes,
) -> InternalLayerUploadResponse:
    filename = f"{name_prefix}.geojson"
    upload = UploadFile(filename=filename, file=BytesIO(geojson_bytes))

    result: InternalLayerUploadResponse = await internal_upload_layer(
        map_id=mundi.map_id,
        file=upload,
        layer_name=name_prefix,
        add_layer_to_map=False,
        user_id=mundi.user_uuid,
        project_id=mundi.project_id,
    )
    return result


async def report_disaster_text(
    args: ReportDisasterTextArgs, mundi: AnwayToolCallMetaArgs
) -> Dict[str, Any]:
    """Create an unattached point layer to record a disaster text report at a clicked location.

    输入: 文本、经纬度，时间（"now" 或 ISO8601）。\
    Output: layer_id（未挂载），供 add_layer_to_map 使用。
    """
    # basic validation
    if not (-180.0 <= args.lon <= 180.0 and -90.0 <= args.lat <= 90.0):
        return {"status": "error", "error": "无效经纬度范围/Invalid lon/lat"}
    raw = (args.raw_text or "").strip()
    if not raw:
        return {"status": "error", "error": "请输入有效文本/Empty text"}
    if len(raw) > 4000:
        raw = raw[:4000]

    ts = _now_iso() if args.current_time_iso.lower() == "now" else args.current_time_iso
    props = {"type": "disaster_report", "raw_text": raw, "timestamp": ts}
    gbytes = _make_point_geojson(args.lon, args.lat, props)

    layer_name = f"Disaster report {ts[:19].replace('T',' ')}"
    async with kue_ephemeral_action(mundi.conversation_id, f"提交灾情上报：{layer_name}"):
        uploaded = await _upload_point_layer(mundi, layer_name, gbytes)

    return {
        "status": "success",
        "message": f"灾情上报已记录为未挂载图层：{uploaded.name}",
        "layer_id": uploaded.id,
        "kue_instructions": (
            "使用 add_layer_to_map 将此标注显示在地图上（提供 layer_id 与一个易懂的新名称）。"
        ),
    }


async def report_road_issue_text(
    args: ReportRoadIssueTextArgs, mundi: AnwayToolCallMetaArgs
) -> Dict[str, Any]:
    """Create an unattached point layer to record a road issue text report at a clicked location.

    输入: 文本、经纬度，时间（"now" 或 ISO8601）。\
    Output: layer_id（未挂载），供 add_layer_to_map 使用。
    """
    # basic validation
    if not (-180.0 <= args.lon <= 180.0 and -90.0 <= args.lat <= 90.0):
        return {"status": "error", "error": "无效经纬度范围/Invalid lon/lat"}
    raw = (args.raw_text or "").strip()
    if not raw:
        return {"status": "error", "error": "请输入有效文本/Empty text"}
    if len(raw) > 4000:
        raw = raw[:4000]

    ts = _now_iso() if args.current_time_iso.lower() == "now" else args.current_time_iso
    props = {"type": "road_issue", "raw_text": raw, "timestamp": ts}
    gbytes = _make_point_geojson(args.lon, args.lat, props)

    layer_name = f"Road issue {ts[:19].replace('T',' ')}"
    async with kue_ephemeral_action(mundi.conversation_id, f"提交道路问题上报：{layer_name}"):
        uploaded = await _upload_point_layer(mundi, layer_name, gbytes)

    return {
        "status": "success",
        "message": f"道路问题已记录为未挂载图层：{uploaded.name}",
        "layer_id": uploaded.id,
        "kue_instructions": (
            "使用 add_layer_to_map 将此标注显示在地图上（提供 layer_id 与一个易懂的新名称）。"
        ),
    }
