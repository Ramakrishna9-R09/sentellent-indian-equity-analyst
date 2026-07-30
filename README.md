# Sentellent Personal Agentic AI Indian Equity Analyst

A deployable RAG research assistant for NSE/BSE investors. It ingests responsible fundamentals, Indian financial-news RSS, and INR price data; maintains a user-owned investor profile; and answers only from cited evidence.

The full architecture, AWS topology, data model, safety contract, and delivery plan are in [the design document](docs/ARCHITECTURE_DESIGN.md).

## What is implemented

- Next.js/React dashboard for following stocks, research chat, source citations, and investor profile facts.
- FastAPI API with Google OpenID Connect flow (plus an explicitly local-only developer bypass).
- PostgreSQL + pgvector schema, Alembic migrations, content-addressed embedding cache, and HNSW vector index.
- LangGraph research workflow: profile extraction, retrieval, deterministic ranking, grounded response, and citation validation.
- Responsible Screener-compatible, RSS, and yfinance connector boundaries; idempotent per-ticker jobs with advisory locks and source fingerprints.
- Docker Compose local environment; Terraform AWS infrastructure; GitHub Actions CI and deployment workflow.

## Local run

1. Copy .env.example to .env and choose a local PostgreSQL password.
2. Start the application:

~~~sh
docker compose up --build
~~~

3. Open http://localhost:3000. With DEV_BYPASS_AUTH=true, a local demo user is created automatically. Set it to false and configure the Google values before any shared deployment.

The API documentation is at http://localhost:8000/docs. The worker continuously claims deduplicated refresh jobs. Add OPENAI_API_KEY for production embeddings and structured article tagging; without it, local development uses a deterministic fallback that is intentionally marked as non-production.

## Important OAuth handoff step

Before sending the application URL to Sentellent, configure the Google OAuth consent screen in Testing mode and add:

- harisankar@sentellent.com
- naga@sentellent.com

Only OpenID Connect scopes (openid, email, profile) are used. No Gmail or Calendar scopes are requested.

## AWS deployment

Terraform lives in infra/. GitHub Actions authenticates to AWS using OIDC, pushes immutable web/API images to ECR, applies Terraform, runs Alembic as a one-off ECS task, rolls the services, and smoke-tests the live endpoint.

See docs/DEPLOYMENT_BOOTSTRAP.md for the one-time AWS/OIDC handoff, docs/RUNBOOK.md for operations, and docs/DEMO_SCRIPT.md for the reviewer walkthrough.
