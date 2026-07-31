# Sentellent - Proof of Work & Evidence Map

Live status doc for the Aug 5 submission. Every item maps to verified evidence, a screenshot, or a command a reviewer can re-run. **Status legend:** DONE = verified/committed | BLOCKED = waiting on external party | PENDING = not started.

## 1. Live application

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1.1 | Public HTTP app is live | DONE | ALB `http://sentellent-equity-analyst-dev-al-157660511.ap-south-1.elb.amazonaws.com` — `/health`, `/ready`, `/` all return 200. |
| 1.2 | Public HTTPS app (CloudFront) | BLOCKED | `aws cloudfront create-distribution` fails with `AccessDenied: Your account must be verified before you can add new CloudFront resources`. AWS support case submitted; awaiting account verification. Once verified, flip `ENABLE_CLOUDFRONT=true` and re-run Deploy AWS. |
| 1.3 | RDS PostgreSQL + pgvector available | DONE | `sentellent-equity-analyst-dev-rag.cf064ki6yt4a.ap-south-1.rds.amazonaws.com` — status `available`, engine PostgreSQL `18.3`. |
| 1.4 | Live ingestion has real data | DONE | Live DB: 5 seed stocks (HDFCBANK, INFY, ITC, RELIANCE, TCS). News ingestion exercises on live follow. |

## 2. Local stack (recording fallback while HTTPS is blocked)

All verified 2026-07-31 against `docker compose` (postgres healthy, api:8000, web:3000, worker).

| # | Claim | Status | Evidence |
|---|---|---|---|
| 2.1 | Ingestion pulls 3 source types | DONE | RELIANCE + TCS ingested: Screener fundamentals, Yahoo Finance price, Google News RSS search feed (per-stock, query-driven). |
| 2.2 | News pipeline returns real articles | DONE | 67 RELIANCE + 77 TCS news `source_document` rows from `news.google.com/rss/search?q=<SYMBOL>+stock+when:14d`. |
| 2.3 | Groq LLM article tagging works | DONE | `tag_article` uses Groq `llama-3.3-70b-versatile` via `json_object` response format (tool-calling is rejected 400 by Groq for this model). 144 `article_signal` rows, confidence up to 0.90. |
| 2.4 | Chunks + embeddings stored | DONE | 72 `document_chunk` rows with pgvector embeddings (deterministic fallback model when no embedding key is set — documented design). |
| 2.5 | RAG research question with citations | DONE | `POST /api/chat/threads/{id}/messages` "What is the sentiment on TCS this week?" -> 8 retrieved sources, claims + citations with title/publisher/url/published_at/excerpt. |
| 2.6 | Recommendation intent + hard profile rules | DONE | "Which followed stock should I buy?" -> ranked candidate (RELIANCE 38.44/100) with cited rationale; citation IDs deduped. |
| 2.7 | Answer audit persisted | DONE | `answer_audit` row: `validation_status=validated`, model + latency recorded. |
| 2.8 | Auth session cookie flow works | DONE | Created session via `create_session`, exercised all chat endpoints over HTTP with cookie `sentellent_session`. |

## 3. Pipeline (GitHub Actions)

| # | Claim | Status | Evidence |
|---|---|---|---|
| 3.1 | CI green on HEAD | DONE | Run `30632082861` success on `3e36958` (46 tests pass, terraform fmt/validate, images build). Note: earlier failure was transient `registry.terraform.io` network timeout, re-run green. |
| 3.2 | Deploy AWS green on HEAD | DONE | Run `30632082863` success on `3e36958` (ECR push, terraform apply, alembic migration task, ECS rollout, live smoke test). |
| 3.3 | Deployment is OIDC-only | DONE | `.github/workflows/deploy.yml` + `infra/modules/iam` OIDC trust; no long-lived AWS keys in GitHub. |
| 3.4 | CloudFront flag wired for pipeline | DONE | `ENABLE_CLOUDFRONT` repo var drives `-var="enable_cloudfront=..."`; set to `false` until AWS verification lands. |

## 4. Unit test coverage (46 tests)

`apps/api/app/tests/` — run with `cd apps/api && python -m pytest -q`.

| Area | Tests |
|---|---|
| Settings/config | `test_config.py` (4) |
| Profile memory | `test_profiles.py` (10) |
| Ingestion (chunker, INR normalization, sentiment, heuristics) | `test_ingestion.py` (11) |
| Agent/citations/intent | `test_agent.py` (4) |
| Embeddings deterministic fallback | `test_embeddings.py` (4) |
| Cache | `test_cache.py` (6) |
| Health/API | `test_main.py` (4) |
| Rate limit | `test_rate_limit.py` (3) |

## 5. Demo script coverage (docs/DEMO_SCRIPT.md)

| Demo step | Status | Where it is proven |
|---|---|---|
| 1. Sign in with Google Test User | PENDING | Needs `http://localhost:8000/api/auth/google/callback` (local) or `https://<dist>.cloudfront.net/...` (live) registered in Google Console + Test Users added. Session-cookie auth itself verified (2.8). |
| 2. Search + follow RELIANCE/TCS | DONE local | Follows created for RELIANCE + TCS; ingestion job -> succeeded. |
| 3. Ingestion status + open source record | DONE local | 144 source rows; `GET /api/sources/{id}` works. |
| 4. "Sentiment on TCS this week?" + citations | DONE local | 8 cited sources returned (2.5). |
| 5. "I am a conservative, dividend-focused investor..." | DONE local | Profile extraction verified by `test_profiles.py` (10 tests). |
| 6. Profile page shows sourced memory fact | PENDING | Needs UI login; profile backend verified. |
| 7. Profile-matched recommendation + exclusions + INR | DONE local | 2.6; INR formatting + hard debt rule verified in code/tests. |
| 8. GitHub Actions + AWS screenshots | DONE | 3.1–3.3; AWS console screenshots pending HTTPS for the "final" state. |

## 6. Open blockers

1. **AWS CloudFront account verification** — support case submitted; response to `pavankumarchowdary9010@gmail.com` or Support Center. Until verified, HTTPS is impossible on this account (verified again 2026-07-31: still `AccessDenied`).
2. **Google Console redirect URIs** — need `http://localhost:8000/api/auth/google/callback` added now (for local recording) and `https://<dist>.cloudfront.net/api/auth/google/callback` after CloudFront. Test Users `harisankar@sentellent.com`, `naga@sentellent.com` must be on the consent screen.
3. **Secrets** — Secrets Manager `sentellent-equity-analyst-dev/application` holds real Google/Groq values; OpenAI key empty (deterministic embedding fallback is the documented non-production path).

## 7. Quick evidence commands

```sh
# live app
curl -s http://sentellent-equity-analyst-dev-al-157660511.ap-south-1.elb.amazonaws.com/health
# local stack
docker compose up --build
cd apps/api && python -m pytest -q
# pipeline
gh run list --limit 3
```
