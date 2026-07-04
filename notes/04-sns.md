# SNS

## What SNS Is

Amazon SNS is a publish-subscribe service.

One producer publishes a message to a topic, and SNS delivers that message to all matching subscribers.

```text
Publisher -> SNS topic -> Subscriber A
                       -> Subscriber B
                       -> Subscriber C
```

## Why SNS Exists

SNS is useful when one event should notify multiple systems.

Without SNS, the producer must know every consumer:

```text
Producer -> Queue A
Producer -> Queue B
Producer -> Queue C
```

With SNS:

```text
Producer -> SNS topic
SNS topic -> Queue A
SNS topic -> Queue B
SNS topic -> Queue C
```

This makes the producer simpler and downstream systems easier to add later.

## Our Topic

In `template.yaml`:

```yaml
OrdersTopic:
  Type: AWS::SNS::Topic
```

The ingest Lambda publishes order events to this topic.

## Subscriptions

The main queue subscription:

```yaml
OrdersQueueSubscription:
  Type: AWS::SNS::Subscription
  Properties:
    TopicArn: !Ref OrdersTopic
    Protocol: sqs
    Endpoint: !GetAtt OrdersQueue.Arn
    RawMessageDelivery: true
```

This means every SNS message goes into `OrdersQueue`.

The high-priority subscription:

```yaml
HighPrioritySubscription:
  Type: AWS::SNS::Subscription
  Properties:
    FilterPolicy:
      priority:
        - HIGH
```

This means only messages with message attribute `priority = HIGH` go to `HighPriorityAuditQueue`.

## Message Attributes

In `src/order_ingest/app.py`:

```python
MessageAttributes={
    "priority": {
        "DataType": "String",
        "StringValue": order["priority"],
    }
}
```

SNS filter policies inspect message attributes, not the message body.

That is why the code publishes `priority` as a message attribute.

## SNS vs SQS

SNS pushes messages to subscribers.

SQS stores messages until consumers pull or Lambda polls them.

They are often used together:

```text
SNS for fanout
SQS for durable buffering
```

## Interview Answer

SNS is used for pub/sub fanout. It lets a producer publish an event once and deliver it to multiple subscribers. With filter policies, subscribers can receive only the events they care about. SNS plus SQS is common because SNS fans out and SQS provides durable buffering and retries.
