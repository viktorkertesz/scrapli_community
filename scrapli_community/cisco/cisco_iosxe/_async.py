"""scrapli_community.cisco.cisco_iosxe._async"""
import re
from typing import Any
from scrapli.driver.core.cisco_iosxe.async_driver import AsyncIOSXEDriver
from scrapli_community.transport.asyncscp import AsyncSCPFeature, FileCheckResult


class AsyncCommunityIOSXEDriver(AsyncIOSXEDriver, AsyncSCPFeature):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    async def _ensure_scp_capability(self):
        """Check if scp is enabled and enable it if not"""

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
        self.logger.info(f"Checking {device_fs}{filename} MD5 hash..")
        outputs = await self.send_commands([f"verify /md5 {device_fs}{filename}",
                                            f"dir {device_fs}{filename}"
                                            ], timeout_ops=300)
        m = re.search(r"^verify.*=\s*(?P<hash>\w{32})", outputs[0].result, re.M)
        if m:
            file_hash = m.group('hash')
        else:
            file_hash = ""
        m = re.search(r"^\s*\d+\s*[rw-]+\s*(?P<size>\d+).*" + filename, outputs[1].result, re.M)
        if m:
            file_size = int(m.group('size'))
        else:
            file_size = 0
        m = re.search(r"\((?P<free>\d+) bytes free\)", outputs[1].result, re.M)
        if m:
            free_space = int(m.group('free'))
        else:
            free_space = 0
        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)
