# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
"""! Syslog implementation of Publisher"""

import syslog
from . import builder
from . import publisher

_defaults = { "PRIORITY": "info" }

"""map various log level aliases to the syslog enumeration"""
_PRIORITYNAMES = {
     "alert": syslog.LOG_ALERT,
     "crit": syslog.LOG_CRIT,
     "debug": syslog.LOG_DEBUG,
     "emerg": syslog.LOG_EMERG,
     "err": syslog.LOG_ERR,
     "error": syslog.LOG_ERR,
     "info": syslog.LOG_INFO,
     "notice": syslog.LOG_NOTICE,
     "panic": syslog.LOG_EMERG,
     "warn": syslog.LOG_WARNING,
     "warning": syslog.LOG_WARNING,
     "log_alert": syslog.LOG_ALERT,
     "log_crit": syslog.LOG_CRIT,
     "log_debug": syslog.LOG_DEBUG,
     "log_emerg": syslog.LOG_EMERG,
     "log_err": syslog.LOG_ERR,
     "log_error": syslog.LOG_ERR,
     "log_info": syslog.LOG_INFO,
     "log_notice": syslog.LOG_NOTICE,
     "log_panic": syslog.LOG_EMERG,
     "log_warn": syslog.LOG_WARNING,
     "log_warning": syslog.LOG_WARNING
     }


def _get_priority_from_string(priority: str):
    p = priority.lower()
    if p in _PRIORITYNAMES:
        return _PRIORITYNAMES[p]
    return syslog.LOG_INFO

class SyslogPublisher(publisher.Publisher):
    """! Publish to syslog.
        Syslog priority is a global in C, so _priority is the last value we
        set it to using openlog across all instances of this publisher.

        Environment variables:
        - ADC_SYSLOG_PLUGIN_PRIORITY

    @ingroup pub_impl
    """

    _name = "syslog"
    _version = "1.0.0"
    _priority = None

    def __init__(self):
        super().__init__()
        self.defaults = _defaults
        self.paused = False
        self.plugin_prefix = "ADC_SYSLOG_PLUGIN_"

    def _config(self, priority: str) -> int:
        SyslogPublisher._priority = _get_priority_from_string(priority)
        return 0

    def config(self, **kwargs) -> int:
        """the only option for the syslog plugin is "PRIORITY=<syslog_level>"""
        priority = self._get(kwargs, "PRIORITY")
        self.mode = publisher.Publisher.Mode.INIT
        return self._config(priority.lower())

    def initialize(self) -> int:
        syslog.openlog("ADC", logoption=(syslog.LOG_CONS | syslog.LOG_PID),
            facility=syslog.LOG_USER)
        self.mode = publisher.Publisher.Mode.PUB_OR_FINAL
        return 0

    def publish(self, b: builder.Builder) -> int:
        if self.paused:
            return 0
        if SyslogPublisher._priority is None:
            self._config("info")
        if self.mode != publisher.Publisher.Mode.PUB_OR_FINAL:
            self.initialize()
        message = b.serialize()
        syslog.syslog(SyslogPublisher._priority, message)
        return 0

    def finalize(self) -> None:
        return None
