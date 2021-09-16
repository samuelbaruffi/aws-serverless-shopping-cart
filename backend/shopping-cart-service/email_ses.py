import boto3
from botocore.exceptions import ClientError
from datetime import datetime


def send_email(user, email, items):
    SENDER = f'Oktank Order Confirmation <{email}>'
    RECIPIENT = email
    AWS_REGION = 'us-east-1'

    print('Sending from:   ' + SENDER)
    print('Sending to:     ' + RECIPIENT)
    print('Sending region: ' + AWS_REGION)

    SUBJECT = 'Thank you for your order!'

    BODY_TEXT = ("Hi " + user + ",\r\n"
                 "Thank you for your order on " +
                 datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "!\r\n"
                 "This is a summary of your order:\r\n\r\n"
                 ""
                 )

    total_price = 0
    total_items = 0
    for i in items:
        BODY_TEXT += 'Quantity: ' + str(i["quantity"]) + '\r\n'
        BODY_TEXT += 'Name:     ' + str(i["productDetail"]["name"]) + '\r\n'
        BODY_TEXT += 'Price:    ' + \
            str(round(i["productDetail"]["price"]/100, 2)) + '\r\n'
        total_price += (i["productDetail"]["price"] * i["quantity"])
        total_items += i["quantity"]

    total_price_dollar = str(round(total_price/100, 2))

    BODY_TEXT += '\r\n\r\n Total items: ' + str(total_items)
    BODY_TEXT += '\r\n Total price: ' + str(total_price_dollar)

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    <head></head>
    <p style="text-align: right;">Order Confirmation</p>
    <hr />
    <h1 style="color: #5e9ca0;"><span style="color: #0421f9;">Hello {user},</span></h1>
    <p>Thank you for shopping with us. Here is a summary of your order.</p>
    <table>
    <thead>
    <tr>
    <td><strong>Quantity</strong></td>
    <td><strong>Item</strong></td>
    <td><strong>Price</strong></td>
    </tr>
    </thead>
    <tbody>
    <tr>
                """
    for i in items:
        BODY_HTML += "\n\r<tr>"
        BODY_HTML += "\n\r<td>" + str(i["quantity"]) + "</td>"
        BODY_HTML += "\n\r<td>" + str(i["productDetail"]["name"]) + "</td>"
        BODY_HTML += "\n\r<td> $" + \
            str(round(i["productDetail"]["price"]/100, 2)) + "</td>"
        BODY_HTML += "\n\r</tr>"

    BODY_HTML += "</tbody>"
    BODY_HTML += "</table>"
    BODY_HTML += "<p>Order total: $" + str(total_price_dollar) + "</p>"
    BODY_HTML += "</html>"

    print("HTML BODY:")
    print(BODY_HTML)

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=AWS_REGION)

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print("Email error!")
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
