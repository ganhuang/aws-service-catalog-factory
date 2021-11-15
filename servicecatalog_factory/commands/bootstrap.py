#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from threading import Thread

import boto3
import click
from betterboto import client as betterboto_client
from jinja2 import Template

from servicecatalog_factory import constants
from servicecatalog_factory.commands.portfolios import get_regions
from servicecatalog_factory.template_builder import product_templates
from servicecatalog_factory.utilities.assets import (
    read_from_site_packages,
    resolve_from_site_packages,
)
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def bootstrap_branch(
    branch_to_bootstrap,
    source_provider,
    owner,
    repo,
    branch,
    poll_for_source_changes,
    webhook_secret,
    scm_connection_arn,
    scm_full_repository_id,
    scm_branch_name,
    scm_bucket_name,
    scm_object_key,
    create_repo,
    should_validate,
    custom_source_action_git_url,
    custom_source_action_git_web_hook_ip_address,
    custom_source_action_custom_action_type_version,
    custom_source_action_custom_action_type_provider,
):
    constants.VERSION = "https://github.com/awslabs/aws-service-catalog-factory/archive/{}.zip".format(
        branch_to_bootstrap
    )
    bootstrap(
        source_provider,
        owner,
        repo,
        branch,
        poll_for_source_changes,
        webhook_secret,
        scm_connection_arn,
        scm_full_repository_id,
        scm_branch_name,
        scm_bucket_name,
        scm_object_key,
        create_repo,
        should_validate,
        custom_source_action_git_url,
        custom_source_action_git_web_hook_ip_address,
        custom_source_action_custom_action_type_version,
        custom_source_action_custom_action_type_provider,
    )


def bootstrap(
    source_provider,
    owner,
    repo,
    branch,
    poll_for_source_changes,
    webhook_secret,
    scm_connection_arn,
    scm_full_repository_id,
    scm_branch_name,
    scm_bucket_name,
    scm_object_key,
    create_repo,
    should_validate,
    custom_source_action_git_url,
    custom_source_action_git_web_hook_ip_address,
    custom_source_action_custom_action_type_version,
    custom_source_action_custom_action_type_provider,
):
    click.echo("Starting bootstrap")
    click.echo("Starting regional deployments")
    all_regions = get_regions()
    with betterboto_client.MultiRegionClientContextManager(
        "cloudformation", all_regions
    ) as clients:
        logger.info("Creating {}-regional".format(constants.BOOTSTRAP_STACK_NAME))
        threads = []
        template = read_from_site_packages(
            "{}.template.yaml".format(
                "{}-regional".format(constants.BOOTSTRAP_STACK_NAME)
            )
        )
        template = Template(template).render(
            VERSION=constants.VERSION, ALL_REGIONS=all_regions
        )
        args = {
            "StackName": "{}-regional".format(constants.BOOTSTRAP_STACK_NAME),
            "TemplateBody": template,
            "Capabilities": ["CAPABILITY_IAM"],
            "Parameters": [
                {
                    "ParameterKey": "Version",
                    "ParameterValue": constants.VERSION,
                    "UsePreviousValue": False,
                },
            ],
        }
        for client_region, client in clients.items():
            process = Thread(
                name=client_region, target=client.create_or_update, kwargs=args
            )
            process.start()
            threads.append(process)
        for process in threads:
            process.join()
        logger.info(
            "Finished creating {}-regional".format(constants.BOOTSTRAP_STACK_NAME)
        )
    click.echo("Completed regional deployments")

    click.echo("Starting main deployment")
    s3_bucket_name = None
    logger.info("Creating {}".format(constants.BOOTSTRAP_STACK_NAME))
    template = read_from_site_packages(
        "{}.template.yaml".format(constants.BOOTSTRAP_STACK_NAME)
    )
    source_args = {"Provider": source_provider}
    if source_provider.lower() == "codestarsourceconnection":
        source_args.update(
            {
                "Configuration": {
                    "ConnectionArn": scm_connection_arn,
                    "FullRepositoryId": scm_full_repository_id,
                    "BranchName": scm_branch_name,
                    "OutputArtifactFormat": "CODE_ZIP",
                },
            }
        )

    elif source_provider == "S3":
        source_args.update(
            {
                "Configuration": {
                    "S3Bucket": scm_bucket_name,
                    "S3ObjectKey": scm_object_key,
                    "PollForSourceChanges": poll_for_source_changes,
                },
            }
        )

    elif source_provider == "CodeCommit":
        source_args.update(
            {
                "Configuration": {
                    "RepositoryName": repo,
                    "BranchName": branch,
                    "PollForSourceChanges": poll_for_source_changes,
                },
            }
        )
    elif source_provider == "GitHub":
        source_args.update(
            {
                "Configuration": {
                    "Owner": owner,
                    "Repo": repo,
                    "Branch": branch,
                    "PollForSourceChanges": poll_for_source_changes,
                    "SecretsManagerSecret": webhook_secret,
                },
            }
        )
    elif source_provider == "Custom":
        source_args.update(
            {
                "Configuration": {
                    "Owner": "Custom",
                    "GitUrl": custom_source_action_git_url,
                    "Branch": branch,
                    "GitWebHookIpAddress": custom_source_action_git_web_hook_ip_address,
                    "CustomActionTypeVersion": custom_source_action_custom_action_type_version,
                    "CustomActionTypeProvider": custom_source_action_custom_action_type_provider,
                },
            }
        )
    template = Template(template).render(
        VERSION=constants.VERSION,
        ALL_REGIONS=all_regions,
        Source=source_args,
        create_repo=create_repo,
        should_validate=should_validate,
    )
    template = Template(template).render(
        VERSION=constants.VERSION,
        ALL_REGIONS=all_regions,
        Source=source_args,
        create_repo=create_repo,
        should_validate=should_validate,
    )
    args = {
        "StackName": constants.BOOTSTRAP_STACK_NAME,
        "TemplateBody": template,
        "Capabilities": ["CAPABILITY_NAMED_IAM"],
        "Parameters": [
            {
                "ParameterKey": "Version",
                "ParameterValue": constants.VERSION,
                "UsePreviousValue": False,
            },
        ],
    }
    with betterboto_client.ClientContextManager("cloudformation") as cloudformation:
        cloudformation.create_or_update(**args)
        cloudformation.create_or_update(
            StackName=constants.BOOTSTRAP_TEMPLATES_STACK_NAME,
            TemplateBody=product_templates.get_template().to_yaml(clean_up=True),
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )
        response = cloudformation.describe_stacks(
            StackName=constants.BOOTSTRAP_STACK_NAME
        )
        assert len(response.get("Stacks")) == 1, "Error code 1"
        stack_outputs = response.get("Stacks")[0]["Outputs"]
        for stack_output in stack_outputs:
            if stack_output.get("OutputKey") == "CatalogBucketName":
                s3_bucket_name = stack_output.get("OutputValue")
                break
        logger.info(
            "Finished creating {}. CatalogBucketName is: {}".format(
                constants.BOOTSTRAP_STACK_NAME, s3_bucket_name
            )
        )

    logger.info("Adding empty product template to s3")
    template = open(resolve_from_site_packages("empty.template.yaml")).read()
    s3 = boto3.resource("s3")
    obj = s3.Object(s3_bucket_name, "empty.template.yaml")
    obj.put(Body=template)
    logger.info("Finished adding empty product template to s3")
    logger.info("Finished bootstrap")
