"""scrapli_community.cisco.cisco_iosxe.cisco_iosxe_community"""
from scrapli.driver.core.cisco_iosxe.async_driver import iosxe_on_close as default_async_on_close
from scrapli.driver.core.cisco_iosxe.async_driver import iosxe_on_open as default_async_on_open
from scrapli.driver.core.cisco_iosxe.base_driver import FAILED_WHEN_CONTAINS
from scrapli.driver.core.cisco_iosxe.base_driver import PRIVS as DEFAULT_PRIVILEGE_LEVELS
from scrapli.driver.core.cisco_iosxe.sync_driver import iosxe_on_close as default_sync_on_close
from scrapli.driver.core.cisco_iosxe.sync_driver import iosxe_on_open as default_sync_on_open

from scrapli_community.cisco.cisco_iosxe.async_driver import AsyncCommunityIOSXEDriver
from scrapli_community.cisco.cisco_iosxe.sync_driver import CommunityIOSXEDriver

SCRAPLI_PLATFORM = {
    "driver_type": {
        "sync": CommunityIOSXEDriver,
        "async": AsyncCommunityIOSXEDriver,
    },
    "defaults": {
        "privilege_levels": DEFAULT_PRIVILEGE_LEVELS,
        "default_desired_privilege_level": "privilege_exec",
        "sync_on_open": default_sync_on_open,
        "async_on_open": default_async_on_open,
        "sync_on_close": default_sync_on_close,
        "async_on_close": default_async_on_close,
        "failed_when_contains": FAILED_WHEN_CONTAINS,
        "textfsm_platform": "cisco_iosxe",
        "genie_platform": "iosxe",
    },
}
