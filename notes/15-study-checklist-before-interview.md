# Study Checklist Before Interview

This checklist is tailored for serverless backend interviews, including automotive or connected-vehicle backend roles.

## Must Know

### Lambda

Study:

- handler and event shapes
- execution role
- timeout and memory
- cold starts
- retries
- concurrency
- environment variables
- CloudWatch logs

Be ready to answer:

```text
What happens when Lambda is triggered by SQS and the function throws an error?
```

### SQS

Study:

- standard vs FIFO
- visibility timeout
- long polling
- message retention
- DLQ and redrive policy
- at-least-once delivery
- idempotency
- queue backlog and scaling

Be ready to answer:

```text
Why does SQS not delete a message immediately after receive?
```

### SNS

Study:

- topic
- subscription
- fanout
- message attributes
- filter policies
- SNS to SQS queue policy
- email subscription confirmation

Be ready to answer:

```text
When would you use SNS plus SQS instead of directly sending to SQS?
```

### EventBridge

Study:

- schedule vs event bus
- rules and targets
- event patterns
- Lambda invoke permission
- replacing cron

Be ready to answer:

```text
How is EventBridge different from SNS?
```

### CloudWatch

Study:

- log groups and log streams
- metrics
- alarms
- dashboards
- alarm actions
- metric delay
- state transitions

Be ready to answer:

```text
Why did the email not arrive if the SNS subscription was pending when the alarm fired?
```

### IAM

Study:

- user vs role
- trust policy vs permission policy
- Lambda execution role
- GitHub Actions deployment role
- `iam:PassRole`
- least privilege

Be ready to answer:

```text
What is the difference between the role that deploys Lambda and the role Lambda uses at runtime?
```

### GitHub Actions And OIDC

Study:

- workflow dispatch
- `id-token: write`
- `configure-aws-credentials`
- role assumption
- AWS OIDC provider
- trust policy `sub` condition

Be ready to answer:

```text
Why is OIDC better than storing AWS access keys in GitHub Secrets?
```

## Should Know Next

### DynamoDB

Learn it for:

- idempotency
- event processing state
- conditional writes
- TTL

Why it matters:

```text
SQS can duplicate messages; DynamoDB conditional writes help prevent duplicate side effects.
```

### Step Functions

Learn it for:

- multi-step workflows
- retries and branching
- human-readable orchestration

Why it matters:

```text
Lambda chains get messy when business processes have many steps.
```

### API Gateway

Learn it for:

- HTTP entry points
- request validation
- auth
- throttling

Why it matters:

```text
Many serverless systems start with API Gateway -> Lambda.
```

### DynamoDB Streams Or EventBridge Pipes

Learn it for:

- event propagation from data changes
- connecting sources to targets with less glue code

### X-Ray Or Tracing

Learn it for:

- distributed tracing
- latency debugging
- service maps

### Cost Awareness

Learn:

- Lambda request and duration cost
- CloudWatch log retention
- SQS request cost
- NAT Gateway cost trap
- EventBridge event cost

Interview point:

```text
Serverless can be cheap, but bad logging, high retries, or NAT usage can surprise teams.
```

## MBRDI-Framed Practice Stories

### Vehicle Telemetry

```text
Vehicle sends telemetry
  -> API/Lambda ingests
  -> SNS/EventBridge publishes event
  -> SQS queues feed diagnostics, analytics, notification workers
  -> DLQs preserve failed telemetry events
  -> CloudWatch alarms detect processing failures
```

### Service Reminder

```text
EventBridge schedule runs daily
  -> Lambda checks due services
  -> SNS fans out reminders
  -> SQS buffers email/push notification workers
```

### Charging Session Completed

```text
charging.session.completed
  -> event bus
  -> billing worker
  -> analytics worker
  -> user notification worker
```

## How To Sound Senior

Say less generic AWS trivia and more tradeoff-aware sentences:

```text
I would put SQS between producer and worker so producer availability is not tied to consumer availability.
```

```text
Because SQS is at-least-once, I would make the worker idempotent using a processed-event store.
```

```text
I would alarm on DLQ depth and age of oldest message, not just Lambda errors.
```

```text
I would use OIDC for CI/CD so GitHub does not store long-lived AWS credentials.
```

```text
I would create log groups in IaC so retention is explicit and cost-controlled.
```

## Final Self-Test

Before interview, explain this without notes:

```text
What happens from the moment manual-order.json is sent to Lambda until CloudWatch logs show it processed?
```

Then explain:

```text
What changes when poison-order.json is sent?
```

If you can explain both flows clearly, you understand the architecture.
