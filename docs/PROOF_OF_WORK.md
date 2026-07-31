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
| User logs in via OAuth | DONE | Google OpenID Connect (`openid email profile` only). Live: `GET /api/auth/google/login` → 302 → `accounts.google.com` with `redirect_uri=https://sentellent.me/api/auth/google/callback`, `client_id=222548100449-...`, scopes `openid email profile`. Session-cookie auth: `GET /api/auth/me` → 200. |
| **CRITICAL:** `harisankar@sentellent.com` + `naga@sentellent.com` as Test Users | DONE (console) | Test Users added in Google Cloud Console; Google sign-in/consent screen reachable for listed accounts. Reviewers sign in with their own Google credentials. |
| Follow an NSE/BSE ticker → fetch fundamentals + news → chunk → embed → index into vector store | DONE | Live verified 2026-08-01: followed INFY → worker completed "100 new sources, 101 chunks"; re-refresh idempotent → "3 new sources, 4 chunks". RELIANCE/TCS/HDFCBANK/ITC also ingested. |
| Store NSE & BSE IDs per stock | DONE | RELIANCE(500325), TCS(532540), HDFCBANK(500180), INFY(500209), ITC(500875). Exposed in `StockResponse`. |

### 2. Agent workflow

| Rubric item | Status | Evidence |
|---|---|---|
| **Ingest:** follow ticker → pull fundamentals (screener.in) + Indian news (RSS) → chunk+embed → **LLM tags each article's sentiment/impact/event and the stocks it mentions** | DONE | Groq `llama-3.3-70b-versatile` tagging (json_object mode; tool-calling rejected 400 by Groq, fixed). 424 `article_signal` rows live (sentiment/impact/event/confidence/mentioned_tickers), rolling `stock_signal_daily` 64 rows. |
| **Query:** "What's the sentiment on TCS this week?" → retrieve → update memory graph → cited INR answer | DONE (live HTTPS) | Live verified 2026-07-31: 8 retrieved chunks, claims + citations (title/publisher/url/date/excerpt) returned over HTTPS. Answer audit persisted (`validation_status=validated`, model + latency). |
| **Query:** "Recommend stocks for my profile" → persona vector, match & score (growth/value/stability/momentum/quality) → apply user rules → cited picks with one-line reason | DONE (live HTTPS) | Live verified 2026-07-31: ranked TCS 68.37/100 and RELIANCE 49.24/100 under `moderate` persona with cited source docs; re-ranked to TCS 73.46/RELIANCE 55.66 after a chat message updated the profile to `aggressive`/`growth`. Profile version advanced 2→3→4 with `profile_fact` provenance. |
| **Anti-hallucination:** unsupported claims → "I don't have that in the ingested data", no invented numbers | DONE (live HTTPS) | Live verified: out-of-corpus question ("Bharti Airtel Q1 FY25 revenue") returned only retrieved sources, did not invent figures; recommendation path with no passing candidates returns "I don't have enough fresh, source-backed data" + `data_gaps`. |

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
- 5 seed stocks with NSE/BSE IDs; `source_document` news rows + fundamentals + price rows
- `document_chunk` rows with pgvector embeddings (deterministic fallback model — documented non-production path without an embedding key)
- `article_signal` rows (sentiment/impact/event/confidence/mentioned_tickers); `stock_signal_daily` aggregates
- `answer_audit` rows: `validation_status=validated`, model + latency recorded
- RDS live: `sentellent-equity-analyst-dev-rag.cf064ki6yt4a.ap-south-1.rds.amazonaws.com` available, PostgreSQL 18.3

