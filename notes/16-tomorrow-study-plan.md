# Tomorrow Study Plan

Use this file as your study route. Do not read the notes alphabetically. Read like an engineer tracing one event through a production system.

## Goal For Tomorrow

By the end of the session, you should be able to explain this without looking:

```text
Manual test event
  -> OrderIngest Lambda
  -> SNS topic
  -> SQS queue
  -> OrderProcessor Lambda
  -> CloudWatch logs
  -> DLQ on failure
  -> CloudWatch alarm
  -> SNS email notification
```

The real skill is not saying "I used Lambda, SQS, SNS." The real skill is explaining why each hop exists and what fails at each hop.

## Before You Start

Keep three tabs or windows open:

```text
README.md
template.yaml
notes/
```

Your main files:

```text
src/order_ingest/app.py
src/order_processor/app.py
template.yaml
.github/workflows/deploy.yml
.github/workflows/destroy.yml
```

Your main notes:

```text
00-learning-map.md
02-lambda.md
03-sqs.md
04-sns.md
05-eventbridge.md
06-cloudwatch.md
08-github-actions-oidc.md
09-code-walkthrough.md
14-production-issues-troubleshooting.md
17-deep-dive-field-guide.md
```

## Study Block 1: The Story First

Read:

```text
00-learning-map.md
01-architecture-use-case.md
README.md
```

What to understand:

- This is not five random AWS services.
- It is one event-driven backend.
- Lambda does compute.
- SNS broadcasts.
- SQS buffers.
- EventBridge triggers scheduled work.
- CloudWatch makes the system observable.
- SAM and GitHub Actions make it repeatable.

Draw this by hand:

```text
OrderIngest Lambda
  publishes order.created
        |
        v
      SNS topic
       /     \
      v       v
 OrdersQueue  HighPriorityAuditQueue
      |
      v
OrderProcessor Lambda
      |
      v
CloudWatch Logs and Metrics
      |
      v
DLQ Alarm -> SNS Email
```

Checkpoint question:

```text
Why did we not directly call OrderProcessor from OrderIngest?
```

Good answer:

```text
Direct calls couple the producer to the worker. If the worker is slow or down, the producer is affected. SQS decouples them, stores messages durably, and lets the worker process at its own pace.
```

## Study Block 2: Lambda

Read:

```text
02-lambda.md
09-code-walkthrough.md
```

Look at:

```text
src/order_ingest/app.py
src/order_processor/app.py
```

What to understand:

- A Lambda function is code plus configuration.
- AWS invokes the handler.
- `event` is the input.
- `context` is invocation metadata.
- The execution role is the runtime identity.
- Environment variables connect code to deployed resources.
- Logs go to CloudWatch automatically when the role has log permissions.

Key code:

```python
def lambda_handler(event, context):
    ...
```

Explain it:

```text
AWS does not run the whole file like a normal script from the command line. It imports the module and calls the configured handler. In this repo the handler is app.lambda_handler, meaning app.py and lambda_handler function.
```

Checkpoint question:

```text
What is the difference between the deploy role and the Lambda execution role?
```

Good answer:

```text
The deploy role creates or updates infrastructure. The Lambda execution role is assumed by Lambda at runtime when the function needs to write logs, publish to SNS, or poll SQS.
```

## Study Block 3: SNS And SQS Together

Read:

```text
03-sqs.md
04-sns.md
17-deep-dive-field-guide.md
```

What to understand:

- SNS is push-based fanout.
- SQS is pull-based buffering.
- SNS plus SQS is a common production pattern.
- SNS filter policies use message attributes.
- SQS queue policies are required so SNS can send messages to the queue.
- Standard SQS is at-least-once, so duplicate processing is possible.
- DLQ is for messages that repeatedly fail.

The core pattern:

```text
One event is published once.
Multiple consumers receive their own copy.
Each consumer can fail independently.
```

In our repo:

```text
OrdersTopic -> OrdersQueue -> OrderProcessorFunction
OrdersTopic -> HighPriorityAuditQueue only when priority = HIGH
```

Checkpoint question:

```text
Why did the high-priority audit queue receive only HIGH orders?
```

Good answer:

```text
Because the SNS subscription has a filter policy on the priority message attribute. The producer publishes priority as a MessageAttribute, and SNS evaluates that before delivering to the subscription.
```

## Study Block 4: Failure Path

Read:

```text
11-runbook.md
14-production-issues-troubleshooting.md
```

Understand the poison message:

```json
{
  "item": "espresso",
  "quantity": 0,
  "priority": "HIGH",
  "channel": "manual"
}
```

In the worker:

```python
if quantity <= 0:
    raise ValueError(f"Invalid quantity {quantity} for order {order_id}")
```

What happens:

