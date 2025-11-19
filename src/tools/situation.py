# Copyright (C) 2025 Bunting Labs, Inc.
# Licensed under the AGPLv3 or later.

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.tools.pyd import AnwayToolCallMetaArgs
from src.core.connection_wrapper import get_async_db_connection
from src.routes.websocket import kue_ephemeral_action


class SummarizeSituationArgs(BaseModel):
    current_time_iso: str = Field(..., description="ISO8601 time string; use 'now' if unknown")


def _contains_any(name: str, keywords: List[str]) -> bool:
    lname = (name or "").lower()
    return any(kw in lname for kw in keywords)


async def summarize_situation(
    args: SummarizeSituationArgs, mundi: AnwayToolCallMetaArgs
) -> Dict[str, Any]:
    """Summarize current map layers without new queries/migrations."""
    async with kue_ephemeral_action(mundi.conversation_id, "汇总态势…"):
        async with get_async_db_connection("situation.summary") as conn:
            rows = await conn.fetch(
                """
                SELECT ml.layer_id, ml.name, ml.type, ml.geometry_type, ml.feature_count
                FROM map_layers ml
                JOIN user_mundiai_maps m ON ml.layer_id = ANY(m.layers)
                WHERE m.id = $1
                ORDER BY ml.name
                """,
                mundi.map_id,
            )

    layers = [dict(r) for r in rows]

    stats = {
        "total_layers": len(layers),
        "vectors": sum(1 for r in layers if r.get("type") == "vector"),
        "rasters": sum(1 for r in layers if r.get("type") == "raster"),
        "postgis": sum(1 for r in layers if r.get("type") == "postgis"),
        "points": sum(1 for r in layers if (r.get("geometry_type") or "").lower().find("point") >= 0),
        "lines": sum(1 for r in layers if (r.get("geometry_type") or "").lower().find("line") >= 0),
        "polygons": sum(1 for r in layers if (r.get("geometry_type") or "").lower().find("polygon") >= 0),
    }

    # Buckets by keywords (lightweight, name-based)
    disaster_kws = ["flood", "earthquake", "hazard", "灾", "洪", "震"]
    report_kws = ["report", "issue", "上报"]
    facility_kws = [
        "shelter",
        "school",
        "square",
        "hospital",
        "fire",
        "医院",
        "学校",
        "广场",
        "消防",
        "避难所",
    ]

    buckets = {
        "disaster_layers": [r for r in layers if _contains_any(r.get("name", ""), disaster_kws)],
        "report_layers": [r for r in layers if _contains_any(r.get("name", ""), report_kws)],
        "facility_layers": [r for r in layers if _contains_any(r.get("name", ""), facility_kws)],
    }

    def sum_features(rs: List[Dict[str, Any]]) -> int:
        s = 0
        for r in rs:
            try:
                if r.get("feature_count") is not None:
                    s += int(r.get("feature_count"))
            except Exception:
                pass
        return s

    summary_text = (
        f"图层总数 {stats['total_layers']}，点/线/面="
        f"{stats['points']}/{stats['lines']}/{stats['polygons']}。"
    )

    if buckets["disaster_layers"]:
        summary_text += (
            f" 灾害相关图层 {len(buckets['disaster_layers'])} 个，"
            f"要素约 {sum_features(buckets['disaster_layers'])}。"
        )
    if buckets["report_layers"]:
        summary_text += (
            f" 上报类图层 {len(buckets['report_layers'])} 个，"
            f"要素约 {sum_features(buckets['report_layers'])}。"
        )
    if buckets["facility_layers"]:
        summary_text += (
            f" 设施类图层 {len(buckets['facility_layers'])} 个，"
            f"要素约 {sum_features(buckets['facility_layers'])}。"
        )

    # simple markdown for reliable rendering in chat
    md_lines: list[str] = []
    md_lines.append("**态势总览**")
    md_lines.append("")
    md_lines.append(f"- 图层总数：{stats['total_layers']} (点/线/面：{stats['points']}/{stats['lines']}/{stats['polygons']})")
    if buckets["disaster_layers"]:
        md_lines.append(f"- 灾害相关图层：{len(buckets['disaster_layers'])}，要素≈{sum_features(buckets['disaster_layers'])}")
    if buckets["report_layers"]:
        md_lines.append(f"- 上报类图层：{len(buckets['report_layers'])}，要素≈{sum_features(buckets['report_layers'])}")
    if buckets["facility_layers"]:
        md_lines.append(f"- 设施类图层：{len(buckets['facility_layers'])}，要素≈{sum_features(buckets['facility_layers'])}")

    def _mk_list(title: str, names: list[str]) -> list[str]:
        if not names:
            return []
        out = [f"\n**{title}（Top 5）**"]
        out.extend([f"- {n}" for n in names])
        return out

    md_lines.extend(_mk_list("灾害相关", [r.get("name") for r in buckets["disaster_layers"]][:5]))
    md_lines.extend(_mk_list("上报类", [r.get("name") for r in buckets["report_layers"]][:5]))
    md_lines.extend(_mk_list("设施类", [r.get("name") for r in buckets["facility_layers"]][:5]))

    markdown = "\n".join(md_lines)

    return {
        "status": "success",
        "summary": summary_text,
        "markdown": markdown,
        "stats": stats,
        "disaster_layers": [r.get("name") for r in buckets["disaster_layers"]][:5],
        "report_layers": [r.get("name") for r in buckets["report_layers"]][:5],
        "facility_layers": [r.get("name") for r in buckets["facility_layers"]][:5],
    }
