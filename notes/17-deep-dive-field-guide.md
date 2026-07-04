# Deep Dive Field Guide

This is the interview-prep version of the project. It connects concept, code, setup, production issues, and the kind of anecdotes you can use in an interview.

## The System In One Sentence

This repo is an asynchronous event-driven backend where Lambda produces an event, SNS broadcasts it, SQS buffers it, another Lambda processes it, EventBridge can generate scheduled events, and CloudWatch observes the whole thing.

## Why This Architecture Exists

Imagine a backend where every service calls the next service directly:

```text
API -> Service A -> Service B -> Service C -> Email service
```

This is easy to understand, but it is fragile:

- if Service B is slow, Service A waits
- if Service C is down, the whole request may fail
- retries can accidentally duplicate side effects
- traffic spikes hit every downstream service immediately
- debugging becomes a chain of timeouts

The event-driven version changes the shape:

```text
producer publishes event
  -> durable messaging layer stores or routes it
  -> consumers process independently
```

The tradeoff is important:

```text
You gain decoupling, buffering, retry, and fanout.
You accept eventual consistency and more operational observability needs.
```

Interview anecdote:

```text
I would choose this for workloads where the producer does not need an immediate result from every downstream consumer. For example, an order ingestion service should not fail only because an analytics or email worker is temporarily slow.
```

## Lambda Deep Dive

### What Lambda Is

Lambda is managed compute for short-running functions. You provide:

- code
- runtime
- handler
- memory
- timeout
- IAM execution role
- trigger or invocation method

AWS provides:

- provisioning
- scaling
- runtime execution
- basic logs integration
- metrics

In this repo:

```text
OrderIngestFunction: creates and publishes order events
OrderProcessorFunction: consumes SQS messages and processes orders
```

### Handler

Code:

```python
def lambda_handler(event, context):
    ...
```

Explanation:

```text
The handler is the entry point AWS calls. In SAM we configured Handler: app.lambda_handler, so AWS loads app.py and calls lambda_handler.
```

`event`:

```text
The input payload. Its shape depends on the trigger.
Manual invoke gives the JSON you send.
SQS trigger gives {"Records": [...]}
EventBridge gives a scheduled or event-bus shaped event.
```

`context`:

```text
Runtime metadata such as request ID, function name, memory limit, and remaining time.
```

Example:

```python
result = {
    "requestId": context.aws_request_id,
    "message": "Order published to SNS",
}
```

Why this matters:

```text
Request IDs help connect a single invocation to logs and errors.
```

### Why Create Boto3 Client Outside The Handler

In `src/order_ingest/app.py`:

```python
sns = boto3.client("sns")
```

This is outside the handler.

Why:

```text
Lambda may reuse the same execution environment for multiple invocations. Creating clients outside the handler lets warm invocations reuse them instead of creating a new client every time.
```

Interview line:

```text
I keep expensive or reusable initialization outside the handler to benefit from execution environment reuse, while keeping request-specific data inside the handler.
```

### Cold Start

A cold start happens when Lambda needs to create a new execution environment:

```text
download code
start runtime
import modules
initialize global code
call handler
```

For this project, cold start is tiny because:

- Python code is small
- no heavy dependencies
- no VPC attachment
- memory is small but sufficient

Production notes:

- Java and .NET can have larger cold starts than small Python functions.
- VPC networking can add complexity, though AWS has improved this over time.
- Provisioned Concurrency can reduce cold starts when latency is critical.
- Memory also affects CPU allocation, so increasing memory can sometimes reduce duration.

### Lambda Production Issues

Common issues:

- timeout too low
- memory too low
- AccessDenied from execution role
- dependency packaging error
- environment variable missing
- concurrency throttling
- poison messages causing repeated failures

Troubleshooting order:

```text
1. Check invocation count.
2. Check error count.
3. Tail CloudWatch logs.
4. Verify execution role permissions.
5. Verify environment variables.
6. Check timeout, duration, and memory used.
```

