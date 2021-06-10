"""scrapli_community.cisco.cisco_iosxe.sync"""
from scrapli.driver.core.cisco_iosxe.sync_driver import IOSXEDriver


class CommunityIOSXEDriver(IOSXEDriver):
    async def file_transfer(self):
        """Sync file transfer implemented"""
        raise NotImplementedError
