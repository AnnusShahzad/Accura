"""
Accura – Outbound URL guard (SSRF protection)

Users can make the backend call URLs they choose: MCP servers, custom
OpenAI-compatible endpoints and Slack/Teams webhooks. On a public
deployment that would let anyone probe the host's private network or a
cloud metadata endpoint. With ``security.allow_private_urls`` false, every
such URL must be http(s) and resolve only to public addresses.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from config import settings


class UnsafeURLError(ValueError):
    """A user-supplied URL points somewhere the server must not call."""

    @property
    def message(self) -> str:
        return str(self)


def private_urls_allowed() -> bool:
    return bool(settings.get("security.allow_private_urls", True))


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def ensure_public_url(url: str, *, what: str = "URL") -> None:
    """Raise UnsafeURLError unless *url* is safe to fetch from the server.

    A no-op when private URLs are allowed (the self-hosted default).
    """
    if private_urls_allowed():
        return

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURLError(f"The {what} must be an http(s) URL")

    host = parsed.hostname
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise UnsafeURLError(f"The {what} host '{host}' could not be resolved")
        addresses = [ipaddress.ip_address(info[4][0]) for info in infos]

    if not addresses or not all(_is_public(ip) for ip in addresses):
        raise UnsafeURLError(
            f"The {what} points to a private or local network address, which is not allowed on this server"
        )
