# SQS

## What SQS Is

Amazon SQS is a managed message queue. It stores messages until a consumer is ready to process them.

In plain English:

```text
producer puts work into a queue
consumer picks work up later
```

## Why SQS Exists

Without a queue:

```text
Producer -> Consumer
```

If the consumer is slow or down, the producer suffers.

With SQS:

```text
Producer -> SQS -> Consumer
```

The producer can finish quickly. The consumer processes at its own pace.

## Our Queues

`OrdersQueue` is the main processing queue.

`OrdersDLQ` is the dead-letter queue for messages that fail repeatedly.

`HighPriorityAuditQueue` receives only high-priority messages from SNS.

## Visibility Timeout

When a consumer receives a message, SQS does not delete it immediately.

Instead:

```text
message received
  -> message becomes invisible temporarily
  -> consumer processes it
  -> consumer deletes it on success
```

If the consumer crashes before deleting it, the message becomes visible again after the visibility timeout.

In our template:

```yaml
VisibilityTimeout: 30
```

That means the worker has 30 seconds to process and delete the message before it can be retried.

## Retry And DLQ

In our template:

```yaml
RedrivePolicy:
  deadLetterTargetArn: !GetAtt OrdersDLQ.Arn
  maxReceiveCount: 3
```

If a message is received and fails enough times, SQS moves it to the DLQ.

This is important because a single poison message should not block normal processing forever.

## At-Least-Once Delivery

SQS standard queues provide at-least-once delivery.

That means:

- a message should be delivered
- duplicates can happen
- order is not strictly guaranteed

This leads to a major design rule:

```text
Consumers should be idempotent.
```

Idempotent means processing the same message twice does not corrupt the system.

Example:

```text
If payment for order 123 is already marked paid, do not charge it again.
```

## Long Polling

In our template:

```yaml
ReceiveMessageWaitTimeSeconds: 10
```

This enables long polling. Instead of immediately returning empty when no message exists, SQS waits briefly for a message.

Benefits:

- fewer empty receives
- lower cost
- less noisy polling

## Interview Answer

SQS is used to decouple producers from consumers, buffer spikes, support asynchronous processing, and provide retries with DLQs. The consumer must be idempotent because standard SQS can deliver duplicates.