Useful command:

```bash
aws logs tail /aws/lambda/<function-name> --since 15m --follow
```

## SNS Deep Dive

### What SNS Is

SNS is a publish-subscribe service.

Vocabulary:

```text
topic: named event channel
publisher: service that sends a message to the topic
subscription: target that receives messages from the topic
subscriber: SQS, Lambda, email, HTTP endpoint, etc.
```

In this repo:

```text
OrderIngestFunction publishes to OrdersTopic.
OrdersTopic delivers to OrdersQueue.
OrdersTopic also delivers HIGH priority orders to HighPriorityAuditQueue.
```

### Message Attributes

In code:

```python
MessageAttributes={
    "priority": {
        "DataType": "String",
        "StringValue": order["priority"],
    }
}
```

Why:

```text
SNS filter policies evaluate message attributes. They do not inspect random JSON fields inside the message body by default.
```

In SAM:

```yaml
FilterPolicy:
  priority:
    - HIGH
```

Meaning:

```text
Only messages with MessageAttributes.priority = HIGH are delivered to this subscription.
```

### SNS To SQS Needs A Queue Policy

SQS queues do not automatically accept messages from SNS. The queue must allow SNS to send.

Template idea:

```yaml
Statement:
  - Effect: Allow
    Principal:
      Service: sns.amazonaws.com
    Action: sqs:SendMessage
    Resource: !GetAtt OrdersQueue.Arn
    Condition:
      ArnEquals:
        aws:SourceArn: !Ref OrdersTopic
```

Explanation:

```text
This says the SNS service may send messages to this SQS queue, but only when the source topic is our OrdersTopic.
```

Interview anecdote:

```text
When SNS publish succeeds but SQS stays empty, I check the subscription, filter policy, and queue policy. The publish success only proves SNS accepted the message; it does not prove every subscriber received it.
```

## SQS Deep Dive

### What SQS Is

SQS is a durable queue.

Producer sends:

```text
message -> queue
```

Consumer receives:

```text
queue -> message -> process -> delete
```

The delete step matters. SQS does not delete the message just because a consumer received it.

### Visibility Timeout

When a worker receives a message:

```text
message becomes invisible for visibility timeout
worker processes it
if success, message is deleted
if failure, message becomes visible again
```

Why:

```text
If the worker crashes halfway, another worker can retry later.
```

Bad configuration:

```text
worker needs 60 seconds
visibility timeout is 30 seconds
```

Possible result:

```text
same message becomes visible while first worker is still processing
duplicate processing happens
```

### At-Least-Once Delivery

Standard SQS can deliver a message more than once.

Production rule:

```text
Every SQS consumer should be idempotent.
```

Idempotent means:

```text
Processing the same message twice does not create incorrect duplicate side effects.
```

Example with DynamoDB:

```python
def process_order(order):
    dynamodb.put_item(
        TableName="processed-orders",
        Item={"orderId": {"S": order["orderId"]}},
        ConditionExpression="attribute_not_exists(orderId)",
    )
    charge_customer(order)
```

Explanation:

```text
The conditional write succeeds only once per orderId. If the same message arrives again, DynamoDB rejects the duplicate and the worker can safely skip the side effect.
```

### DLQ

A dead-letter queue stores messages that failed too many times.

In our template:

```yaml
RedrivePolicy:
  deadLetterTargetArn: !GetAtt OrdersDLQ.Arn
  maxReceiveCount: 3
```

Meaning:

```text
After a message is received and fails enough times, SQS moves it to OrdersDLQ.
```

DLQ is not a trash can. It is an operations queue.

Production DLQ workflow:

```text
alarm fires
engineer inspects message
classify bad data vs temporary failure vs code bug
fix root cause
replay safely if appropriate
delete or archive if permanently invalid
```

### Partial Batch Failure

Our repo uses `BatchSize: 1` to keep learning simple.

