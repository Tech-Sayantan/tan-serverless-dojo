# Production Issues And Troubleshooting

This is the file to study when interviewers ask, "What can go wrong in production?"

## Mental Model For Debugging

Always trace the event path:

```text
producer Lambda
  -> SNS publish
  -> SNS subscription/filter
  -> SQS queue
  -> Lambda event source mapping
  -> worker Lambda
  -> DLQ
  -> CloudWatch logs/metrics/alarms
```

Do not debug randomly. Find the last known good point.

## Issue 1: Lambda Does Not Run

Symptoms:

- no CloudWatch logs
- no invocation metric
- CLI invoke fails
- EventBridge schedule appears active but function does not run

Likely causes:

- function not deployed
- wrong region
- wrong function name
- missing Lambda invoke permission
- EventBridge rule disabled
- IAM permission issue

How to troubleshoot:

```bash
aws lambda get-function --function-name <name> --region us-east-1
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>
aws events describe-rule --name <rule-name>
```

For EventBridge:

```text
Rule exists
Rule is ENABLED
Rule target points to Lambda
Lambda permission allows events.amazonaws.com
```

Fix:

- enable rule
- fix target ARN
- add `AWS::Lambda::Permission`
- redeploy SAM stack

## Issue 2: Lambda Runs But SNS Publish Fails

Symptoms:

- producer Lambda logs show AccessDenied
- response contains publish error
- no SQS messages

Likely causes:

- Lambda execution role missing `sns:Publish`
- wrong topic ARN environment variable
- topic deleted or wrong region

How to troubleshoot:

```bash
aws logs tail /aws/lambda/<producer-name> --since 15m
aws sns get-topic-attributes --topic-arn <topic-arn>
```

Fix:

- update function policy
- verify `ORDERS_TOPIC_ARN`
- redeploy stack

Interview line:

```text
Lambda identity is its execution role, not the IAM user who deployed it.
```

## Issue 3: SNS Publishes But SQS Does Not Receive

Symptoms:

- producer succeeds
- SNS has message ID
- SQS queue remains empty

Likely causes:

- missing SNS subscription
- subscription pending or deleted
- SQS queue policy does not allow SNS to send
- filter policy excludes the message
- message attributes missing

How to troubleshoot:

```bash
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names Policy
```

For filter policies, check:

```text
SNS filter reads MessageAttributes, not message body
```

Fix:

- create subscription
- add queue policy allowing `sns.amazonaws.com`
- include required message attributes
- adjust filter policy

## Issue 4: SQS Has Messages But Worker Lambda Does Not Process

Symptoms:

- queue depth increases
- worker Lambda has no invocation logs

Likely causes:

- event source mapping disabled
- Lambda missing SQS poll permissions
- wrong queue ARN in event source
- reserved concurrency set to zero

How to troubleshoot:

```bash
aws lambda list-event-source-mappings --function-name <worker-name>
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

Fix:

- enable event source mapping
- attach `SQSPollerPolicy`
- fix queue ARN
- check Lambda concurrency settings

## Issue 5: Worker Fails And Messages Keep Retrying

Symptoms:

- repeated Lambda errors
- same message appears again
- `ApproximateReceiveCount` increases

Likely causes:

- bad message format
- validation failure
- downstream API/database unavailable
- code bug
- timeout too low

How to troubleshoot:

```bash
aws logs tail /aws/lambda/<worker-name> --since 30m
```

Inspect the SQS record:

```text
record["body"]
attributes.ApproximateReceiveCount
messageAttributes
```

Fix:

- validate input defensively
- send poison messages to DLQ
- increase timeout only if work is legitimately slow
- fix downstream dependency
- add idempotency before retrying side effects

Interview line:

```text
Retries are useful only when the failure is temporary. Bad data should go to DLQ after bounded retries.
```

## Issue 6: DLQ Has Messages But No Email

Symptoms:

- DLQ visible messages > 0
- alarm email not received

Likely causes:

- SNS email subscription pending
- alarm already entered ALARM before subscription confirmation
- alarm action missing
- email in spam/promotions
- CloudWatch metric delay

How to troubleshoot:

```bash
aws cloudwatch describe-alarms --alarm-names <alarm-name>
aws sns list-subscriptions-by-topic --topic-arn <notification-topic-arn>
aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names ApproximateNumberOfMessages
```

Direct SNS test:

```bash
aws sns publish \
  --topic-arn <notification-topic-arn> \
  --subject "SNS test" \
  --message "Testing email delivery"
