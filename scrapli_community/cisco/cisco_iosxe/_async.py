"""scrapli_community.cisco.cisco_iosxe._async"""
import re
from typing import Any, Optional, Union, List

from scrapli.driver.core.cisco_iosxe.async_driver import AsyncIOSXEDriver

from scrapli_community.features.asyncscp import AsyncSCPFeature, FileCheckResult


class AsyncCommunityIOSXEDriver(AsyncIOSXEDriver, AsyncSCPFeature):
    def __init__(self, *args: Any, **kwargs: Any):
        self._scp_to_clean: List[str] = []
        super().__init__(*args, **kwargs)

    async def _ensure_scp_capability(self, force: Optional[bool] = False) -> Union[bool, None]:
        self._scp_to_clean = []
        result = None
        if force is None:
            return result
        # intended configuration:
        #
        # ip scp server enable
        # ip ssh window-size 65536
        # ip tcp window-size 65536
        #
        # ip ssh window-size is supported from 16.6.1
        # 65536 is a recommendation by Cisco
        # https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/sec_usr_ssh/configuration/xe-16-6/sec-usr-ssh-xe-16-6-book/sec-usr-ssh-xe-16-book_chapter_0110.html
        window_size = 65536
        output = await self.send_command(
            "sh run all | i ^ip scp server enable|^ip tcp window|^ip ssh window"
        )
        outputs = output.result.split("\n")
        # find missing or to be adjusted commands
        scp_to_apply = []
        self._scp_to_clean = []
        # check if SCP is enabled
        if "ip scp server enable" not in outputs:
            scp_to_apply.append("ip scp server enable")
            self._scp_to_clean.append("no ip scp server enable")
        # check SSH window size. It might be not supported (old IOS)
        try:
            ssh_window_str = [x for x in outputs if "ip ssh" in x][0]
        except IndexError:
            ssh_window_str = []
        if ssh_window_str:
            m = re.search(r"ip ssh window-size (?P<ssh_window>\d+)", ssh_window_str)
            ssh_window = int(m.group("ssh_window"))
            if ssh_window < window_size:
                scp_to_apply.append(f"ip ssh window-size {window_size}")
                self._scp_to_clean.append(f"ip ssh window-size {ssh_window}")
            # TCP window is only interesting if SCP window is supported
            try:
                tcp_window_str = [x for x in outputs if "ip tcp" in x][0]
            except IndexError:
                tcp_window_str = []
            if tcp_window_str:
                m = re.search(r"ip tcp window-size (?P<tcp_window>\d+)", tcp_window_str)
                tcp_window = int(m.group("tcp_window"))
                if tcp_window < window_size:
                    scp_to_apply.append(f"ip tcp window-size {window_size}")
                    self._scp_to_clean.append(f"ip tcp window-size {tcp_window}")

        # check if we are good
        if not scp_to_apply:
            return result

        # would need configuration but do we want it?
        # We require the minimum configuration to proceed (ip scp server enable)
        if not force and "ip scp server enable" in scp_to_apply:
            result = False
            self._scp_to_clean = []
            return result

        # apply SCP enablement
        output = await self.send_configs(scp_to_apply)

        if output.failed:
            # commands did not succeed
            result = False
            # try to revert
            await self.send_configs(self._scp_to_clean)
            self._scp_to_clean = []
        else:
            # device reconfigured for scp
            result = True

        return result

    async def _cleanup_after_transfer(self) -> None:
        # we assume that _scp_to_clean was populated by a previously called _ensure_scp_capability
        if not self._scp_to_clean:
            return
        await self.send_configs(self._scp_to_clean)

    async def _get_device_fs(self) -> Optional[str]:
        #  Enable mode needed
        await self.acquire_priv(self.default_desired_privilege_level)
        output = await self.send_command("dir | i Directory of (.*)")
        m = re.match("Directory of (?P<fs>.*)", output.result, re.M)
        if m:
            return m.group("fs")
        else:
            return None

    async def check_device_file(self, device_fs: Optional[str], file_name: str) -> FileCheckResult:
        self.logger.info(f"Checking {device_fs}{file_name} MD5 hash..")
        outputs = await self.send_commands(
            [f"verify /md5 {device_fs}{file_name}", f"dir {device_fs}{file_name}"], timeout_ops=300
        )
        m = re.search(r"^verify.*=\s*(?P<hash>\w{32})", outputs[0].result, re.M)
        if m:
            file_hash = m.group("hash")
        else:
            file_hash = ""
        m = re.search(r"^\s*\d+\s*[rw-]+\s*(?P<size>\d+).*" + file_name, outputs[1].result, re.M)
        if m:
            file_size = int(m.group("size"))
        else:
            file_size = 0
        m = re.search(r"\((?P<free>\d+) bytes free\)", outputs[1].result, re.M)
        if m:
            free_space = int(m.group("free"))
        else:
            free_space = 0
        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)
