#!/usr/bin/env python3
# thoth-adviser
# Copyright(C) 2020 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Test removing backport importlib-resources from dependencies."""

from typing import Optional

import pytest

from thoth.adviser.enums import DecisionType
from thoth.adviser.enums import RecommendationType
from thoth.adviser.boots import ImportlibResourcesBackportBoot
from thoth.adviser.context import Context
from thoth.adviser.pipeline_builder import PipelineBuilderContext
from ...base import AdviserTestCase

from thoth.python import PackageVersion
from thoth.python import Source


class TestImportlibResourcesBackportBoot(AdviserTestCase):
    """Test boot removing importlib-resources backport."""

    @pytest.mark.parametrize(
        "python_version,recommendation_type,decision_type,develop",
        [
            ("3.8", RecommendationType.LATEST, None, False),
            ("3.8", None, DecisionType.RANDOM, True),
            ("3.9", RecommendationType.STABLE, None, False),
            ("3.9", RecommendationType.TESTING, None, True),
        ],
    )
    def test_should_include(
        self,
        builder_context: PipelineBuilderContext,
        python_version: str,
        recommendation_type: RecommendationType,
        decision_type: DecisionType,
        develop: bool,
    ) -> None:
        """Test registering this unit."""
        builder_context.project.runtime_environment.python_version = python_version
        builder_context.recommendation_type = recommendation_type
        builder_context.decision_type = decision_type

        package_version = PackageVersion(
            name="importlib-resources", version="==3.0.0", develop=develop, index=Source("https://pypi.org/simple"),
        )

        builder_context.project.pipfile.add_package_version(package_version)

        assert builder_context.is_dependency_monkey_pipeline() or builder_context.is_adviser_pipeline()
        assert ImportlibResourcesBackportBoot.should_include(builder_context) == {}

    @pytest.mark.parametrize(
        "python_version,recommendation_type,decision_type,develop",
        [
            ("3.4", RecommendationType.LATEST, None, False),
            (None, RecommendationType.LATEST, None, False),
            ("3.5", None, DecisionType.RANDOM, True),
            ("3.3", RecommendationType.STABLE, None, False),
            ("3.6", RecommendationType.TESTING, None, True),
            ("3.7", None, DecisionType.ALL, False),
        ],
    )
    def test_no_include(
        self,
        builder_context: PipelineBuilderContext,
        python_version: Optional[str],
        recommendation_type: RecommendationType,
        decision_type: DecisionType,
        develop: bool,
    ) -> None:
        """Test not including this unit."""
        builder_context.project.runtime_environment.python_version = python_version
        builder_context.recommendation_type = recommendation_type
        builder_context.decision_type = decision_type

        package_version = PackageVersion(
            name="importlib-resources", version="==3.0.0", develop=develop, index=Source("https://pypi.org/simple"),
        )

        builder_context.project.pipfile.add_package_version(package_version)

        assert builder_context.is_dependency_monkey_pipeline() or builder_context.is_adviser_pipeline()
        assert ImportlibResourcesBackportBoot.should_include(builder_context) is None

    def test_remove(self, context: Context) -> None:
        """Test removing importlib-resources dependency."""
        package_version = PackageVersion(
            name="importlib-resources", version="==3.0.0", develop=False, index=Source("https://pypi.org/simple"),
        )

        context.project.pipfile.add_package_version(package_version)
        assert "importlib-resources" in context.project.pipfile.packages.packages
        assert "importlib-resources" not in context.project.pipfile.dev_packages.packages
        assert not context.stack_info

        with ImportlibResourcesBackportBoot.assigned_context(context):
            unit = ImportlibResourcesBackportBoot()
            assert unit.run() is None

        assert len(context.stack_info) == 1
        assert "importlib-resources" not in context.project.pipfile.packages.packages
        assert "importlib-resources" not in context.project.pipfile.dev_packages.packages

    def test_remove_develop(self, context: Context) -> None:
        """Test removing develop importlib-resources dependency."""
        package_version = PackageVersion(
            name="importlib-resources", version="==3.0.0", develop=True, index=Source("https://pypi.org/simple"),
        )

        context.project.pipfile.add_package_version(package_version)
        assert "importlib-resources" not in context.project.pipfile.packages.packages
        assert "importlib-resources" in context.project.pipfile.dev_packages.packages
        assert not context.stack_info

        with ImportlibResourcesBackportBoot.assigned_context(context):
            unit = ImportlibResourcesBackportBoot()
            assert unit.run() is None

        assert len(context.stack_info) == 1
        assert "importlib-resources" not in context.project.pipfile.packages.packages
        assert "importlib-resources" not in context.project.pipfile.dev_packages.packages
