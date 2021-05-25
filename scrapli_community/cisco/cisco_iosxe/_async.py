"""scrapli_community.cisco.cisco_iosxe._async"""
import re
from dataclasses import dataclass
from typing import Dict, Literal, Callable, Optional, Any
from scrapli.driver.core.cisco_iosxe.async_driver import AsyncIOSXEDriver
from scrapli_community.scrapli.helper import AsyncSCPConnection, ConnectionParameterType, check_local_file


@dataclass()
class FileTransferResult:
    Exists: bool
    Transferred: bool
    Verified: bool


class AsyncCommunityIOSXEDriver(AsyncIOSXEDriver):
    def __init__(self, **kwargs):
        self.scp_was_enabled = False
        super().__init__(**kwargs)

    async def _ensure_scp_capability(self):
        """Check if scp is enabled and enable it if not"""

    async def check_device_file(self, device_fs: str, filename: str) -> Dict[str, Any]:
        """Get MD5 hash and size of a file on IOS device"""
        # Need to set timeout big else MD5 verification time outs!!!!!!!!!
        outputs = await self.send_commands([f"verify /md5 {device_fs}{filename}",
                                            f"dir {device_fs}{filename}"
                                            ])
        m = re.search(r"^verify.*=\s*(?P<md5>\w{32})", outputs[0].result, re.M)
        if m:
            md5_hash = m.group('md5')
        else:
            raise FileNotFoundError(f"{device_fs}{filename} was not found")
        m = re.search(r"^\s*\d+\s*[rw-]+\s*(?P<size>\d+).*" + filename, outputs[1].result, re.M)
        file_size = m.group('size')
        return {'md5': md5_hash, 'size': file_size}

    async def file_transfer(self, operation: Literal['get', 'put'], src: str, dst: str, md5_verify: bool = True,
                            device_fs: str = "", callback: Optional[Callable] = None):
        """
        Cisco IOS XE file transfer
        Args:
            operation: put/get file to/from device
            src: source file name
            dst: destinateion file name
            md5_verify: True if MD5 checksum verification is needed
            device_fs: IOS device filesystem (autodetect if empty)
            callback: function to call by file copy (used as by scp function)

        Returns:

        """
        scp_options = ConnectionParameterType(
            username=self.auth_username,
            password=self.auth_password,
            host=self.host,
            options=self.transport.session._options
        )
        scp = AsyncSCPConnection(scp_options)
        result = FileTransferResult(
            Exists=False,
            Transferred=False,
            Verified=False
        )

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
            if md5_verify:
                device_file_md5, device_file_size = (await self.check_device_file(device_fs, src)).values()
                self.logger.debug(f"device file {src} size: {device_file_size}, md5: {device_file_md5}")
                try:
                    local_file_md5, local_file_size = (await check_local_file(dst)).values()
                    result.Exists = True
                except FileNotFoundError as e:
                    local_file_md5, local_file_size = "", ""
                if device_file_md5 == local_file_md5:
                    result.Verified = True
                    return result
            try:
                await scp.async_file_transfer(operation, src, dst, callback=callback)
            except Exception as e:
                raise e
