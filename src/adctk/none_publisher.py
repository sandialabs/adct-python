# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

from . import publisher
from . import builder

class NonePublisher(publisher.Publisher):
    """! The no-op publisher. Silently ignores all calls. No environment variables.

    @ingroup pub_impl
    """
    _name = "none"
    _version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = None
        self.plugin_prefix = "ADC_NONE_PLUGIN_"
        self.paused = False

    def config(self, **kwargs) -> int:
        return 0

    def initialize(self) -> int:
        return 0

    def publish(self, b: builder.Builder) -> int:
        return 0

    def finalize(self) -> None:
        return None
