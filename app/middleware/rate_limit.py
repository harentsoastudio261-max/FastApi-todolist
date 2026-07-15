"""HTTP middleware for route-specific IP rate limits."""
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.rate_limit_service import RateLimitDecision, RateLimitService


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce IP quotas before a protected route reaches a controller."""

    def __init__(self, app, *, rate_limiter: RateLimitService) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        decision = self._rate_limiter.consume_ip_request(
            request.method,
            request.url.path,
            self._client_ip(request),
        )
        if decision is not None and not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests",
                    }
                },
                headers=self._headers(decision),
            )

        response = await call_next(request)
        if decision is not None:
            response.headers.update(self._headers(decision))
        return response

    @staticmethod
    def _client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _headers(decision: RateLimitDecision) -> dict[str, str]:
        if decision.limit is None or decision.remaining is None:
            return {}

        headers = {
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
        }
        if not decision.allowed:
            headers["Retry-After"] = str(decision.retry_after_seconds)
        return headers
