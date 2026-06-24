import httpx

from src.core.http.client import http_client


async def get_http_client() -> httpx.AsyncClient:
    return await http_client.get()
