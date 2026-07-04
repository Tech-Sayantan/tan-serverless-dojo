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
