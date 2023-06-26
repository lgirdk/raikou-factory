"""Docker Orchestration API code."""

from typing import Any, Optional

from docker_orchestrator import (
    VolumeMounts,
    docker_compose_run,
    docker_context_ls,
    docker_inspect_containers,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

APP = FastAPI()

# List to store cached Docker contexts
_DOCKER_CONTEXTS: dict[str, str]


class ComposeContent(BaseModel):
    """Data Model for Passing Docker Compose files."""

    yaml_content: str
    context: str
    additional_args: Optional[str]


class ComposeContentWithFiles(BaseModel):
    """Data Model for Passing Docker Compose files with mounted volumes."""

    yaml_content: str
    context: str
    mounts: dict[str, VolumeMounts]
    additional_args: Optional[str]


@APP.post("/docker-compose")
async def execute_docker_compose(content: ComposeContent) -> JSONResponse:
    """Execute the Docker Compose on a target context.

    :param content: The Docker Compose YAML content with context details.
    :type content: ComposeContent
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided or YAML syntax is invalid.
    :return: Dictionary containing the stdout, stderr, and returncode
             of the docker-compose command.
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

    :param content: The Docker Compose YAML content with context details.
    :type content: ComposeContentWithFiles
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided, or YAML syntax is invalid.
    :return: JSONResponse containing the stdout, stderr, and returncode
             of the docker-compose command.
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
    """
    Inspect containers API endpoint.

    This endpoint allows inspecting all containers in the Docker Compose project
    associated with the specified Docker context. It returns a dictionary containing
    the container IDs as keys and their corresponding inspect data as values.

    :param context: The Docker context associated with the Docker Compose project.
    :type context: str
    :raises HTTPException: If the context is already being used, or if the
                           context is not provided, or YAML syntax is invalid.
    :return: A dictionary containing the container IDs as keys and their
             corresponding inspect data as values.
    :rtype: dict[str, Any]
    """
    if context not in _DOCKER_CONTEXTS:
        raise HTTPException(status_code=400, detail="Invalid Docker context.")

    container_data = await docker_inspect_containers(context)
    return container_data


@APP.get("/docker-contexts")
def list_docker_contexts() -> JSONResponse:
    """Execute the Docker Context ls command and return configured context names.

    :return: Context list
    :rtype: JSONResponse
    """
    # Note: If we consider adding context via API, then maybe we won't
    # need the cache.
    return JSONResponse(content=_DOCKER_CONTEXTS)


if __name__ == "__main__":
    import uvicorn

    # Cache Docker contexts at startup
    _DOCKER_CONTEXTS = docker_context_ls()
    uvicorn.run(APP, host="0.0.0.0", port=8000, timeout_keep_alive=300)
