# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import errno
import json
import requests

from adctk.builder import Builder
from adctk.publisher import Publisher
from adctk.log import logger
#from . import publisher


# pylint: disable=W1203

_defaults = { "URL": Publisher.get_url_default(),
             "TIMEOUTS": Publisher.get_timeout_defaults(),
             "PORT": Publisher.get_port_default()}

class HttpStatusCodeError(Exception):
    """Formatter exception for an error code"""
    def __init__(self, code):
        self.code = code
    def __str__(self):
        return f"ERROR: Status code returned {self.code}"


def handle_request_status(returned_data):
    """log status and raise if error is unexpected"""
    status_code = returned_data.status_code
    if status_code < 200 or status_code > 300:
        logger.error(f"Status Code: {status_code}, Message: {returned_data.text}")
        raise HttpStatusCodeError(status_code)
    logger.info(f"Posting successful with status Code: {status_code}")

def http_post(method, url, headers, payload, timeouts):
    """log message send attempt"""
    logger.info(f"Posting to URL: {url}")
    logger.debug(f"Headers: {headers}, Payload: {payload}, timeout{timeouts}")
    ret = method(url, headers=headers, data=payload, timeout=timeouts)
    try:
        handle_request_status(ret)
    except HttpStatusCodeError as e:
        logger.info("adctk.http_post: exception %s for message %s", e, payload)
    return ret


#pylint: disable-next=too-many-instance-attributes
class HttpPublisher(Publisher):
    """! @brief Web server publisher implementation using the requests library.

        This plugin generates a message sends it to the configured web service.
        Multiple independent instances of this plugin may be used simultaneously.
        Timeouts are applied, so applications will not hang on failures.

        Environment Variables
        - ADC_HTTP_PLUGIN_URL
        - ADC_HTTP_PLUGIN_PORT
        - ADC_HTTP_PLUGIN_TIMEOUTS

    @ingroup pub_impl
    """

    def __init__(self):
        super().__init__()
        self.plugin_prefix = "ADC_HTTP_PLUGIN_"
        self._base_url = Publisher.get_url_default()
        self._base_port = Publisher.get_port_default()
        self._timeouts = Publisher.get_timeout_defaults()
        self._headers = {"Content-type" : "application/json", "Accept" : "application/json"}
        self._post_method = None

    @property
    def post_method(self):
        """@return requests.post, or an alternative if debugging"""
        if not self._post_method:
            self._post_method=requests.post
        return self._post_method

    def old_publish(self, builder):
        """publish json extracted from builder to _base_url server"""
        url = f"{self._base_url}:{self._base_port}/log"
        ret = http_post(self.post_method, url, self._headers,
                 builder.get_json_dump(), self._timeouts)
        logger.info(f"Returned json: {ret.json()}")
        return ret

    def config(self, **kwargs) -> int:
        """ The config options for the http plugin are url=<URL>,
            port=<PORT NUMBER>, timeouts=<timeout_connect:timeout_post>.
            If not specified, then the environment variables ADC_HTTP_PLUGIN_*
            are checked, where * is URL or PORT or TIMEOUTS.
            Bad timeout values will be ignored.
        """
        self._base_url = self._get(kwargs, "URL")
        self._base_port = self._get(kwargs, "PORT")
        times = self._get(kwargs, "TIMEOUTS")
        if isinstance(times, str):
            tlist = times.split(":")
            if len(tlist) == 1:
                try:
                    t = float(tlist[0])
                    self._timeouts = (t,t)
                except ValueError as e:
                    logger.error("adctk.HttpPublisher.config: valid timeouts %s not "\
                            "found in %s%s", times, self.plugin_prefix, "TIMEOUTS")
            try:
                ct = float(tlist[0])
                pt = float(tlist[1])
                self._timeouts = (ct,pt)
            except ValueError as e:
                logger.error("adctk.HttpPublisher.config: valid timeouts %s not "\
                        "found in %s%s", times, self.plugin_prefix, "TIMEOUTS")
        else:
            self._timeouts = times
        self.mode = Publisher.Mode.INIT
        return 0

    def initialize(self) -> int:
        if self.mode == Publisher.Mode.CONFIG:
            self.config()
        if self.mode != Publisher.Mode.INIT:
            self.state = Publisher.State.ERR
            return errno.EINVAL
        self.mode = Publisher.Mode.PUB_OR_FINAL
        return 0

    def publish(self, b: Builder) -> int:
        """publish json extracted from builder."""
        if self.paused:
            return 0
        if self.state != Publisher.State.OK:
            return 1
        if self.mode != Publisher.Mode.PUB_OR_FINAL:
            return 2
        url = f"{self._base_url}:{self._base_port}/log"
        ret = http_post(self.post_method, url, self._headers, b.get_json_dump(), self._timeouts)
        logger.info(f"Returned json: {ret.json()}")
        return ret

    def publish_str(self, json_string):
        """publish json_raw from caller to _base_url server"""
        if self.paused:
            return 0
        if self.state != Publisher.State.OK:
            return 1
        if self.mode != Publisher.Mode.PUB_OR_FINAL:
            return 2
        url = f"{self._base_url}:{self._base_port}/log"
        ret = http_post(self.post_method, url, self._headers, json_string, self._timeouts)
        logger.info(f"Returned json: {ret.json()}")
        return ret

    def publish_obj(self, obj):
        """publish obj from caller to _base_url server"""
        if self.paused:
            return 0
        if self.state != Publisher.State.OK:
            return 1
        if self.mode != Publisher.Mode.PUB_OR_FINAL:
            return 2
        url = f"{self._base_url}:{self._base_port}/log"
        ret = http_post(self.post_method, url, self._headers, json.dumps(obj), self._timeouts)
        logger.info(f"Returned json: {ret.json()}")
        return ret

    def finalize(self) -> None:
        return None
