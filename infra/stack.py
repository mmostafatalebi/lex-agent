"""LexAgent deployment stack.

Design choices worth stating plainly:

- Aurora Serverless v2 PostgreSQL 16, min 0 / max 1 ACU: scales to zero when idle
  and supports the pgvector extension the taxonomy needs.
- Lambda runs in the same VPC as the database for a proper network boundary; the
  tradeoff is a longer cold start. Bedrock, Secrets Manager, and S3 are reached
  over VPC endpoints, so no NAT gateway is required.
- API Gateway HTTP API (not REST): cheaper and enough for this surface.
- Container image code, not a zip, to carry the Python dependency footprint.
- Bedrock access is scoped to the specific model ARNs, never ``bedrock:*``.
"""

from typing import Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secrets
from aws_cdk.aws_apigatewayv2 import HttpApi
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct

from infra.migrations_resource import MigrationsResource
from infra.seed_resource import SeedResource

_DATABASE_NAME = "lexagent"
_DATABASE_USER = "lexagent"
_API_HANDLER = "lexagent.api.handler.lambda_handler"


class LexAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_repo_name = self.node.try_get_context("image_repo") or "lexagent"
        image_tag = self.node.try_get_context("image_tag") or "latest"
        repository = ecr.Repository.from_repository_name(self, "ImageRepo", image_repo_name)

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                )
            ],
        )
        vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)
        vpc.add_interface_endpoint(
            "SecretsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
        )
        vpc.add_interface_endpoint(
            "BedrockEndpoint", service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME
        )

        lambda_sg = ec2.SecurityGroup(self, "LambdaSg", vpc=vpc, allow_all_outbound=True)
        db_sg = ec2.SecurityGroup(self, "DbSg", vpc=vpc, allow_all_outbound=True)
        db_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(5432), "Lambda to Postgres")

        cluster = rds.DatabaseCluster(
            self,
            "Db",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_6
            ),
            serverless_v2_min_capacity=0,
            serverless_v2_max_capacity=1,
            writer=rds.ClusterInstance.serverless_v2("Writer"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_sg],
            credentials=rds.Credentials.from_generated_secret(_DATABASE_USER),
            default_database_name=_DATABASE_NAME,
            removal_policy=RemovalPolicy.DESTROY,
        )
        assert cluster.secret is not None
        db_secret = cluster.secret

        bucket = s3.Bucket(
            self,
            "Contracts",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(prefix="contracts/", expiration=Duration.days(30))
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        api_key_secret = secrets.Secret(
            self,
            "ApiKey",
            generate_secret_string=secrets.SecretStringGenerator(
                exclude_punctuation=True, password_length=40
            ),
        )

        password = db_secret.secret_value_from_json("password").unsafe_unwrap()
        database_url = (
            f"postgresql://{_DATABASE_USER}:{password}"
            f"@{cluster.cluster_endpoint.hostname}:5432/{_DATABASE_NAME}"
        )
        environment = {
            "S3_BUCKET": bucket.bucket_name,
            "CHECKPOINT_BACKEND": "postgres",
            "DATABASE_URL": database_url,
            "REQUIRE_API_KEY": "true",
            "LEXAGENT_API_KEY": api_key_secret.secret_value.unsafe_unwrap(),
        }

        api_fn = lambda_.DockerImageFunction(
            self,
            "ApiFn",
            code=lambda_.DockerImageCode.from_ecr(repository, tag_or_digest=image_tag),
            memory_size=1024,
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[lambda_sg],
            environment=environment,
        )
        _grant_bedrock(api_fn)
        bucket.grant_read_write(api_fn)
        db_secret.grant_read(api_fn)

        http_api = HttpApi(
            self,
            "HttpApi",
            default_integration=HttpLambdaIntegration("ApiIntegration", handler=api_fn),
        )

        migrations = MigrationsResource(
            self,
            "Migrations",
            repository=repository,
            image_tag=image_tag,
            vpc=vpc,
            security_group=lambda_sg,
            environment=environment,
            db_secret=db_secret,
        )
        seed = SeedResource(
            self,
            "Seed",
            repository=repository,
            image_tag=image_tag,
            vpc=vpc,
            security_group=lambda_sg,
            environment=environment,
            db_secret=db_secret,
        )
        seed.node.add_dependency(migrations)

        CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "DbSecretArn", value=db_secret.secret_arn)
        CfnOutput(self, "ApiKeySecretArn", value=api_key_secret.secret_arn)


def _grant_bedrock(fn: lambda_.IFunction) -> None:
    fn.add_to_role_policy(
        iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-3-5-sonnet-*",
                "arn:aws:bedrock:*:*:foundation-model/amazon.titan-embed-text-v2:0",
            ],
        )
    )
