# AWS deployment bootstrap

This one-time sequence creates remote Terraform state, then establishes the OIDC deployment role GitHub Actions uses afterwards. It requires temporary administrator credentials in the intended AWS account; the normal workflow never stores long-lived AWS access keys.

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
  -backend-config="encrypt=true"
terraform apply -target=module.registry \
  -var="github_repository=OWNER/REPOSITORY" \
  -var="api_image=placeholder" \
  -var="web_image=placeholder"
~~~

Authenticate Docker to ECR, build and push the API and web images using the two repository URLs from Terraform output, then apply the whole dev stack with those immutable image URIs and the GitHub repository name.

## 3. Populate the application secret

After the dev stack creates the secret container, store a JSON document containing exactly these keys:

~~~json
{
  "google_client_id": "YOUR_GOOGLE_CLIENT_ID",
  "google_client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
  "openai_api_key": "YOUR_OPENAI_API_KEY"
}
~~~

The RDS password is generated and managed by RDS. It does not belong in this application secret.

## 4. Connect GitHub Actions

Set GitHub repository variables:

- AWS_REGION — normally ap-south-1
- TF_STATE_BUCKET and TF_LOCK_TABLE — the bootstrap outputs
- ECR_API_REPOSITORY and ECR_WEB_REPOSITORY — full ECR repository URLs

Set the AWS_ROLE_ARN repository secret to the github_deploy_role_arn Terraform output. Push to main; the deploy workflow will build immutable images, apply Terraform, run Alembic as a one-off ECS task, roll both services, and smoke-test the /health endpoint.

## 5. OAuth and reviewer access

Use the CloudFront domain output to set the Google redirect URI to https://DOMAIN/api/auth/google/callback. Keep the OAuth consent screen in Testing mode and add harisankar@sentellent.com and naga@sentellent.com as test users.
