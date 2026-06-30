import logging

from fastapi import FastAPI

from src.core.http.client import http_client

logger = logging.getLogger("http")


async def on_http_startup(app: FastAPI) -> None:
    await http_client.init()

    app.state.http_client = http_client

    logger.info("HTTP client initialized successfully.")


async def on_http_shutdown(app: FastAPI) -> None:
    await http_client.close()

    logger.info("HTTP client closed.")
