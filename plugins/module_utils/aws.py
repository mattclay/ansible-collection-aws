from __future__ import annotations

import functools
import typing as t

if t.TYPE_CHECKING:
    import boto3 as t_boto3

    from types_boto3_apigateway import APIGatewayClient
    from types_boto3_ec2 import EC2Client
    from types_boto3_events import EventBridgeClient
    from types_boto3_lambda import LambdaClient
    from types_boto3_sqs.service_resource import SQSServiceResource
    from types_boto3_sts import STSClient


from ansible.module_utils.basic import AnsibleModule


class AwsModule(AnsibleModule):
    @functools.cached_property
    def client(self) -> AwsClient:
        return AwsClient(self)

    @functools.cached_property
    def resource(self) -> AwsResource:
        return AwsResource(self)

    @functools.cached_property
    def account_id(self) -> str:
        return self.client.sts.get_caller_identity()["Account"]

    @functools.cached_property
    def region(self) -> str:
        return self.session.region_name

    @functools.cached_property
    def session(self) -> t_boto3.Session:
        import boto3

        return boto3.Session()


class AwsClient:
    def __init__(self, module: AwsModule) -> None:
        self._module = module

    def _client(self, service_name: str) -> t.Any:
        return self._module.session.client(service_name)

    @functools.cached_property
    def apigateway(self) -> APIGatewayClient:
        return self._client('apigateway')

    @functools.cached_property
    def awslambda(self) -> LambdaClient:
        return self._client('lambda')

    @functools.cached_property
    def ec2(self) -> EC2Client:
        return self._client('ec2')

    @functools.cached_property
    def events(self) -> EventBridgeClient:
        return self._client('events')

    @functools.cached_property
    def sts(self) -> STSClient:
        return self._client('sts')


class AwsResource:
    def __init__(self, module: AwsModule) -> None:
        self._module = module

    def _resource(self, service_name: str) -> t.Any:
        return self._module.session.resource(service_name)

    @functools.cached_property
    def sqs(self) -> SQSServiceResource:
        return self._resource('sqs')
