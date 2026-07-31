# Sentellent - Proof of Work mapped to the challenge rubric

Live status doc for the Aug 5, 11:59 PM submission (forms.gle/qWxabTxLjEkJ2LcEA). Each rubric requirement maps to verified evidence, a screenshot, or a re-runnable command. **Legend:** DONE = verified/committed | BLOCKED = waiting on external party | PENDING = not started.

## Submission checklist (Google Form)

| # | Form field | Status | Evidence |
|---|---|---|---|
| 1 | GitHub Repo Link | DONE | `https://github.com/Ramakrishna9-R09/sentellent-indian-equity-analyst` — frontend (`apps/web`), backend (`apps/api`), Dockerfiles, Terraform, workflows, migrations, tests, docs. |
| 2 | Live Application URL | DONE | Live over HTTPS: `https://sentellent.me` (ACM cert + ALB HTTPS listener, DNS at Namecheap) — `/health`, `/ready`, `/` all 200. |
| 3 | Proof of Cloud | DONE (CI/CD) / PENDING (console shots) | CI + Deploy AWS green on HEAD. AWS console screenshots to be captured; interim ECS/RDS/ECR screenshots available. |

**Bonus (submit by Aug 3):** on track — core is done; remaining work is external verification + screenshots.

## Core requirement: RAG + Dynamic Memory (LangGraph)

| Rubric item | Status | Evidence |
|---|---|---|
| **From Chat** — "I'm a conservative, dividend-focused investor and I avoid high-debt companies" updates investor persona memory | DONE | `extract_profile_patch` writes typed facts with chat provenance (`profile_fact`, versioned). 10 tests in `test_profiles.py` (conservative/income/avoid-debt extraction). |
| **From Data (RAG ingest)** — ingesting an article auto-extracts sentiment/impact/event + mentioned stocks, embeds it, updates rolling sentiment without being told | DONE | `tag_article` (Groq `json_object`, deterministic fallback) → `article_signal` + idempotent `stock_signal_daily` upsert. `mentioned_tickers` now extracted (live: `['RELIANCE','TCS','INFY']`). |
| **Retrieval (grounded + cited)** — "What should I buy this week?" screens high-debt names, returns cited picks in INR | DONE | Recommendation graph: profile hard rules (`max_debt_to_equity`, `avoid_high_debt`) filter before deterministic scoring; answer cites source docs; INR formatting. Live verified. |
| **From Scale — efficient retrieval & ranking** — cache/reuse embeddings, dedupe overlapping news, rank with testable logic (not one LLM call per stock) | DONE | Content-addressed `embedding_cache` (sha256+model), source fingerprints, chunk-hash dedupe, deterministic `_rank_candidates` score (no per-stock LLM). |
| **From Scale — robust concurrent ingestion** — two jobs for same ticker must be idempotent, no duplicate indexing / race | DONE | Unique active-job index, `pg_try_advisory_lock(hashtext(stock_id))`, `INSERT ON CONFLICT`, unique fingerprints, `SELECT FOR UPDATE SKIP LOCKED`. Verified by design + code. |

## Feature checklist

### 1. Authentication & stock ingestion

| Rubric item | Status | Evidence |
|---|---|---|
| User logs in via OAuth | DONE (code) / PENDING (console) | Google OpenID Connect (`openid email profile` only). Session-cookie flow verified locally; live login redirects to Google with `redirect_uri=https://sentellent.me/api/auth/google/callback`. Requires Google Console redirect URI + Test Users to actually sign in. |
| **CRITICAL:** `harisankar@sentellent.com` + `naga@sentellent.com` as Test Users | PENDING | User action in Google Cloud Console OAuth consent screen. |
| Follow an NSE/BSE ticker → fetch fundamentals + news → chunk → embed → index into vector store | DONE | RELIANCE/TCS ingested: Screener fundamentals, Yahoo price, Google News RSS (67 RELIANCE + 77 TCS articles), chunked + embedded into pgvector. |
| Store NSE & BSE IDs per stock | DONE | RELIANCE(500325), TCS(532540), HDFCBANK(500180), INFY(500209), ITC(500875). Exposed in `StockResponse`. |

### 2. Agent workflow

