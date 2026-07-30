# Operations runbook

## Local development

1. Create .env from .env.example.
2. Run docker compose up --build.
3. Read API health at /health; readiness also verifies PostgreSQL at /ready.
4. Follow a ticker in the dashboard. The worker claims the generated job and marks it succeeded, queued, or failed.

## AWS deployment

1. Create an AWS account/region configuration and a Route53-hosted domain.
2. Configure GitHub OIDC, then add the repository variables/secrets named in .github/workflows/deploy.yml.
3. Set the `APPLICATION_SECRET_JSON` GitHub repository secret with non-empty `google_client_id`, `google_client_secret`, and `openai_api_key` fields. The deployment writes it to Secrets Manager before ECS services are created; the RDS password remains RDS-managed.
4. Configure Google OAuth callback URI as https://<domain>/api/auth/google/callback; add both Sentellent test users.
5. Push a reviewed commit to main. Watch the GitHub Actions deployment summary and verify ECS task stability.
6. Capture screenshots of ECR images, ECS services/tasks, RDS, EventBridge schedule, CloudFront/ALB, and the passing Actions run.

## Recovery

- A failed ingestion job retries with capped exponential backoff. Inspect the job and source rows by correlation ID; do not delete valid older evidence because a refresh failed.
- Roll back an application release by running the deployment workflow manually with the previous immutable image tag.
- If a model provider is unavailable, retrieval remains available but the response must return the safe evidence-gap message rather than synthesize claims.
