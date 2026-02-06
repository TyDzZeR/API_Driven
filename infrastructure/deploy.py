import boto3
import os
import time
import zipfile

# Configuration
# Endpoint pour communiquer avec LocalStack DEPUIS le conteneur (localhost)
LOCALSTACK_ENDPOINT = 'http://localhost:4566' 
# URL externe pour l'affichage final (fournie par l'utilisateur ou env var)
EXTERNAL_URL_BASE = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')

# Nettoyage de l'URL externe (retirer le slash final s'il existe)
if EXTERNAL_URL_BASE.endswith('/'):
    EXTERNAL_URL_BASE = EXTERNAL_URL_BASE[:-1]

def create_zip():
    print("Creation de l'archive lambda...")
    with zipfile.ZipFile('function.zip', 'w') as z:
        z.write('infrastructure/lambda_function.py', 'lambda_function.py')

def main():
    ec2 = boto3.client('ec2', endpoint_url=LOCALSTACK_ENDPOINT, region_name='us-east-1')
    lam = boto3.client('lambda', endpoint_url=LOCALSTACK_ENDPOINT, region_name='us-east-1')
    apigateway = boto3.client('apigateway', endpoint_url=LOCALSTACK_ENDPOINT, region_name='us-east-1')

    # 1. Lancer une instance EC2
    print("Lancement de l'instance EC2...")
    run_instances = ec2.run_instances(
        ImageId='ami-ff065c7e', # AMI factice pour LocalStack
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro'
    )
    instance_id = run_instances['Instances'][0]['InstanceId']
    print(f"Instance EC2 creee: {instance_id}")

    # 2. Deployer la Lambda
    create_zip()
    
    # Check if exists and delete if so (idempotency simple)
    try:
        lam.delete_function(FunctionName='ControlEC2')
    except:
        pass

    with open('function.zip', 'rb') as f:
        zipped_code = f.read()

    print("Creation de la fonction Lambda...")
    lambda_response = lam.create_function(
        FunctionName='ControlEC2',
        Runtime='python3.9',
        Role='arn:aws:iam::000000000000:role/lambda-role',
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zipped_code},
        Timeout=30
    )
    lambda_arn = lambda_response['FunctionArn']

    # Grant permission to API Gateway
    try:
        lam.add_permission(
            FunctionName='ControlEC2',
            StatementId='apigateway-test-2',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com'
        )
    except:
        pass

    # 3. Configurer API Gateway
    print("Configuration API Gateway...")
    apis = apigateway.get_rest_apis()
    api_id = None
    for api in apis.get('items', []):
        if api['name'] == 'EC2ControlAPI':
            api_id = api['id']
            # Delete existing to start fresh
            apigateway.delete_rest_api(restApiId=api_id)
            api_id = None
            break
    
    api = apigateway.create_rest_api(name='EC2ControlAPI')
    api_id = api['id']
    
    root_id = apigateway.get_resources(restApiId=api_id)['items'][0]['id']

    # Pour chaque endpoint
    for path_part in ['start', 'stop', 'status']:
        resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart=path_part
        )
        resource_id = resource['id']
        
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='GET',
            authorizationType='NONE'
        )
        
        # Integration avec Lambda
        # Note: L'URI d'invocation pour LocalStack est specifique
        # arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{LambdaArn}/invocations
        uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri
        )


    # Deploiement
    apigateway.create_deployment(
        restApiId=api_id,
        stageName='prod'
    )

    print("\n--- URLs de pilotage ---")
    # Construction des URLs avec l'URL externe fournie
    # Format LocalStack via external host: https://<external_host>/restapis/<api_id>/<stage>/_user_request_/<path>
    # Note: Dans Codespaces, le port forward se fait souvent sur le port 4566.
    # Si on utilise l'URL codespace directe port 4566, LocalStack route souvent via /restapis/...
    
    base_url = f"{EXTERNAL_URL_BASE}/restapis/{api_id}/prod/_user_request_"
    
    print(f"{base_url}/start")
    print(f"{base_url}/stop")
    print(f"{base_url}/status")

    # Clean up zip
    os.remove('function.zip')

if __name__ == '__main__':
    main()
