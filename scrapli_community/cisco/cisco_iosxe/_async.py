"""scrapli_community.cisco.cisco_iosxe._async"""
import re
from typing import Any, Optional
from scrapli.driver.core.cisco_iosxe.async_driver import AsyncIOSXEDriver
from scrapli_community.transport.asyncscp import AsyncSCPFeature, FileCheckResult


class AsyncCommunityIOSXEDriver(AsyncIOSXEDriver, AsyncSCPFeature):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    async def _ensure_scp_capability(self, force: bool = True) -> bool:
        pass

    async def _cleanup_after_transfer(self) -> None:
        pass

    async def _get_device_fs(self) -> Optional[str]:
        #  Enable mode needed
        await self.acquire_priv(self.default_desired_privilege_level)
        output = await self.send_command("dir | i Directory of (.*)")
        m = re.match("Directory of (?P<fs>.*)", output.result, re.M)
        if m:
            return m.group('fs')
        else:
            return None

    async def check_device_file(self, device_fs: str, filename: str) -> FileCheckResult:
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
