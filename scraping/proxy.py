from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import quote


@dataclass
class ProxyRotator:
    rotate_seconds: int
    hosts: list[str]
    username: str = ""
    password: str = ""
    port: str = ""
    index: int = 0
    last_rotated_at: float = 0.0

    @classmethod
    def from_env(cls, rotate_seconds: int) -> "ProxyRotator":
        def host_number(item: tuple[str, str]) -> int:
            suffix = item[0].removeprefix("PROXY_HOST_")
            return int(suffix) if suffix.isdigit() else 999

        hosts = [value for key, value in sorted(os.environ.items(), key=host_number) if key.startswith("PROXY_HOST_") and value.strip()]
        return cls(
            rotate_seconds=rotate_seconds,
            hosts=hosts,
            username=os.getenv("PROXY_USER", ""),
            password=os.getenv("PROXY_PASS", ""),
            port=os.getenv("PROXY_PORT", ""),
            last_rotated_at=time.monotonic(),
        )

    def requests_proxy(self) -> dict[str, str] | None:
        if not (self.hosts and self.username and self.password and self.port):
            return None
        self._rotate_if_needed()
        host = self.hosts[self.index % len(self.hosts)]
        username = quote(self.username, safe="")
        password = quote(self.password, safe="")
        proxy_url = f"socks5://{username}:{password}@{host}:{self.port}"
        return {"http": proxy_url, "https": proxy_url}

    def _rotate_if_needed(self) -> None:
        if time.monotonic() - self.last_rotated_at < self.rotate_seconds:
            return
        self.index = (self.index + 1) % len(self.hosts)
        self.last_rotated_at = time.monotonic()
