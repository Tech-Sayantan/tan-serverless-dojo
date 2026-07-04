# CloudWatch

## What CloudWatch Is

CloudWatch is the observability layer for AWS.

It helps answer:

- What happened?
- How many times did it happen?
- Did anything fail?
- Is the system healthy?
- When should someone be alerted?

## Logs

When Lambda code runs:

```python
print(json.dumps(result))
```

that output goes to CloudWatch Logs.

For Lambda, log groups usually follow this pattern:

```text
/aws/lambda/<function-name>
```

In this repo:

```text
/aws/lambda/tan-serverless-dojo-order-ingest
/aws/lambda/tan-serverless-dojo-order-processor
```

## Log Group

A log group is the top-level container for logs.

```text
Log group
  -> log stream
    -> log events
```

For Lambda:

- log group usually maps to a function
- log stream usually maps to an execution environment
- log events are the individual lines

## Manual Log Groups

AWS can auto-create Lambda log groups, but our template creates them explicitly:

```yaml
OrderIngestLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    RetentionInDays: 7
```

Why create them ourselves?

- set retention
- avoid infinite log storage
- make logging part of infrastructure as code

## Metrics

Lambda automatically emits metrics such as:

- invocations
- errors
- duration
- throttles

SQS emits metrics such as:

- visible message count
- age of oldest message
- messages sent/received/deleted

## Alarm

This repo creates a CloudWatch alarm:

```yaml
OrdersDlqVisibleAlarm:
  MetricName: ApproximateNumberOfMessagesVisible
  Threshold: 0
  ComparisonOperator: GreaterThanThreshold
```

Meaning:

```text
if DLQ has more than 0 visible messages, alarm
```

That is a production-minded signal. A DLQ message means something failed repeatedly and needs investigation.

## Email Notification

The alarm publishes to an SNS notification topic:

```yaml
AlarmNotificationTopic:
  Type: AWS::SNS::Topic
```

The email subscription is:

```yaml
AlarmEmailSubscription:
  Type: AWS::SNS::Subscription
  Properties:
    Protocol: email
    Endpoint: !Ref NotificationEmail
```

CloudWatch does not email people directly in this design. The chain is:

```text
DLQ has visible messages
  -> CloudWatch alarm changes state
  -> alarm publishes to SNS topic
  -> SNS emails the subscribed address
```

Important: email subscriptions require confirmation. After deploy, AWS sends a confirmation email. Until the recipient clicks confirm, SNS will not deliver alarm emails.

## Dashboard

This repo also creates a dashboard with:

- Lambda invocations/errors
- SQS queue depth
- DLQ depth
- high-priority audit queue depth

## Interview Answer

CloudWatch provides logs, metrics, dashboards, and alarms. For Lambda and SQS systems, it is how teams debug execution, detect failures, watch queue backlogs, and alert when messages hit DLQs.
