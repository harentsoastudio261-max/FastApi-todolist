# Rate limiting

The API applies fixed-window quotas through two independent boundaries:

```text
request -> RateLimitMiddleware -> IP quota -> route/service -> account or user quota
```

The middleware protects the route before its controller is called. Application services apply the second quota where a reliable identity is available. Both use the shared `rate_limit_buckets` database table, so quotas work across multiple API processes connected to the same MySQL database.

## Protected routes

| Route | IP quota | Account or user quota |
|---|---:|---:|
| `POST /auth/login` | 10 / minute | 5 / email / 15 minutes |
| `POST /auth/register` | 5 / hour | 3 / email / hour |
| `POST /auth/refresh` | 30 / minute | 20 / user / 15 minutes |
| `POST /tasks/summary` | 10 / minute | 10 / user / 15 minutes |
| `POST /task_creation` | 10 / minute | 20 / user / hour |

`/tasks/summary` now requires an authenticated user so the user quota can be enforced. Its worker behavior is unchanged after a summary has been queued.

Login and registration use a normalized email as the account identifier because a user record may not exist yet. Refresh, summary and AI generation use the authenticated or resolved user id.

## Client response

An exceeded quota returns `429` with the standard error envelope and a `Retry-After` header:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests"
  }
}
```

Requests subject to an IP quota also return `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers.

## Configuration and deployment

All quotas are environment variables beginning with `RATE_LIMIT_`; see `.env.example` for the complete list. Set a unique, high-entropy `RATE_LIMIT_KEY_SECRET` in production. The limiter stores an HMAC hash of the IP or account/user identifier, not the raw value.

The middleware relies on `request.client.host`. Behind a reverse proxy, configure Uvicorn or the platform proxy-header handling so this value is the real client IP, and only trust forwarding headers from your own proxy infrastructure. Do not pass arbitrary client-provided forwarding headers through to the application.

The project currently creates tables through `Base.metadata.create_all`. For a deployed database, add the `rate_limit_buckets` table through the normal migration process before rolling out multiple API instances.
