"""Rate-limit policies shared by HTTP middleware and application services."""
from dataclasses import dataclass
from enum import Enum

from app.core.config import Settings


class RateLimitScope(str, Enum):
    LOGIN_IP = "login_ip"
    LOGIN_ACCOUNT = "login_account"
    REGISTER_IP = "register_ip"
    REGISTER_ACCOUNT = "register_account"
    REFRESH_IP = "refresh_ip"
    REFRESH_USER = "refresh_user"
    SUMMARY_IP = "summary_ip"
    SUMMARY_USER = "summary_user"
    AI_IP = "ai_ip"
    AI_USER = "ai_user"


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: RateLimitScope
    max_requests: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise ValueError(f"{self.scope.value} max_requests must be positive")
        if self.window_seconds < 1:
            raise ValueError(f"{self.scope.value} window_seconds must be positive")


class RateLimitPolicies:
    """Builds explicit quotas from environment-backed application settings."""

    def __init__(self, settings: Settings) -> None:
        self._policies = {
            RateLimitScope.LOGIN_IP: RateLimitPolicy(
                RateLimitScope.LOGIN_IP,
                settings.rate_limit_login_ip_limit,
                settings.rate_limit_login_ip_window_seconds,
            ),
            RateLimitScope.LOGIN_ACCOUNT: RateLimitPolicy(
                RateLimitScope.LOGIN_ACCOUNT,
                settings.rate_limit_login_account_limit,
                settings.rate_limit_login_account_window_seconds,
            ),
            RateLimitScope.REGISTER_IP: RateLimitPolicy(
                RateLimitScope.REGISTER_IP,
                settings.rate_limit_register_ip_limit,
                settings.rate_limit_register_ip_window_seconds,
            ),
            RateLimitScope.REGISTER_ACCOUNT: RateLimitPolicy(
                RateLimitScope.REGISTER_ACCOUNT,
                settings.rate_limit_register_account_limit,
                settings.rate_limit_register_account_window_seconds,
            ),
            RateLimitScope.REFRESH_IP: RateLimitPolicy(
                RateLimitScope.REFRESH_IP,
                settings.rate_limit_refresh_ip_limit,
                settings.rate_limit_refresh_ip_window_seconds,
            ),
            RateLimitScope.REFRESH_USER: RateLimitPolicy(
                RateLimitScope.REFRESH_USER,
                settings.rate_limit_refresh_user_limit,
                settings.rate_limit_refresh_user_window_seconds,
            ),
            RateLimitScope.SUMMARY_IP: RateLimitPolicy(
                RateLimitScope.SUMMARY_IP,
                settings.rate_limit_summary_ip_limit,
                settings.rate_limit_summary_ip_window_seconds,
            ),
            RateLimitScope.SUMMARY_USER: RateLimitPolicy(
                RateLimitScope.SUMMARY_USER,
                settings.rate_limit_summary_user_limit,
                settings.rate_limit_summary_user_window_seconds,
            ),
            RateLimitScope.AI_IP: RateLimitPolicy(
                RateLimitScope.AI_IP,
                settings.rate_limit_ai_ip_limit,
                settings.rate_limit_ai_ip_window_seconds,
            ),
            RateLimitScope.AI_USER: RateLimitPolicy(
                RateLimitScope.AI_USER,
                settings.rate_limit_ai_user_limit,
                settings.rate_limit_ai_user_window_seconds,
            ),
        }
        self._ip_scopes_by_route = {
            ("POST", "/auth/login"): RateLimitScope.LOGIN_IP,
            ("POST", "/auth/register"): RateLimitScope.REGISTER_IP,
            ("POST", "/auth/refresh"): RateLimitScope.REFRESH_IP,
            ("POST", "/tasks/summary"): RateLimitScope.SUMMARY_IP,
            ("POST", "/task_creation"): RateLimitScope.AI_IP,
        }

    def get(self, scope: RateLimitScope) -> RateLimitPolicy:
        return self._policies[scope]

    def ip_scope_for_route(self, method: str, path: str) -> RateLimitScope | None:
        return self._ip_scopes_by_route.get((method, path))
