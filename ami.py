import boto3
import os
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    # Initialize the Boto3 client for EC2
    ec2_client = boto3.client('ec2')

    # Get the environment variable for AMI deletion
    amidelete = os.getenv('amidelete', 'false').lower() == 'true'
    
    # Calculate the time threshold for one year ago
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    
    # Get AMIs owned by the account
    amis = ec2_client.describe_images(Owners=['self'])['Images']
    
    old_amis = []

    # Loop through AMIs and find those older than one year
    for ami in amis:
        # Get the AMI's creation date
        creation_date = ami['CreationDate']
        creation_date = datetime.strptime(creation_date, '%Y-%m-%dT%H:%M:%S.%fZ')

        # Check if the AMI is older than one year
        if creation_date < one_year_ago:
            old_amis.append({
                'ImageId': ami['ImageId'],
                'Name': ami['Name'],
                'CreationDate': creation_date
            })

    count_of_old_amis = len(old_amis)
    
    if amidelete:
        # Print the details of old AMIs
        if count_of_old_amis > 0:
            for ami in old_amis:
                print(f"ImageId: {ami['ImageId']}, Name: {ami['Name']}, CreationDate: {ami['CreationDate']}")
            print(f"Total AMIs to be deleted: {count_of_old_amis}")

        # Deregister old AMIs
        deregistered_amis = []
        for ami in old_amis:
            ec2_client.deregister_image(ImageId=ami['ImageId'])
            deregistered_amis.append(ami['ImageId'])

        result = {
            'count_of_deregistered_amis': len(deregistered_amis),
            'deregistered_amis': deregistered_amis
        }
    
    else:
        # Print the details of old AMIs ready for deletion
        if count_of_old_amis > 0:
            for ami in old_amis:
                print(f"ImageId: {ami['ImageId']}, Name: {ami['Name']}, CreationDate: {ami['CreationDate']}")
            print(f"Total AMIs ready to delete: {count_of_old_amis}")
        else:
            print("No AMIs older than one year found.")
        
        result = {
            'count_of_old_amis': count_of_old_amis,
            'old_amis': old_amis
        }

    # Return results
    return {
        'statusCode': 200,
        'body': result  # Directly returning the result dictionary
    }
