import boto3
import time

def create_stack(stack_name, template_file, parameters):
    cloudformation = boto3.client('cloudformation')

    # Check if the stack already exists
    if stack_exists(stack_name):
        print(f"Stack {stack_name} already exists. Skipping creation.")
        return False

    try:
        response = cloudformation.create_stack(
            StackName=stack_name,
            TemplateBody=open(template_file).read(),
            Parameters=parameters,
            Capabilities=['CAPABILITY_IAM']
        )
        print(f"Creating stack {stack_name}...")

        # Wait for stack creation to complete, log events meanwhile
        waiter = cloudformation.get_waiter('stack_create_complete')
        log_stack_events(stack_name)

        waiter.wait(StackName=stack_name)
        print(f"Stack {stack_name} created successfully.")

        # Detect any rollback after creation
        detect_rollback(stack_name)

        return True
    except Exception as e:
        print(f"Error creating stack {stack_name}: {e}")
        return False


def delete_stack(stack_name):
    cloudformation = boto3.client('cloudformation')

    try:
        response = cloudformation.delete_stack(StackName=stack_name)
        print(f"Deleting stack {stack_name}...")

        # Wait for stack deletion to complete, log events meanwhile
        waiter = cloudformation.get_waiter('stack_delete_complete')
        log_stack_events(stack_name)

        waiter.wait(StackName=stack_name)
        print(f"Stack {stack_name} deleted successfully.")

        return True
    except Exception as e:
        print(f"Error deleting stack {stack_name}: {e}")
        return False


def stack_exists(stack_name):
    """Check if the stack already exists."""
    cloudformation = boto3.client('cloudformation')
    try:
        cloudformation.describe_stacks(StackName=stack_name)
        return True
    except cloudformation.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            return False
        else:
            raise e


def log_stack_events(stack_name):
    """Logs the stack events while the stack is being created or deleted."""
    cloudformation = boto3.client('cloudformation')
    try:
        while True:
            events = cloudformation.describe_stack_events(StackName=stack_name)['StackEvents']
            for event in events:
                print(f"{event['Timestamp']} - {event['ResourceStatus']}: {event['ResourceType']} - {event['LogicalResourceId']}")
            time.sleep(10)  # Sleep for 10 seconds before fetching the next batch of events
    except Exception as e:
        print(f"Error logging events for stack {stack_name}: {e}")


def detect_rollback(stack_name):
    """Detect if a rollback happened after stack creation failed."""
    cloudformation = boto3.client('cloudformation')
    try:
        stack_info = cloudformation.describe_stacks(StackName=stack_name)['Stacks'][0]
        if stack_info['StackStatus'].endswith('_ROLLBACK_COMPLETE'):
            print(f"Stack {stack_name} failed and rolled back. Checking reason for rollback...")

            # Get events related to the rollback
            events = cloudformation.describe_stack_events(StackName=stack_name)['StackEvents']
            for event in events:
                if 'ROLLBACK' in event['ResourceStatus']:
                    print(f"Rollback event: {event['Timestamp']} - {event['ResourceStatus']}: {event['ResourceType']} - {event['ResourceStatusReason']}")
        else:
            print(f"Stack {stack_name} created successfully without rollback.")
    except Exception as e:
        print(f"Error detecting rollback for stack {stack_name}: {e}")


# Test scenario
def test_scenario():
    stack_name = "MyTestStack"
    
    # Dynamically pass template paths and parameters for testing
    vpc_template = "vpc.yml"
    rds_template = "rds.yml"
    asg_template = "asg.yml"
    route53_template = "route53.yml"

    # Define parameters as needed for each stack
    vpc_parameters = [
        {'ParameterKey': 'VpcCIDR', 'ParameterValue': '10.0.0.0/16'},
        {'ParameterKey': 'PublicSubnetCIDR', 'ParameterValue': '10.0.1.0/24'},
        {'ParameterKey': 'PrivateSubnet1CIDR', 'ParameterValue': '10.0.2.0/24'}
    ]

    rds_parameters = [
        {'ParameterKey': 'DBUsername', 'ParameterValue': 'admin'},
        {'ParameterKey': 'DBPassword', 'ParameterValue': 'admin123'},
    ]

    asg_parameters = [
        {'ParameterKey': 'VpcId', 'ParameterValue': 'your_vpc_id'},
        {'ParameterKey': 'PrivateSubnet1Id', 'ParameterValue': 'your_private_subnet_id'},
        {'ParameterKey': 'KeyName', 'ParameterValue': 'YourKeyPair'}
    ]

    route53_parameters = [
        {'ParameterKey': 'DomainName', 'ParameterValue': 'example.com'}
    ]

    try:
        # Create VPC Stack
        create_stack(stack_name + "-VPC", vpc_template, vpc_parameters)

        # Create RDS Stack
        create_stack(stack_name + "-RDS", rds_template, rds_parameters)

        # Create ASG Stack
        create_stack(stack_name + "-ASG", asg_template, asg_parameters)

        # Create Route53 Stack
        create_stack(stack_name + "-Route53", route53_template, route53_parameters)

    finally:
        # Clean up: Delete stacks after testing
        delete_stack(stack_name + "-VPC")
        delete_stack(stack_name + "-RDS")
        delete_stack(stack_name + "-ASG")
        delete_stack(stack_name + "-Route53")


# Run the test scenario
test_scenario()
