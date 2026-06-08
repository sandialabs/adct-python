# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
"""! Stdout printing implementation of Publisher"""

from . import publisher
from . import builder

class StdoutPublisher(publisher.Publisher):
    """! The console printing publisher. No environment variables.

    @ingroup pub_impl
    """

    _name = "stdout"
    _version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = None
        self.plugin_prefix = "ADC_STDOUT_PLUGIN_"
        self.paused = False
        self.mode = publisher.Publisher.Mode.PUB_OR_FINAL

    def config(self, **kwargs) -> int:
        return 0

    def initialize(self) -> int:
        return 0

    def publish(self, b: builder.Builder) -> int:
        if self.paused:
            return 0
        print(b.serialize())
        return 0

    def finalize(self) -> None:
        return None
