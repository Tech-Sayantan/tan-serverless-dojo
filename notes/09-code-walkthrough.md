# Code Walkthrough

## `src/order_ingest/app.py`

This Lambda is the producer.

Imports:

```python
import json
import os
import uuid
from datetime import datetime, timezone
import boto3
```

Why:

- `json`: convert Python dictionaries to JSON strings
- `os`: read environment variables
- `uuid`: generate unique order IDs
- `datetime`: create timestamps
- `boto3`: call AWS services from Python

SNS client:

```python
sns = boto3.client("sns")
```

This creates a reusable AWS SDK client outside the handler. Lambda may reuse the execution environment, so this avoids recreating the client every invocation.

Handler:

```python
def lambda_handler(event, context):
```

AWS calls this function when Lambda is invoked.

Normalize input:

```python
event = event or {}
```

This prevents errors if the event is missing or null.

Build the order:

```python
order = {
    "eventType": "order.created",
    "orderId": event.get("orderId", str(uuid.uuid4())),
    "item": event.get("item", "cold brew"),
    "quantity": int(event.get("quantity", 1)),
    "priority": event.get("priority", "NORMAL"),
    "channel": event.get("channel", "manual"),
    "createdAt": datetime.now(timezone.utc).isoformat(),
}
```

This creates a consistent event even if the caller sends only partial input.

Publish to SNS:

```python
publish_response = sns.publish(
    TopicArn=os.environ["ORDERS_TOPIC_ARN"],
    Message=json.dumps(order),
    MessageAttributes={
        "priority": {
            "DataType": "String",
            "StringValue": order["priority"],
        }
    },
)
```

Important parts:

- `ORDERS_TOPIC_ARN` comes from the SAM template environment variable.
- `Message` is the JSON body.
- `MessageAttributes.priority` powers the SNS filter policy.

Return:

```python
return result
```

The result goes back to the caller when you invoke the Lambda manually.

## `src/order_processor/app.py`

This Lambda is the worker.

It is triggered by SQS, so the event contains `Records`.

```python
for record in event.get("Records", []):
    body = json.loads(record["body"])
```

Each record is one SQS message. `record["body"]` is a JSON string, so we parse it.

Validation:

```python
if quantity <= 0:
    raise ValueError(f"Invalid quantity {quantity} for order {order_id}")
```

This intentionally creates a failure for the poison test event.

Why raise an error?

Because Lambda plus SQS treats function failure as processing failure. The message is not deleted, so it can be retried.

Successful processing:

```python
processed.append(
    {
        "orderId": order_id,
        "item": item,
        "quantity": quantity,
        "status": "processed",
    }
)
```

In a real app this might write to a database, call another service, or publish another event.

## What Is Missing On Purpose

This repo is intentionally small, so it does not yet include:

- database writes
- idempotency store
- unit tests
- structured logger library
- tracing
- separate dev/stage/prod environments

Those are good next labs.
