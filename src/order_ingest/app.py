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
