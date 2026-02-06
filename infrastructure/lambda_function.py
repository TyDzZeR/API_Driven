import boto3
import json
import os

def lambda_handler(event, context):
    print("Lambda started")
    endpoint_url = "unknown"
    try:
        # Determine endpoint
        # Default to 'localstack' or IP of bridge usually 172.17.0.1
        hostname = os.environ.get('LOCALSTACK_HOSTNAME', '172.17.0.1')
        endpoint_url = f"http://{hostname}:4566"
        print(f"Connecting to EC2 at {endpoint_url}...")
        
        ec2 = boto3.client('ec2', endpoint_url=endpoint_url, region_name='us-east-1')
        
        # Récupérer l'instance ID
        print("Describing instances...")
        instances = ec2.describe_instances()
        print("Instances described")
        
        instance_id = None
        if instances['Reservations']:
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'terminated':
                        instance_id = instance['InstanceId']
                        break
                if instance_id:
                    break
        
        if not instance_id:
            return {
                'statusCode': 404,
                'body': json.dumps('No active instance found')
            }

        path = event.get('path', '')
        action = path.split('/')[-1]  # start, stop, or status
        
        response_body = {}
        
        if action == 'start':
            ec2.start_instances(InstanceIds=[instance_id])
            response_body = f"Instance {instance_id} starting..."
        elif action == 'stop':
            ec2.stop_instances(InstanceIds=[instance_id])
            response_body = f"Instance {instance_id} stopping..."
        elif action == 'status':
            status_resp = ec2.describe_instances(InstanceIds=[instance_id])
            status = status_resp['Reservations'][0]['Instances'][0]['State']['Name']
            response_body = f"Instance {instance_id} is {status}"
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid action. Use start, stop, or status.')
            }

        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'endpoint_used': endpoint_url})
        }
