from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ai.dependencies import get_ai_client
from src.core.ai.interfaces import BaseAIClient
from src.core.ai.schemas import DiagnosticResponse
from src.core.database.session import get_session
from src.core.utils.datetime_utils import get_utc_now
from src.system.dependencies import get_health_service, get_readiness_service
from src.system.readiness import ReadinessService, overall_status
from src.system.schemas import HealthCheckResponse, ReadyResponse
from src.system.services import HealthService

router = APIRouter()


@router.get("/health/", response_model=HealthCheckResponse)
@router.head("/health/", response_model=HealthCheckResponse, include_in_schema=False)
async def check_health(
    health_service: HealthService = Depends(get_health_service),
    session: AsyncSession = Depends(get_session),
) -> HealthCheckResponse:
    """Health check endpoint that verifies the service and dependencies are running."""
    return await health_service.get_status(session=session)


@router.get("/health/ready", response_model=ReadyResponse)
async def check_ready(
    response: Response,
    service: ReadinessService = Depends(get_readiness_service),
) -> ReadyResponse:
    """Barcha komponentlar holati (monitoring / load balancer uchun).

    200 — "ok" yoki "degraded" (fon xizmatlari: RabbitMQ/Celery yiqilgan,
    chat ishlayveradi); 503 — "down" (Postgres/Redis/Qdrant/Ollama).
    Tafsilotlar (kechikish, sabab) faqat admin endpointida: /v1/admin/system.
    """
    components = await service.check_all()
    state = overall_status(components)
    if state == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status=state, components={c.name: c.ok for c in components})


@router.get("/time/", response_model=dict)
def get_utc_time() -> dict[str, str]:
    """Endpoint to get the current UTC time in ISO format."""
    now = get_utc_now()
    return {"time": now.replace(microsecond=0).isoformat()}


@router.get(
    "/diagnostic",
    summary="AI connectivity diagnostic.",
    response_model=DiagnosticResponse,
)
async def diagnostic(
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> DiagnosticResponse:
    return await ai_client.ping()
