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

from typing import Awaitable, Callable, TypeAlias, Any, Mapping
from pydantic import BaseModel

from src.tools.zoom import (
    ZoomToBoundsArgs,
    zoom_to_bounds,
)
from src.tools.pyd import AnwayToolCallMetaArgs
from src.tools.openstreetmap import (
    download_from_openstreetmap as osm_download_tool,
    DownloadFromOpenStreetMapArgs,
)
from src.openstreetmap import has_openstreetmap_api_key


ToolFn = Callable[[Any, Any], Awaitable[dict]]
PydanticToolRegistry: TypeAlias = Mapping[
    str, tuple[ToolFn, type[BaseModel], type[BaseModel]]
]


def get_pydantic_tool_calls() -> PydanticToolRegistry:
    """Return mapping of tool name -> (async function, ArgModel, AnwayArgModel).

    Defined as a FastAPI dependency to allow overrides in tests or different deployments.
    """
    registry: dict[str, tuple[ToolFn, type[BaseModel], type[BaseModel]]] = {
        "zoom_to_bounds": (
            zoom_to_bounds,
            ZoomToBoundsArgs,
            AnwayToolCallMetaArgs,
        ),
    }
    if has_openstreetmap_api_key():
        registry["download_from_openstreetmap"] = (
            osm_download_tool,
            DownloadFromOpenStreetMapArgs,
            AnwayToolCallMetaArgs,
        )

    # Emergency reporting tools (always available; no schema changes)
    try:
        from src.tools.reporting import (
            report_disaster_text,
            ReportDisasterTextArgs,
            report_road_issue_text,
            ReportRoadIssueTextArgs,
        )
        registry["report_disaster_text"] = (
            report_disaster_text,
            ReportDisasterTextArgs,
            AnwayToolCallMetaArgs,
        )
        registry["report_road_issue_text"] = (
            report_road_issue_text,
            ReportRoadIssueTextArgs,
            AnwayToolCallMetaArgs,
        )
    except Exception as _e:
        # Keep core tools working even if optional modules are missing
        print("[Anway tools] reporting tools not loaded:", str(_e))

    # Situation summary tool
    try:
        from src.tools.situation import summarize_situation, SummarizeSituationArgs
        registry["summarize_situation"] = (
            summarize_situation,
            SummarizeSituationArgs,
            AnwayToolCallMetaArgs,
        )
    except Exception as _e:
        print("[Anway tools] situation tool not loaded:", str(_e))

    # AMap routing tool (optional; only when AMAP_API_KEY is present)
    try:
        import os as _os
if _os.environ.get("AMAP_API_KEY") or _os.environ.get("AMAP_MCP_BASE_URL")
            from src.tools.amap import plan_evac_amap, PlanEvacAmapArgs
            registry["plan_evac_amap"] = (
                plan_evac_amap,
                PlanEvacAmapArgs,
                AnwayToolCallMetaArgs,
            )
    except Exception as _e:
        print("[Anway tools] AMap tool not loaded:", str(_e))

    return registry
    """Return mapping of tool name -> (async function, ArgModel, AnwayArgModel).

    Defined as a FastAPI dependency to allow overrides in tests or different deployments.
    """
    registry: dict[str, tuple[ToolFn, type[BaseModel], type[BaseModel]]] = {
        "zoom_to_bounds": (
            zoom_to_bounds,
            ZoomToBoundsArgs,
            AnwayToolCallMetaArgs,
        ),
    }
    if has_openstreetmap_api_key():
        registry["download_from_openstreetmap"] = (
            osm_download_tool,
            DownloadFromOpenStreetMapArgs,
            AnwayToolCallMetaArgs,
        )
    return registry
