"""Database persistence for shared rate-limit counters."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.entities import RateLimitBucket


@dataclass(frozen=True)
class RateLimitConsumption:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimitRepository:
    def __init__(self, db: Session):
        self.db = db

    def consume(
        self,
        *,
        scope: str,
        subject_hash: str,
        max_requests: int,
        window_seconds: int,
        now: datetime,
    ) -> RateLimitConsumption:
        window_ends_at = now + timedelta(seconds=window_seconds)
        if self.db.bind and self.db.bind.dialect.name == "mysql":
            self._consume_with_mysql_upsert(
                scope=scope,
                subject_hash=subject_hash,
                now=now,
                window_ends_at=window_ends_at,
            )
        else:
            self._consume_with_row_lock(
                scope=scope,
                subject_hash=subject_hash,
                now=now,
                window_ends_at=window_ends_at,
            )

        bucket = self._get_bucket(scope, subject_hash)
        allowed = bucket.request_count <= max_requests
        remaining = max(0, max_requests - bucket.request_count)
        retry_after_seconds = max(1, ceil((bucket.window_ends_at - now).total_seconds()))
        return RateLimitConsumption(
            allowed=allowed,
            limit=max_requests,
            remaining=remaining,
            retry_after_seconds=retry_after_seconds,
        )

    def _consume_with_mysql_upsert(
        self,
        *,
        scope: str,
        subject_hash: str,
        now: datetime,
        window_ends_at: datetime,
    ) -> None:
        from sqlalchemy.dialects.mysql import insert

        is_expired = RateLimitBucket.window_ends_at <= now
        statement = insert(RateLimitBucket).values(
            scope=scope,
            subject_hash=subject_hash,
            request_count=1,
            window_started_at=now,
            window_ends_at=window_ends_at,
        )
        statement = statement.on_duplicate_key_update(
            request_count=case((is_expired, 1), else_=RateLimitBucket.request_count + 1),
            window_started_at=case((is_expired, now), else_=RateLimitBucket.window_started_at),
            window_ends_at=case((is_expired, window_ends_at), else_=RateLimitBucket.window_ends_at),
        )
        self.db.execute(statement)

    def _consume_with_row_lock(
        self,
        *,
        scope: str,
        subject_hash: str,
        now: datetime,
        window_ends_at: datetime,
    ) -> None:
        statement = (
            select(RateLimitBucket)
            .where(
                RateLimitBucket.scope == scope,
                RateLimitBucket.subject_hash == subject_hash,
            )
            .with_for_update()
        )
        bucket = self.db.execute(statement).scalar_one_or_none()
        if bucket is None:
            self.db.add(
                RateLimitBucket(
                    scope=scope,
                    subject_hash=subject_hash,
                    request_count=1,
                    window_started_at=now,
                    window_ends_at=window_ends_at,
                )
            )
        elif bucket.window_ends_at <= now:
            bucket.request_count = 1
            bucket.window_started_at = now
            bucket.window_ends_at = window_ends_at
        else:
            bucket.request_count += 1
        self.db.flush()

    def _get_bucket(self, scope: str, subject_hash: str) -> RateLimitBucket:
        statement = select(RateLimitBucket).where(
            RateLimitBucket.scope == scope,
            RateLimitBucket.subject_hash == subject_hash,
        )
        return self.db.execute(statement).scalar_one()
