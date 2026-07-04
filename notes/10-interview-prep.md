# Interview Prep

## Core Explanation

I built a serverless event-driven pipeline using AWS SAM. A producer Lambda creates order events and publishes them to SNS. SNS fans out events to SQS queues. A worker Lambda consumes from SQS asynchronously. Failed messages retry and eventually go to a DLQ. CloudWatch captures logs, metrics, a dashboard, and a DLQ alarm that publishes to SNS for email notification. GitHub Actions deploys the stack using OIDC, so no long-lived AWS keys are stored in GitHub.

## Questions You Should Expect

### Why Lambda?

Lambda is useful for event-driven compute where workloads are intermittent or scale based on events. It reduces server management, but we must design around timeout limits, cold starts, retries, and observability.

### Why SQS between services?

SQS decouples producer and consumer. It absorbs spikes, supports asynchronous processing, and retries failed work. If the consumer is down, messages wait in the queue instead of breaking the producer.

### Why SNS plus SQS?

SNS gives fanout. SQS gives durable buffering. Together they let one event be broadcast to multiple reliable consumers.

### What is a DLQ?

A dead-letter queue stores messages that failed repeatedly. It prevents poison messages from being retried forever and gives operators a place to inspect failures.

### What is visibility timeout?

When SQS gives a message to a consumer, it hides the message temporarily. If processing succeeds, the consumer deletes it. If processing fails, the message becomes visible again after the timeout.

### Why should consumers be idempotent?

SQS standard queues can deliver duplicates. Idempotent processing ensures repeated handling of the same message does not corrupt data or duplicate side effects.

### Why EventBridge?

EventBridge can route events or invoke targets on a schedule. In this repo it replaces a cron server by invoking Lambda on a schedule.

### Why CloudWatch?

CloudWatch provides logs, metrics, dashboards, and alarms. It is necessary to debug Lambda execution, monitor queue depth, and detect DLQ failures.

### How does email notification work?

CloudWatch alarm actions publish to an SNS topic. The SNS topic has an email subscription. When the alarm changes state, CloudWatch publishes to SNS and SNS sends the email. The email address must confirm the subscription first.

### Why OIDC for GitHub Actions?

OIDC allows GitHub Actions to assume an AWS IAM role using short-lived credentials. This avoids storing long-lived AWS access keys in GitHub secrets.

## Tradeoffs To Mention

Lambda is simple operationally, but cold starts and timeout limits matter.

SQS improves reliability, but standard queues can duplicate messages.

SNS fanout is clean, but subscribers must handle failures independently.

DLQs prevent infinite retries, but someone must monitor and replay or fix failed messages.

Broad IAM permissions are okay for a practice lab, but production should use least privilege.

## Strong MBRDI-Style Framing

For an automotive backend, I would use the same architecture for vehicle events. For example, a telemetry ingest Lambda could receive vehicle diagnostics, publish a normalized event to SNS, then SQS queues could feed independent workers for alerting, service recommendations, analytics, and audit. DLQs would preserve failed events, and CloudWatch alarms would detect processing issues.

## Whiteboard Flow

Draw this:

```text
Vehicle or app event
  -> Lambda ingest
  -> SNS topic
  -> SQS diagnostics queue -> Lambda diagnostics worker
  -> SQS analytics queue -> Lambda analytics worker
  -> DLQ on failure
  -> CloudWatch logs/metrics/alarms
```

Then say:

```text
The key design goal is loose coupling. Producers publish events once. Consumers process independently. SQS protects consumers from traffic spikes and failures. DLQs and CloudWatch make failures visible.
```
