import json
import os
import time
import email_ses
import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from boto3.dynamodb.conditions import Key

from shared import get_cart_id, get_headers, handle_decimal_type

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource("dynamodb")

logger.debug("Initializing DDB Table %s", os.environ["TABLE_NAME"])
table = dynamodb.Table(os.environ["TABLE_NAME"])
logger.debug("Initializing DDB Table %s", os.environ["TABLE_NAME_ORDERS"])
table_order = dynamodb.Table(os.environ["TABLE_NAME_ORDERS"])


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    """
    Update cart table to use user identifier instead of anonymous cookie value as a key. This will be called when a user
    is logged in.
    """
    cart_id, _ = get_cart_id(event["headers"])

    try:
        # Because this method is authorized at API gateway layer, we don't need to validate the JWT claims here
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    except KeyError:

        return {
            "statusCode": 400,
            "headers": get_headers(cart_id),
            "body": json.dumps({"message": "Invalid user"}),
        }

    # Get all cart items belonging to the user's identity
    response = table.query(
        KeyConditionExpression=Key("pk").eq(f"user#{user_id}")
        & Key("sk").begins_with("product#"),
        # Perform a strongly consistent read here to ensure we get correct and up to date cart
        ConsistentRead=True,
    )

    epoch = time.time()
    cart_items = response.get("Items")
    email_ses.send_email(event["requestContext"]["authorizer"]["claims"]["cognito:username"],
                         event["requestContext"]["authorizer"]["claims"]["email"], cart_items)

    # batch_writer will be used to update status for cart entries belonging to the user
    with table.batch_writer() as batch:
        print(cart_items)
        for item in cart_items:

            # Add items to orders table
            orders_pk = f"order#{user_id}#{epoch}"
            product_sk = item["sk"]
            orders_sk = product_sk
            # product_id = item["product_id"]
            # quantity = item["quantity"]
            table_order.put_item(
                Item={
                    "pk": orders_pk,
                    "sk": orders_sk,
                    "quantity": item["quantity"],
                    "productDetail": item["productDetail"],
                }
            )

            # Delete ordered items
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    metrics.add_metric(name="CartCheckedOut", unit="Count", value=1)
    logger.info({"action": "CartCheckedOut", "cartItems": cart_items})

    return {
        "statusCode": 200,
        "headers": get_headers(cart_id),
        "body": json.dumps(
            {"products": response.get("Items")}, default=handle_decimal_type
        ),
    }
