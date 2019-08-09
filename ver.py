import boto3
client = boto3.client('ses',region_name = 'us-east-1')
response = client.verify_email_identity(
    EmailAddress='ketav.bhatt@quantiphi.com'
)
print(response)
