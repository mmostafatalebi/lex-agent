"""Custom resource that runs ``alembic upgrade head`` after the database is up.

A Lambda backed by the same container image (with the migrations handler as its
command) is invoked once by an ``AwsCustomResource`` on create and on update.
"""

from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_secretsmanager as secrets
from aws_cdk import custom_resources as cr
from constructs import Construct

_HANDLER = "lexagent.api.handler.migrations_handler"


class MigrationsResource(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        repository: ecr.IRepository,
        image_tag: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        environment: dict[str, str],
        db_secret: secrets.ISecret,
    ) -> None:
        super().__init__(scope, construct_id)

        function = lambda_.DockerImageFunction(
            self,
            "Fn",
            code=lambda_.DockerImageCode.from_ecr(
                repository, tag_or_digest=image_tag, cmd=[_HANDLER]
            ),
            memory_size=1024,
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            environment=environment,
        )
        db_secret.grant_read(function)

        cr.AwsCustomResource(
            self,
            "Run",
            on_create=self._invoke(function),
            on_update=self._invoke(function),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"], resources=[function.function_arn]
                    )
                ]
            ),
            install_latest_aws_sdk=False,
            timeout=Duration.minutes(10),
        )

    @staticmethod
    def _invoke(function: lambda_.IFunction) -> cr.AwsSdkCall:
        return cr.AwsSdkCall(
            service="Lambda",
            action="invoke",
            parameters={
                "FunctionName": function.function_name,
                "InvocationType": "RequestResponse",
            },
            physical_resource_id=cr.PhysicalResourceId.of("lexagent-migrations"),
        )
