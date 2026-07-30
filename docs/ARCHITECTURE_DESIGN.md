# Sentellent Hiring Challenge - Architecture & Delivery Design

**Product:** Personal Agentic AI Indian Equity Analyst
**Scope:** NSE / BSE research assistant with RAG, durable investor memory, grounded answers, and AWS delivery
**Primary stack:** Next.js (React), FastAPI (Python), LangChain/LangGraph, PostgreSQL + pgvector on Amazon RDS, Docker, AWS, Terraform, GitHub Actions
**Design status:** Implementation-ready

## 1. Executive summary

This project is an equity-research chief of staff for Indian investors. A signed-in user follows NSE/BSE stocks such as RELIANCE, TCS, or HDFCBANK. The system ingests responsible fundamentals, recent Indian financial-news RSS items, and INR price information. It then provides research answers and recommendations that are:

- grounded only in retrieved fundamentals/news;
- cited at the claim level with the original URL, title, published date, and source excerpt;
- personalised from a durable investor profile learned from conversation; and
- efficient: embeddings, data extraction, and recommendation scores are reused rather than recomputed with an LLM on every question.

The first working deployment is deliberately narrow: log in, follow one ticker, ingest it, and answer one cited INR question on AWS. The rest of the system extends that vertical slice without replacing it.

### Non-negotiable product rules

1. The analyst never invents a financial number, event, recommendation rationale, or citation.
2. A source record and citation must exist before a claim can appear in an answer.
3. If evidence is absent or stale, the answer says: **"I don't have that in the ingested data."**
4. User profile rules are hard filters in recommendations, not merely prompt suggestions.
5. Values rendered to users use Indian formatting and an explicit unit, such as Rs. 1,250.50 or Rs. 12,300 crore. The original source unit and observation date are retained.
6. The app provides research assistance, not investment advice.

## 2. Challenge coverage

| Challenge requirement | Design response |
|---|---|
| React.js / Next.js | Functional dashboard, ticker follow flow, research chat, citations panel, and profile controls. |
| Python FastAPI | Typed REST API, OAuth callback/session handling, ingestion controls, chat streaming, and health endpoints. |
| LangChain / LangGraph | A stateful graph for query, retrieval, profile memory, answer generation, and citation validation. |
| RAG with a vector store | Chunk/embedding/retrieval pipeline built in-house using PostgreSQL pgvector on Amazon RDS. |
| Dynamic memory | Canonical investor-profile facts in PostgreSQL plus a persona-vector projection for semantic matching. |
| Indian-market data | Screener-compatible fundamentals connector, RSS news connectors, NSE/yfinance quote adapter, normalized NSE/BSE IDs. |
| Grounded/cited INR answers | Evidence objects are passed to the generator; citation and INR validators gate the response. |
| Efficient engineering | Content-addressed embedding cache, deterministic stock scorer, source dedupe, retrieval filters, and SQL aggregation. |
| Concurrent/idempotent ingestion | Job claims, PostgreSQL advisory locks, unique fingerprints, upserts, and transactional state transitions. |
| AWS deployment | ECS Fargate services/tasks, RDS, ECR, ALB, CloudFront, S3, EventBridge, Secrets Manager, CloudWatch, and IAM. |
| Terraform | Versioned modules provision the full environment, including pgvector-enabled RDS and ECS task definitions. |
| GitHub Actions CI/CD | Tests, image builds, ECR publication, Terraform plan/apply, migrations, ECS rollout, and smoke test. |
| Google OAuth testability | Google OAuth uses OpenID Connect only; harisankar@sentellent.com and naga@sentellent.com are added as Test Users before sharing the URL. |

## 3. Architecture

