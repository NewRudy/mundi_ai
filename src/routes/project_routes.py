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
import math
import json
from fastapi import (
    Request,
    APIRouter,
    HTTPException,
    status,
    Depends,
    BackgroundTasks,
)
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel
from src.dependencies.session import (
    verify_session_required,
    UserContext,
)
from src.dependencies.auth import require_auth
from src.dependencies.base_map import BaseMapProvider, get_base_map_provider
from src.services.dbdoc_enrichment import preview_enrichment, start_enrichment_job
from src.dependencies.database_documenter import generate_id as gen_summary_id
from fastapi import File, UploadFile
from src.utils import get_async_s3_client, get_bucket_name
from typing import List, Optional, Sequence, cast
import logging
from datetime import datetime
from PIL import Image
from redis import Redis
import asyncio
from botocore.exceptions import ClientError

from src.utils import (
    get_bucket_name,
    get_async_s3_client,
    get_openai_client,
)
import io
from opentelemetry import trace
from src.database.models import MundiProject
from src.structures import get_async_db_connection
from src.dependencies.database_documenter import (
    DatabaseDocumenter,
    get_database_documenter,
)
from src.dependencies.chat_completions import (
    ChatArgsProvider,
    get_chat_args_provider,
)
from src.dependencies.postgres_connection import (
    PostgresConnectionManager,
    get_postgres_connection_manager,
    PostgresConnectionURIError,
    PostgresConfigurationError,
)
from src.dependencies.neo4j_connection_manager import (
    get_neo4j_connection_manager,
    verify_neo4j_uri,
    Neo4jConnectionURIError as Neo4jURIError,
    Neo4jConfigurationError as Neo4jConfigError,
)
from src.dependencies.dag import get_project, edit_project
from src.routes.postgres_routes import (
    generate_id,
    get_map_style_internal,
    render_map_internal,
)

# Global semaphore to limit concurrent social image renderings
# This prevents OOM issues when many maps load simultaneously
SOCIAL_RENDER_SEMAPHORE = asyncio.Semaphore(2)  # Max 2 concurrent renders

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

redis = Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    decode_responses=True,
)

project_router = APIRouter()


