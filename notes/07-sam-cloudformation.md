# SAM And CloudFormation

## CloudFormation

CloudFormation is AWS infrastructure as code.

Instead of clicking resources manually in the console, you define them in a template.

CloudFormation creates a stack:

```text
stack = managed collection of AWS resources
```

In this repo, the stack is:

```text
tan-serverless-dojo
```

## SAM

SAM means Serverless Application Model.

SAM is a friendlier layer on top of CloudFormation for serverless apps.

This:

```yaml
Type: AWS::Serverless::Function
```

is SAM syntax.

SAM transforms it into lower-level CloudFormation resources.

## Workflow

```text
sam validate
  -> checks the template

sam build
  -> prepares function artifacts

sam deploy
  -> packages artifacts to S3
  -> creates a CloudFormation changeset
  -> applies the changeset
```

## Changeset

A changeset is a preview of what CloudFormation will do.

Example:

```text
+ Add OrderIngestFunction
+ Add OrdersQueue
+ Add OrdersTopic
```

In companies, changesets matter because infrastructure changes can be reviewed before being applied.

## Why SAM Uploads To S3

CloudFormation cannot read code directly from your laptop.

So SAM uploads deployable artifacts to an S3 bucket, then points CloudFormation to those artifacts.

```text
local repo -> .aws-sam/build -> S3 artifact -> CloudFormation stack
```

## Parameters

Our template has parameters:

```yaml
ProjectName
ScheduleState
ScheduleExpression
```

Parameters let the same template work in different modes or environments.

Example:

```bash
sam deploy --parameter-overrides ScheduleState=DISABLED
```

## Outputs

Outputs print useful values after deployment:

```yaml
OrdersQueueUrl
OrdersDlqUrl
OrdersTopicArn
```

These are the values you use for testing and debugging.

## Interview Answer

CloudFormation manages infrastructure as a stack. SAM is a serverless-focused framework that simplifies Lambda, API, event source, and policy definitions, then transforms them into CloudFormation. This gives repeatable deployments and avoids manual console drift.
