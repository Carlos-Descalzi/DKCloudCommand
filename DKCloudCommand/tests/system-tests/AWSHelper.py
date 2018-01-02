import boto3
import time


class AWSHelper:

    CODE_STOPPED = 80
    CODE_RUNNING = 16
    WAIT_TIME = 20
    CHECK_QTY = 3

    def __init__(self, region, aws_access_key_id, aws_secret_access_key):
        self.region = region
        self. aws_access_key_id =  aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.ec2 = None

    def _get_ec2(self):
        if not self.ec2:
            self.ec2 = boto3.client('ec2',
                                    region_name=self.region,
                                    aws_access_key_id=self.aws_access_key_id,
                                    aws_secret_access_key=self.aws_secret_access_key)
        return self.ec2

    def do(self, command, instances):
        ec2 = self._get_ec2()

        wait_list = {}
        for instance in instances:
            wait_list[instance] = False

        if command == 'start':
            ec2.start_instances(InstanceIds=instances)
        elif command == 'stop':
            ec2.stop_instances(InstanceIds=instances)
        else:
            return None

        checks = AWSHelper.CHECK_QTY
        while checks:
            time.sleep(AWSHelper.WAIT_TIME)
            checks -= 1
            current_instances = ec2.describe_instances(InstanceIds=instances)
            for this_reservation in current_instances['Reservations']:
                for this_instance in this_reservation['Instances']:
                    code = this_instance['State']['Code']
                    if command == 'start' and code == AWSHelper.CODE_RUNNING:
                        wait_list[this_instance['InstanceId']] = True
                    if command == 'stop' and code == AWSHelper.CODE_STOPPED:
                        wait_list[this_instance['InstanceId']] = True

            if all(wait_list.values()):
                return True
        return False