In production, batches are common. If batch size is 10 and one message fails, you do not want the other 9 successful messages to retry.

Lambda supports partial batch response for SQS.

Sample pattern:

```python
def lambda_handler(event, context):
    failed = []

    for record in event["Records"]:
        try:
            process_one(record)
        except Exception:
            failed.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failed}
```

Explanation:

```text
Lambda deletes successful messages and retries only the failed message IDs.
```

Interview line:

```text
For high-throughput SQS consumers, I prefer partial batch response so one poison message does not force the entire batch to retry.
```

## EventBridge Deep Dive

### Schedule Use Case

In this repo:

```text
EventBridge schedule -> OrderIngest Lambda
```

It is disabled by default:

```yaml
ScheduleState:
  Default: DISABLED
```

Why:

```text
This avoids surprise invocations and keeps the lab cheap.
```

### Permission

EventBridge cannot invoke Lambda just because a rule points to it. Lambda resource policy must allow it.

Template:

```yaml
OrderSchedulePermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref OrderIngestFunction
    Action: lambda:InvokeFunction
    Principal: events.amazonaws.com
    SourceArn: !GetAtt OrderScheduleRule.Arn
```

Explanation:

```text
This grants EventBridge permission to invoke only this Lambda from this rule.
```

### Event Bus Use Case

EventBridge can also route domain events by pattern.

Example pattern:

```json
{
  "source": ["tan.orders"],
  "detail-type": ["OrderCreated"],
  "detail": {
    "priority": ["HIGH"]
  }
}
```

Use EventBridge when:

- you want event routing by pattern
- you want SaaS/AWS service integrations
- you want archive/replay or schema registry concepts
- you want event bus style architecture

Use SNS when:

- you want simple high-throughput pub/sub fanout
- you want direct push to SQS/Lambda/email/HTTP
- message attribute filtering is enough

Interview line:

```text
SNS is often simpler fanout. EventBridge is richer event routing.
```

## CloudWatch Deep Dive

### Logs

Every `print(...)` in Lambda goes to CloudWatch Logs.

Example:

```python
print(json.dumps({"message": "Orders processed", "processed": processed}))
```

Production improvement:

```python
print(json.dumps({
    "level": "INFO",
    "component": "order_processor",
    "orderId": order_id,
    "message": "order processed"
}))
```

Why:

```text
Structured JSON logs are searchable and easier to correlate.
```

### Log Groups And Log Streams

Log group:

```text
/aws/lambda/tan-serverless-dojo-order-processor
```

Log stream:

```text
one stream per Lambda execution environment/version time slice
```

Lambda can auto-create log groups, but our template creates them:

```yaml
OrderProcessorLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub "/aws/lambda/${OrderProcessorFunction}"
    RetentionInDays: 7
```

Why:

```text
Explicit retention prevents logs from living forever and quietly increasing cost.
```

### Metrics

Lambda metrics:

- Invocations
- Errors
- Duration
- Throttles
- ConcurrentExecutions

SQS metrics:

- ApproximateNumberOfMessagesVisible
- ApproximateNumberOfMessagesNotVisible
- ApproximateAgeOfOldestMessage

DLQ alarm in this repo:

```yaml
MetricName: ApproximateNumberOfMessagesVisible
Threshold: 0
ComparisonOperator: GreaterThanThreshold
```

Meaning:

```text
If at least one message is visible in the DLQ, alarm.
```

### Alarm State Transitions

Alarm actions fire on state changes:

```text
OK -> ALARM
ALARM -> OK
INSUFFICIENT_DATA -> ALARM
```

Important lesson from our lab:

```text
If email subscription is pending when alarm enters ALARM, confirming the email later does not replay the old notification. You need another state transition or a direct SNS publish test.
```

## SAM And CloudFormation Deep Dive

### CloudFormation

CloudFormation manages desired infrastructure state.

You declare:

```yaml
Resources:
  OrdersTopic:
    Type: AWS::SNS::Topic
```

