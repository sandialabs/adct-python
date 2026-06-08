# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
import pytest

from adctk.adc_version import AdcVersion

@pytest.fixture
def simple_version():
    return AdcVersion()

def test_adc_version(simple_version):
    assert str(simple_version) == "1.0.0-adct-json-1.0.0"
    assert simple_version.__json__() == {"version" : "1.0.0", "tags" : ["adct-json-1.0.0"]}

def test_adc_version_with_tag(simple_version):
    simple_version.add_tag("tagged")
    assert str(simple_version) == "1.0.0-adct-json-1.0.0-tagged"

def test_adc_version_tag_list(simple_version):
    simple_version.add_tags(["one"])
