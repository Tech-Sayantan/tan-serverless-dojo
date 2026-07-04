# Lambda

## What Lambda Is

AWS Lambda runs code in response to an event without you managing servers.

You provide:

- code
- runtime, such as Python 3.12
- handler
- memory
- timeout
- IAM execution role

AWS provides:

- compute environment
- scaling
- invocation handling
- integration with services such as SQS, SNS, EventBridge, and CloudWatch

## Mental Model

```text
event comes in
  -> AWS starts or reuses a Lambda execution environment
  -> AWS calls your handler
  -> your code returns or fails
  -> logs and metrics go to CloudWatch
```

## Handler

In our template:

```yaml
Handler: app.lambda_handler
CodeUri: src/order_ingest/
```

This means:

```text
folder: src/order_ingest/
file: app.py
function: lambda_handler
```

AWS imports `app.py` and calls:

```python
lambda_handler(event, context)
```

## Event

`event` is the input data for the invocation.

For manual invocation:

```json
{
  "item": "flat white",
  "quantity": 2,
  "priority": "HIGH",
  "channel": "manual"
}
```

For SQS-triggered Lambda, the event shape is different:

```json
{
  "Records": [
    {
      "body": "{\"orderId\":\"123\",\"item\":\"flat white\"}"
    }
  ]
}
```

Interview point: the same Lambda programming model is used, but each trigger sends a different event shape.

## Context

`context` is metadata from AWS about the current invocation.

Examples:

- request ID
- function name
- memory limit
- remaining execution time

In our ingest Lambda:

```python
"requestId": context.aws_request_id
```

This request ID is useful when tracing one execution through logs.

## Execution Role

Lambda does not automatically have permission to do everything. It assumes an IAM role.

In this repo, SAM creates function roles because the template uses `Policies`.

For `OrderIngestFunction`, the role allows:

- writing CloudWatch logs
- publishing to SNS

For `OrderProcessorFunction`, the role allows:

- writing CloudWatch logs
- polling and deleting messages from SQS

## Cold Start

If AWS needs to create a fresh execution environment, the first invocation has extra startup time. That is called a cold start.

Cold starts are affected by:

- runtime
- package size
- VPC configuration
- memory
- initialization code

Our functions are tiny, so cold starts should be low.

## Interview Answer

Lambda is good for event-driven workloads where code runs in response to events, scales automatically, and avoids server management. The tradeoffs are cold starts, timeout limits, package/runtime constraints, and the need to design for retries and idempotency.