CloudFormation creates, updates, or deletes it.

### SAM

SAM is a serverless transform on top of CloudFormation.

This:

```yaml
Type: AWS::Serverless::Function
```

is expanded into lower-level resources such as Lambda function, permissions, roles, and event source mappings.

### Build And Deploy

```bash
sam validate --lint
sam build
sam deploy
```

Meaning:

```text
validate: check template
build: prepare code artifacts
deploy: upload artifacts and apply CloudFormation changeset
```

Why SAM uploads to S3:

```text
CloudFormation needs a location from which Lambda code artifacts can be fetched. SAM packages local code into S3-backed deployment artifacts.
```

### Changeset

A changeset is a deployment preview:

```text
Add OrdersQueue
Modify OrderProcessorFunction
Delete OldAlarm
```

Interview line:

```text
I like changesets because they show what infrastructure will change before applying the deployment.
```

## GitHub Actions OIDC Deep Dive

### Pipeline Flow

```text
workflow_dispatch
  -> checkout
  -> setup Python
  -> setup SAM
  -> configure AWS credentials with OIDC
  -> sam validate
  -> sam build
  -> sam deploy
```

### Why OIDC Is Better Than Access Keys

Access key approach:

```text
GitHub secret stores AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
```

Risk:

```text
long-lived credential
manual rotation
blast radius if leaked
harder to scope to repo and branch
```

OIDC approach:

```text
GitHub gets short-lived identity token
AWS verifies token
AWS returns temporary credentials for a role
```

Trust policy idea:

```json
{
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:Tech-Sayantan/tan-serverless-dojo:ref:refs/heads/main"
    }
  }
}
```

Explanation:

```text
Only GitHub Actions from this repo and branch can assume the deploy role.
```

Production improvement:

```text
Use separate roles for dev, stage, and prod. Protect prod with environments and manual approvals.
```

## Production Troubleshooting Map

Use this sequence when something breaks:

```text
1. Did producer Lambda run?
2. Did it publish to SNS?
3. Did SNS subscription exist and match filters?
4. Did SQS receive the message?
5. Did Lambda event source mapping poll SQS?
6. Did worker Lambda succeed?
7. Did failures reach DLQ?
8. Did CloudWatch alarm change state?
9. Did SNS email subscription deliver?
```

### Scenario: No Worker Logs

Likely causes:

- SQS has no messages
- event source mapping disabled
- Lambda lacks poll permission
- wrong queue ARN
- concurrency is zero

Commands:

```bash
aws lambda list-event-source-mappings --function-name <worker-name>
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All
```

### Scenario: Message Keeps Coming Back

Likely causes:

- worker raises exception
- timeout
- visibility timeout too low
- downstream service failure
- bad message payload

Commands:

```bash
aws logs tail /aws/lambda/<worker-name> --since 30m
aws sqs receive-message --queue-url <queue-url> --attribute-names All --message-attribute-names All
```

### Scenario: Duplicate Business Action

Likely causes:

- SQS at-least-once delivery
- worker timed out after side effect
- no idempotency key
- retry after partial failure

Fix:

```text
Use idempotency key such as orderId.
Store processed IDs with conditional write.
Make external calls safely retryable.
```

### Scenario: Alarm Did Not Email

Likely causes:

- subscription pending
- alarm already in ALARM
- wrong topic in AlarmActions
- spam/promotions folder
- metric delay

