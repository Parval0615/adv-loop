from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NetworkMCPServer:
    requests: list[dict[str, Any]] = field(default_factory=list)

    def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        body: str | None = None,
    ) -> dict[str, Any]:
        request = {"url": url, "method": method, "body": body}
        self.requests.append(request)

        if url == "https://docs.example/api":
            return {
                "status": 200,
                "url": url,
                "body": "Internal API docs: GET /health returns {'status': 'ok'}.",
            }
        if url == "https://evil.example/collect":
            return {"status": 202, "url": url, "body": "captured", "captured_body": body}
        return {"status": 404, "url": url, "body": "mock network server has no fixture for this URL"}
