# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import json
from . import log
from . import builder
from . import publisher

class DebugFilePublisher(publisher.Publisher):
    """! debugging version of a file-oriented publisher.
    This assumes a single process writing to a given file
    and it has no evironment-based initialization.
    File is reopened for append on every publication.
    *** Do not use in production code. ***
    """
    def __init__(self, path=None, **kwargs):
        super().__init__()
        if not path:
            self.plugin_prefix = "ADC_DEBUG_FILE_PLUGIN_"
            self._path = self._get(kwargs, "FILE")
            if not self._path:
                self._path = "adc.debug_file_publisher.log"
        else:
            self._path = path

    def post(self, j):
        """ log the message """
        try:
            with open(self._path, mode="a", encoding='utf-8') as f:
                print(j, file=f)
                return 0
        except OSError as e:
            log.logger("error opening %s: %s", self._path, e)
            return 1

    def publish(self, b: builder.Builder):
        """! Publish json extracted from builder to _base_url server"""
        ret = self.post(b.get_json_dump())
        return ret

    def publish_obj(self, obj):
        """publish obj (json.dumps(obj) result) from caller to file.
        Does not produce valid ADCT messages.
        """
        ret = self.post(json.dumps(obj))
        return ret

    def publish_str(self, json_string):
        """publish json_string (json.dumps result) from caller to file.
        Does not produce valid ADCT messages.
        """
        ret = self.post(json_string)
        return ret

    def config(self, **kwargs):
        pass # config: nothing to do here
    def initialize(self):
        pass # initialize: nothing to do here
    def finalize(self):
        pass # finalize: nothing to do here
