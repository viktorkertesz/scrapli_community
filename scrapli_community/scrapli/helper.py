import hashlib
import os
from typing import Optional, Callable, TypedDict, Literal, Dict
from asyncssh import SSHClientConnectionOptions, connect, scp
from dataclasses import dataclass
import aiofiles


@dataclass()
class ConnectionParameterType(TypedDict):
    username: str
    password: str
    host: str
    options: SSHClientConnectionOptions


class AsyncSCPConnection:
    def __init__(self, conn_parameters: ConnectionParameterType):
        self.conn_parameters = conn_parameters

    async def async_file_transfer(self, operation: Literal['get', 'put'], src: str, dst: str,
                                  callback: Optional[Callable] = None) -> bool:
        """
        SCP a file from device to localhost

        Args:
            operation: 'get' or 'put' files from or to the device
            src: Source file name
            dst: Destination file name
            callback: scp callback function to be able to follow the copy progress

        Returns:
            bool: True if file was transferred successfully
        """
        try:
            async with connect(**self.conn_parameters) as scp_conn:
                if operation == 'get':
                    await scp((scp_conn, src), dst, callback=callback)
                else:
                    await scp(src, (scp_conn, dst), callback=callback)
        except Exception as e:
            return False
        return True


async def _read_file(file_name) -> bytes:
    async with aiofiles.open(file_name, "rb") as f:
        contents = await f.read()
    return contents


async def check_local_file(file_name: str) -> Dict[str, str]:
    """Compute MD5 hash of file."""
    file_contents = await _read_file(file_name)
    file_size = os.path.getsize(file_name)
    return {'md5': hashlib.md5(file_contents).hexdigest(), 'size': file_size}