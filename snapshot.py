import boto3
import os
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    # Initialize the Boto3 client for EC2
    ec2_client = boto3.client('ec2')

    # Get the environment variable for snapshot deletion
    snapshotdelete = os.getenv('snapshotdelete', 'false').lower() == 'true'
    
    # Calculate the time threshold for one year ago
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    
    # Get the snapshots
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    
    # Get AMIs owned by the account
    amis = ec2_client.describe_images(Owners=['self'])['Images']
    
    # Collect snapshot IDs used by AMIs
    snapshots_in_use = set()
    for ami in amis:
        for mapping in ami['BlockDeviceMappings']:
            if 'Ebs' in mapping and 'SnapshotId' in mapping['Ebs']:
                snapshots_in_use.add(mapping['Ebs']['SnapshotId'])
    
    old_snapshots = []

    # Loop through snapshots and find those older than one year, excluding those in use and locked
    for snapshot in snapshots:
        # Get the snapshot's creation date
        creation_date = snapshot['StartTime']
        
        # Check for the 'lock-state' tag
        lock_state_tag = next((tag['Value'] for tag in snapshot.get('Tags', []) if tag['Key'] == 'lock-state'), 'false')
        
        # Check if the snapshot is older than one year, not in use, and not locked
        if creation_date < one_year_ago and snapshot['SnapshotId'] not in snapshots_in_use and lock_state_tag != 'true':
            old_snapshots.append({
                'SnapshotId': snapshot['SnapshotId'],
                'Name': 'Unnamed',  # Name is not available, so default to 'Unnamed'
                'Size': snapshot['VolumeSize']
            })

    count_of_old_snapshots = len(old_snapshots)
    
    if snapshotdelete:
        # Print the details of old snapshots
        if count_of_old_snapshots > 0:
            for snap in old_snapshots:
                print(f"SnapshotId: {snap['SnapshotId']}, Name: {snap['Name']}, Size: {snap['Size']} GiB")
            print(f"Total snapshots deleted: {count_of_old_snapshots}")

        # Delete snapshots
        deleted_snapshots = []
        for snapshot in old_snapshots:
            ec2_client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
            deleted_snapshots.append(snapshot['SnapshotId'])

        result = {
            'count_of_deleted_snapshots': len(deleted_snapshots),
            'deleted_snapshots': deleted_snapshots
        }
    
    else:
        # Print the details of old snapshots ready to delete
        if count_of_old_snapshots > 0:
            for snap in old_snapshots:
                print(f"SnapshotId: {snap['SnapshotId']}, Name: {snap['Name']}, Size: {snap['Size']} GiB")
            print(f"Total snapshots ready to delete: {count_of_old_snapshots}")
        else:
            print("No snapshots older than one year found.")
        
        result = {
            'count_of_old_snapshots': count_of_old_snapshots,
            'old_snapshots': old_snapshots
        }

    # Return results
    return {
        'statusCode': 200,
        'body': result  # Directly returning the result dictionary
    }
