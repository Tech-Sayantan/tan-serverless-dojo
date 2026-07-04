# Runbook

Use this when the stack is deployed and you want to test it.

## 1. Check Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name tan-serverless-dojo \
  --profile serverless-lab \
  --region us-east-1 \
  --query "Stacks[0].Outputs"
```

Find:

- `OrderIngestFunctionName`
- `OrderProcessorFunctionName`
- `OrdersQueueUrl`
- `OrdersDlqUrl`
- `HighPriorityAuditQueueUrl`
- `AlarmNotificationTopicArn`

## 2. Confirm Email Subscription

After deploy, AWS sends a confirmation email to:

```text
sayantan.chowdhury.tech@gmail.com
```

Open the email and click `Confirm subscription`.

Why:

```text
CloudWatch alarm -> SNS topic -> email subscription
```

The SNS topic cannot email you until the subscription is confirmed.

## 3. Happy Path

Invoke the producer:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/manual-order.json \
  --cli-binary-format raw-in-base64-out \
  --profile serverless-lab \
  --region us-east-1 \
  response.json
cat response.json
```

What should happen:

```text
OrderIngest Lambda publishes to SNS
SNS sends to OrdersQueue
OrderProcessor Lambda receives from SQS
OrderProcessor succeeds
message disappears from main queue
```

## 4. Check Logs

Producer logs:

```bash
aws logs tail /aws/lambda/tan-serverless-dojo-order-ingest \
  --since 10m \
  --profile serverless-lab \
  --region us-east-1
```

Worker logs:

```bash
aws logs tail /aws/lambda/tan-serverless-dojo-order-processor \
  --since 10m \
  --profile serverless-lab \
  --region us-east-1
```

## 5. Check High Priority Fanout

Receive from `HighPriorityAuditQueueUrl`:

```bash
aws sqs receive-message \
  --queue-url "<HighPriorityAuditQueueUrl>" \
  --max-number-of-messages 1 \
  --wait-time-seconds 2 \
  --profile serverless-lab \
  --region us-east-1
```

Because `manual-order.json` has:

```json
"priority": "HIGH"
```

the audit queue should receive a copy.

## 6. Poison Message Path

Invoke the producer with an invalid quantity:

```bash
aws lambda invoke \
  --function-name tan-serverless-dojo-order-ingest \
  --payload fileb://events/poison-order.json \
  --cli-binary-format raw-in-base64-out \
  --profile serverless-lab \
  --region us-east-1 \
  response.json
cat response.json
```

What should happen:

```text
OrderProcessor receives message
quantity = 0
worker raises ValueError
Lambda fails
SQS retries
after maxReceiveCount = 3, message moves to DLQ
CloudWatch alarm can enter ALARM
SNS can send email notification
```

The email can take a few minutes because the message must fail, retry, move to DLQ, and then CloudWatch must evaluate the SQS metric.

## 7. Watch The Alarm

Check alarm state:

```bash
aws cloudwatch describe-alarms \
  --alarm-names tan-serverless-dojo-orders-dlq-visible \
  --profile serverless-lab \
  --region us-east-1 \
  --query "MetricAlarms[0].StateValue"
```

When it becomes `ALARM`, the confirmed email subscription should receive a notification.

## 8. Cleanup

From local machine:

```bash
sam delete --stack-name tan-serverless-dojo --profile serverless-lab --region us-east-1 --no-prompts
```

Or from GitHub:

```text
Actions -> Destroy serverless stack -> Run workflow
```

## Debug Checklist

If Lambda does not run:

- check the function exists
- check CloudFormation stack status
- check IAM role permissions
- check CloudWatch logs

If SQS messages do not process:

- check event source mapping
- check Lambda errors
- check visibility timeout
- check DLQ

If GitHub Actions cannot authenticate:

- check `id-token: write`
- check AWS role trust policy
- check repo name in `sub`
- check branch is `main`