```

Fix:

- confirm SNS subscription
- reset alarm by clearing DLQ and waiting for OK
- retrigger failure
- verify `AlarmActions`

Important concept:

```text
CloudWatch alarm actions fire on state transitions, such as OK -> ALARM.
```

If the subscription is confirmed after the alarm is already in ALARM, the old notification will not be replayed.

## Issue 7: Queue Backlog Grows

Symptoms:

- `ApproximateNumberOfMessagesVisible` keeps increasing
- processing is delayed
- users see stale results

Likely causes:

- producer sends faster than consumer processes
- Lambda concurrency too low
- downstream bottleneck
- worker timeout/errors

How to troubleshoot:

```text
Check SQS visible messages
Check Lambda concurrent executions
Check Lambda duration and errors
Check downstream dependency latency
```

Fix options:

- increase Lambda reserved concurrency
- increase SQS batch size
- optimize worker code
- scale downstream systems
- add backpressure or rate limits

Interview line:

```text
SQS absorbs spikes, but it does not make downstream capacity infinite.
```

## Issue 8: Duplicate Processing

Symptoms:

- same order processed twice
- duplicate emails/payments/records

Why it happens:

SQS standard queues are at-least-once delivery.

Fix:

- design idempotent consumers
- store processed IDs in DynamoDB
- make side effects conditional
- use FIFO queue only when ordering/deduplication requirements justify it

Sample pattern:

```text
receive message
  -> conditionally insert orderId into DynamoDB
  -> if insert succeeds, process
  -> if insert fails, skip duplicate
```

## Issue 9: IAM AccessDenied

Symptoms:

- GitHub Actions fails at deploy
- Lambda logs show AccessDenied
- SAM fails to create or update resources

How to troubleshoot:

```text
Who is calling?
What action?
On what resource?
What policy should allow it?
Is there an explicit deny?
```

Common identities:

- GitHub Actions role
- Lambda execution role
- local IAM user/profile

Fix:

- update correct role policy
- do not confuse deploy role with runtime role
- use least privilege after the lab works

Interview line:

```text
There are two permission planes: deployment permissions and runtime permissions.
```

## Issue 10: GitHub Actions OIDC Fails

Symptoms:

- `Could not assume role with OIDC`
- `Not authorized to perform sts:AssumeRoleWithWebIdentity`

Likely causes:

- missing `id-token: write`
- wrong repo owner/name in trust policy
- branch mismatch
- wrong OIDC provider audience
- role ARN typo

Checklist:

```text
Workflow has id-token: write
Trust policy has aud = sts.amazonaws.com
Trust policy has sub = repo:<owner>/<repo>:ref:refs/heads/main
Workflow runs on main
role-to-assume ARN is correct
```

Fix:

- update trust policy
- push workflow to main
- retry manually

## Issue 11: CloudFormation Stack Stuck Or Rollback

Symptoms:

- deploy fails
- stack in `ROLLBACK_COMPLETE`
- resources partially created

How to troubleshoot:

```bash
aws cloudformation describe-stack-events --stack-name <stack-name>
```

Look for the first failed resource, not the last log line.

Common causes:

- resource name already exists
- IAM permission missing
- invalid property
- subscription confirmation waiting is not usually a stack blocker for email SNS

Fix:

- adjust names
- fix IAM
- delete failed stack if needed
- redeploy

## Production Readiness Checklist

Before calling this production-grade, add:

- least-privilege IAM
- structured logs with correlation IDs
- idempotency store
- alarms for Lambda errors and queue age
- DLQ replay process
- environment separation
- tests
- dashboards owned by the team
- runbooks for common incidents
- cost guardrails
- tagging strategy

## Strong Interview Summary

In production, I would troubleshoot this system by following the event path from producer logs to SNS delivery, SQS queue depth, Lambda event source mapping, worker logs, DLQ metrics, and CloudWatch alarm state. I would design consumers to be idempotent, use DLQs for poison messages, monitor queue age and Lambda errors, and use OIDC for CI/CD authentication instead of static cloud credentials.