| Rubric item | Status | Evidence |
|---|---|---|
| **Ingest:** follow ticker → pull fundamentals (screener.in) + Indian news (RSS) → chunk+embed → **LLM tags each article's sentiment/impact/event and the stocks it mentions** | DONE | Groq `llama-3.3-70b-versatile` tagging (json_object mode; tool-calling rejected 400 by Groq, fixed). 144 tagged signals, confidence up to 0.90. |
| **Query:** "What's the sentiment on TCS this week?" → retrieve → update memory graph → cited INR answer | DONE | Live over HTTP: 8 retrieved sources, claims + citations (title/publisher/url/date/excerpt). Answer audit persisted (`validation_status=validated`). |
| **Query:** "Recommend stocks for my profile" → persona vector, match & score (growth/value/stability/momentum/quality) → apply user rules → cited picks with one-line reason | DONE | Persona embedding written on profile update (`profiles.py`); deterministic weighted scorer + hard exclusions; cited one-line rationale. Live verified (RELIANCE 38.44/100). |
| **Anti-hallucination:** unsupported claims → "I don't have that in the ingested data", no invented numbers | DONE | `_compose` data-gap response + `_validate` rejects uncited claims (`validation_status` in `answer_audit`). |

### 3. Infrastructure & DevOps

| Rubric item | Status | Evidence |
|---|---|---|
| Dockerized application | DONE | `docker-compose.yml` (postgres/api/web/worker) + `docker/*.Dockerfile`. Local stack running and verified. |
| Terraform provisions resources incl. vector store | DONE | `infra/modules/{network,data,registry,ecs,edge,scheduler,observability,iam}`; RDS PostgreSQL + pgvector (`db_engine_version=18.3`). |
| CI/CD auto-deploy on push to main | DONE | `.github/workflows/{ci,deploy}.yml` — OIDC auth, image build/push to ECR, Terraform apply, Alembic migration task, ECS rollout, live smoke test. Green on HEAD. |
| Scheduled refresh worker (cron) | DONE | EventBridge schedule → ECS RunTask worker (`infra/modules/scheduler`); worker also polls follow-triggered jobs. |

## Phase coverage (recommended build path)

| Phase | Coverage | Status |
|---|---|---|
| Phase 1 — Foundation | RAG chat live on AWS, one NSE stock ingested, one grounded cited INR answer | DONE (HTTPS live) |
| Phase 2 — Integration | fundamentals + news RSS, chunk/embed/index, LLM per-stock tagging, retrieval + citation tools, cron refresh | DONE |
| Phase 3 — The Brain | persona memory from chat, persona vector, match/score to persona, anti-hallucination, INR correctness | DONE |

## Evidence bank

### Live/local data verified 2026-07-31
- 5 seed stocks with NSE/BSE IDs; 144 `source_document` news rows + fundamentals + price rows
- 72 `document_chunk` rows with pgvector embeddings (deterministic fallback model — documented non-production path without an embedding key)
- 144 `article_signal` rows (sentiment/impact/event/confidence/mentioned_tickers); `stock_signal_daily` aggregates
- `answer_audit` rows: `validation_status=validated`, model + latency recorded
- RDS live: `sentellent-equity-analyst-dev-rag.cf064ki6yt4a.ap-south-1.rds.amazonaws.com` available, PostgreSQL 18.3

### Unit tests (46 passing)
`cd apps/api && python -m pytest -q` — settings(4), profiles(10), ingestion(11), agent(4), embeddings(4), cache(6), main(4), rate-limit(3).

### Pipeline
`gh run list --limit 3` — CI + Deploy AWS green on `c266b57`.

## Open blockers (external)

| # | Blocker | Owner | Unblocks |
|---|---|---|---|
| 1 | ~~AWS CloudFront account verification~~ — resolved: HTTPS served directly on the ALB with an ACM cert for `sentellent.me`, DNS at Namecheap | User | HTTPS live URL (DONE) |
| 2 | Google Console: add redirect URI `https://sentellent.me/api/auth/google/callback` and Test Users `harisankar@`, `naga@sentellent.com` | User | Sign-in for demo + reviewers |

## Quick evidence commands

```sh
curl -s https://sentellent.me/health
docker compose up --build
cd apps/api && python -m pytest -q
gh run list --limit 3
```
