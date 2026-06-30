import httpx


class HTTPClient:
    def __init__(self, default_timeout: float = 10.0) -> None:
        self.client: httpx.AsyncClient | None = None
        self.default_timeout = default_timeout

    async def init(self) -> None:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.default_timeout)

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None

    async def get(self) -> httpx.AsyncClient:
        if not self.client:
            raise RuntimeError("HTTP client is not initialized")
        return self.client


http_client = HTTPClient()
