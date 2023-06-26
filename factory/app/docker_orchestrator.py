"""Docker Orchestration code."""

import asyncio
import os
import subprocess
import json
from functools import cache
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import urlparse

import asyncssh
import yaml
from fastapi import HTTPException
from sftp import copy_files

# Dictionary to store context locks
_CONTEXT_LOCKS: dict[str, bool] = {}


class VolumeMounts(TypedDict):
    """Schema for providing volume mounts as dictionary."""

    source: str
    file: str


async def copy_mount_files(
    mounts: dict[str, VolumeMounts], compose_config: str, ssh_url: str
) -> str:
    """Copy mount files to a remote server using SSH.

    This function takes a dictionary of mount points, where each mount point
    is represented as a dictionary with 'source' and 'file' keys.

    The 'source' key specifies the source path of the target host in the
    Docker Compose YAML file, and the 'file' key contains the binary data
    of the file to be copied.

    The function updates the Docker Compose YAML file with the actual source
    path and then copies the mount files to the remote server using SSH.

    :param mounts: Dictionary of mount points and corresponding files.
    :type mounts: dict[str, VolumeMounts]
    :param compose_config: Docker Compose configuration as a dictionary.
    :type compose_config: str
    :param ssh_url: SSH URL of the remote server.
    :type ssh_url: str
    :return: updated yaml content
    :rtype: str
    :raises HTTPException: If there's an error copying the files over SSH.
    """
    files_to_copy: list[tuple[str, str]] = []

    for env_name, mount in mounts.items():
        # First replace the env_name in the YAML with the source path
        compose_config = compose_config.replace(env_name, mount["source"])

        # Store the file in /tmp first before SFTP put.
        file_name = Path(mount["source"]).name
        Path(f"/tmp/{file_name}").write_text(mount["file"], encoding="utf-8")
        files_to_copy.append((f"/tmp/{file_name}", mount["source"]))

    try:
        ssh = urlparse(ssh_url)
        await copy_files(
            files=files_to_copy,
            ip_address=str(ssh.hostname),
            username=str(ssh.username),
            port=int(ssh.port or 22),
        )
    except asyncssh.Error as exc:
        raise HTTPException(
            status_code=504, detail=f"Failed to copy SSH file to URL: {ssh_url}"
        ) from exc

    return compose_config


async def _get_compose_service_states(file_path: str) -> list[str]:
    # Check if all containers were created
    check_command = ["docker-compose", "-f", file_path, "ps", "--services"]
    check_process = await asyncio.create_subprocess_exec(
        *check_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ
    )
    stdout, _ = await check_process.communicate()

    # collect service status here

    if check_process.returncode != 0:
        raise HTTPException(status_code=500, detail="Failed to check container status.")
    return stdout.decode().strip().split("\n")


