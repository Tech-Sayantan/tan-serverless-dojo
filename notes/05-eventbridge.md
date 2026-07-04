# EventBridge

## What EventBridge Is

Amazon EventBridge is an event routing and scheduling service.

It can be used in two major ways:

- event bus routing
- scheduled rules

This repo uses scheduled rules.

## Our Use Case

In `template.yaml`:

```yaml
OrderScheduleRule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: !Ref ScheduleExpression
    State: !Ref ScheduleState
    Targets:
      - Arn: !GetAtt OrderIngestFunction.Arn
```

This means EventBridge can invoke `OrderIngestFunction` on a timer.

By default:

```yaml
ScheduleState:
  Default: DISABLED
```

That keeps the lab cheap and quiet unless you intentionally enable it.

## Why Not Cron On A Server?

Old style:

```text
EC2 server with cron -> call script every 15 minutes
```

Serverless style:

```text
EventBridge schedule -> Lambda
```

Benefits:

- no server to patch
- no cron machine to monitor
- AWS handles triggering
- integrates cleanly with IAM and CloudWatch

## Permission

EventBridge cannot invoke Lambda unless Lambda permits it.

In our template:

```yaml
OrderSchedulePermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref OrderIngestFunction
    Action: lambda:InvokeFunction
    Principal: events.amazonaws.com
    SourceArn: !GetAtt OrderScheduleRule.Arn
```

This grants EventBridge permission to call the Lambda.

## EventBridge Event Shape

Our scheduled rule sends a simple static input:

```json
{
  "source": "eventbridge",
  "channel": "scheduled"
}
```

The ingest Lambda then fills missing fields with defaults.

## Interview Answer

EventBridge is useful for event routing and scheduled automation. In this repo it replaces a cron server by triggering a Lambda on a schedule. The schedule is disabled by default to avoid accidental recurring invocations during practice.
