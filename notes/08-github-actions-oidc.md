# GitHub Actions And OIDC

## What The Pipeline Does

The deploy workflow is manual:

```yaml
on:
  workflow_dispatch:
```

That means pushing code does not automatically deploy. You choose when to run it from the GitHub Actions tab.

The deploy job does:

```text
checkout repo
  -> install Python
  -> install SAM
  -> authenticate to AWS using OIDC
  -> sam validate --lint
  -> sam build
  -> sam deploy
```

The destroy job does:

```text
checkout repo
  -> install SAM
  -> authenticate to AWS using OIDC
  -> sam delete
```

## Why OIDC

Bad practice:

```text
store AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in GitHub secrets
```

Better practice:

```text
GitHub OIDC token -> AWS IAM role -> temporary credentials
```

OIDC avoids long-lived AWS keys in GitHub.

## Critical Workflow Permission

In `.github/workflows/deploy.yml`:

```yaml
permissions:
  id-token: write
  contents: read
```

`id-token: write` allows GitHub Actions to request an OIDC token.

Without it, the AWS credential step cannot assume the role via OIDC.

## Role Assumption

In the workflow:

```yaml
AWS_ROLE_TO_ASSUME: arn:aws:iam::923988301700:role/tan-serverless-github-actions-role
```

Then:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ env.AWS_ROLE_TO_ASSUME }}
    role-session-name: github-actions-deploy
    aws-region: ${{ env.AWS_REGION }}
```

This action exchanges the GitHub OIDC token for temporary AWS credentials.

## AWS Trust Policy

The role trust policy restricts who can assume the role.

Important condition:

```text
repo:Tech-Sayantan/tan-serverless-dojo:ref:refs/heads/main
```

That means only workflows from this repo on `main` can assume the role.

## Pipeline Code Walkthrough

`actions/checkout@v4` downloads the repo code into the runner.

`actions/setup-python@v5` installs Python 3.12.

`aws-actions/setup-sam@v2` installs SAM CLI on the runner.

`aws-actions/configure-aws-credentials@v4` authenticates to AWS using OIDC.

`sam validate --lint` checks infrastructure syntax and rules.

`sam build` prepares Lambda artifacts.

`sam deploy` creates or updates the CloudFormation stack.

## Interview Answer

The pipeline uses GitHub Actions with OIDC to assume an AWS IAM role and deploy a SAM stack. This avoids storing static AWS credentials in GitHub, uses temporary credentials, and restricts trust to a specific repo and branch.
