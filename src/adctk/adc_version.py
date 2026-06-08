# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
"""Based on semver: https://semver.org/"""
class AdcVersion():
    """! Construct for ADC Toolkit Python Version"""
    def __init__(self, **kwargs):
        if "name" in kwargs:
            self.version = kwargs["name"]
        else:
            self.version = "1.0.0"
        self.__version__ = self.version
        if "tags" in kwargs:
            self.tags = kwargs["tags"]
        else:
            self.tags = ["adct-json-1.0.0"]

    def __str__(self):
        if self.tags:
            stringified_tag = "-".join(self.tags)
            return f"{self.version}-{stringified_tag}"
        return f"{self.version}"

    def _dict(self):
        return {"version" : self.version,
                "tags" : self.tags}

    def __json__(self):
        return self._dict()

    def add_tag(self, tag: str):
        """! Add a tag to the list in the version object"""
        self.tags.append(tag)
        return self

    def add_tags(self, tags: list):
        """! Add an iterable of tags to the list in the version object"""
        self.tags.extend(tags)
        return self
