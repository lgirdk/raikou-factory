"""Docker Orchestration API code."""

from typing import Any, ClassVar

from docker_orchestrator import (
    VolumeMounts,
    docker_compose_run,
    docker_context_ls,
    docker_inspect_containers,
    update_file_on_remote_container,
    update_json_file_on_remote_container,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

APP = FastAPI()

# List to store cached Docker contexts
_DOCKER_CONTEXTS: dict[str, str]


class UpdateFileRequest(BaseModel):
    """Pydantic model for updating a file inside a Docker container.

    :param container_id: The ID of the Docker container.
    :type container_id: str
    :param file_path: The path to the file inside the container.
    :type file_path: str
    :param file_content: The new content to write to the file.
    :type file_content: str
    :param context: The Docker context to use for the Docker command.
    :type context: str
    """

    container_id: str
    file_path: str
    file_content: str
    context: ClassVar[str] = Field(..., description="Docker context name")

    class Config:
        """Configuration for the Pydantic model."""

        schema_extra: ClassVar[dict[str, dict[str, str]]] = {
            "example": {
                "container_id": "container_id_123",
                "file_path": "/path/to/file.txt",
                "file_content": "New file content here",
                "context": "my_docker_context",
            }
        }


class UpdateJsonFileRequest(BaseModel):
    """Pydantic model for updating a JSON file inside a Docker container.

    :param container_id: The ID of the Docker container
    :type container_id: str
    :param file_path: The path to the JSON file inside the container
    :type file_path: str
    :param json_content: The JSON content to merge with the existing file content
    :type json_content: dict
    :param merge_schema: The merge schema to use for merging JSON content (optional)
    :type merge_schema: dict, optional
    :param context: The Docker context to use for the Docker command
    :type context: str
    """

    container_id: str
    file_path: str
    json_content: dict
    merge_schema: dict | None = None
    context: str = Field(..., description="Docker context name")

    class Config:
        """Configuration for the Pydantic model."""

        schema_extra: ClassVar[[str, str]] = {
            "example": {
                "container_id": "container_id_123",
                "file_path": "/path/to/file.json",
                "json_content": {"key": "value"},
                "merge_schema": {"mergeStrategy": "append"},
                "context": "my_docker_context",
            }
        }


class ComposeContent(BaseModel):
    """Data Model for Passing Docker Compose files."""

    yaml_content: str
    context: str
    additional_args: str = Field(
        default="", description="Additional docker compose arguments"
    )


class ComposeContentWithFiles(BaseModel):
    """Data Model for Passing Docker Compose files with mounted volumes."""

    yaml_content: str
    context: str
    mounts: dict[str, VolumeMounts]
    additional_args: str = Field(
        default="", description="Additional docker compose arguments"
    )


@APP.post("/docker-compose")
async def execute_docker_compose(content: ComposeContent) -> JSONResponse:
    """Execute the Docker Compose on a target context.

    :param content: The Docker Compose YAML content with context details
    :type content: ComposeContent
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided or YAML syntax is invalid
    :return: Dictionary containing the stdout, stderr, and returncode
             of the docker-compose command
    :rtype: JSONResponse
    """
    # Check if the provided context is part of the cached Docker contexts
    if content.context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    # Execute the async function and return the result
    if not content.additional_args:
        content.additional_args = "--force-recreate --pull always --quiet-pull"
    result = await docker_compose_run(
        content.yaml_content, content.context, additional_args=content.additional_args
    )
    return JSONResponse(content=result)


@APP.post("/docker-compose-with-mounts")
async def execute_docker_compose_with_mounts(
    content: ComposeContentWithFiles,
) -> JSONResponse:
    """Execute the Docker Compose command.

    The API accepts the following:
    - Docker Compose YAML content.
    - Target Context Location to work with.
    - Volume Mounts.
    - Additional Compose arguments.

    If the API does not receive any additional_args,
    "--force-recreate --pull always" are added by default.

    :param content: The Docker Compose YAML content with context details
    :type content: ComposeContentWithFiles
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided, or YAML syntax is invalid
    :return: JSONResponse containing the stdout, stderr, and returncode
             of the docker-compose command
    :rtype: JSONResponse
    """
    # Check if the provided context is part of the cached Docker contexts
    if content.context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    # Execute the async function and return the result
    if not content.additional_args:
        content.additional_args = "--force-recreate --pull always"

    result = await docker_compose_run(
        content.yaml_content,
        content.context,
        mounts=content.mounts,
        additional_args=content.additional_args,
    )
    return JSONResponse(content=result)


@APP.get("/inspect")
async def inspect_containers_endpoint(context: str) -> dict[str, Any]:
    """Inspect containers API endpoint.

    This endpoint allows inspecting all containers in the Docker Compose project
    associated with the specified Docker context. It returns a dictionary containing
    the container IDs as keys and their corresponding inspect data as values.

    :param context: The Docker context associated with the Docker Compose project.
    :type context: str
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided, or YAML syntax is invalid
    :return: A dictionary containing the container IDs as keys and their
             corresponding inspect data as values
    :rtype: dict[str, Any]
    """
    if context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    return await docker_inspect_containers(context)


@APP.get("/docker-contexts")
def list_docker_contexts() -> JSONResponse:
    """Execute the Docker Context ls command and return configured context names.

    :return: Context list
    :rtype: JSONResponse
    """
    # Note: If we consider adding context via API, then maybe we won't
    # need the cache.
    return JSONResponse(content=_DOCKER_CONTEXTS)


@APP.post("/update_file")
async def update_file(request_data: UpdateFileRequest) -> dict[str, str]:
    """Update a file inside a Docker container on a remote host.

    :param request_data: The request data containing container ID,
        file path, file content, and Docker context
    :type request_data: UpdateFileRequest
    :raises HTTPException: If the Docker context is invalid or
                           if the Docker command fails
    :return: A dictionary containing a message indicating whether
             the file was updated successfully
    :rtype: dict
    """
    if request_data.context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    # Update the file inside the Docker container on the remote host
    result = await update_file_on_remote_container(
        container_id=request_data.container_id,
        file_path=request_data.file_path,
        file_content=request_data.file_content,
        context=request_data.context,
    )
    return {"message": result}


@APP.post("/update_json_file")
async def update_json_file(request_data: UpdateJsonFileRequest) -> dict[str, str]:
    """Update a JSON file inside a Docker container.

    :param request_data: The request data containing the container ID,
                         file path, JSON content, and context.
    :type request_data: UpdateJsonFileRequest
    :raises HTTPException: If the Docker context is invalid or
                        if the Docker command fails.
    :return: A message indicating the success of the update operation.
    :rtype: str
    """
    if request_data.context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    # Update the JSON file inside the Docker container on the remote host
    result = await update_json_file_on_remote_container(
        request_data.container_id,
        request_data.file_path,
        request_data.json_content,
        request_data.context,
        request_data.merge_schema,
    )
    return {"message": result}


if __name__ == "__main__":
    import uvicorn

    # Cache Docker contexts at startup
    _DOCKER_CONTEXTS = docker_context_ls()
    uvicorn.run(APP, host="0.0.0.0", port=8000, timeout_keep_alive=300)  # noqa: S104
