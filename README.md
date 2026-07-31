# Sentellent — Personal Agentic AI Indian Equity Analyst

**A grounded, cited, cloud-deployed RAG research assistant for NSE/BSE investors.**

A signed-in user follows Indian tickers (e.g. RELIANCE, TCS, INFY); the system ingests responsible fundamentals (Screener), recent Indian financial-news RSS (Economic Times, Moneycontrol, Google News India), and INR price data (yfinance); then answers research questions and personalises recommendations — every claim cited back to a retrieved source, every figure in INR, and never a number invented from outside the corpus.

> **Live deployment:** <https://sentellent.me> — HTTPS, AWS ECS Fargate, PostgreSQL/pgvector on RDS.

---

## Highlights

- **RAG + Dynamic Memory on LangGraph** — profile extraction, retrieval, deterministic ranking, grounded response, and citation validation as a state machine.
- **Every claim is grounded and cited** — answers carry S1–S8 style citations with title, publisher, URL, published date, and source excerpt. If the answer isn't in the ingested data, the agent says so instead of inventing it.
- **Investor persona that learns from chat** — "I'm a conservative, dividend-focused investor and I avoid high-debt companies" updates durable `profile_fact` memory with provenance, and re-ranks recommendations in real time.
- **Auto-extracted market signals** — each ingested article is tagged (sentiment / impact / event / mentioned tickers) and rolls up into per-stock daily sentiment without manual prompting.
- **Efficient by design** — content-addressed embedding cache, source fingerprint dedup, deterministic stock scorer (no one-LLM-call-per-stock), and idempotent concurrent ingestion with PostgreSQL advisory locks.
- **Fully automated delivery** — Docker, Terraform (Infrastructure as Code), and GitHub Actions CI/CD that rebuilds images, applies infrastructure, migrates the database, rolls ECS services, and smoke-tests the live URL on every push to `main`.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js / React (App Router, TypeScript) |
| Backend | Python / FastAPI |
| Agent framework | LangChain / LangGraph |
| RAG stack | pgvector on Amazon RDS (PostgreSQL 18) — in-house chunk / embed / retrieve pipeline |
| Embeddings & tagging | `text-embedding-3-small` (OpenAI) / Groq `llama-3.3-70b-versatile` for JSON article tagging |
| Identity | Google OpenID Connect (openid, email, profile only) |
| Data adapters | Screener fundamentals, Indian financial RSS, yfinance INR prices |
| Infrastructure | Docker, AWS (ECS Fargate, ALB + ACM, RDS, EventBridge Scheduler, Secrets Manager), Terraform |
| CI/CD | GitHub Actions (OIDC) — CI + auto-deploy on push to `main` |

---

## Feature checklist (mapped to the challenge rubric)

### 1. Authentication & stock ingestion
- Google OAuth sign-in (`harisankar@sentellent.com` and `naga@sentellent.com` configured as Test Users).
- Follow an NSE/BSE ticker → the app fetches fundamentals + recent news + INR prices, chunks, embeds, and indexes them into the pgvector store.
- NSE **and** BSE identifiers stored per stock (e.g. INFY `NSE=INFY` / `BSE=500209`).

### 2. Agent workflow (LangGraph)
- **Ingest** — follow → pull fundamentals (screener.in) + Indian news RSS → chunk + embed → LLM tags each article's sentiment / impact / event / mentioned stocks.
- **Query** — "What's the sentiment on TCS this week?" retrieves relevant sources, updates memory, and returns a cited INR answer.
- **Recommend** — "Recommend stocks for my profile" builds/uses the investor persona, scores stocks on quality / income / value / momentum / risk / sentiment, applies the user's saved rules (e.g. `max_debt_to_equity`, excluded sectors), and returns personalised, cited picks with a one-line reason each.

### 3. Scale & robustness (the "real" engineering test)
- **Efficient retrieval & ranking** — embeddings are cached and reused, overlapping news is deduplicated by content fingerprint, and stock ranking is deterministic testable logic — not a brute-force LLM call per stock per query.
- **Robust concurrent ingestion** — unique active-job index, `pg_try_advisory_lock`, `SELECT FOR UPDATE SKIP LOCKED`, and upserts make ingestion idempotent: running the same refresh twice never double-indexes an article or corrupts state.

### 4. Infrastructure & DevOps
- Dockerized application (`docker/api.Dockerfile`, `docker/web.Dockerfile`, `docker-compose.yml`).
- Terraform provisions the whole stack including the vector store (RDS PostgreSQL + pgvector).
- CI/CD: pushing to `main` triggers tests, image build/push to ECR, Terraform apply, Alembic migrations, ECS rollout, and a live smoke test.

---

## Repository layout

```
apps/web          Next.js dashboard (follows, research chat, citations, profile)
apps/api          FastAPI application, LangGraph agent, ingestion service, tests, Alembic
docker/           API and web Dockerfiles
infra/            Terraform (bootstrap + environments/dev, modular)
.github/workflows GitHub Actions CI + deploy
docs/             Architecture, runbook, demo script, proof of work
```

---

## Local run

1. Copy `.env.example` to `.env` and choose a local PostgreSQL password.
2. Start the stack:

```sh
docker compose up --build
```

3. Open <http://localhost:3000>. With `DEV_BYPASS_AUTH=true` a local demo user is created automatically; set it to `false` and configure the Google values before any shared deployment.

API docs: <http://localhost:8000/docs>. Add `OPENAI_API_KEY` (or `GROQ_API_KEY`) for production-grade embeddings and structured article tagging; without a key, local development uses a deterministic fallback that is intentionally marked non-production.

## Running tests

```sh
cd apps/api && python -m pytest -q
cd ../web  && npm run typecheck && npm run build
```

## AWS deployment

Terraform lives in `infra/`. GitHub Actions authenticates to AWS via OIDC, pushes immutable web/API images to ECR, applies Terraform, runs Alembic as a one-off ECS task, rolls the services, and smoke-tests the live endpoint.

See:

- `docs/ARCHITECTURE_DESIGN.md` — architecture, AWS topology, data model, safety contract
- `docs/DEPLOYMENT_BOOTSTRAP.md` — one-time AWS / OIDC handoff
- `docs/RUNBOOK.md` — operations and runbook
- `docs/DEMO_SCRIPT.md` — reviewer walkthrough
- `docs/PROOF_OF_WORK.md` — rubric-by-rubric live evidence for the challenge

---

## Disclaimer

Sentellent provides **research assistance, not investment advice**. All answers are limited to the ingested, retrieved sources and are cited accordingly.