~~~mermaid
flowchart TB
  U["Investor"] --> CF["CloudFront + HTTPS"]
  CF --> ALB["Application Load Balancer"]
  ALB --> WEB["Next.js (React)<br/>ECS Fargate"]
  ALB --> API["FastAPI<br/>ECS Fargate"]

  API --> LG["LangGraph service"]
  LG --> RDS["Amazon RDS PostgreSQL<br/>pgvector + relational memory"]
  API --> RDS
  API --> SEC["AWS Secrets Manager"]

  API --> Q["Ingestion jobs<br/>PostgreSQL queue"]
  EB["EventBridge schedule"] --> WORKER["Ingestion worker<br/>Fargate task"]
  Q --> WORKER
  WORKER --> DATA["Fundamentals + RSS + prices<br/>source adapters"]
  WORKER --> RDS
  WORKER --> S3["S3 raw-source archive"]

  GH["GitHub Actions via OIDC"] --> ECR["Amazon ECR"]
  ECR --> WEB
  ECR --> API
  GH --> TF["Terraform"]
  TF --> AWS["AWS infrastructure"]
~~~

### 3.1 Deployment topology

- **CloudFront** provides the public HTTPS entry point, caching static Next.js assets and forwarding authenticated/dynamic paths to the Application Load Balancer.
- **Application Load Balancer** routes /api/*, /health, and /docs to FastAPI; all other paths go to the Next.js service. This gives browser and API one domain, so the secure OAuth session cookie works without CORS complexity.
- **Next.js service** runs as a Docker container on ECS Fargate and renders the React interface.
- **FastAPI service** runs separately on ECS Fargate. It owns authentication, user data, RAG orchestration, ingestion-job creation, and API access.
- **Ingestion worker** is the same Python image with a worker command. It is started by EventBridge on a schedule and also polls claimed jobs created after a user follows a ticker.
- **RDS PostgreSQL** is private, multi-AZ configurable, and is the system of record. The pgvector extension stores news, fundamentals, and persona embeddings. No second vector database is required.
- **S3** retains the raw normalized source payload or extraction snapshot for reproducibility. The application stores a source URL, source time, content hash, and S3 key with each indexed document.
- **Secrets Manager** holds OAuth client secret, model-provider keys, database credentials, and session signing material. ECS receives secret references, never plaintext values in Terraform state or GitHub logs.

For an economical demonstration environment, RDS can start single-AZ and ECS service desired count can start at one. The Terraform variables make two-AZ RDS and multiple task replicas a production switch, not a redesign.

### 3.2 Fixed technology choices

| Layer | Choice | Why it is used |
|---|---|---|
| Web UI | Next.js App Router + TypeScript + React | Required frontend stack; server-rendered shell, clean functional dashboard, simple deployment in a container. |
| API | Python 3.12, FastAPI, Pydantic, SQLAlchemy/Alembic | Required backend stack; typed contracts and repeatable PostgreSQL migrations. |
| Agent framework | LangChain components orchestrated with LangGraph StateGraph | Required agent stack; explicit, testable state and controlled side effects. |
| LLM / embeddings | Provider adapter selected by environment variables; first implementation uses LangChain chat and embedding clients | Keeps the required LangChain layer while avoiding provider-specific business logic. |
| Vector store | PostgreSQL pgvector on Amazon RDS | Meets RAG requirements while keeping transactional ingestion, filters, and user memory in one durable store. |
| Container runtime | Docker + Amazon ECR + ECS Fargate | Repeatable builds and a clearly inspectable AWS deployment. |
| Infrastructure | Terraform | All AWS resources are declarative and reviewable. |
| Delivery | GitHub Actions + AWS OIDC | Push-to-main automated deployment without long-lived AWS access keys. |

AWS AgentCore Runtime/Memory is not a dependency for the first release. LangGraph plus RDS keeps the graph, memory, and deployment observable. It can be introduced later behind the same agent interface if it improves operational needs.

## 4. User experience and functional flows

### 4.1 Pages

1. **Sign in** - Google OAuth login with only openid, email, and profile scopes.
2. **Portfolio / Followed stocks** - add a NSE/BSE ticker, see ingestion state, source freshness, and last price.
3. **Research chat** - ask a ticker-specific or cross-ticker question; shows answer, in-line citation markers, source drawer, freshness, and clear data-gap responses.
4. **Investor profile** - displays editable risk, horizon, objectives, dividend preference, exclusions, and debt tolerance learned from chat. Each fact shows its source conversation turn and can be corrected/deleted.
5. **Source detail** - original title/URL, publisher, published time, retrieved time, quoted excerpt, and data type.

### 4.2 Follow and ingest

1. The user selects RELIANCE and exchange NSE.
2. FastAPI validates the canonical instrument record (RELIANCE.NS, NSE ID, BSE ID where known), inserts user_follow, and creates a deduplicated refresh job.
3. The worker claims the job and acquires a PostgreSQL advisory lock for the stock. A concurrent manual follow or scheduled refresh therefore cannot index the same ticker at the same time.
4. It fetches permitted fundamentals, RSS news, and a price snapshot; normalizes each source; stores the raw extraction in S3; and writes a durable source record.
5. New content is chunked deterministically, embedded only when its content hash/model pair has not been seen before, and upserted into pgvector.
6. A single structured LLM extraction runs for each genuinely new article: mentioned tickers, event type, sentiment, impact, and cited supporting excerpt. The result is schema-validated before storage.
7. SQL updates the rolling stock-sentiment aggregate. The job becomes succeeded only after its source/document/chunk writes succeed.

### 4.3 Research question

1. The user asks: "What is the sentiment on TCS this week?"
2. The graph resolves the intent and ticker, loads the user profile, embeds the question once, retrieves filtered evidence from pgvector and the associated source rows, and ranks it by semantic relevance, recency, source type, and sentiment relevance.
3. The response node receives only the user question, profile constraints, normalized facts, and citation-ready excerpts - not arbitrary database access.
4. The answer validator checks that citations refer to retrieved source IDs and verifies that every numeric output has a supporting source field. The renderer formats money in INR.
5. The API returns the answer, claims, citations, retrieval timestamp, and an explicit data-gap state when evidence is insufficient.

### 4.4 Investor persona and recommendations

For a statement such as "I am conservative, dividend-focused, and avoid high-debt companies":

1. A graph node extracts a typed profile patch: risk_tolerance=conservative, objectives=[income], avoid_high_debt=true.
2. The profile service validates the allowed values, saves a versioned fact with the chat message as evidence, updates the canonical JSON profile, and regenerates its small persona-vector projection.
3. Recommendation requests use the canonical fields as rules. A deterministic scorer evaluates only stocks with fresh, cited structured features.
4. The hard debt rule filters noncompliant stocks before ranking. The LLM explains the precomputed short list; it does not re-score every stock or bypass the filter.

## 5. Data model and pgvector design

PostgreSQL is both the transactional database and vector layer. All tables use UTC timestamps, UUID primary keys, and migrations through Alembic.

| Table | Purpose / key fields |
|---|---|
| app_user | OAuth identity: id, email, provider subject, created/last-login time. |
| auth_session | Rotatable opaque session ID, user ID, expiry, revocation time. The cookie is HttpOnly, Secure, SameSite=Lax. |
| stock | Canonical instrument: symbol, exchange, NSE/BSE IDs, yfinance symbol, company name, sector. Unique (symbol, exchange). |
| user_follow | User-to-stock relation, refresh policy, created time. Unique (user_id, stock_id). |
| ingestion_job | Durable queue: id, stock, trigger, status, attempt, lock metadata, source window, error. Partial unique index prevents duplicate active jobs for a stock/window. |
| source_document | Immutable source metadata: type, publisher, canonical URL, title, published/retrieved time, S3 snapshot key, content hash, source attribution. Unique fingerprint. |
| document_chunk | Retrieval unit: source ID, stock ID, chunk index, text, token count, embedding vector(n), text-search vector, chunker/model versions. Unique (source_id, chunk_index, chunker_version). |
| embedding_cache | Reusable embedding keyed by (content_sha256, embedding_model). Avoids re-embedding duplicated RSS stories and repeated fundamentals. |
| fundamental_snapshot | Normalized point-in-time metrics with raw label, numeric value, unit, currency=INR, source ID, observed/retrieved date. |
| article_signal | Schema-validated LLM extraction per article/stock: sentiment, impact, event type, confidence, supporting excerpt. Unique (source_id, stock_id, extraction_version). |
| stock_signal_daily | Precomputed rolling sentiment and counts by stock/date. Updated with idempotent SQL upsert. |
| investor_profile | Canonical typed profile JSON plus persona_embedding vector(n), profile version, update time. One row per user. |
| profile_fact | Provenance for each remembered fact: key, value JSON, source message ID, confidence, state, valid-from/to. |
| chat_thread / chat_message | Conversation audit trail and LangGraph checkpoint/thread linkage. |
| answer_audit | Request ID, retrieved chunk IDs, graph state summary, cited IDs, model/version, validation result, latency. Enables debugging and evaluation. |

### 5.1 Required indexes and constraints

- A HNSW index on document_chunk.embedding with cosine distance; exact index parameters are Terraform/migration managed.
- PostgreSQL full-text GIN index on normalized chunk text for lexical ticker/company matches.
- B-tree indexes on (stock_id, published_at DESC), source_document(content_hash), user_follow(user_id), and active job state.
- source_document.fingerprint is a SHA-256 of canonical URL + normalized title + publication timestamp/content hash. It stops overlapping feed stories from creating duplicate source records.
- SELECT ... FOR UPDATE SKIP LOCKED claims pending jobs. pg_try_advisory_xact_lock(hash(stock_id)) serializes all refreshes for a particular stock.
- Source, chunks, and derived signals are written in a transaction. Retrying a job uses INSERT ... ON CONFLICT ... DO UPDATE and therefore is safe.

### 5.2 Source and value normalization

Every stored figure includes raw_value, raw_unit, normalized_value, normalized_unit, currency, as_of_date, and source_document_id. Rupees are represented internally as decimal INR (or paise where precision requires), never a locale-formatted string. A presentation function emits Rs. values with Indian grouping and preserves larger source units such as crore.

Fundamentals are stored as source-backed snapshots rather than silently merged. When multiple data points disagree, the assistant identifies the source/date; it does not average them.

## 6. RAG and LangGraph design

### 6.1 Graph state

~~~
ResearchState
  request_id, user_id, thread_id, question
  intent, resolved_tickers, time_window
  profile, profile_constraints
  retrieved_evidence[], candidate_features[]
  answer_draft, citations[], validation_errors[]
  memory_patch, response
~~~

### 6.2 Nodes and routing

~~~mermaid
flowchart LR
  A["Load user & profile"] --> B["Classify intent / resolve ticker"]
  B --> C["Extract profile patch"]
  C --> D["Retrieve evidence"]
  D --> E{"Recommendation?"}
  E -- Yes --> F["Deterministic filter & rank"]
  E -- No --> G["Compose cited answer"]
  F --> G
  G --> H["Validate citations, claims & INR"]
  H -- valid --> I["Persist audit + respond"]
  H -- insufficient evidence --> J["Data-gap response"]
~~~

| Node | Responsibility | Side-effect rule |
|---|---|---|
| Load user/profile | Fetch canonical persona, followed stocks, and thread checkpoint. | Read only. |
| Classify/resolve | Parse intent and map symbols/company aliases to canonical stock ID. | Read only; ambiguity becomes a clarification. |
| Extract profile patch | Pull only explicit user preferences into a Pydantic patch schema. | Writes only validated, material facts with chat provenance. |
| Retrieve evidence | Query pgvector and full-text search with ticker, type, date, and freshness filters. | Read only. |
| Filter/rank | Apply profile exclusions and score data-backed candidates using SQL/Python. | Read only, deterministic. |
| Compose | Generate a concise answer constrained to evidence JSON and allowed citation IDs. | Cannot call data tools directly. |
| Validate | Reject unknown citation IDs, unsupported numbers, unsupported recommendation reasons, or malformed INR display. | Read only. |
| Persist audit | Store output and evidence set. | Write after validation only. |

### 6.3 Retrieval policy

- Query embedding is calculated once per question.
- The retriever applies ticker and source-type filters before vector search. It searches the user's followed universe by default; a discovered stock must be ingested before it can be recommended.
- It combines semantic similarity with deterministic recency and source-quality boosts. The latest fundamental snapshot and time-windowed news are retrieved separately so a news-heavy query cannot bury core data.
- The response context has a fixed token budget with one compact citation object per fact. This prevents duplicated chunks and keeps model cost predictable.
- Cache key: normalized question + resolved tickers + data freshness watermark + profile version. Cached answers are invalidated when a matching stock refresh or profile update occurs.
- If retrieval returns too little evidence or only stale data, the graph returns a gap response instead of escalating to an unsupported answer.

### 6.4 Citation contract

The generator returns structured JSON before UI rendering:

~~~json
{
  "answer_markdown": "TCS has mixed recent news sentiment [S1].",
  "claims": [
    {"text": "TCS has mixed recent news sentiment", "citation_ids": ["S1"]}
  ],
  "citations": [
    {
      "id": "S1",
      "source_document_id": "uuid",
      "title": "Original article title",
      "publisher": "Publisher",
      "url": "https://...",
      "published_at": "2026-08-01T10:00:00Z",
      "excerpt": "Grounding text shown to the user"
    }
  ],
  "data_gaps": []
}
~~~

The validator confirms every citation ID was in the retrieval bundle, every claim has at least one citation, every currency/number string matches a cited normalized fact, and each recommendation's reason cites supporting evidence. If any check fails, the graph retries once with a correction instruction; otherwise it returns the safe data-gap answer.

## 7. Efficient recommendation design

The agent is not allowed to make one LLM call per stock. It makes a single explanation call after a cheap and auditable ranking step.

### 7.1 Candidate feature materialization

Ingestion computes/updates a small stock_feature_snapshot view from cited fundamental and sentiment records:

- quality: source-backed profitability / stability fields when available;
- value: valuation fields when available;
- income: dividend fields when available;
- momentum: recent INR price-change field when available;
- risk: debt/equity and volatility fields when available;
- sentiment: decayed seven-day and thirty-day article-signal aggregates.

Each feature stores its source_document_id, as_of_date, freshness, and confidence. Missing data is NULL, never guessed.

### 7.2 Ranking rules

1. Start from followed/ingested candidates with fresh required data.
2. Apply hard persona exclusions: banned sectors/stocks, non-INR data, maximum debt tolerance, risk band, and explicit rules such as avoid_high_debt.
3. Normalize available cited features to a 0-100 scale within the candidate universe.
4. Apply user weights. For a conservative dividend profile, income, quality, balance-sheet health, and recent sentiment are weighted more heavily than momentum.
5. Return only candidates whose explanation has sufficient source coverage. A missing required metric excludes a stock from a strict screen and is shown as a data limitation.
6. Sort deterministically; store score components in the answer audit; use the LLM only to state the result and cited one-line rationale.

The output is transparent: "Excluded because latest ingested debt/equity exceeds your stated tolerance" is allowed only when it cites the underlying snapshot. The application must not say "buy" in an absolute sense; it presents researched, profile-matched candidates and risks.

## 8. Ingestion, concurrency, and data quality

### 8.1 Connector boundary

Each provider implements the same Python protocol:

~~~
fetch_stock_identity(symbol, exchange) -> StockIdentity
fetch_fundamentals(stock) -> list[SourcePayload]
fetch_news(stock, since) -> list[SourcePayload]
fetch_prices(stock, range) -> list[SourcePayload]
~~~

The initial adapters are a responsible fundamentals source compatible with Screener data (robots/rate-limit compliant), RSS feeds from Indian financial publishers, and an NSE/yfinance price adapter using .NS symbols. Providers are configured, logged, and easy to substitute; source pages are never treated as permission to ignore their terms.

### 8.2 Idempotency and race handling

- A user follow calls enqueue_refresh(stock_id, reason) which is an upsert, not an unconditional insert.
- Only one worker may hold the per-stock advisory lock. Another job exits cleanly as superseded or waits for the existing job result.
- Article fingerprinting, content-hash dedupe, deterministic chunk IDs, and embedding cache keys make a second run a no-op for already indexed content.
- Derived article signals and daily aggregate rows have unique source/stock/date keys, so retries cannot double-count sentiment.
- A job records a correlation ID, attempt number, lease expiry, and failure detail. Failed jobs retry with capped exponential backoff; poison jobs become visible in an operator query rather than retrying forever.
- The worker never deletes previously valid evidence during a failed refresh. New data is promoted only at the end of a successful transaction.

### 8.3 Freshness

The UI displays data freshness per stock. Defaults are configurable: intraday price snapshot, daily news refresh, and weekly fundamentals refresh. The answer includes retrieval time and calls out when a required source is older than the configured limit.

## 9. API contract

| Endpoint | Method | Purpose |
|---|---|---|
| /api/auth/google/login | GET | Begin Google OpenID Connect login. |
| /api/auth/google/callback | GET | Validate callback and set secure session cookie. |
| /api/me | GET | Current user and investor-profile summary. |
| /api/stocks/search?q= | GET | Resolve NSE/BSE ticker/company names. |
| /api/follows | GET / POST | List followed stocks or follow a ticker and enqueue ingestion. |
| /api/follows/{stock_id} | DELETE | Unfollow a stock; retains source data under retention policy. |
| /api/stocks/{symbol}/status | GET | Ingestion state, freshness, and latest source time. |
| /api/stocks/{symbol}/refresh | POST | Request a deduplicated manual refresh. |
| /api/chat/threads | GET / POST | Create/list research threads. |
| /api/chat/threads/{id}/messages | POST | Run the LangGraph query; stream answer and citation events. |
| /api/profile | GET / PATCH | View or explicitly edit investor profile. |
| /api/sources/{id} | GET | Citation detail and source provenance. |
| /health / /ready | GET | ECS health and dependency readiness checks. |

All endpoints are authenticated except health checks. API errors use a consistent problem response with request ID; the UI never exposes model-provider errors or secrets.

## 10. Security, privacy, and responsible operation

- Google OAuth is OpenID Connect only. Configure the consent screen in testing mode and add **harisankar@sentellent.com** and **naga@sentellent.com** as Test Users before handoff. No Gmail/Calendar scopes are requested.
- Use HTTPS only, secure HttpOnly cookies, CSRF validation for state-changing calls, session rotation, rate limiting, and strict input validation.
- The RDS database, ECS tasks, and worker live in private subnets; only the ALB is public. Security groups allow database access only from the FastAPI/worker task groups.
- IAM is least privilege: GitHub OIDC assumes a deploy role; task roles access only their ECR/S3/Secrets/CloudWatch resources.
- Raw source snapshots have an S3 retention/lifecycle policy. Profile data is user-specific, editable, and deletable. Chat content is not used to train a model.
- Log correlation IDs, source IDs, timing, and validation status, but redact cookies, authorization headers, OAuth codes, user email, and source body text from production logs.
- Show a concise in-product disclaimer: research information only, not financial advice; source coverage and timeliness can be limited.

## 11. AWS infrastructure as code

Terraform is organized by environment and modules:

~~~text
infra/
  environments/dev/
    main.tf variables.tf outputs.tf terraform.tfvars.example
  modules/
    network/          # VPC, public/private subnets, NAT, security groups
    data/             # RDS PostgreSQL, pgvector bootstrap, S3
    registry/         # ECR repositories and lifecycle policy
    ecs/              # cluster, task definitions, services, worker task
    edge/             # ALB, ACM, Route53 option, CloudFront
    scheduler/        # EventBridge schedules
    observability/    # log groups, alarms, dashboards
    iam/              # ECS roles and GitHub OIDC deploy role
~~~

Provisioned resources:

- VPC across two availability zones, public ALB subnets, private ECS/RDS subnets, security groups, and VPC endpoints where cost/useful.
- ECR repositories for web and api, immutable image tags, vulnerability scanning, and retention policies.
- ECS cluster and Fargate task definitions/services for web and api, including CPU/memory, health checks, autoscaling, deployment circuit breaker, and structured CloudWatch logs.
- EventBridge schedule and ECS RunTask target for the ingestion worker.
- RDS PostgreSQL with backups, encryption, private access, parameter group/extension bootstrap, and pgvector migration.
- S3 source archive with encryption, blocked public access, lifecycle policy, and task-role-only access.
- ALB, ACM certificate, CloudFront distribution, and DNS variables/outputs. If a custom domain is unavailable for the assessment, use the ALB DNS endpoint with a documented temporary callback URI.
- Secrets Manager entries created as placeholders by Terraform; secret values are written manually/through the secured deployment flow, not committed.
- CloudWatch alarms for ECS task failure, 5xx rate, RDS CPU/connections/storage, worker failure, and ingestion backlog.

## 12. CI/CD with GitHub Actions

### 12.1 Pull request pipeline

1. Checkout, set up Node and Python, restore dependency caches.
2. Run frontend lint/typecheck/unit tests and backend format/lint/typecheck/unit tests.
3. Run migration validation and integration tests against a disposable PostgreSQL+pgvector service.
4. Build both Docker images; run container smoke tests.
5. Run terraform fmt -check, terraform validate, and a non-applying Terraform plan.
6. Publish test, coverage, image, and Terraform-plan artifacts for review.

### 12.2 Push-to-main deployment pipeline

1. Authenticate to AWS through GitHub Actions OIDC; no static AWS access key is stored in GitHub.
2. Build immutable web and api images tagged with Git SHA, scan them, and push to ECR.
3. Run Terraform apply for the selected environment, passing only image tags as deployment variables.
4. Execute Alembic migration as a one-off ECS task and wait for success.
5. Update ECS services, wait for stability, and run an authenticated/health smoke test against the live URL.
6. Post a deployment summary containing commit SHA, image digests, Terraform output, migration version, service status, and live URL.

Deployment automatically stops if tests, image build, Terraform, migration, ECS stability, or smoke test fails. Rollback is performed by redeploying the last known-good image tag through a manual workflow_dispatch job.

## 13. Repository layout

~~~text
apps/
  web/                      # Next.js React frontend
  api/
    app/
      routers/ services/ models/ repositories/
      agent/                # LangGraph state, nodes, tools, validators
      ingestion/            # connectors, normalizers, jobs, workers
      migrations/
    tests/
infra/                      # Terraform modules and environments
.github/workflows/
  ci.yml
  deploy.yml
docs/
  ARCHITECTURE_DESIGN.md
  RUNBOOK.md
  DEMO_SCRIPT.md
docker/
  web.Dockerfile
  api.Dockerfile
docker-compose.yml           # local development only
README.md
~~~

## 14. Quality gates and acceptance tests

| Scenario | Expected result |
|---|---|
| Login as Sentellent tester | Google OAuth completes for the two configured Test Users and creates a secure local session. |
| Follow RELIANCE twice quickly | One active ingestion job runs; second request reuses/observes it; no duplicate documents or chunks exist. |
| Scheduled and manual refresh collide | Advisory lock plus source uniqueness keep data consistent; one job safely completes or becomes superseded. |
| Ask about a followed stock | Answer has valid citations linked to retrieved news/fundamental rows and labels its data freshness. |
| Ask for an unsupported fact | Exact safe response says the fact is not in ingested data; no fabricated number/citation. |
| State an investor preference | A traceable profile_fact is written, shown in profile UI, and applied to the next recommendation. |
| Conservative dividend recommendation | High-debt candidates are excluded by deterministic policy; returned candidates include cited feature reasons and INR data. |
| Re-ingest unchanged feed | No duplicate source/chunk/signal rows; embedding-cache hit count increases; sentiment does not double-count. |
| Push a tested main commit | GitHub Actions builds/pushes images, applies Terraform, migrates, rolls ECS, and passes a live smoke test. |

### Observability dashboard

Track API p50/p95 latency, graph/node duration, retrieval hit rate, evidence-gap rate, citation-validation failure rate, cache hit rate, embedding calls, ingestion duration, job backlog/retries, duplicate suppressions, RDS connections, ECS memory/CPU, and deployment health. Each answer/audit record has a request ID that joins frontend/API/worker logs.

## 15. Delivery plan

### Phase 1 - Foundation: ship the credible AWS vertical slice

1. Scaffold Next.js and FastAPI containers; local Docker Compose includes PostgreSQL + pgvector.
2. Implement Google OAuth, session handling, dashboard shell, stock search, and follow state.
3. Create RDS schema/migrations, pgvector retrieval table, one RSS connector, and one ticker ingestion path.
4. Build a minimal LangGraph retrieval -> cited-answer flow with data-gap response.
5. Provision ECR, ECS Fargate, RDS, ALB/CloudFront, S3, Secrets, and logs in Terraform.
6. Add main-branch GitHub Actions deployment with migration and smoke test.
7. Deploy it. Capture AWS and Actions screenshots only after the live smoke test is green.

**Phase 1 demonstration:** Sign in, follow one NSE stock, see its sources, ask one question, receive one cited answer in INR from the AWS URL.

### Phase 2 - Integration: make the analyst useful

1. Add Screener-compatible fundamentals normalization and multiple responsible Indian-finance RSS connectors.
2. Add price snapshots, source detail page, freshness indicators, and manual refresh.
3. Add structured sentiment/event extraction for newly ingested articles and rolling stock summaries.
4. Implement resilient job state, dedupe, advisory locks, retry/backoff, metrics, and ingestion tests.
5. Add citation-quality evaluation fixtures and answer audit views.

### Phase 3 - Contextual intelligence: make it personal

1. Add investor profile extraction, versioned memory facts, correction controls, and persona embeddings.
2. Materialize cited stock features and deterministic profile matching/ranking.
3. Add hard persona exclusions, explanation guardrails, profile-aware recommendations, and test fixtures.
4. Tune retrieval, response cache invalidation, rate limits, alerting, and rollback runbook.

## 16. Submission checklist

- [ ] Public GitHub repository contains frontend, backend, Dockerfiles, Terraform, workflows, migrations, tests, README, and this design.
- [ ] Live AWS URL works from an incognito browser.
- [ ] Google OAuth consent screen has harisankar@sentellent.com and naga@sentellent.com as Test Users.
- [ ] README documents exact local setup, environment variables, architecture diagram, deployment process, and trade-offs.
- [ ] Screenshot: ECS services/tasks healthy, RDS instance, CloudFront/ALB, ECR images, and EventBridge worker schedule.
- [ ] Screenshot: successful GitHub Actions CI and deployment job, including Terraform and smoke-test steps.
- [ ] Demo video/script: login -> follow ticker -> ingestion -> cited INR answer -> profile statement -> filtered recommendation.
- [ ] Submission form includes GitHub URL, live URL, AWS proof, and CI/CD proof.

## 17. Explicit trade-offs

- RDS pgvector is selected over Pinecone/OpenSearch because it satisfies the challenge vector-store choice while giving transactional idempotency, relational profile memory, SQL aggregates, and one backup/operational surface. It is sufficient for the assessment scale.
- The first release does not scrape at uncontrolled rates. RSS and one respectful fundamentals adapter give a demonstrable source pipeline; adapters can expand after the correct job/dedupe contract is proven.
- LangGraph is used as the agent control plane, while policy, validation, aggregation, and filtering are deterministic application code. This is more reliable and cheaper than an LLM-only agent.
- Recommendation language is bounded and evidence-led. The product should communicate uncertainty and data gaps rather than simulate certainty.

## 18. Definition of done

The assessment is ready to submit when a Sentellent reviewer can log in with either configured test account, follow a real Indian ticker, observe an ingestion run, ask a question, open its citations, see all monetary data in INR, teach the system a simple investor preference, and receive a source-grounded filtered result - all on the deployed AWS URL. The repository must make that deployment reproducible through Terraform and show an automated GitHub Actions pipeline that performs it.