class MostRecentVersion(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    last_edited: Optional[str] = None


class PostgresConnectionDetails(BaseModel):
    connection_id: str
    table_count: int
    is_documented: bool
    processed_tables_count: Optional[int] = None
    friendly_name: Optional[str] = None
    last_error_text: Optional[str] = None
    last_error_timestamp: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: str
    title: Optional[str] = None
    maps: Optional[List[str]] = None
    created_on: str
    most_recent_version: Optional[MostRecentVersion] = None
    soft_deleted_at: Optional[datetime] = None


class UserProjectsResponse(BaseModel):
    projects: List[ProjectResponse]
    total_pages: int
    total_items: int


@project_router.get(
    "/test", operation_id="test_projects"
)
async def test_projects():
    """Test endpoint without authentication"""
    return {"message": "Project routes are working!"}


@project_router.get(
    "/", response_model=UserProjectsResponse, operation_id="list_user_projects"
)
async def list_user_projects(
    session: UserContext = Depends(verify_session_required),
    page: int = 1,
    limit: int = 12,
    include_deleted: bool = False,
):
    """
    List all projects associated with the authenticated user.
    A project is associated if the user is the owner, an editor, or a viewer.
    """
    try:
        user_id = session.get_user_id()

        # Calculate offset for pagination
        offset = (page - 1) * limit

        async with get_async_db_connection() as conn:
            # Get total count for pagination
            total_items = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM user_mundiai_projects p
                WHERE (
                    p.owner_uuid = $1 OR
                    $2 = ANY(p.editor_uuids) OR
                    $3 = ANY(p.viewer_uuids)
                ) AND ($4 OR p.soft_deleted_at IS NULL)
                """,
                user_id,
                user_id,
                user_id,
                include_deleted,
            )

            # Calculate total pages
            total_pages = (total_items + limit - 1) // limit

            projects_data = await conn.fetch(
                """
                SELECT p.id, p.title, p.maps, p.created_on, p.soft_deleted_at
                FROM user_mundiai_projects p
                WHERE (
                    p.owner_uuid = $1 OR
                    $2 = ANY(p.editor_uuids) OR
                    $3 = ANY(p.viewer_uuids)
                ) AND ($4 OR p.soft_deleted_at IS NULL)
                ORDER BY p.created_on DESC
                LIMIT $5 OFFSET $6
                """,
                user_id,
                user_id,
                user_id,
                include_deleted,
                limit,
                offset,
            )

            projects_response = []
            for project_data in projects_data:
                created_on_str = (
                    project_data["created_on"].isoformat()
                    if isinstance(project_data["created_on"], datetime)
                    else str(project_data["created_on"])
                )
                most_recent_map_details = None

                if project_data["maps"] and len(project_data["maps"]) > 0:
                    most_recent_map_id = project_data["maps"][-1]

                    map_details = await conn.fetchrow(
                        """
                        SELECT title, description, last_edited
                        FROM user_mundiai_maps
                        WHERE id = $1 AND soft_deleted_at IS NULL
                        """,
                        most_recent_map_id,
                    )
                    if map_details:
                        last_edited_str = (
                            map_details["last_edited"].isoformat()
                            if isinstance(map_details["last_edited"], datetime)
                            else str(map_details["last_edited"])
                        )
                        most_recent_map_details = MostRecentVersion(
                            title=map_details["title"],
                            description=map_details["description"],
                            last_edited=last_edited_str,
                        )

                projects_response.append(
                    ProjectResponse(
                        id=project_data["id"],
                        title=project_data["title"],
                        maps=project_data["maps"],
                        created_on=created_on_str,
                        most_recent_version=most_recent_map_details,
                        soft_deleted_at=project_data["soft_deleted_at"],
                    )
                )

        return UserProjectsResponse(
            projects=projects_response,
            total_pages=total_pages,
            total_items=total_items,
        )

    except Exception as e:
        import traceback
        logger.error(f"Error in list_user_projects: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}",
        )


@project_router.get(
    "/{project_id}/sources",
    response_model=List[PostgresConnectionDetails],
    operation_id="list_project_sources",
)
async def list_project_sources(
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
    connection_manager: PostgresConnectionManager = Depends(
        get_postgres_connection_manager
    ),
):
    user_id = session.get_user_id()
    if str(project.owner_uuid) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can view sources",
        )
    async with get_async_db_connection() as conn:
        postgres_connections: List[PostgresConnectionDetails] = []

        postgres_conn_results = await conn.fetch(
            """
            SELECT id, connection_uri, connection_name
            FROM project_postgres_connections
            WHERE project_id = $1 AND soft_deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            project.id,
        )

        for postgres_conn_result in postgres_conn_results:
            connection_id = postgres_conn_result["id"]

            # Get AI-generated friendly name and table_count
            summary_result = await conn.fetchrow(
                """
                SELECT friendly_name, table_count
                FROM project_postgres_summary
                WHERE connection_id = $1
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                connection_id,
            )

            # Prefer stored summary values; otherwise fall back to progress from Redis
            if summary_result:
                friendly_name: str = summary_result["friendly_name"]
                table_count: int = summary_result["table_count"] or 0
                processed_tables_count: Optional[int] = None
            else:
                friendly_name = postgres_conn_result["connection_name"] or "Loading..."
                table_count = int(
                    redis.get(f"dbdocumenter:{connection_id}:total_tables") or 0
                )
                processed_tables_count = int(
                    redis.get(f"dbdocumenter:{connection_id}:processed_tables") or 0
                )

            # Get error details recorded for this connection attempt
            connection_details = await connection_manager.get_connection(connection_id)

            postgres_connections.append(
                PostgresConnectionDetails(
                    connection_id=connection_id,
                    table_count=table_count,
                    processed_tables_count=processed_tables_count,
                    friendly_name=friendly_name,
                    is_documented=summary_result is not None,
                    last_error_text=connection_details["last_error_text"],
                    last_error_timestamp=connection_details["last_error_timestamp"],
                )
            )

        return postgres_connections


@project_router.get(
    "/{project_id}", response_model=ProjectResponse, operation_id="get_project"
)
async def get_project_route(
    project: MundiProject = Depends(get_project),
):
    async with get_async_db_connection() as conn:
        created_on_str = project.created_on.isoformat()
        most_recent_map_details = None

        maps_value = cast(Sequence[str] | None, project.maps)
        if maps_value and len(maps_value) > 0:
            most_recent_map_id = maps_value[-1]
            map_details = await conn.fetchrow(
                """
                SELECT title, description, last_edited
                FROM user_mundiai_maps
                WHERE id = $1 AND soft_deleted_at IS NULL
                """,
                most_recent_map_id,
            )
            if map_details:
                last_edited_str = (
                    map_details["last_edited"].isoformat()
                    if isinstance(map_details["last_edited"], datetime)
                    else str(map_details["last_edited"])
                )
                most_recent_map_details = MostRecentVersion(
                    title=map_details["title"],
                    description=map_details["description"],
                    last_edited=last_edited_str,
                )

        return ProjectResponse(
            id=project.id,
            title=project.title,
            maps=project.maps,
            created_on=created_on_str,
            most_recent_version=most_recent_map_details,
        )


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None


class ProjectUpdateResponse(BaseModel):
    updated: bool


@project_router.post(
    "/{project_id}", response_model=ProjectUpdateResponse, operation_id="update_project"
)
async def update_project(
    update_data: ProjectUpdateRequest,
    project: MundiProject = Depends(edit_project),
):
    async with get_async_db_connection() as conn:
        updated = False

        if update_data.title is not None:
            await conn.execute(
                """
                UPDATE user_mundiai_projects
                SET title = $1
                WHERE id = $2
                """,
                update_data.title,
                project.id,
            )
            updated = True

        return ProjectUpdateResponse(updated=updated)


class PostgresConnectionRequest(BaseModel):
    connection_uri: str
    connection_name: Optional[str] = None


class PostgresConnectionResponse(BaseModel):
    success: bool
    message: str


class PostgresCreateConnectionResponse(BaseModel):
    message: str
    connection_id: str


class DatabaseDocumentationResponse(BaseModel):
    connection_id: str
    connection_name: str
    friendly_name: Optional[str] = None
    documentation: Optional[str] = None
    generated_at: Optional[datetime] = None


# ---- Neo4j external connections ----
class Neo4jConnectionRequest(BaseModel):
    connection_uri: str
    connection_name: Optional[str] = None


class Neo4jCreateConnectionResponse(BaseModel):
    message: str
    connection_id: str


class Neo4jConnectionListItem(BaseModel):
    connection_id: str
    connection_name: Optional[str] = None
    last_error_text: Optional[str] = None
    last_error_timestamp: Optional[datetime] = None


@project_router.post(
    "/{project_id}/postgis-connections",
    response_model=PostgresCreateConnectionResponse,
    operation_id="add_postgis_connection",
)
async def add_postgis_connection(
    connection_data: PostgresConnectionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
    database_documenter: DatabaseDocumenter = Depends(get_database_documenter),
    connection_manager: PostgresConnectionManager = Depends(
        get_postgres_connection_manager
    ),
    chat_args_provider: ChatArgsProvider = Depends(get_chat_args_provider),
):
    """
    Add a PostgreSQL connection URI to a project.
    Only the project owner or editors can add connections.
    """
    user_id = session.get_user_id()

    async with get_async_db_connection() as conn:
        # Validate the connection URI format and accessibility
        connection_uri = connection_data.connection_uri.strip()

        # Handle demo database
        if connection_uri == "DEMO":
            demo_uri = os.environ.get("DEMO_POSTGIS_URI")
            if not demo_uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Demo database is not available",
                )
            connection_uri = demo_uri

        try:
            processed_uri, was_rewritten = connection_manager.verify_postgresql_uri(
                connection_uri
            )
            # Use the processed URI (which may have been rewritten for Docker)
            connection_uri = processed_uri
        except PostgresConnectionURIError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.message,
            )
        except PostgresConfigurationError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Generate new connection ID
        connection_id = generate_id(prefix="C")

        # Insert the new connection
        await conn.execute(
            """
            INSERT INTO project_postgres_connections
            (id, project_id, user_id, connection_uri, connection_name)
            VALUES ($1, $2, $3, $4, $5)
            """,
            connection_id,
            project.id,
            user_id,
            connection_uri,
            connection_data.connection_name,
        )

        # Start background task to generate database documentation
        background_tasks.add_task(
            database_documenter.generate_documentation,
            connection_id,
            connection_uri,
            connection_data.connection_name or "Database",
            connection_manager,
            get_openai_client(request),
            chat_args_provider,
            user_id,
        )

        return PostgresCreateConnectionResponse(
            message="PostgreSQL connection added successfully",
            connection_id=connection_id,
        )


@project_router.delete(
    "/{project_id}/postgis-connections/{connection_id}",
    response_model=PostgresConnectionResponse,
    operation_id="soft_delete_postgis_connection",
)
async def soft_delete_postgis_connection(
    connection_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    """
    Soft delete a PostgreSQL connection from a project.
    Only the project owner or editors can delete connections.
    """
    async with get_async_db_connection() as conn:
        # Check if the connection exists and belongs to this project
        connection = await conn.fetchrow(
            """
            SELECT id, soft_deleted_at
            FROM project_postgres_connections
            WHERE id = $1 AND project_id = $2
            """,
            connection_id,
            project.id,
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PostgreSQL connection {connection_id} not found in project {project.id}.",
            )

        if connection["soft_deleted_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="PostgreSQL connection is already deleted.",
            )

        # Soft delete the connection by setting the timestamp
        await conn.execute(
            """
            UPDATE project_postgres_connections
            SET soft_deleted_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND project_id = $2
            """,
            connection_id,
            project.id,
        )

        return PostgresConnectionResponse(
            success=True, message="PostgreSQL connection deleted successfully"
        )


@project_router.get(
    "/{project_id}/postgis-connections/{connection_id}/documentation",
    response_model=DatabaseDocumentationResponse,
    operation_id="get_database_documentation",
)
async def get_database_documentation(
    connection_id: str,
    project: MundiProject = Depends(get_project),
):
    async with get_async_db_connection() as conn:
        # Get the database connection and documentation (most recent summary)
        connection = await conn.fetchrow(
            """
            SELECT
                ppc.id,
                ppc.connection_name,
                pps.friendly_name,
                pps.summary_md,
                pps.generated_at
            FROM project_postgres_connections ppc
            LEFT JOIN project_postgres_summary pps ON ppc.id = pps.connection_id
            WHERE ppc.id = $1 AND ppc.project_id = $2 AND ppc.soft_deleted_at IS NULL
            ORDER BY pps.generated_at DESC
            LIMIT 1
            """,
            connection_id,
            project.id,
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database connection {connection_id} not found.",
            )

        return DatabaseDocumentationResponse(
            connection_id=connection["id"],
            connection_name=connection["connection_name"] or "Loading...",
            friendly_name=connection["friendly_name"],
            documentation=connection["summary_md"],
            generated_at=connection["generated_at"],
        )


@project_router.post(
    "/{project_id}/postgis-connections/{connection_id}/regenerate-documentation",
    response_model=PostgresConnectionResponse,
    operation_id="regenerate_database_documentation",
)
async def regenerate_database_documentation(
    connection_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    project: MundiProject = Depends(get_project),
    database_documenter: DatabaseDocumenter = Depends(get_database_documenter),
    connection_manager: PostgresConnectionManager = Depends(
        get_postgres_connection_manager
    ),
    chat_args_provider: ChatArgsProvider = Depends(get_chat_args_provider),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        # Get the database connection
        connection = await conn.fetchrow(
            """
            SELECT id, connection_uri, connection_name
            FROM project_postgres_connections
            WHERE id = $1 AND project_id = $2 AND soft_deleted_at IS NULL
            """,
            connection_id,
            project.id,
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database connection {connection_id} not found.",
            )

        # Start background task to regenerate database documentation
        user_id = session.get_user_id()
        background_tasks.add_task(
            database_documenter.generate_documentation,
            connection_id,
            connection["connection_uri"],
            connection["connection_name"] or "Database",
            connection_manager,
            get_openai_client(request),
            chat_args_provider,
            user_id,
        )

        return PostgresConnectionResponse(
            success=True, message="Database documentation regeneration started"
        )


class SocialImageCacheBustedError(Exception):
    pass


@project_router.get("/{project_id}/social.webp", response_class=Response)
async def get_project_social_preview(
    project: MundiProject = Depends(get_project),
    base_map_provider: BaseMapProvider = Depends(get_base_map_provider),
):
    latest_map_id = project.maps[-1]

    # If map has no layers, stream the provider's default basemap preview directly
    async with get_async_db_connection() as conn:
        map_row = await conn.fetchrow(
            """
            SELECT layers
            FROM user_mundiai_maps
            WHERE id = $1 AND soft_deleted_at IS NULL
            """,
            latest_map_id,
        )

        layer_ids = (map_row["layers"] or []) if map_row else []
    if not layer_ids:
        with open(base_map_provider.get_default_preview_path(), "rb") as f:
            return Response(
                content=f.read(),
                media_type="image/webp",
                headers={
                    "Content-Type": "image/webp",
                    "Cache-Control": "max-age=900, public",
                },
            )

    # S3 configuration - key by map_id instead of project_id
    bucket_name = get_bucket_name()
    s3_key = f"social_previews/map_{latest_map_id}.webp"

    # Try to get the image from S3
    try:
        s3 = await get_async_s3_client()
        s3_response = await s3.get_object(Bucket=bucket_name, Key=s3_key)
        image_data = await s3_response["Body"].read()

    except ClientError:
        # Re-render with semaphore to limit concurrent renders
        async with SOCIAL_RENDER_SEMAPHORE:
            print(
                f"Rendering social image for map {latest_map_id} (semaphore acquired)"
            )

            style_json = await get_map_style_internal(
                latest_map_id,
                base_map_provider,
                only_show_inline_sources=True,
            )

            render_response, _ = await render_map_internal(
                map_id=latest_map_id,
                bbox=None,
                width=1200,
                height=630,
                renderer="mbgl",
                bgcolor="#ffffff",
                style_json=style_json,
            )

            img = Image.open(io.BytesIO(render_response.body))
            webp_buffer = io.BytesIO()
            img.save(webp_buffer, format="WEBP", quality=80, lossless=False)

            s3 = await get_async_s3_client()
            await s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=webp_buffer.getvalue(),
                ContentType="image/webp",
            )

            image_data = webp_buffer.getvalue()

    return Response(
        content=image_data,
        media_type="image/webp",
        headers={
            "Content-Type": "image/webp",
            "Cache-Control": "max-age=900, public",
        },
    )


@project_router.delete(
    "/{project_id}",
    operation_id="delete_project",
    summary="Delete a map",
    description="Marks a map project as deleted (uses soft delete).",
)
async def delete_project(
    project: MundiProject = Depends(edit_project),
):
    """
    Soft deletes a map project. This project will no longer be listed in the user's
    list of projects, but will appear in recently deleted projects.
    """
    async with get_async_db_connection() as conn:
        # Soft delete the project
        updated_project = await conn.fetchrow(
            """
            UPDATE user_mundiai_projects
            SET soft_deleted_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
            """,
            project.id,
        )

        if not updated_project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project",
            )

        return {
            "message": "Project successfully deleted",
            "project_id": project.id,
        }


class DemoPostgisConfigResponse(BaseModel):
    available: bool
    description: str = ""


@project_router.get(
    "/config/demo-postgis-available", response_model=DemoPostgisConfigResponse
)
async def get_demo_postgis_config():
    demo_uri = os.environ.get("DEMO_POSTGIS_URI")
    demo_description = os.environ.get("DEMO_POSTGIS_DESCRIPTION", "")

    if not demo_uri:
        return DemoPostgisConfigResponse(available=False)

    return DemoPostgisConfigResponse(available=True, description=demo_description)


@project_router.post(
    "/{project_id}/neo4j-connections",
    response_model=Neo4jCreateConnectionResponse,
    operation_id="add_neo4j_connection",
)
async def add_neo4j_connection(
    connection_data: Neo4jConnectionRequest,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    user_id = session.get_user_id()

    # Validate and normalize URI per policy
    try:
        processed_uri, _ = verify_neo4j_uri(connection_data.connection_uri)
    except Neo4jURIError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Neo4jConfigError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    connection_id = generate_id(prefix="G")
    async with get_async_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO project_neo4j_connections (id, project_id, user_id, connection_uri, connection_name)
            VALUES ($1, $2, $3, $4, $5)
            """,
            connection_id,
            project.id,
            user_id,
            processed_uri,
            connection_data.connection_name,
        )

    # Optionally attempt connectivity to populate error state immediately
    try:
        manager = get_neo4j_connection_manager()
        from contextlib import AsyncExitStack
        async with AsyncExitStack() as stack:
            session_ctx = manager.session_for_connection(connection_id)
            session = await stack.enter_async_context(session_ctx)
            await session.run("RETURN 1 AS ok")
    except Exception:
        # Error is already recorded by manager; do not fail creation
        pass

    return Neo4jCreateConnectionResponse(message="Neo4j connection added successfully", connection_id=connection_id)


