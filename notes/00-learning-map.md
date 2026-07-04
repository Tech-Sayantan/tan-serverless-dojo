# Learning Map

This repo is not just a demo. Treat it like a small backend system that you can explain in an interview.

## The Story

We built a tiny event-driven order pipeline:

```text
Manual test or EventBridge schedule
  -> OrderIngest Lambda
  -> SNS topic
  -> SQS queues
  -> OrderProcessor Lambda
  -> CloudWatch logs, metrics, dashboard, alarm
```

The coffee-order example is intentionally simple, but the same pattern maps to real systems:

```text
Vehicle sends telemetry event
  -> ingestion Lambda validates/enriches
  -> SNS broadcasts event
  -> SQS queues buffer independent consumers
  -> worker Lambdas process asynchronously
  -> CloudWatch observes failures and latency
```

For an automotive backend, replace `order.created` with examples such as:

- `vehicle.telemetry.received`
- `battery.health.updated`
- `service.appointment.requested`
- `diagnostic.trouble_code.detected`
- `charging.session.completed`

## What You Should Be Able To Explain

After practicing this repo, you should be able to explain:

- Why Lambda is useful for event-driven workloads
- Why direct service-to-service calls can be fragile
- Why SQS gives buffering, retry, and failure isolation
- Why SNS is useful for fanout
- Why EventBridge is useful for scheduled or event-routed automation
- Why CloudWatch matters for operations, debugging, and interviews
- How GitHub Actions can deploy to AWS without storing AWS access keys
- How SAM turns repo code into AWS infrastructure

## Learning Order

1. Lambda: code runs only when invoked.
2. CloudWatch Logs: every `print(...)` becomes operational evidence.
3. SQS: messages wait safely until a consumer is ready.
4. SNS: one event can notify many downstream systems.
5. EventBridge: schedules or routes events without a custom cron server.
6. CloudWatch metrics and alarms: production systems need signals, not hope.
7. GitHub Actions OIDC: CI/CD should use short-lived credentials, not static keys.

## Interview One-Liner

This project is an event-driven serverless pipeline where a producer Lambda publishes domain events to SNS, SNS fans those events into SQS queues, worker Lambdas process asynchronously, EventBridge can generate scheduled events, and CloudWatch provides logs, dashboards, and alarms.

## How To Use These Notes

Read in this order:

```text
16 tomorrow study plan
01 architecture
02 Lambda
03 SQS
04 SNS
05 EventBridge
06 CloudWatch
07 SAM/CloudFormation
08 GitHub Actions/OIDC
09 code walkthrough
10 interview prep
11 runbook
13 reproduce from zero
14 production issues
15 study checklist
17 deep dive field guide
```

The goal is not to memorize every AWS property. The goal is to explain the movement of an event through the system and the tradeoffs at each hop.

If you have only one serious study session, start with `16-tomorrow-study-plan.md`. It tells you exactly what to read, what to draw, and what interview answers to practice.
