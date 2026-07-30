# AWS deployment bootstrap

This one-time sequence creates remote Terraform state, then establishes the OIDC deployment role GitHub Actions uses afterwards. It requires Terraform 1.11 or later and temporary administrator credentials in the intended AWS account; the normal workflow never stores long-lived AWS access keys.

## 1. Create remote state

Choose a globally unique S3 bucket name, then run the bootstrap stack from an authenticated terminal:

~~~sh
cd infra/bootstrap
terraform init
terraform apply -var="state_bucket_name=your-unique-sentellent-tf-state"
~~~

Save the two outputs. They become the GitHub repository variables TF_STATE_BUCKET and TF_LOCK_TABLE.

## 2. Seed ECR and application infrastructure

The initial role cannot be assumed by GitHub until Terraform creates it. From the same temporary administrator session:

~~~sh
cd ../environments/dev
terraform init \
  -backend-config="bucket=your-unique-sentellent-tf-state" \
  -backend-config="key=sentellent/dev/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="dynamodb_table=sentellent-terraform-locks" \
  -backend-config="use_lockfile=true" \
  -backend-config="encrypt=true"
terraform apply -target=module.registry \
  -var="github_repository=OWNER/REPOSITORY" \
  -var="api_image=placeholder" \
  -var="web_image=placeholder"
~~~

Authenticate Docker to ECR and build/push the API and web images using the two repository URLs from Terraform output. Before creating ECS services, create the data layer and populate the application secret. This prevents ECS tasks from failing during startup because the referenced secret JSON does not yet exist.

## 3. Populate the application secret

Create a local file named `application-secret.json` containing exactly these keys:

~~~json
{
  "google_client_id": "YOUR_GOOGLE_CLIENT_ID",
  "google_client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
  "openai_api_key": "YOUR_OPENAI_API_KEY"
}
~~~

The RDS password is generated and managed by RDS. It does not belong in this application secret.

Provision the data layer (which also creates the application-secret container), write the secret value, then apply the remaining stack:

~~~sh
terraform apply -target=module.data \
  -var="github_repository=OWNER/REPOSITORY" \
  -var="api_image=YOUR_API_IMAGE" \
  -var="web_image=YOUR_WEB_IMAGE"
aws secretsmanager put-secret-value \
  --secret-id "$(terraform output -raw application_secret_arn)" \
  --secret-string file://application-secret.json
terraform apply \
  -var="github_repository=OWNER/REPOSITORY" \
  -var="api_image=YOUR_API_IMAGE" \
  -var="web_image=YOUR_WEB_IMAGE"
~~~

## 4. Connect GitHub Actions

Set GitHub repository variables:

- AWS_REGION — normally ap-south-1
- TF_STATE_BUCKET and TF_LOCK_TABLE — the bootstrap outputs
- ECR_API_REPOSITORY and ECR_WEB_REPOSITORY — full ECR repository URLs

Set these repository secrets:

- `AWS_ROLE_ARN` â€” the `github_deploy_role_arn` Terraform output.
- `APPLICATION_SECRET_JSON` â€” the compact JSON object above. It is validated and written to Secrets Manager before the workflow creates ECS services.

Push to main; the deploy workflow will build immutable images, prepare the data layer and secret, apply Terraform, run Alembic as a one-off ECS task, roll both services, and smoke-test the /health endpoint.

## 5. OAuth and reviewer access

Use the CloudFront domain output to set the Google redirect URI to https://DOMAIN/api/auth/google/callback. Keep the OAuth consent screen in Testing mode and add harisankar@sentellent.com and naga@sentellent.com as test users.