@cache
def docker_context_ls() -> dict[str, str]:
    """Cache the docker context pre-configured on the orchestrator.

    :return: context names with their respective docker host URL.
    :rtype: dict[str, str]
    """
    docker_context = {}

    command = [
        "docker",
        "context",
        "ls",
        "--format",
        "{{.Name}}|{{.DockerEndpoint}}",
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode == 0:
        output = process.stdout.strip().splitlines()
        for line in output:
            context_name, docker_endpoint = line.split("|")
            docker_context[context_name] = docker_endpoint

    return docker_context


async def docker_inspect_containers(context: str) -> dict[str, Any]:
    """
    Inspect containers using docker-compose and docker inspect commands.

    This function inspects all containers in the Docker Compose project
    associated with the specified Docker context. It collects the container
    details by running the `docker-compose ps` command to obtain the container
    IDs, and then runs the `docker inspect` command for each container ID.

    :param context: The Docker context associated with the Docker Compose
                    project.
    :type context: str
    :return: A dictionary containing the container IDs as keys and their
             corresponding inspect data as values.
    :rtype: dict[str, Any]
    """
    original_docker_host = os.environ.get("DOCKER_HOST")
    try:
        # Set Docker context using environment variable
        docker_host = docker_context_ls()[context]
        os.environ["DOCKER_HOST"] = docker_host

        file_path = f"/tmp/docker-compose_{context}.yaml"

        # Run the docker-compose command asynchronously
        command = ["docker", "compose", "-f", file_path, "ps", "-aq"]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await process.communicate()

        if process.returncode != 0:
            # Return an empty dictionary if the command failed
            return {"error": "failed to execute docker compose inspect!"}

        container_ids = stdout.decode().strip().split()

        container_data = {}
        for container_id in container_ids:
            command = ["docker", "inspect", container_id]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                inspect_data = json.loads(stdout.decode().strip())
                container_info = {}
                if inspect_data:
                    container_info = inspect_data[0]
                container_data[inspect_data[0]["Name"]] = container_info
            else:
                container_data[container_id] = "Failed to collect Data!!"

        return container_data
    finally:
        # Restore original DOCKER_HOST value
        if original_docker_host:
            os.environ["DOCKER_HOST"] = original_docker_host
        else:
            os.environ.pop("DOCKER_HOST", None)


async def docker_compose_run(
    yaml_content: str,
    context: str,
    mounts: None | dict[str, VolumeMounts] = None,
    additional_args: None | str = "",
) -> dict[str, str | int]:
    """Run docker-compose command asynchronously with the specified context.

    If ```mounts``` are provided:
        - The key needs to be an env variable that can be substituted
          inside the yaml_content.
        - If the key is not provided raise an exception with error code 415.

    :param yaml_content: The Docker Compose YAML content.
    :type yaml_content: str
    :param context: The target Docker context.
    :type context: str
    :param mounts: File mounts for each service.
    :type mounts: None | dict[str, VolumeMounts]
    :param additional_args: additional compose cli args, example
                            ```--force-recreate --pull-always```
    :type additional_args: Optional[str]
    :raises HTTPException: error code 409 if target context already in use.
    :raises HTTPException: error code 400 if invalid YAML file provided.
    :return: Dictionary containing the stdout, stderr, and returncode of
             the docker-compose command.
    :rtype: dict[str, str|int]
    """
    # Acquire the lock for the context
    if _CONTEXT_LOCKS.get(context):
        raise HTTPException(status_code=409, detail="Context is already being used.")
    _CONTEXT_LOCKS[context] = True

    original_docker_host = os.environ.get("DOCKER_HOST")
    services_requested: dict
    try:
        # Check YAML syntax
        try:
            compose_config = yaml.safe_load(yaml_content)
            services_requested = compose_config.get("services", {})
        except yaml.YAMLError as exc:
            raise HTTPException(status_code=400, detail="Invalid YAML syntax.") from exc

        docker_host = docker_context_ls()[context]

        # Copy files to be mounted to target destination
        if mounts:
            yaml_content = await copy_mount_files(
                mounts=mounts, compose_config=yaml_content, ssh_url=docker_host
            )

        # Set Docker Compose context using environment variable
        os.environ["DOCKER_HOST"] = docker_host

        # Save the YAML content to a temporary file
        file_path = f"/tmp/docker-compose_{context}.yaml"
        Path(file_path).write_text(yaml_content, encoding="utf-8")

        # Run docker-compose command asynchronously
        command = [
            "docker-compose",
            "-f",
            file_path,
            "up",
            "-d",
            "--remove-orphans",
        ]
        if additional_args:
            command.extend(additional_args.split())
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute docker-compose command.\n{stderr.decode()}",
            )

        container_ids = await _get_compose_service_states(file_path)
        if len(container_ids) != len(services_requested):
            raise HTTPException(
                status_code=500,
                detail="Invalid container creation count.",
            )

        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }
    finally:
        # Release the lock for the context
        del _CONTEXT_LOCKS[context]

        # Restore original DOCKER_HOST value
        if original_docker_host:
            os.environ["DOCKER_HOST"] = original_docker_host
        else:
            os.environ.pop("DOCKER_HOST", None)
