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


async def _list_project_docs(project_id: str) -> list[dict[str, Any]]:
    """List knowledge docs for a project from S3 (no DB schema change)."""
    from src.utils import get_async_s3_client, get_bucket_name
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    prefix = f"knowledge_docs/{project_id}/"
    docs: dict[str, dict[str, Any]] = {}

    paginator = s3.get_paginator("list_objects_v2")
    async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) if page else []:
            key = obj["Key"]
            parts = key.split("/")
            if len(parts) < 4:
                continue
            _, pid, doc_id, filename = parts[0], parts[1], parts[2], "/".join(parts[3:])
            d = docs.setdefault(doc_id, {"doc_id": doc_id, "filename": filename, "size": 0, "uploaded_at": obj.get("LastModified").isoformat() if obj.get("LastModified") else None})
            d["size"] += int(obj.get("Size", 0))
    return sorted(docs.values(), key=lambda x: x.get("uploaded_at") or "")


async def _read_doc_head(project_id: str, doc_id: str, max_bytes: int = 2000) -> tuple[str, bytes]:
    from src.utils import get_async_s3_client, get_bucket_name
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    prefix = f"knowledge_docs/{project_id}/{doc_id}/"
    # Read the first object under this doc_id (assume single file)
    resp = await s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
    contents = resp.get("Contents") if resp else None
    if not contents:
        return "", b""
    key = contents[0]["Key"]
    head = await s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes-1}")
    data = await head["Body"].read()
    filename = key.split("/")[-1]
    return filename, data


def _format_domain_docs_section(project_id: str, docs: list[dict[str, Any]], language: str = "zh-CN") -> str:
    if not docs:
        return ""
    if language.lower().startswith("zh"):
        title = "## 领域知识文档"
        header = "以下为已上传的专业文档："
    else:
        title = "## Domain Knowledge Documents"
        header = "Uploaded domain documents:"
    lines = [title, header]
    for d in docs:
        lines.append(f"- {d.get('filename')} (id={d.get('doc_id')})")
    return "\n".join(lines) + "\n"


def _format_domain_snippets(snippets: list[tuple[str, str]], language: str = "zh-CN") -> str:
    if not snippets:
        return ""
    title = "## 领域知识片段" if language.lower().startswith("zh") else "## Domain Snippets"
    lines = [title]
    for fname, text in snippets:
        # Keep it short and safe
        text = text.replace("\r\n", "\n").strip()
        if len(text) > 600:
            text = text[:600] + "…"
        lines.append(f"**{fname}**\n\n{text}\n")
    return "\n".join(lines) + "\n"


async def generate_enriched_markdown(
    project_id: str,
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

    if useDomainDocs:
        docs = await _list_project_docs(project_id)
        sections.append(_format_domain_docs_section(project_id, docs, language))
        # Pull small head snippets from up to 3 docs
        snippets: list[tuple[str, str]] = []
        for d in docs[:3]:
            fname, data = await _read_doc_head(project_id, d["doc_id"], max_bytes=2000)
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            # Take first non-empty paragraph
            para = next((p for p in text.split("\n\n") if p.strip()), "")
            if para:
                snippets.append((fname or d.get("filename", "doc"), para))
        if snippets:
            sections.append(_format_domain_snippets(snippets, language))

    # if useSpatial: pass  # reserved for later

    separator = "\n\n---\n\n"
    enriched = base_md.rstrip() + separator + "\n\n".join(sections) + "\n"

    # Keep the same friendly name for now to avoid UI churn
    friendly_name = base_name or "Database"
    return friendly_name, enriched


async def preview_enrichment(
    project_id: str,
    connection_id: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    friendly, md = await generate_enriched_markdown(
        project_id,
        connection_id,
        language=options.get("language", "zh-CN"),
        useKG=bool(options.get("useKG", True)),
        useDomainDocs=bool(options.get("useDomainDocs", False)),
        useSpatial=bool(options.get("useSpatial", False)),
    )
    return {"friendly_name": friendly, "preview_md": md}


async def start_enrichment_job(
    job_id: str,
    project_id: str,
    connection_id: str,
    options: Dict[str, Any],
) -> Optional[str]:
    """Run enrichment and persist a new version; returns summary_id or None on failure."""
    status_key = f"dbdoc_enrich:{job_id}:status"
    try:
        redis.set(status_key, "running")
        friendly, md = await generate_enriched_markdown(
            project_id,
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