```text
Worker raises error
  -> Lambda reports batch failure
  -> SQS message is not deleted
  -> visibility timeout expires
  -> message is retried
  -> after maxReceiveCount, SQS moves it to DLQ
  -> CloudWatch alarm sees DLQ visible message
  -> alarm publishes to SNS notification topic
  -> confirmed email subscription receives mail
```

Checkpoint question:

```text
Why did email not arrive before subscription confirmation?
```

Good answer:

```text
SNS email subscriptions must be confirmed before delivery. Also, CloudWatch alarms publish actions on state transitions such as OK to ALARM. If the alarm entered ALARM before the subscription was confirmed, that old notification is not replayed.
```

## Study Block 5: EventBridge

Read:

```text
05-eventbridge.md
```

What to understand:

- EventBridge can be a scheduler.
- EventBridge can also be an event bus.
- In this repo we used it as a schedule trigger.
- The schedule is disabled by default to avoid surprise invocations.
- Lambda needs explicit permission allowing `events.amazonaws.com` to invoke it.

Checkpoint question:

```text
Why use EventBridge instead of cron on an EC2 server?
```

Good answer:

```text
EventBridge removes server maintenance, integrates with AWS targets, has managed scheduling, and can invoke Lambda directly with IAM-controlled permissions.
```

## Study Block 6: CloudWatch

Read:

```text
06-cloudwatch.md
14-production-issues-troubleshooting.md
```

What to understand:

- Logs are evidence.
- Metrics show behavior over time.
- Alarms detect conditions.
- Dashboards give shared visibility.
- Log groups can be auto-created by Lambda, but production teams usually define them in IaC to control retention.

Important production lesson:

```text
Do not only alarm on Lambda errors. Also alarm on queue depth, age of oldest message, and DLQ depth.
```

Checkpoint question:

```text
If SQS backlog grows but Lambda errors are zero, what could be happening?
```

Good answer:

```text
The worker may be too slow, concurrency may be limited, downstream systems may be slow, or the producer rate may exceed consumer capacity. Error-free does not mean healthy.
```

## Study Block 7: SAM, CloudFormation, And GitHub Actions

Read:

```text
07-sam-cloudformation.md
08-github-actions-oidc.md
13-reproduce-from-zero.md
```

What to understand:

- `template.yaml` is desired infrastructure state.
- SAM simplifies serverless CloudFormation.
- `sam build` packages code.
- `sam deploy` creates a CloudFormation changeset and applies it.
- GitHub Actions runs the same commands in CI.
- OIDC lets GitHub assume an AWS role without static AWS keys.

Checkpoint question:

```text
Why is OIDC better than AWS access keys in GitHub Secrets?
```

Good answer:

```text
OIDC uses short-lived credentials and a trust policy scoped to a repo and branch. Static access keys can leak, live too long, and need manual rotation.
```

## Study Block 8: Interview Story Practice

Read:

```text
10-interview-prep.md
15-study-checklist-before-interview.md
17-deep-dive-field-guide.md
```

Practice this answer:

```text
I built an event-driven serverless pipeline using Lambda, SNS, SQS, EventBridge, CloudWatch, SAM, and GitHub Actions OIDC. A producer Lambda normalizes an order event and publishes it to SNS. SNS fans out to SQS queues, including a filtered high-priority audit queue. A worker Lambda consumes from SQS, and failures are retried and moved to a DLQ. CloudWatch logs, metrics, dashboard, and alarms provide operational visibility, and alarm notifications are sent through SNS email. The stack is deployed through GitHub Actions using OIDC, so no long-lived AWS keys are stored in GitHub.
```

Then practice the production version:

```text
In production I would add idempotency with DynamoDB, partial batch failure handling, structured logs with correlation IDs, alarms on queue age and DLQ depth, least-privilege IAM, separate environments, and a DLQ replay process.
```

## Final Tomorrow Checklist

You are ready when you can answer these without notes:

- What is Lambda?
- What are `event` and `context`?
- What is an execution role?
- Why SNS?
- Why SQS?
- Why SNS plus SQS?
- What is visibility timeout?
- What is a DLQ?
- Why can SQS process duplicates?
- What is EventBridge?
- What is a CloudWatch log group?
- Why did email require SNS confirmation?
- What does SAM do?
- What does GitHub Actions OIDC do?
- What production issues can happen in this architecture?
- How would you troubleshoot a missing email, queue backlog, duplicate message, or AccessDenied?

## Tomorrow's Best Order

Use this exact sequence:

```text
1. 00-learning-map.md
2. 01-architecture-use-case.md
3. 02-lambda.md
4. 09-code-walkthrough.md
5. 03-sqs.md
6. 04-sns.md
7. 05-eventbridge.md
8. 06-cloudwatch.md
9. 07-sam-cloudformation.md
10. 08-github-actions-oidc.md
11. 14-production-issues-troubleshooting.md
12. 17-deep-dive-field-guide.md
13. 15-study-checklist-before-interview.md
```

Keep `13-reproduce-from-zero.md` for the day you want to recreate the lab hands-on.

