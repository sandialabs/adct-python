# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
import errno
import os
import tempfile
import subprocess

from . import builder
from . import publisher
from . import log

# TODO:
# make system version an async subprocess
# extend to ldmsd_msg_publish binary (pipe and async subprocess)
# extend to ldmsd_msg_publish binary (ldms python library call)

################################# ldms stream bus
_defaults_system = {
    "DIRECTORY": "/dev/shm/adc",
    "PROG":  "/usr/sbin/ldmsd_stream_publish",
    "STREAM": "adc_publish_api",
    "AUTH":  "munge",
    "PORT":  "412",
    "HOST":  "localhost",
    "AFFINITY": "all"
}

_defaults_pipe = {
    "PROG":  "/usr/sbin/ldmsd_stream_publish",
    "STREAM": "adc_publish_api",
    "AUTH":  "munge",
    "PORT":  "412",
    "TIMEOUT":  "2",
    "HOST":  "localhost",
    "AFFINITY": "all"
}

class LDMSPipePublisher(publisher.Publisher): # pylint: disable=R0902
    """! Publish data over a pipe to ldmsd_stream_publish once via pipe recreated at each call.

        Environment Variables
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_PROG
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_STREAM
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_AUTH
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_PORT
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_HOST
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_TIMEOUT

    @ingroup pub_impl
    """
    _name = "ldms-pipe-stream"
    _version= "1.0.0"
    def __init__(self):
        super().__init__()
        self.plugin_prefix = "ADC_LDMSD_STREAM_PUBLISH_PLUGIN_"
        self.defaults = _defaults_pipe
        self.prog: str = None
        self.port: str = None
        self.auth: str = None
        self.timeout: int = 2
        self.stream: str = None
        self.host: str = None

    def config(self, **kwargs) -> int:
        self.prog = self._get(kwargs, "PROG")
        self.port = self._get(kwargs, "PORT")
        self.auth = self._get(kwargs, "AUTH")
        self.stream = self._get(kwargs, "STREAM")
        self.host = self._get(kwargs, "HOST")
        timeout = self._get(kwargs, "TIMEOUT")
        try:
            x = int(timeout)
            self.timeout = x
        except ValueError:
            log.logger.error("LDMSPipe-publisher TIMEOUT %s is invalid."\
                " Integer needed from %s%s.", timeout, self.plugin_prefix, "TIMEOUT")
        return 0

    def initialize(self) -> int:
        if self.mode == publisher.Publisher.Mode.CONFIG:
            self.config()
        if self.mode != publisher.Publisher.Mode.INIT:
            self.state = publisher.Publisher.State.ERR
            return errno.EINVAL
        self.mode = publisher.Publisher.Mode.PUB_OR_FINAL
        return 0

    def _post(self, msg) ->int:
        try:
            cmd = [self.prog,
                   "-t", "json",
                   "-x", "sock",
                   "-p", self.port,
                   "-a", self.auth,
                   "-s", self.stream,
                   "-h", self.host
                   ]
            log.logger.info("LDMSPipe-publisher command: %s", cmd)
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)
            process.stdin.write(msg)
            process.stdin.flush()
            process.stdin.close()
            stdout, stderr = process.communicate(timeout=self.timeout)
            output_string = stdout.decode("utf-8")
            error_string = stderr.decode("utf-8")
            log.logger.debug("Output: %s Error: %s", output_string, error_string)
            ret = process.returncode
            if ret != 0:
                log.logger.warning("LDMSPipe-publisher: publish process failed with error: %d",
                                    ret)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            log.logger.warning("LDMSPipe-publisher: timeout expired")
        return ret

    def publish(self, b: builder.Builder):
        """publish json extracted from builder to _base_url server"""
        s = b.get_json_dump()
        ret = self._post(s)
        return ret

    def finalize(self):
        pass # nothing to do here. LDMSPipePublisher.finalize

class LDMSSystemPublisher(LDMSPipePublisher):
    """! Publish data via file to ldmsd_stream_publish once via process recreated at each call.

        Environment Variables
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_PROG
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_STREAM
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_AUTH
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_PORT
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_HOST
        - ADC_LDMSD_STREAM_PUBLISH_PLUGIN_TIMEOUT

    @ingroup pub_impl
    """
    _name = "ldms-system-stream"
    _version= "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = _defaults_system
        self.dir_: str = None

    def config(self, **kwargs) -> int:
        self.dir_ = self._get(kwargs, "DIRECTORY")
        return super().config(**kwargs)

    def _post(self, msg:str ) ->int:
        if not self.dir_:
            self.initialize()
        f = None
        try:
            f, filepath = tempfile.mkstemp( prefix="adctk-json-system-stream-msg-", dir=self.dir_ )
            f.write(msg)
            f.close()
            cmd = [self.prog,
                   "-t", "json",
                   "-x", "sock",
                   "-p", self.port,
                   "-a", self.auth,
                   "-s", self.stream,
                   "-h", self.host,
                   "-f", filepath
                   ]
            log.logger.info("LDMSSystem-publisher command: %s", cmd)
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                stdout, stderr = process.communicate(timeout=self.timeout)
                output_string = stdout.decode("utf-8")
                error_string = stderr.decode("utf-8")
                log.logger.debug("Output: %s", output_string)
                log.logger.debug("Error: (may be empty): %s", error_string)
                ret = process.wait()
                if ret != 0:
                    log.logger.warning("LDMSSystem-publisher: publish process failed "\
                        "with error: %s", ret)
        except subprocess.TimeoutExpired:
            log.logger.warning("LDMSSystem-publisher: timeout expired")
        if f:
            os.unlink(filepath)

