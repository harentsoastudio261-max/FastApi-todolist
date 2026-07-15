"""Application service for persistent IP and account rate limits."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import new as hmac_new

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException
from app.core.rate_limit import RateLimitPolicies, RateLimitScope
from app.core.database import SessionLocal
from app.repositories.rate_limit_repository import RateLimitRepository


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int | None
    remaining: int | None
    retry_after_seconds: int


class RateLimitService:
    """Consumes quotas in an independent transaction so denied attempts persist."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        policies: RateLimitPolicies,
        *,
        secret: str,
        enabled: bool,
    ) -> None:
        self._session_factory = session_factory
        self._policies = policies
        self._secret = secret.encode("utf-8")
        self._enabled = enabled

    def consume(self, scope: RateLimitScope, subject: str) -> RateLimitDecision:
        if not self._enabled:
            return RateLimitDecision(True, None, None, 0)

        policy = self._policies.get(scope)
        with self._session_factory() as db:
            repository = RateLimitRepository(db)
            consumption = repository.consume(
                scope=scope.value,
                subject_hash=self._subject_hash(scope, subject),
                max_requests=policy.max_requests,
                window_seconds=policy.window_seconds,
                now=datetime.now(UTC).replace(tzinfo=None),
            )
            db.commit()

        return RateLimitDecision(
            allowed=consumption.allowed,
            limit=consumption.limit,
            remaining=consumption.remaining,
            retry_after_seconds=consumption.retry_after_seconds,
        )

    def enforce(self, scope: RateLimitScope, subject: str) -> RateLimitDecision:
        decision = self.consume(scope, subject)
        if not decision.allowed:
            raise RateLimitExceededException(decision.retry_after_seconds)
        return decision

    def consume_ip_request(self, method: str, path: str, client_ip: str) -> RateLimitDecision | None:
        scope = self._policies.ip_scope_for_route(method, path)
        if scope is None:
            return None
        return self.consume(scope, client_ip)

    def _subject_hash(self, scope: RateLimitScope, subject: str) -> str:
        normalized_subject = subject.strip().casefold() or "unknown"
        payload = f"{scope.value}:{normalized_subject}".encode("utf-8")
        return hmac_new(self._secret, payload, sha256).hexdigest()


def build_rate_limit_service() -> RateLimitService:
    return RateLimitService(
        SessionLocal,
        RateLimitPolicies(settings),
        secret=settings.rate_limit_key_secret,
        enabled=settings.rate_limit_enabled,
    )
