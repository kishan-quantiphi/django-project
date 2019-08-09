import boto3
client = boto3.client('ses',region_name='us-east-1')
response = client.get_identity_verification_attributes(
    Identities=[
        'kishan.rathore@quantiphi.com',
    ],
)

print(response)
print('-----------------------------------------------------------')
response = client.get_identity_verification_attributes(
    Identities=[
        'ketav.bhatt@quantiphi.com',
    ],
)

print(response)