################################# ldms message bus
_defaults_system_message = {
    "DIRECTORY": "/dev/shm/adc",
    "PROG":  "/usr/sbin/ldms_message_publish",
    "TAG": "adc_publish_api",
    "AUTH":  "munge",
    "PORT":  "412",
    "HOST":  "localhost",
    "AFFINITY": "all"
}

_defaults_pipe_message = {
    "PROG":  "/usr/sbin/ldms_message_publish",
    "TAG": "adc_publish_api",
    "AUTH":  "munge",
    "PORT":  "412",
    "TIMEOUT":  "2",
    "HOST":  "localhost",
    "AFFINITY": "all"
}

class LDMSPipeMessagePublisher(publisher.Publisher): # pylint: disable=R0902
    """! Publish data over a pipe to ldms_message_publish once via pipe recreated at each call.

        Environment Variables
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_PROG
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_TAG
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_AUTH
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_PORT
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_HOST
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_TIMEOUT

    @ingroup pub_impl
    """
    _name = "ldms-pipe-message"
    _version= "1.0.0"
    def __init__(self):
        super().__init__()
        self.plugin_prefix = "ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_"
        self.defaults = _defaults_pipe_message
        self.prog: str = None
        self.port: str = None
        self.auth: str = None
        self.timeout: int = 2
        self.tag: str = None
        self.host: str = None

    def config(self, **kwargs) -> int:
        self.prog = self._get(kwargs, "PROG")
        self.port = self._get(kwargs, "PORT")
        self.auth = self._get(kwargs, "AUTH")
        self.tag = self._get(kwargs, "TAG")
        self.host = self._get(kwargs, "HOST")
        timeout = self._get(kwargs, "TIMEOUT")
        try:
            x = int(timeout)
            self.timeout = x
        except ValueError:
            log.logger.error("LDMSPipe-publisher TIMEOUT %s is invalid. integer needed.", timeout)
        return 0

    def initialize(self) -> int:
        if self.mode == publisher.Publisher.Mode.CONFIG:
            self.config()
        if self.mode != publisher.Publisher.Mode.INIT:
            self.state = publisher.Publisher.State.ERR
            return errno.EINVAL
        self.mode = publisher.Publisher.Mode.PUB_OR_FINAL
        return 0

    def _post(self, msg) ->int:
        try:
            cmd = [self.prog,
                   "-t", "json",
                   "-x", "sock",
                   "-p", self.port,
                   "-a", self.auth,
                   "-m", self.tag,
                   "-h", self.host
                   ]
            log.logger.info("LDMSPipe-publisher command: %s", cmd)
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)
            process.stdin.write(msg)
            process.stdin.flush()
            process.stdin.close()
            stdout, stderr = process.communicate(timeout=self.timeout)
            output_string = stdout.decode("utf-8")
            error_string = stderr.decode("utf-8")
            log.logger.debug("Output: %s Error: %s", output_string, error_string)
            ret = process.returncode
            if ret != 0:
                log.logger.warning("LDMSPipe-publisher: publish process failed with error: %d",
                                    ret)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            log.logger.warning("LDMSPipe-publisher: timeout expired")
        return ret

    def publish(self, b: builder.Builder):
        """publish json extracted from builder to _base_url server"""
        s = b.get_json_dump()
        ret = self._post(s)
        return ret

    def finalize(self):
        pass # nothing to do here. LDMSPipeMessagePublisher.finalize

class LDMSSystemMessagePublisher(LDMSPipeMessagePublisher):
    """! Publish data via file to ldms_message_publish once via process recreated at each call.

        Environment Variables
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_PROG
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_TAG
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_AUTH
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_PORT
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_HOST
        - ADC_LDMS_MESSAGE_PUBLISH_PLUGIN_TIMEOUT

    @ingroup pub_impl
    """
    _name = "ldms-system-message"
    _version= "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = _defaults_system_message
        self.dir_: str = None

    def config(self, **kwargs) -> int:
        self.dir_ = self._get(kwargs, "DIRECTORY")
        return super().config(**kwargs)

    def _post(self, msg:str ) ->int:
        if not self.dir_:
            self.initialize()
        f = None
        try:
            f, filepath = tempfile.mkstemp( prefix="adctk-json-system-message-msg-", dir=self.dir_ )
            f.write(msg)
            f.close()
            cmd = [self.prog,
                   "-t", "json",
                   "-x", "sock",
                   "-p", self.port,
                   "-a", self.auth,
                   "-m", self.tag,
                   "-h", self.host,
                   "-f", filepath
                   ]
            log.logger.info("LDMSSystem-publisher command: %s", cmd)
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                stdout, stderr = process.communicate(timeout=self.timeout)
                output_string = stdout.decode("utf-8")
                error_string = stderr.decode("utf-8")
                log.logger.debug("Output: %s", output_string)
                log.logger.debug("Error: (may be empty): %s", error_string)
                ret = process.wait()
                if ret != 0:
                    log.logger.warning("LDMSSystem-publisher: publish process failed "\
                        "with error: %s", ret)
        except subprocess.TimeoutExpired:
            log.logger.warning("LDMSSystem-publisher: timeout expired")
        if f:
            os.unlink(filepath)
        return ret