@project_router.get(
    "/{project_id}/neo4j-connections",
    response_model=List[Neo4jConnectionListItem],
    operation_id="list_neo4j_connections",
)
async def list_neo4j_connections(
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    if str(project.owner_uuid) != session.get_user_id():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can view connections")

    async with get_async_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, connection_name, last_error_text, last_error_timestamp
            FROM project_neo4j_connections
            WHERE project_id = $1 AND soft_deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            project.id,
        )
    return [
        Neo4jConnectionListItem(
            connection_id=r["id"],
            connection_name=r["connection_name"],
            last_error_text=r["last_error_text"],
            last_error_timestamp=r["last_error_timestamp"],
        )
        for r in rows
    ]


@project_router.delete(
    "/{project_id}/neo4j-connections/{connection_id}",
    response_model=PostgresConnectionResponse,
    operation_id="soft_delete_neo4j_connection",
)
async def soft_delete_neo4j_connection(
    connection_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        connection = await conn.fetchrow(
            """
            SELECT id, soft_deleted_at
            FROM project_neo4j_connections
            WHERE id = $1 AND project_id = $2
            """,
            connection_id,
            project.id,
        )
        if not connection:
            raise HTTPException(status_code=404, detail="Neo4j connection not found")
        if connection["soft_deleted_at"] is not None:
            raise HTTPException(status_code=409, detail="Neo4j connection is already deleted")
        await conn.execute(
            """
            UPDATE project_neo4j_connections
            SET soft_deleted_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND project_id = $2
            """,
            connection_id,
            project.id,
        )
    return PostgresConnectionResponse(success=True, message="Neo4j connection deleted successfully")


@project_router.get(
    "/{project_id}/neo4j-connections/{connection_id}/stats",
    operation_id="get_neo4j_connection_stats",
)
async def get_neo4j_connection_stats(
    connection_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    # Validate connection belongs to project
    async with get_async_db_connection() as conn:
        ok = await conn.fetchval(
            """
            SELECT 1 FROM project_neo4j_connections
            WHERE id = $1 AND project_id = $2 AND soft_deleted_at IS NULL
            """,
            connection_id,
            project.id,
        )
    if not ok:
        raise HTTPException(status_code=404, detail="Neo4j connection not found")

    # Delegate to graph service
    return await graph_service.get_graph_stats(connection_id=connection_id)


@project_router.get("/embed/v1/{project_id}.html", response_class=HTMLResponse)
async def get_project_embed(
    project_id: str,
    request: Request,
    base_map_provider: BaseMapProvider = Depends(get_base_map_provider),
    allowed_origins: List[str] = Depends(require_auth),
):
    async with get_async_db_connection() as conn:
        project_data = await conn.fetchrow(
            """
            SELECT id, maps, title
            FROM user_mundiai_projects
            WHERE id = $1 AND soft_deleted_at IS NULL
            """,
            project_id,
        )

        if not project_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        maps = project_data["maps"]
        project_title = project_data["title"] or "Untitled Map"
        if not maps or len(maps) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project has no maps"
            )

        latest_map_id = maps[-1]

        # Get layers for the latest map to calculate bounds
        map_result = await conn.fetchrow(
            """
            SELECT layers
            FROM user_mundiai_maps
            WHERE id = $1 AND soft_deleted_at IS NULL
            """,
            latest_map_id,
        )

        if not map_result or not map_result["layers"]:
            all_layers = []
        else:
            all_layers = await conn.fetch(
                """
                SELECT bounds
                FROM map_layers
                WHERE layer_id = ANY($1)
                """,
                map_result["layers"],
            )

    # Calculate bounds from all layers
    bounds_list = [layer["bounds"] for layer in all_layers if layer.get("bounds")]
    center = [0, 0]
    zoom = 2

    if bounds_list:
        xs = [b[0] for b in bounds_list] + [b[2] for b in bounds_list]
        ys = [b[1] for b in bounds_list] + [b[3] for b in bounds_list]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Apply 25% padding
        ZOOM_PADDING_PCT = 25
        pad_x = (max_x - min_x) * ZOOM_PADDING_PCT / 100
        pad_y = (max_y - min_y) * ZOOM_PADDING_PCT / 100
        min_x -= pad_x
        max_x += pad_x
        min_y -= pad_y
        max_y += pad_y

        center = [(min_x + max_x) / 2, (min_y + max_y) / 2]

        # Calculate zoom to fit both longitude and latitude spans
        lon_span = max_x - min_x
        lat_span = max_y - min_y
        zoom_lon = math.log2(360.0 / lon_span) if lon_span else None
        zoom_lat = math.log2(180.0 / lat_span) if lat_span else None

        zoom = (
            min(zoom_lon, zoom_lat) if zoom_lon and zoom_lat else zoom_lon or zoom_lat
        )
        if zoom is None or zoom <= 0:
            zoom = 2
        else:
            zoom = max(0.5, min(zoom, 18))

    # Get the style JSON directly instead of making client request it
    from src.routes.postgres_routes import get_map_style_internal

    style_json = await get_map_style_internal(
        latest_map_id, base_map_provider, only_show_inline_sources=True
    )

    # Override the calculated center and zoom in the style JSON
    if bounds_list:
        style_json["center"] = center
        style_json["zoom"] = zoom

    style_json_str = json.dumps(style_json)

    base_map_csp = base_map_provider.get_csp_policies()
    base_csp = {
        "frame-ancestors": ["'self'"] + allowed_origins,
        "script-src": ["'self'", "'unsafe-inline'", "https://unpkg.com"],
        "worker-src": ["'self'", "blob:"],
        "style-src": ["'self'", "'unsafe-inline'", "https://unpkg.com"],
        "connect-src": ["'self'", "https://unpkg.com"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'", "https://unpkg.com"],
    }

    for directive, sources in base_map_csp.items():
        if directive in base_csp:
            base_csp[directive].extend(sources)
        else:
            base_csp[directive] = sources

    csp_parts = []
    for directive, sources in base_csp.items():
        sources_str = " ".join(sources)
        csp_parts.append(f"{directive} {sources_str}")
    csp_header = "; ".join(csp_parts)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mundi Map Embed</title>
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
    <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
    <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
        #title-overlay {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: #1e2939;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
            max-width: calc(100% - 40px);
            box-sizing: border-box;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="title-overlay">{project_title}</div>
    <script>
        const map = new maplibregl.Map({{
            container: 'map',
            attributionControl: {{
                compact: false
            }},
            style: {style_json_str}
        }});

        map.addControl(new maplibregl.NavigationControl());
    </script>
</body>
</html>"""

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": csp_header,
        "X-Frame-Options": "SAMEORIGIN",
    }

    return HTMLResponse(content=html_content, headers=headers)


class EnrichOptions(BaseModel):
    useKG: bool | None = True
    useDomainDocs: bool | None = False
    useSpatial: bool | None = False
    language: str | None = "zh-CN"


class EnrichStartResponse(BaseModel):
    job_id: str
    message: str


class EnrichStatusResponse(BaseModel):
    status: str
    summary_id: str | None = None
    error: str | None = None


@project_router.get(
    "/{project_id}/postgis-connections/{connection_id}/docs/enrich/preview",
    operation_id="preview_enriched_database_documentation",
)
async def preview_enriched_database_documentation(
    connection_id: str,
    options: EnrichOptions = Depends(),
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    # Validate connection exists in project
    async with get_async_db_connection() as conn:
        exists = await conn.fetchval(
            """
            SELECT 1 FROM project_postgres_connections
            WHERE id = $1 AND project_id = $2 AND soft_deleted_at IS NULL
            """,
            connection_id,
            project.id,
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found")

    result = await preview_enrichment(
        project.id,
        connection_id,
        {
            "useKG": bool(options.useKG),
            "useDomainDocs": bool(options.useDomainDocs),
            "useSpatial": bool(options.useSpatial),
            "language": options.language or "zh-CN",
        },
    )
    return result


@project_router.post(
    "/{project_id}/postgis-connections/{connection_id}/docs/enrich/start",
    response_model=EnrichStartResponse,
    operation_id="start_enriched_database_documentation",
)
async def start_enriched_database_documentation(
    connection_id: str,
    options: EnrichOptions,
    background_tasks: BackgroundTasks,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    # Validate connection exists in project
    async with get_async_db_connection() as conn:
        exists = await conn.fetchval(
            """
            SELECT 1 FROM project_postgres_connections
            WHERE id = $1 AND project_id = $2 AND soft_deleted_at IS NULL
            """,
            connection_id,
            project.id,
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found")

    job_id = gen_summary_id(prefix="J")
    # Fire-and-forget background job
    background_tasks.add_task(
        start_enrichment_job,
        job_id,
        project.id,
        connection_id,
        {
            "useKG": bool(options.useKG),
            "useDomainDocs": bool(options.useDomainDocs),
            "useSpatial": bool(options.useSpatial),
            "language": options.language or "zh-CN",
        },
    )
    return EnrichStartResponse(job_id=job_id, message="Enrichment started")


@project_router.get(
    "/{project_id}/postgis-connections/{connection_id}/docs/enrich/status",
    response_model=EnrichStatusResponse,
    operation_id="get_enrichment_status",
)
async def get_enrichment_status(
    connection_id: str,
    job_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    # Validate the connection belongs to the project
    async with get_async_db_connection() as conn:
        exists = await conn.fetchval(
            """
            SELECT 1 FROM project_postgres_connections
            WHERE id = $1 AND project_id = $2 AND soft_deleted_at IS NULL
            """,
            connection_id,
            project.id,
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found")

    # Read status from Redis
    from redis import Redis
    r = Redis(host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"]), decode_responses=True)

    status_val = r.get(f"dbdoc_enrich:{job_id}:status") or "unknown"
    if status_val == "done":
        summary_id = r.get(f"dbdoc_enrich:{job_id}:summary_id")
        return EnrichStatusResponse(status=status_val, summary_id=summary_id)
    elif status_val == "error":
        error = r.get(f"dbdoc_enrich:{job_id}:error")
        return EnrichStatusResponse(status=status_val, error=error)
    else:
        return EnrichStatusResponse(status=status_val)


class KnowledgeDocItem(BaseModel):
    doc_id: str
    filename: str
    size: int
    uploaded_at: str | None = None


class KnowledgeDocsResponse(BaseModel):
    items: list[KnowledgeDocItem]


@project_router.get(
    "/{project_id}/knowledge/docs",
    response_model=KnowledgeDocsResponse,
    operation_id="list_knowledge_docs",
)
async def list_knowledge_docs(
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    prefix = f"knowledge_docs/{project.id}/"
    items: dict[str, KnowledgeDocItem] = {}

    paginator = s3.get_paginator("list_objects_v2")
    async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) if page else []:
            key = obj["Key"]
            parts = key.split("/")
            if len(parts) < 4:
                continue
            _, pid, doc_id, filename = parts[0], parts[1], parts[2], "/".join(parts[3:])
            existing = items.get(doc_id)
            if not existing:
                items[doc_id] = KnowledgeDocItem(
                    doc_id=doc_id,
                    filename=filename,
                    size=int(obj.get("Size", 0)),
                    uploaded_at=obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
                )
            else:
                existing.size += int(obj.get("Size", 0))
                if obj.get("LastModified"):
                    existing.uploaded_at = obj.get("LastModified").isoformat()

    return KnowledgeDocsResponse(items=sorted(items.values(), key=lambda x: x.uploaded_at or ""))


@project_router.put(
    "/{project_id}/knowledge/docs/{doc_id}",
    response_model=KnowledgeDocItem,
    operation_id="replace_knowledge_doc",
)
async def replace_knowledge_doc(
    doc_id: str,
    file: UploadFile = File(...),
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    # Delete old files under the doc prefix, then upload new one
    prefix = f"knowledge_docs/{project.id}/{doc_id}/"
    resp = await s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents") if resp else None
    if contents:
        await s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": o["Key"]} for o in contents]})
    key = f"{prefix}{file.filename}"
    content = await file.read()
    await s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType=file.content_type or "application/octet-stream")
    head = await s3.head_object(Bucket=bucket, Key=key)
    size = int(head.get("ContentLength", len(content)))
    uploaded_at = head.get("LastModified").isoformat() if head.get("LastModified") else None
    return KnowledgeDocItem(doc_id=doc_id, filename=file.filename, size=size, uploaded_at=uploaded_at)


@project_router.post(
    "/{project_id}/knowledge/docs",
    response_model=KnowledgeDocItem,
    operation_id="upload_knowledge_doc",
)
async def upload_knowledge_doc(
    file: UploadFile = File(...),
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    # Generate a doc id and upload to S3 under knowledge_docs/{project_id}/{doc_id}/{filename}
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    from src.routes.postgres_routes import generate_id
    doc_id = generate_id(prefix="D")
    key = f"knowledge_docs/{project.id}/{doc_id}/{file.filename}"

    content = await file.read()
    await s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType=file.content_type or "application/octet-stream")

    head = await s3.head_object(Bucket=bucket, Key=key)
    size = int(head.get("ContentLength", len(content)))
    uploaded_at = head.get("LastModified").isoformat() if head.get("LastModified") else None

    return KnowledgeDocItem(doc_id=doc_id, filename=file.filename, size=size, uploaded_at=uploaded_at)


@project_router.delete(
    "/{project_id}/knowledge/docs/{doc_id}",
    operation_id="delete_knowledge_doc",
)
async def delete_knowledge_doc(
    doc_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    s3 = await get_async_s3_client()
    bucket = get_bucket_name()
    prefix = f"knowledge_docs/{project.id}/{doc_id}/"
    # List and delete all objects under the doc prefix
    to_delete = []
    resp = await s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents") if resp else None
    for obj in contents or []:
        to_delete.append({"Key": obj["Key"]})
    if to_delete:
        # S3 bulk delete requires a specific structure
        await s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
    return {"message": "Deleted"}


# ---- Versions API (list, get, rollback) ----
class DocVersionItem(BaseModel):
    summary_id: str
    friendly_name: str
    generated_at: str | None = None
    size: int | None = None


class DocVersionsResponse(BaseModel):
    items: list[DocVersionItem]


class DocVersionContent(BaseModel):
    summary_id: str
    friendly_name: str
    generated_at: str | None = None
    content: str


@project_router.get(
    "/{project_id}/postgis-connections/{connection_id}/docs/versions",
    response_model=DocVersionsResponse,
    operation_id="list_doc_versions",
)
async def list_doc_versions(
    connection_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, friendly_name, summary_md, generated_at
            FROM project_postgres_summary
            WHERE connection_id = $1
            ORDER BY generated_at DESC NULLS LAST
            """,
            connection_id,
        )
    items = []
    for r in rows:
        content = r["summary_md"] or ""
        items.append(
            DocVersionItem(
                summary_id=r["id"],
                friendly_name=r["friendly_name"] or "",
                generated_at=r["generated_at"].isoformat() if r.get("generated_at") else None,
                size=len(content),
            )
        )
    return DocVersionsResponse(items=items)


@project_router.get(
    "/{project_id}/postgis-connections/{connection_id}/docs/versions/{summary_id}",
    response_model=DocVersionContent,
    operation_id="get_doc_version",
)
async def get_doc_version(
    connection_id: str,
    summary_id: str,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        r = await conn.fetchrow(
            """
            SELECT id, friendly_name, summary_md, generated_at
            FROM project_postgres_summary
            WHERE connection_id = $1 AND id = $2
            """,
            connection_id,
            summary_id,
        )
        if not r:
            raise HTTPException(status_code=404, detail="summary not found")
    return DocVersionContent(
        summary_id=r["id"],
        friendly_name=r["friendly_name"] or "",
        generated_at=r["generated_at"].isoformat() if r.get("generated_at") else None,
        content=r["summary_md"] or "",
    )


class RollbackRequest(BaseModel):
    summary_id: str


@project_router.post(
    "/{project_id}/postgis-connections/{connection_id}/docs/rollback",
    operation_id="rollback_doc_version",
)
async def rollback_doc_version(
    connection_id: str,
    req: RollbackRequest,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        r = await conn.fetchrow(
            "SELECT friendly_name, summary_md FROM project_postgres_summary WHERE connection_id=$1 AND id=$2",
            connection_id,
            req.summary_id,
        )
        if not r:
            raise HTTPException(status_code=404, detail="summary not found")
        new_id = gen_summary_id(prefix="S")
        await conn.execute(
            """
            INSERT INTO project_postgres_summary (id, connection_id, friendly_name, summary_md)
            VALUES ($1,$2,$3,$4)
            """,
            new_id,
            connection_id,
            r["friendly_name"],
            r["summary_md"],
        )
    return {"message": "rolled back", "summary_id": new_id}


# ---- Simple block-level ops (by heading) ----
class DeleteByHeadingRequest(BaseModel):
    heading: str


class ReplaceByHeadingRequest(BaseModel):
    heading: str
    new_content: str


def _delete_section_by_heading(md: str, heading: str) -> str:
    import re
    lines = md.splitlines()
    # Find the line with specified heading (e.g., '## Title') ignoring extra spaces
    target_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,6}\s+" + re.escape(heading.strip()) + r"\s*$", line):
            target_idx = i
            break
    if target_idx == -1:
        return md
    # Find next heading line after target
    end_idx = len(lines)
    for j in range(target_idx + 1, len(lines)):
        if re.match(r"^\s*#{1,6}\s+", lines[j]):
            end_idx = j
            break
    new_lines = lines[:target_idx] + lines[end_idx:]
    return "\n".join(new_lines)


def _replace_section_by_heading(md: str, heading: str, new_content: str) -> str:
    import re
    lines = md.splitlines()
    target_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,6}\s+" + re.escape(heading.strip()) + r"\s*$", line):
            target_idx = i
            break
    if target_idx == -1:
        # If heading not found, append as a new section at end
        return md.rstrip() + f"\n\n## {heading}\n\n{new_content}\n"
    end_idx = len(lines)
    for j in range(target_idx + 1, len(lines)):
        if re.match(r"^\s*#{1,6}\s+", lines[j]):
            end_idx = j
            break
    # Keep heading line, replace its body
    new_lines = lines[: target_idx + 1] + [""] + new_content.splitlines() + [""] + lines[end_idx:]
    return "\n".join(new_lines)


@project_router.post(
    "/{project_id}/postgis-connections/{connection_id}/docs/ops/delete_by_heading",
    operation_id="doc_op_delete_by_heading",
)
async def doc_op_delete_by_heading(
    connection_id: str,
    req: DeleteByHeadingRequest,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        cur = await conn.fetchrow(
            """
            SELECT id, friendly_name, summary_md
            FROM project_postgres_summary
            WHERE connection_id = $1
            ORDER BY generated_at DESC NULLS LAST
            LIMIT 1
            """,
            connection_id,
        )
        if not cur:
            raise HTTPException(status_code=404, detail="no current summary")
        updated = _delete_section_by_heading(cur["summary_md"] or "", req.heading)
        new_id = gen_summary_id(prefix="S")
        await conn.execute(
            "INSERT INTO project_postgres_summary (id, connection_id, friendly_name, summary_md) VALUES ($1,$2,$3,$4)",
            new_id,
            connection_id,
            cur["friendly_name"] or "",
            updated,
        )
    return {"message": "deleted", "summary_id": new_id}


@project_router.post(
    "/{project_id}/postgis-connections/{connection_id}/docs/ops/replace_by_heading",
    operation_id="doc_op_replace_by_heading",
)
async def doc_op_replace_by_heading(
    connection_id: str,
    req: ReplaceByHeadingRequest,
    project: MundiProject = Depends(get_project),
    session: UserContext = Depends(verify_session_required),
):
    async with get_async_db_connection() as conn:
        cur = await conn.fetchrow(
            """
            SELECT id, friendly_name, summary_md
            FROM project_postgres_summary
            WHERE connection_id = $1
            ORDER BY generated_at DESC NULLS LAST
            LIMIT 1
            """,
            connection_id,
        )
        if not cur:
            raise HTTPException(status_code=404, detail="no current summary")
        updated = _replace_section_by_heading(cur["summary_md"] or "", req.heading, req.new_content)
        new_id = gen_summary_id(prefix="S")
        await conn.execute(
            "INSERT INTO project_postgres_summary (id, connection_id, friendly_name, summary_md) VALUES ($1,$2,$3,$4)",
            new_id,
            connection_id,
            cur["friendly_name"] or "",
            updated,
        )
    return {"message": "replaced", "summary_id": new_id}
