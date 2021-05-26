import re
import hashlib
import shutil
import os
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, Callable, Literal, TypedDict
from asyncssh import SSHClientConnectionOptions, connect, scp
from scrapli.driver import AsyncNetworkDriver
import aiofiles


@dataclass()
class FileCheckResult:
    hash: str  # hash value string
    size: int  # size in bytes
    free: int  # free space in bytes


@dataclass()
class SCPConnectionParameterType(TypedDict):
    username: str
    password: str
    host: str
    options: SSHClientConnectionOptions


@dataclass()
class FileTransferResult:
    exists: bool
    transferred: bool
    verified: bool


class AsyncSCPFeature(AsyncNetworkDriver, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    async def check_device_file(self, device_fs: str, filename: str) -> FileCheckResult:
        """
        Check remote file and storage space
        Returning empty hash means error accessing the file
        Args:
            device_fs: filesystem on device (e.g. disk0:/)
            filename: file to examine

        Returns:
            FileCheckResult: returns hash, size and free space. Empty/zero on error for each.
        """
        ...

    @abstractmethod
    async def _ensure_scp_capability(self):
        ...

    @classmethod
    async def check_local_file(cls, file_name: str) -> FileCheckResult:
        """
        Check local file and storage space
        Returning empty hash means error accessing the file
        Args:
            file_name: local file to examine

        Returns:
            FileCheckResult: returns hash, size and free space. Empty/zero on error for each.
        """
        try:
            async with aiofiles.open(file_name, "rb") as f:
                file_hash = hashlib.md5(await f.read()).hexdigest()
            file_size = os.path.getsize(file_name)
        except FileNotFoundError:
            file_size = 0
            file_hash = ""
        try:
            path = os.path.dirname(file_name)
            # check free space of directory of the file or the local dir
            free_space = shutil.disk_usage(path if path else ".").free
        except FileNotFoundError:
            free_space = 0
        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)

    async def async_file_transfer(self, operation: Literal['get', 'put'], src: str, dst: str,
                                  progress_handler: Optional[Callable] = None) -> None:
        """
        SCP a file from device to localhost

        Args:
            operation: 'get' or 'put' files from or to the device
            src: Source file name
            dst: Destination file name
            progress_handler: scp callback function to be able to follow the copy progress

        Returns:
            bool: True if file was transferred successfully
        """
        # noinspection PyProtectedMember
        scp_options = SCPConnectionParameterType(
            username=self.auth_username,
            password=self.auth_password,
            host=self.host,
            options=self.transport.session._options
        )
        async with connect(**scp_options) as scp_conn:
            if operation == 'get':
                await scp((scp_conn, src), dst, progress_handler=progress_handler, block_size=32768)
            elif operation == 'put':
                await scp(src, (scp_conn, dst), progress_handler=progress_handler, block_size=32768)
            else:
                raise ValueError(f"Invalid operation: {operation}")

    async def file_transfer(self, operation: Literal['get', 'put'], src: str, dst: str, hash_verify: bool = True,
                            device_fs: str = "", overwrite: bool = False,
                            progress_handler: Optional[Callable] = None) -> FileTransferResult:
        """
        Cisco IOS XE file transfer
        This transfer is idempotent and does the following checks before/after transfer:
        1. checksum
        2. existence of file at destination (also with hash)
        3. available space at destination
        4. scp enablement on device (and tries to turn it on if needed)
        Transfer can be considered as success if the result has `verified` set to True

        Args:
            operation: put/get file to/from device
            src: source file name
            dst: destination file name
            hash_verify: True if checksum verification is needed
            device_fs: IOS device filesystem (autodetect if empty)
            overwrite: If set to True, destination will be overwritten in case hash verification fails
            progress_handler: function to call by file copy (used by asyncssh.scp function)

        Returns:
            FileTransferResult: returns exists, transferred, verified results
        """

        result = FileTransferResult(False, False, False)
        device_file_data = FileCheckResult("", 0, 0)
        local_file_data = FileCheckResult("", 0, 0)

        # set destination filename to source if missing
        if dst == "" or dst == ".":
            dst = src

        # Detect default filesystem the device use
        if not device_fs:
            #  Enable mode needed
            await self.acquire_priv(self.default_desired_privilege_level)
            output = await self.send_command("dir | i Directory of (.*)")
            m = re.match("Directory of (?P<fs>.*)", output.result, re.M)
            device_fs = m.group('fs')

        if operation == 'get':
            if hash_verify:
                # gather info on remote side
                device_file_data = await self.check_device_file(device_fs, src)
                self.logger.debug(f"device file {src}: {device_file_data}")
                if not device_file_data.hash:
                    # source file cannot be found, we are done here
                    self.logger.warning(f"Source file {src} does NOT exists!")
                    return result
                # gather info on local file
                local_file_data = await self.check_local_file(dst)
                self.logger.debug(f"local file {dst}: {local_file_data}")
                # check if local file exists
                if local_file_data.hash:
                    result.exists = True
                # check if local file has the same hash as source
                if local_file_data.hash and device_file_data.hash == local_file_data.hash:
                    result.verified = True
                    # no need to transfer file
                    self.logger.info(f"{dst} file already exists at destination and verified OK")
                    return result
            if local_file_data.hash and not overwrite:
                # if hash does not match and we want to overwrite
                self.logger.warning(f"{dst} file would NOT be overwritten!")
                return result
            # check if we have enough free space to transfer the file
            if local_file_data.free < device_file_data.size:
                self.logger.warning(f"{dst} file is too big ({device_file_data.size}). Local free space: "
                                    f"{local_file_data.free}")
                return result
            # transfer the file
            try:
                await self.async_file_transfer(operation, src, dst, progress_handler=progress_handler)
                result.transferred = True
            except Exception as e:
                raise e
            if hash_verify:
                # check local file after copy
                local_file_data = await self.check_local_file(dst)
                # check if file was created
                if local_file_data.hash:
                    result.exists = True
                # check if file has the same hash as source
                if local_file_data.hash and local_file_data.hash == device_file_data.hash:
                    result.verified = True
                else:
                    self.logger.warning(f"{dst} failed hash verification!")
            return result
        elif operation == 'put':
            pass
        else:
            raise ValueError(f"Operation {operation} does not supported")
