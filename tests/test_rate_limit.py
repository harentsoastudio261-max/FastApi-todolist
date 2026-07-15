"""Regression tests for the database-backed rate-limit boundaries."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.exceptions import RateLimitExceededException
from app.core.rate_limit import RateLimitPolicies, RateLimitScope
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.entities import RateLimitBucket
from app.services.rate_limit_service import RateLimitService


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        RateLimitBucket.__table__.create(self.engine)
        session_factory = sessionmaker(bind=self.engine, future=True)
        policies = RateLimitPolicies(
            Settings(
                rate_limit_login_ip_limit=1,
                rate_limit_login_account_limit=1,
            )
        )
        self.rate_limiter = RateLimitService(
            session_factory,
            policies,
            secret="test-rate-limit-secret",
            enabled=True,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_account_limit_persists_a_rejected_attempt(self) -> None:
        self.rate_limiter.enforce(RateLimitScope.LOGIN_ACCOUNT, "person@example.com")

        with self.assertRaises(RateLimitExceededException) as raised:
            self.rate_limiter.enforce(RateLimitScope.LOGIN_ACCOUNT, "person@example.com")

        self.assertGreater(raised.exception.retry_after_seconds, 0)

    def test_ip_middleware_returns_429_and_rate_headers(self) -> None:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, rate_limiter=self.rate_limiter)

        @app.post("/auth/login")
        def login() -> dict[str, bool]:
            return {"ok": True}

        client = TestClient(app)
        first = client.post("/auth/login")
        second = client.post("/auth/login")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["X-RateLimit-Limit"], "1")
        self.assertEqual(first.headers["X-RateLimit-Remaining"], "0")
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()["error"]["code"], "rate_limit_exceeded")
        self.assertIn("Retry-After", second.headers)


if __name__ == "__main__":
    unittest.main()