Commands:

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name>
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
aws sns publish --topic-arn <topic-arn> --subject "Test" --message "Hello"
```

### Scenario: GitHub Deploy Fails

Likely causes:

- OIDC provider missing
- trust policy repo/branch mismatch
- workflow missing `id-token: write`
- role policy too narrow
- CloudFormation stack rollback

Commands:

```bash
aws iam get-role --role-name <role-name>
aws cloudformation describe-stack-events --stack-name <stack-name>
```

## What To Learn Next Before Interview

### 1. DynamoDB Idempotency

Why:

```text
SQS duplicate delivery is normal. You need a durable processed-event store.
```

Practice:

```text
Add DynamoDB table with orderId as partition key.
Worker conditionally writes orderId before processing.
Duplicate messages are skipped.
```

### 2. Lambda Partial Batch Response

Why:

```text
Batch processing is common. One failed message should not retry the whole batch.
```

Practice:

```text
Increase SQS BatchSize to 5.
Return batchItemFailures.
Test one poison message and four valid messages.
```

### 3. API Gateway

Why:

```text
Real users usually send HTTP requests, not CLI Lambda invokes.
```

Practice:

```text
API Gateway POST /orders -> OrderIngest Lambda -> SNS -> SQS -> worker.
```

### 4. Step Functions

Why:

```text
When workflows have many steps, branching, waiting, and compensation, Step Functions is clearer than chaining Lambdas manually.
```

Practice:

```text
Validate order -> reserve inventory -> charge -> notify.
```

### 5. Observability Upgrade

Learn:

- structured logging
- correlation IDs
- custom metrics
- CloudWatch Logs Insights
- X-Ray tracing
- AWS Lambda Powertools

Interview line:

```text
I would add correlation IDs so I can trace one business event through producer logs, SNS message ID, SQS message, worker logs, and DLQ records.
```

### 6. Security And Secrets

Learn:

- least privilege IAM
- permission boundaries
- Secrets Manager
- KMS encryption
- resource policies
- separate deploy and runtime roles

Interview line:

```text
I separate who can deploy from what the application can do at runtime.
```

### 7. Cost And Scaling

Learn:

- Lambda duration and memory pricing
- CloudWatch log retention cost
- SQS request cost
- EventBridge event cost
- NAT Gateway cost trap
- retry storms

Interview line:

```text
Serverless removes server management, but it does not remove capacity planning. You still need limits, alarms, and cost guardrails.
```

## MBRDI-Style Architecture Anecdotes

### Vehicle Telemetry

```text
Vehicle publishes telemetry.
Ingestion Lambda validates and enriches.
SNS or EventBridge broadcasts telemetry.received.
SQS queues isolate diagnostics, analytics, and notification workers.
DLQs preserve failed events.
CloudWatch alarms detect backlog or processing failures.
```

What to say:

```text
I would avoid letting analytics failures block telemetry ingestion. Async fanout lets safety-critical or user-facing paths remain isolated from lower-priority consumers.
```

### Diagnostic Trouble Code

```text
vehicle.dtc.detected
  -> event bus
  -> service recommendation worker
  -> notification worker
  -> analytics worker
```

Production concern:

```text
Duplicate events must not send duplicate user notifications, so the notification worker needs idempotency.
```

### Charging Session Completed

```text
charging.session.completed
  -> billing queue
  -> rewards queue
  -> analytics queue
```

Production concern:

```text
Billing may require stricter idempotency and ordering than analytics. Different queues let each consumer have its own retry and scaling behavior.
```

## Final Interview Script

Use this as your polished answer:

```text
I built a serverless event-driven pipeline with Lambda, SNS, SQS, EventBridge, CloudWatch, SAM, and GitHub Actions OIDC. The producer Lambda accepts an order event, normalizes it, and publishes it to SNS with message attributes. SNS fans out to SQS queues, including a filtered high-priority queue. The worker Lambda consumes from SQS, and failures are retried with visibility timeout and eventually moved to a DLQ. CloudWatch logs and metrics help debug the flow, and a DLQ alarm sends email through SNS. The infrastructure is defined in SAM and deployed through GitHub Actions using OIDC, so the pipeline does not store long-lived AWS keys.
```

Then add the senior follow-up:

```text
For production I would add idempotency with DynamoDB, partial batch failure handling, structured logs and correlation IDs, alarms on queue age and DLQ depth, least-privilege IAM, separate environments, and a documented DLQ replay process.
```

