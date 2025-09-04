"""Heimdall service checks"""

from asyncio import create_subprocess_shell, open_connection
from asyncio.subprocess import PIPE
from enum import StrEnum, auto
from logging import getLogger

from aiohttp.client import ClientSession

logger = getLogger(__name__)


class ComponentState(StrEnum):
    OK = auto()
    DEGRADED = auto()
    DEAD = auto()


async def check_url(url: str, *, ignore_unauthorized: bool = False) -> ComponentState:
    async with ClientSession() as session, session.get(url) as response:
        if response.ok or ignore_unauthorized and response.status in (401, 403):
            return ComponentState.OK
        if response.status >= 500:
            return ComponentState.DEAD
        else:
            return ComponentState.DEGRADED


async def ping_host(host: str) -> ComponentState:
    proc = await create_subprocess_shell(f"ping -c 1 -W 10 {host}", stdout=PIPE, stderr=PIPE)
    await proc.communicate()
    return ComponentState.OK if proc.returncode == 0 else ComponentState.DEAD


async def tcp_connect(host: str, port: int) -> ComponentState:
    try:
        _, _ = await open_connection(host, port)
        return ComponentState.OK
    except Exception:
        return ComponentState.DEAD