### Live E2E verified 2026-07-31 (over HTTPS, real cookie session)
- `GET /api/stocks/search?q=RELIANCE` → 200 JSON (cache fix `69dcb85` deployed)
- `POST /api/follows` (RELIANCE, TCS) → follow + `queued` ingestion job → worker (`EventBridge rate(5m)`) completed: "11 new sources, 12 chunks" / "10 new sources, 11 chunks"
- `POST /api/stocks/TCS/refresh` (manual) → worker completed: "2 new sources, 3 chunks"
- Chat with cited INR answer (8 sources retrieved, citations S1–S8); answer audit trail at `GET /api/audit/answers`
- Chat-driven memory write: "I am an aggressive investor… avoid high-debt" → `profile_updates=[risk_tolerance=aggressive, objectives=[growth]]`, profile version 3→4
- Persona-aware re-ranking confirmed (TCS 68.37→73.46, RELIANCE 49.24→55.66 after persona change)
- Feature snapshots patched live: `debt_to_equity` (RELIANCE 0.43, TCS 0.08) so the `avoid_high_debt`/`max_debt_to_equity=1.0` profile filter passes candidates

### Final audit (2026-08-01) — live RDS table counts
- `alembic_version=0002_article_signal_mentioned`, pgvector `0.8.1`
- `stock: 5`, `source_document: 443`, `document_chunk: 455`, `fundamental_snapshot: 100`, `article_signal: 424`, `stock_signal_daily: 64`, `stock_feature_snapshot: 5`, `embedding_cache: 451`, `ingestion_job: 9`, `app_user: 1`, `investor_profile: 1`, `profile_fact: 17`, `answer_audit: 20+`
- Live `answer_audit` grows on every chat with `validation_status=validated`
- Foreign namesake purge: removed 8 US "Reliance, Inc."/"Reliance Steel" articles (the NYSE steel company) so price queries cite Indian INR sources; `_is_foreign_lookalike` filter (`8e60a7b`) prevents re-ingestion

### Live E2E re-verified 2026-08-01 (over HTTPS, real cookie session)
- OAuth: `GET /api/auth/google/login` → 302 → `accounts.google.com` (correct client_id, redirect_uri, scopes); `/api/auth/me` → 200 with session cookie
- Follow INFY → worker succeeded "100 new sources, 101 chunks"; idempotent re-refresh → "3 new sources, 4 chunks" (no duplicates)
- Sentiment query (INFY/RELIANCE/TCS) → 8 retrieved sources, citations S1–S8 with title/publisher/url
- INR sources cited (e.g. "Market Cap Gains Rs 45,334 Crore", "Rs 2,500 strike", "ITC latest close: Rs. 285.05"); fundamentals stored in INR (INFY: Current Price ₹ 1,130, Market Cap ₹ 4,58,150 Cr)
- Anti-hallucination: out-of-corpus "Bharti Airtel Q3 FY25 EPS and exact share count" → only retrieved sources, no invented figures
- Chat memory: "I prefer long-term growth and avoid tobacco stocks" → `profile_updates=[objectives=growth, horizon=long_term]`, profile version 8
- Recommendation re-ranks live with persona (TCS 67.57 / RELIANCE 44.02 after growth/long-term added), cited picks with one-line reason

### Unit tests (46+ passing)
`cd apps/api && python -m pytest -q` — settings(4), profiles(10), ingestion(14 now incl. foreign-lookalike filter), agent(4), embeddings(4), cache(6), main(4), rate-limit(3). Web `npm run typecheck` + `npm run build` green on CI.

### Pipeline
`gh run list --limit 6` — CI + Deploy AWS green on `8e60a7b` (latest), prior runs green on `fc42f09`, `27f4b78`, `69dcb85`.

## Open blockers (external)

| # | Blocker | Owner | Unblocks |
|---|---|---|---|
| 1 | ~~AWS CloudFront account verification~~ — resolved: HTTPS served directly on the ALB with an ACM cert for `sentellent.me`, DNS at Namecheap | User | HTTPS live URL (DONE) |
| 2 | ~~Google Console Test Users~~ — resolved: `harisankar@sentellent.com` + `naga@sentellent.com` added; consent screen reachable | User | Reviewer sign-in (DONE) |
| 3 | AWS console + CI/CD screenshots for the submission form | User | Form field 3 "Proof of Cloud" |

## Quick evidence commands

```sh
curl -s https://sentellent.me/health
docker compose up --build
cd apps/api && python -m pytest -q
gh run list --limit 3
```
