# Tan Serverless Dojo

This repo is a small but realistic serverless practice project built for interview prep. It keeps the full workflow in git: Lambda code, infrastructure as code, test events, and GitHub Actions deploy and destroy pipelines.

## Architecture

```text
Manual invoke or EventBridge schedule
  -> OrderIngest Lambda
  -> SNS topic
  -> Orders SQS queue
  -> OrderProcessor Lambda
  -> CloudWatch logs, dashboard, and DLQ alarm

SNS also fans out HIGH priority orders
  -> HighPriorityAuditQueue
```

## Services included

- Lambda: one producer and one worker function
- SNS: fanout topic for order notifications
- SQS: main queue, audit queue, and dead-letter queue
- EventBridge: scheduled rule to generate sample orders
- CloudWatch: logs, dashboard, and alarm
- SAM and CloudFormation: infrastructure as code and repeatable deployment

## Project structure

```text
tan-serverless-dojo/
  .github/workflows/
    deploy.yml
    destroy.yml
  events/
    manual-order.json
    poison-order.json
  src/
    order_ingest/app.py
    order_processor/app.py
  .gitignore
  README.md
  samconfig.toml
  template.yaml
```

## How the app works

### OrderIngest Lambda

`src/order_ingest/app.py` accepts an event payload and creates a normalized coffee order. It then publishes that order to SNS.

Important concepts:

- `event`: the input payload sent to Lambda
- `context`: metadata AWS provides for the current invocation
- `boto3.client("sns")`: the AWS SDK client used to publish messages
- message attributes: metadata used by SNS filter policies

### OrderProcessor Lambda

`src/order_processor/app.py` is triggered by SQS. SQS delivers events to Lambda in the form of a `Records` list. The function parses each record, validates the order, and raises an error for invalid input such as `quantity: 0`.

Important concepts:

- `event["Records"]`: batch of SQS messages
- `record["body"]`: the actual message payload
- retries: failed messages return to the queue after visibility timeout
- DLQ: after enough failed receives, the message moves to the dead-letter queue

## AWS concepts covered

### Lambda

Runs code on demand without managing servers. This repo uses:

- `OrderIngestFunction` for publishing orders
- `OrderProcessorFunction` for async queue processing

### SNS

Acts as the pub/sub fanout layer. One publish can notify multiple downstream consumers. Here it sends to:

- the main orders queue
- a filtered audit queue for `HIGH` priority orders

### SQS

Provides durable asynchronous buffering. The app uses:

- `OrdersQueue` for normal processing
- `OrdersDLQ` for failures
- `HighPriorityAuditQueue` for filtered fanout

### EventBridge

Provides scheduled automation. The `OrderScheduleRule` can invoke the producer Lambda on a timer. It ships disabled by default so the stack stays cheap until you choose to enable it.

### CloudWatch

Handles:

- Lambda logs from `print(...)`
- a dashboard for Lambda and queue metrics
- an alarm when the DLQ has visible messages

## Local workflow

Validate the template:

```bash
sam validate --lint
```

Build the app:

```bash
sam build
```

Deploy manually:

```bash
sam deploy --guided --profile serverless-lab --region us-east-1
```

Suggested guided answers:

```text
Stack Name: tan-serverless-dojo
AWS Region: us-east-1
Confirm changes before deploy: Y
Allow SAM CLI IAM role creation: Y
Disable rollback: N
Save arguments to configuration file: Y
SAM configuration file: samconfig.toml
SAM configuration environment: default
```

Note: the EventBridge schedule is parameterized and defaults to `DISABLED`.

## Test commands

Invoke the producer with a valid order:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/manual-order.json \
  --cli-binary-format raw-in-base64-out \
  --profile serverless-lab \
  --region us-east-1 \
  response.json
cat response.json
```

Invoke the producer with a poison order:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/poison-order.json \
  --cli-binary-format raw-in-base64-out \
  --profile serverless-lab \
  --region us-east-1 \
  response.json
cat response.json
```

Tail logs for the producer:

```bash
aws logs tail /aws/lambda/tan-serverless-dojo-order-ingest \
  --since 10m \
  --profile serverless-lab \
  --region us-east-1
```

Tail logs for the worker:

```bash
aws logs tail /aws/lambda/tan-serverless-dojo-order-processor \
  --since 10m \
  --profile serverless-lab \
  --region us-east-1
```

Receive a message from the high-priority audit queue:

```bash
aws sqs receive-message \
  --queue-url "<paste queue url from stack outputs>" \
  --max-number-of-messages 1 \
  --profile serverless-lab \
  --region us-east-1
```

## GitHub Actions

The workflows are intentionally manual so nothing deploys unexpectedly when you push the repo.

- `.github/workflows/deploy.yml`: manual deploy with optional schedule enablement
- `.github/workflows/destroy.yml`: manual stack teardown

GitHub Actions authenticates to AWS through OIDC, so the repo does not need long-lived AWS access key secrets.

Required AWS role:

```text
arn:aws:iam::923988301700:role/tan-serverless-github-actions-role
```

That role trusts only this repo on the `main` branch:

```text
repo:Tech-Sayantan/tan-serverless-dojo:ref:refs/heads/main
```

## Cleanup

Delete the stack from your machine:

```bash
sam delete --stack-name tan-serverless-dojo --profile serverless-lab --region us-east-1 --no-prompts
```

Or run the manual GitHub Actions destroy workflow after the repo is pushed.
