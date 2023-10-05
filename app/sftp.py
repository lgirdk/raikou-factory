"""Module to copy local files to target context using SFTP."""

import asyncio

import asyncssh


async def copy_files(
    files: list[tuple[str, str]], ip_address: str, username: str, port: int
) -> None:
    """Copy multiple files from the local machine to the remote server.

    Files are copied over SSH using asyncssh.

    :param files: List of tuples containing the local path and remote path for each file.
    :type files: list[tuple[str, str]]
    :param ip_address: Remote server IP address.
    :type ip_address: str
    :param username: Remote server username.
    :type username: str
    :param port: Remote server port.
    :type port: int
    """

    async def _copy_file(local_path: str, remote_path: str, sftp: asyncssh.SFTPClient):
        for attempt in range(3):
            try:
                await sftp.put(local_path, remote_path)
                return
            except asyncssh.Error as exc:
                print(f"Error occurred while copying file: {exc}")
                if attempt < 3:
                    await asyncio.sleep(1)
                else:
                    raise

    async with asyncssh.connect(ip_address, username=username, port=port) as conn:
        async with conn.start_sftp_client() as sftp:
            async with asyncio.TaskGroup() as group:
                for local_path, remote_path in files:
                    task = _copy_file(local_path, remote_path, sftp)
                    group.create_task(task)
