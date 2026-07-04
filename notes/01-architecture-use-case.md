# Architecture And Use Case

## Why This Architecture Exists

Imagine one service receives a request and directly calls five other services:

```text
Order API -> Kitchen service
Order API -> Billing service
Order API -> Audit service
Order API -> Notification service
Order API -> Analytics service
```

This is easy at first, but it gets fragile:

- If billing is slow, the order request becomes slow.
- If audit is down, the main user flow may fail.
- If analytics has a traffic spike, it can hurt order creation.
- If you add a new consumer, you must modify the producer.

Event-driven architecture solves this by turning the important business moment into an event:

```text
OrderIngest Lambda -> "order.created" event -> SNS -> interested consumers
```

The producer does not need to know every downstream consumer. It just publishes the event.

## Our Repo Architecture

```text
events/manual-order.json
  -> OrderIngest Lambda
  -> SNS OrdersTopic
  -> OrdersQueue
  -> OrderProcessor Lambda
  -> CloudWatch Logs

SNS OrdersTopic
  -> HighPriorityAuditQueue, only when priority = HIGH

OrderProcessor failures
  -> retries
  -> OrdersDLQ
  -> CloudWatch alarm

EventBridge scheduled rule
  -> OrderIngest Lambda
```

## What Each Piece Does

`OrderIngestFunction` is the producer. It receives a test event, normalizes it into an order, and publishes that order to SNS.

`OrdersTopic` is the broadcaster. It accepts one event and fans it out to subscriptions.

`OrdersQueue` is the buffer. It stores events until the worker Lambda can process them.

`OrderProcessorFunction` is the consumer. It is triggered by SQS and processes orders.

`OrdersDLQ` is the failure parking lot. After repeated failures, messages move there for inspection.

`HighPriorityAuditQueue` is an example of filtered fanout. It receives only `HIGH` priority messages.

`OrderScheduleRule` is the timer. It can invoke the producer automatically, but it is disabled by default.

`CloudWatch` is the operational layer. Logs show what happened; metrics and alarms show whether the system is healthy.

## Why It Is Interview-Relevant

This architecture lets you discuss:

- async processing
- loose coupling
- fanout
- retries
- dead-letter queues
- observability
- least-privilege IAM
- CI/CD with OIDC
- infrastructure as code

## Automotive Mapping

For an MBRDI-style discussion, map the same shape to vehicle events:

```text
Vehicle telemetry ingest
  -> validation/enrichment Lambda
  -> SNS vehicle-events topic
  -> SQS queues for diagnostics, alerts, analytics, service recommendations
  -> worker Lambdas
  -> DLQs and CloudWatch alarms
```

This is the same architecture, only the domain nouns change.
