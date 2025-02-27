#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import skip
from servicecatalog_factory.workflow import tasks_unit_tests_helper


class CreatePortfolioAssociationTaskTest(tasks_unit_tests_helper.FactoryTaskUnitTest):
    region = "region"
    portfolio_group_name = "portfolio_group_name"
    display_name = "display_name"
    portfolio_name = "portfolio_name"
    description = "description"
    provider_name = "provider_name"
    tags = []
    associations = []
    factory_version = "factory_version"

    def setUp(self) -> None:
        from servicecatalog_factory.workflow.portfolios import (
            create_portfolio_association_task,
        )

        self.module = create_portfolio_association_task

        self.sut = self.module.CreatePortfolioAssociationTask(
            region=self.region,
            portfolio_group_name=self.portfolio_group_name,
            portfolio_name=self.portfolio_name,
            display_name=self.display_name,
            description=self.description,
            provider_name=self.provider_name,
            tags=self.tags,
            associations=self.associations,
            factory_version=self.factory_version,
        )

        self.wire_up_mocks()

    @skip
    def test_requires(self):
        # setup
        # exercise
        actual_result = self.sut.requires()

        # verify
        raise NotImplementedError()

    def test_params_for_results_display(self):
        # setup
        expected_result = {
            "region": self.region,
            "portfolio_group_name": self.portfolio_group_name,
            "display_name": self.display_name,
            "portfolio_name": self.portfolio_name,
        }

        # exercise
        actual_result = self.sut.params_for_results_display()

        # verify
        self.assertEqual(expected_result, actual_result)

    @skip
    def test_run(self):
        # setup
        # exercise
        actual_result = self.sut.run()

        # verify
        raise NotImplementedError()
