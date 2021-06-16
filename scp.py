from scrapli_community.cisco.cisco_iosxe.cisco_iosxe_community import AsyncCommunityIOSXEDriver
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

device = {
   "host": "172.16.255.100",
   "auth_username": "admin",
   "auth_password": "test123",
   "auth_strict_key": False,
   "transport": "asyncssh",
   "ssh_config_file": "sshconfig.txt"
}

filename = "e:/download/mr.pdf"

async def main():
    async with AsyncCommunityIOSXEDriver(**device) as conn:
        result = await conn.file_transfer("put", src=filename, dst=".", force_scp_config=True)
    print(result)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
