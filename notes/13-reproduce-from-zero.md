# Reproduce From Zero

Use this guide when you want to rebuild the same lab from an empty AWS account and a GitHub repo.

## Big Picture

The system has two tracks:

```text
application track:
  Lambda code
  SAM template
  test events

deployment track:
  GitHub Actions workflow
  GitHub OIDC provider in AWS
  IAM role for the workflow
  CloudFormation stack
```

The application track explains what we want AWS to create. The deployment track explains who is allowed to create it.

## Step 1: Local Repo

Create a repo:

```bash
mkdir tan-serverless-dojo
cd tan-serverless-dojo
git init
git branch -m main
```

Create folders:

```bash
mkdir -p src/order_ingest src/order_processor events .github/workflows notes
```

The important files are:

```text
template.yaml
src/order_ingest/app.py
src/order_processor/app.py
events/manual-order.json
events/poison-order.json
.github/workflows/deploy.yml
.github/workflows/destroy.yml
```

## Step 2: Producer Lambda Code

`src/order_ingest/app.py`:

```python
import json
import os
import uuid
from datetime import datetime, timezone

import boto3


sns = boto3.client("sns")


def lambda_handler(event, context):
    event = event or {}
    order = {
        "eventType": "order.created",
        "orderId": event.get("orderId", str(uuid.uuid4())),
        "item": event.get("item", "cold brew"),
        "quantity": int(event.get("quantity", 1)),
        "priority": event.get("priority", "NORMAL"),
        "channel": event.get("channel", "manual"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

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

    result = {
        "message": "Order published to SNS",
        "order": order,
        "snsMessageId": publish_response["MessageId"],
        "requestId": context.aws_request_id,
    }
    print(json.dumps(result))
    return result
```

Concept:

```text
Lambda receives input
  -> creates a normalized event
  -> publishes it to SNS
```

Important detail:

`priority` is sent as an SNS message attribute because SNS filter policies read attributes, not the JSON body.

## Step 3: Worker Lambda Code

`src/order_processor/app.py`:

```python
import json


def lambda_handler(event, context):
    print(json.dumps({"message": "Worker received event", "event": event}))

    processed = []
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        order_id = body["orderId"]
        quantity = int(body["quantity"])
        item = body["item"]

        if quantity <= 0:
            raise ValueError(f"Invalid quantity {quantity} for order {order_id}")

        processed.append(
            {
                "orderId": order_id,
                "item": item,
                "quantity": quantity,
                "status": "processed",
            }
        )

    result = {"message": "Orders processed", "processed": processed}
    print(json.dumps(result))
    return result
```

Concept:

```text
SQS event contains Records
  -> each record has a body
  -> body is JSON string
  -> worker validates and processes it
```

The `quantity <= 0` branch creates the failure scenario used to test retries, DLQ, CloudWatch alarm, and email notification.

## Step 4: SAM Template

The SAM template defines AWS resources:

```text
SNS topic
SQS main queue
SQS DLQ
SQS high-priority audit queue
Lambda producer
Lambda worker
EventBridge scheduled rule
CloudWatch log groups
CloudWatch DLQ alarm
SNS email topic for alarm notifications
```

Key connection:

```text
OrderIngestFunction publishes to OrdersTopic
OrdersTopic subscribes OrdersQueue
OrdersQueue triggers OrderProcessorFunction
OrdersQueue redrives failed messages to OrdersDLQ
OrdersDLQ metric triggers CloudWatch alarm
CloudWatch alarm publishes to AlarmNotificationTopic
AlarmNotificationTopic emails the confirmed subscriber
```

## Step 5: Local Validation

```bash
sam validate --lint
sam build
```

If `sam validate --lint` fails, the problem is usually template syntax or invalid resource properties.

If `sam build` fails, the problem is usually code folder paths or dependency packaging.

## Step 6: GitHub Repo

Create and push:

```bash
gh auth login
gh repo create tan-serverless-dojo --public --source=. --remote=origin --push
```

## Step 7: AWS OIDC Provider

Check provider:

```bash
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com
```

Create provider if missing:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

Concept:

```text
AWS trusts GitHub's OIDC token issuer
```

## Step 8: AWS Role For GitHub Actions

Create a role trusted by only this repo and branch:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:ref:refs/heads/main"
    }
  }
}
```

Concept:

```text
Only GitHub Actions from this repo's main branch can assume the role
```

## Step 9: GitHub Actions Deploy

The important OIDC pieces are:

```yaml
permissions:
  id-token: write
  contents: read
```

and:

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::<account-id>:role/<role-name>
    aws-region: us-east-1
```

Then the workflow runs:

```bash
sam validate --lint
sam build
sam deploy
```

## Step 10: Email Confirmation

After deploy, AWS SNS sends a confirmation email.

Until you click confirm:

```text
SNS subscription = Pending confirmation
alarm emails = not delivered
```

After confirmation:

```text
CloudWatch alarm -> SNS -> email
```

## Step 11: Test

Happy path:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/manual-order.json \
  --cli-binary-format raw-in-base64-out \
  response.json
```

Failure path:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/poison-order.json \
  --cli-binary-format raw-in-base64-out \
  response.json
```

Expected failure journey:

```text
worker fails
SQS retries
message moves to DLQ
CloudWatch alarm enters ALARM
SNS sends email
```

## Step 12: Cleanup

Delete app stack:

```bash
sam delete --stack-name tan-serverless-dojo --region us-east-1 --no-prompts
```

Then delete bootstrap IAM resources if this was only a lab:

```text
GitHub Actions role
attached GitHub Actions policy
OIDC provider, if no other repo uses it
lab IAM user/access keys/group/policies
manual test Lambda and manual SQS queue
```
