# Next Labs

This project is a strong start, but interviews often go one level deeper. These labs are the next upgrades.

## Lab 1: Idempotency

Problem:

SQS can deliver duplicate messages.

Upgrade:

Add DynamoDB and store processed `orderId` values. If a message arrives twice, skip the second processing attempt.

Interview concept:

```text
At-least-once delivery requires idempotent consumers.
```

## Lab 2: Partial Batch Failure

Problem:

When Lambda receives a batch of SQS messages and one fails, handling gets tricky.

Upgrade:

Set batch size above 1 and implement partial batch response.

Interview concept:

```text
One bad message should not force successful messages to retry.
```

## Lab 3: Structured Logging

Problem:

Plain `print(...)` works, but production logs need consistent fields.

Upgrade:

Log JSON with fields such as:

- `orderId`
- `eventType`
- `correlationId`
- `component`
- `status`

Interview concept:

```text
Logs should support debugging across distributed systems.
```

## Lab 4: Environment Separation

Problem:

Real teams deploy to dev, staging, and prod.

Upgrade:

Add parameters:

- `EnvironmentName`
- `ProjectName`

Deploy stacks:

```text
tan-serverless-dojo-dev
tan-serverless-dojo-stage
tan-serverless-dojo-prod
```

Interview concept:

```text
Same template, different parameters.
```

## Lab 5: EventBridge Event Bus

Problem:

We currently use EventBridge only as a scheduler.

Upgrade:

Create a custom event bus and route events by pattern.

Interview concept:

```text
EventBridge is not only cron; it is also event routing.
```

## Lab 6: Least Privilege IAM

Problem:

The GitHub Actions role policy is broad for practice.

Upgrade:

Restrict actions and resources to only what this stack needs.

Interview concept:

```text
Start broad for learning, tighten for production.
```

## Lab 7: Replay DLQ

Problem:

DLQ messages should not just sit forever.

Upgrade:

Add a manual replay Lambda or documented replay command.

Interview concept:

```text
DLQ is an operational workflow, not a trash can.
```

## Lab 8: API Gateway Entry Point

Problem:

Manual Lambda invoke is not how users call production systems.

Upgrade:

Add API Gateway in front of `OrderIngestFunction`.

Interview concept:

```text
API Gateway handles HTTP, Lambda handles compute, SNS/SQS handles async backend processing.
```

## Lab 9: Vehicle Telemetry Domain Version

Problem:

Coffee orders are good for learning, but MBRDI interview discussion should use automotive language.

Upgrade:

Rename event examples:

```text
order.created -> vehicle.telemetry.received
item -> vin or signalType
quantity -> mileage or batteryPercentage
priority -> severity
```

Interview concept:

```text
Architecture patterns transfer across domains; only event schema and business rules change.
```

## Lab 10: Observability Upgrade

Problem:

Logs alone are not enough for production incident response.

Upgrade:

Add:

- correlation ID
- custom CloudWatch metric
- alarm on Lambda errors
- alarm on queue age
- dashboard widget for DLQ age

Interview concept:

```text
Monitor symptoms users feel, not just whether code threw exceptions.
```

## Suggested Next Session

Start with Lab 1: idempotency using DynamoDB.

Why:

It turns this from a demo pipeline into a production-minded system and gives a very strong interview story.
