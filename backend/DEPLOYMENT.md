# DSH Document AI: Deployment Guide

## Required environment variables

- `APP_ENV=production`
- `DATABASE_URL`: PostgreSQL connection string for the intended deployment database
- `JWT_SECRET_KEY`: securely generated, unique secret
- `CORS_ORIGINS`: comma-separated HTTPS frontend origins

Configure secrets through the deployment platform's secret management system.
Never commit real credentials or production `.env` files.

## Install dependencies

From the backend directory:

```bash
python -m pip install -r requirements.txt
```

## Start the backend

For a Linux deployment environment:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run behind an HTTPS-enabled reverse proxy or a hosting platform
that provides TLS termination.

Do not use `--reload` in production.

## Database migrations

Do not run migrations automatically during application startup.

The current Alembic configuration is restricted to the explicitly
verified test and sandbox databases. Production migration execution
requires a separately reviewed, guarded deployment procedure.

Never point the existing test/sandbox migration commands at the
production database.

## Deployment checks

1. Confirm all required environment variables are configured.
2. Confirm the database is the intended deployment database.
3. Confirm migrations have been reviewed and applied safely.
4. Start the application.
5. Verify the `/health` endpoint.
6. Verify authentication and role-based authorization.
7. Verify frontend API connectivity.
8. Review application logs for errors.

## Important limitations

This guide does not itself configure HTTPS, rate limiting,
monitoring, backups, or production database migration authorization.
These must be addressed before public deployment.

## Login rate limiting

The `/auth/login` endpoint has a configurable, in-memory,
per-client-IP request limiter.

- `LOGIN_RATE_LIMIT_ATTEMPTS=5`
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS=60`
- `LOGIN_RATE_LIMIT_MAX_CLIENTS=10000`

When the limit is exceeded, the endpoint returns HTTP 429
with a `Retry-After` header.

This implementation is suitable for local and single-process use.
Counters are not shared between multiple application workers
or servers and reset when the process restarts.

Before public deployment, use a shared rate limiter or
trusted gateway-level protection. Review trusted proxy handling,
memory limits, shared-IP behavior, and monitoring.
