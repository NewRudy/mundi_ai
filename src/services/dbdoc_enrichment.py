# Incremental enrichment for Postgres documentation
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from redis import Redis

from src.structures import get_async_db_connection
from src.services.graph_service import graph_service
from src.dependencies.database_documenter import generate_id

redis = Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
)


async def _fetch_latest_base_doc(connection_id: str) -> Tuple[Optional[str], Optional[str]]:
    async with get_async_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT friendly_name, summary_md
            FROM project_postgres_summary
            WHERE connection_id = $1
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            connection_id,
        )
        if not row:
            return None, None
        return row["friendly_name"], row["summary_md"]


def _format_kg_section(stats: Dict[str, Any], language: str = "zh-CN") -> str:
    # Basic text in zh-CN or en-US
    total_nodes = stats.get("total_nodes", 0)
    total_relationships = stats.get("total_relationships", 0)
    nodes = stats.get("nodes", {}) or {}
    rels = stats.get("relationships", {}) or {}

    top_labels = sorted(nodes.items(), key=lambda x: x[1], reverse=True)[:5]
    top_rels = sorted(rels.items(), key=lambda x: x[1], reverse=True)[:5]

    now_iso = datetime.utcnow().isoformat()

    if language.lower().startswith("zh"):
        lines = [
            "## 知识图谱概览",
            f"- 节点总数: {total_nodes}",
            f"- 关系总数: {total_relationships}",
        ]
        if top_labels:
            lines.append("- 主要节点类型: " + ", ".join([f"{k}: {v}" for k, v in top_labels]))
        if top_rels:
            lines.append("- 主要关系类型: " + ", ".join([f"{k}: {v}" for k, v in top_rels]))
        lines.append("")
        lines.append("> 元数据: 本次富化包含来自 Neo4j 的统计快照; 时间: " + now_iso)
    else:
        lines = [
            "## Knowledge Graph Overview",
            f"- Total nodes: {total_nodes}",
            f"- Total relationships: {total_relationships}",
        ]
        if top_labels:
            lines.append("- Top labels: " + ", ".join([f"{k}: {v}" for k, v in top_labels]))
        if top_rels:
            lines.append("- Top relationship types: " + ", ".join([f"{k}: {v}" for k, v in top_rels]))
        lines.append("")
        lines.append("> Metadata: Enrichment includes snapshot from Neo4j graph stats; time: " + now_iso)

    return "\n".join(lines)


async def generate_enriched_markdown(
    connection_id: str,
    *,
    language: str = "zh-CN",
    useKG: bool = True,
    useDomainDocs: bool = False,
    useSpatial: bool = False,
) -> Tuple[str, str]:
    # Fetch base
    base_name, base_md = await _fetch_latest_base_doc(connection_id)
    if not base_md:
        base_name = base_name or "Database"
        base_md = f"# {base_name}\n\n(基础文档尚未生成，以下为富化内容预览)\n\n"

    sections: list[str] = []

    if useKG:
        stats = await graph_service.get_graph_stats()
        sections.append(_format_kg_section(stats, language))

    # Domain docs and spatial sections are placeholders for now (future phases)
    # if useDomainDocs: ...
    # if useSpatial: ...

    separator = "\n\n---\n\n"
    enriched = base_md.rstrip() + separator + "\n\n".join(sections) + "\n"

    # Keep the same friendly name for now to avoid UI churn
    friendly_name = base_name or "Database"
    return friendly_name, enriched


async def preview_enrichment(
    connection_id: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    friendly, md = await generate_enriched_markdown(
        connection_id,
        language=options.get("language", "zh-CN"),
        useKG=bool(options.get("useKG", True)),
        useDomainDocs=bool(options.get("useDomainDocs", False)),
        useSpatial=bool(options.get("useSpatial", False)),
    )
    return {"friendly_name": friendly, "preview_md": md}


async def start_enrichment_job(
    job_id: str,
    connection_id: str,
    options: Dict[str, Any],
) -> Optional[str]:
    """Run enrichment and persist a new version; returns summary_id or None on failure."""
    status_key = f"dbdoc_enrich:{job_id}:status"
    try:
        redis.set(status_key, "running")
        friendly, md = await generate_enriched_markdown(
            connection_id,
            language=options.get("language", "zh-CN"),
            useKG=bool(options.get("useKG", True)),
            useDomainDocs=bool(options.get("useDomainDocs", False)),
            useSpatial=bool(options.get("useSpatial", False)),
        )
        summary_id = generate_id(prefix="S")
        async with get_async_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO project_postgres_summary
                (id, connection_id, friendly_name, summary_md)
                VALUES ($1, $2, $3, $4)
                """,
                summary_id,
                connection_id,
                friendly,
                md,
            )
        redis.set(status_key, "done")
        redis.set(f"dbdoc_enrich:{job_id}:summary_id", summary_id)
        return summary_id
    except Exception as e:
        redis.set(status_key, "error")
        redis.set(f"dbdoc_enrich:{job_id}:error", str(e))
        return None