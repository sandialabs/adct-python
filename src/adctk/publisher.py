# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
"""! @package docstring
publisher module comment
"""

import errno
import os
import json
import copy
import getpass
import enum
import sys
from . import log
from . import builder
from . import adc_version

_ENV_PREFIX = "ADC_SERVER_"
_PORT_DEFAULT = "443"
_SERVER_DEFAULT = "https://adct-data"
_CONNECT_TIMEOUT_DEFAULT = 5.0
_POST_TIMEOUT_DEFAULT = 5.0

class Publisher():
    """ The API for various implementations which publish Builder objects.
        Subclasses need to implement __init__, config, initialize, publish, finalize only.
        In subclass __init__, data items
            self.defaults: dict[str,str]
            self.plugin_prefix: str
        need to be set for the plugin.
        In each subclass, data members
            _name: str
            _version: str
        need to be reassigned.
    Particularly simple subclasses may not need to use data items: state, mode.

    @ingroup pub_impl
    """
    API_VERSION = adc_version.AdcVersion()._dict()

    class State(enum.Enum):
        """! For plugins where the output target becomes unrecoverable,
        state == ERR means no further output will be attempted."""
        OK = enum.auto()
        ERR = enum.auto()

    class Mode(enum.Enum):
        """! For plugins managing external resources (files, pipes),
        this enum is used to track where in the lifecycle they are.
        Each mode value indicates the next step that is needed.
        Plugins which need no tracking should initialize mode to PUB_OR_FINAL
        in the __init__ call."""
        CONFIG = enum.auto() # call config next
        INIT = enum.auto() # call initialize next
        PUB_OR_FINAL = enum.auto() # call publish or finalize next

    @staticmethod
    def get_timeout_defaults() -> tuple[float]:
        """! Get the adc server connect and response timeouts
        defined in the environment ADC_SERVER_CONNECT_TIMEOUT and
        ADC_SERVER_POST_TIMEOUT as a tuple or default values if not
        defined.
        """
        env_name = _ENV_PREFIX + "CONNECT_TIMEOUT"
        env_val = os.getenv(env_name)
        if env_val:
            try:
                ct = float(env_val)
            except ValueError:
                log.logger.error("adctk.Publisher.get_timeout_defaults: unable to "\
                        "convert %s to float from %s", env_val, env_name)
        else:
            ct = _CONNECT_TIMEOUT_DEFAULT
        env_name = _ENV_PREFIX + "POST_TIMEOUT"
        env_val = os.getenv(env_name)
        if env_val:
            try:
                pt = float(env_val)
            except ValueError:
                log.logger.error("adctk.Publisher.get_timeout_defaults: unable to "\
                        "convert %s to float from %s", env_val, env_name)
        else:
            pt = _POST_TIMEOUT_DEFAULT
        return (ct, pt)

    @staticmethod
    def get_url_default() -> str:
        """! Get the alleged adc server url base from environment ADC_SERVER_URL
        or the default if it is not present."""
        env_name = _ENV_PREFIX + "URL"
        env_val = os.getenv(env_name)
        if not env_val:
            return _SERVER_DEFAULT
        return env_val

    @staticmethod
    def get_port_default() -> str:
        """! Get the adc server port number to use if it is properly
        defined in the environment ADC_SERVER_PORT or the default
        if it is not."""
        env_name = _ENV_PREFIX + "PORT"
        env_val = os.getenv(env_name)
        if not env_val:
            return _PORT_DEFAULT
        try:
            i = int(env_val)
        except ValueError:
            i = int(_PORT_DEFAULT)
        return str(i)

    _name = "unknown"
    _version = "0.0.0"

    def __init__(self):
        self.defaults = None
        self.plugin_prefix = None
        self.paused = False
        self.state = Publisher.State.OK
        self.mode = Publisher.Mode.CONFIG

    def name(self) ->str:
        """! Get the name which a factory or error message should use."""
        return self._name

    def version(self) ->str:
        """! @return publisher version"""
        return self._version

    def get_option_defaults(self) -> dict[str,str]:
        """! @return modifiable copy of publisher option defaults"""
        return copy.deepcopy(self.defaults)

    def config(self, **kwargs) -> int:
        """! @brief Configure the plugin with the options given.
        For plugin QQQ, Environment variables ADC_QQQ_PLUGIN_<key> will override the plugin
        default for any key not defined in kwargs. Here QQQ is plugin.name().upper().
        Generic options:

        @param kwargs If env_prefix is included in kwargs, replaces plugin environment variables
        with those which are prefixed using env_prefix.

        @param env_prefix Typically, env_prefix is set to "PPP_ADC_QQQ_PLUGIN_" if application PPP wants to
        override the defaults of adctk plugin QQQ. Here QQQ is plugin.name().upper().
        If no prefixed version of the variable is present, the plugin default is used.
        kwargs takes precedence over environment variables. Plugin defaults are used
        if not overridden by kwargs or an environment variable.

        @return int non-zero if configuration cannot be completed using the arguments,
        environment, and default.
        """
        raise NotImplementedError("Publisher.config not implemented")

    def initialize(self) -> int:
        """! Set up any resources needed for reuse in publish()."""
        raise NotImplementedError("Publisher.initialize not implemented")

    def publish(self, b: builder.Builder) -> int:
        """! Publish json extracted from builder"""
        raise NotImplementedError("Publisher.publish not implemented")

    def finalize(self) -> None:
        """! Clean up any resources set up in initialize (files, pipes, etc)."""
        raise NotImplementedError("Publisher.finalize not implemented")

    def pause(self) -> None:
        """! Cause publish calls to be ignored until resume is called."""
        self.paused = True

    def resume(self) -> None:
        """! Cancel an prior calls to pause."""
        self.paused = False

    def publish_str(self, json_string: str) -> int:
        """ Deprecated function; prefer publish() Publish json string supplied by user,
        by creating a Builder and
        defining the application block to contain the string given as a single
        field. Use of this method is discouraged, as it hides important
        datatype information from downstream consumers and it must generate
        an application name."""
        from . import factory # break import loop
        if json_string is None:
            return errno.ENODATA
        af = factory.Factory()
        b = af.get_builder()
        # make header
        app = f"{getpass.getuser()}.publish_str"
        b.add_header_section(app)
        # make 'application' section
        ads = factory.Factory.get_builder()
        ads.add_json_string("payload", json_string)
        ads.add("argv", sys.argv)
        b.add_app_data_section(ads)
        # send the composed message
        self.publish(builder)
        return 0

    def publish_obj(self, obj) -> int:
        """ Deprecated function. Call publish_str with the result of json.dumps(obj), if possible.
        Returns EINVAL when dumps fails.
        Use of this method is discouraged"""
        try:
            js = json.dumps(obj)
            return self.publish_str(js)
        except TypeError:
            return errno.EINVAL
        return 0

    def _get(self, opts: dict[str,str], field: str) -> str:
        """ Check for short option named by field in opts and return if present.
            (In most cases the short name is in all capitals.)
            When named field is not present, use opts[env_prefix]
            (or if opts[env_prefix] is not present, then self.plugin_prefix)
            to search for env(prefix+field) and return that value if present.
            If no environment value found, return self.defaults[field]."""
        if field in opts:
            return opts[field]
        if "env_prefix" in opts:
            prefix = opts["env_prefix"]
        else:
            prefix = self.plugin_prefix
        env_name = prefix + field
        env_val = os.getenv(env_name)
        if not env_val:
            return self.defaults[field]
        return env_val

    def _get_bool(self, opts: dict[str,str], field: str) -> bool:
        s = self._get(opts, field)
        if s in ["TRUE", "true", "True", "1", "t", "T", "y", "Yes", "YES"]:
            return True
        return False

class MultiPublisher:
    """! Interface for a group of publishers all being fed the same message(s)."""

    def _config_from_dict(self, plugins: dict[dict[str]], strict):
        """@brief custom conf plugin X using plugins[X] dictionary."""
        for plug, d in plugins.items():
            p = self.factory.get_publisher(plug)
            if strict and not p:
                raise ValueError(f"MultiPublisher unable to construct plugin {plug}")
            if d:
                if not isinstance(d, dict):
                    raise ValueError(f"plugins must be a dictionary of dictionaries of strings, not {plugins}")
                p.config(d)
            else:
                p.config({})
            p.initialize()
            self.add(p)

    def _config_from_list(self, plugins: list[str], strict: bool):
        """@brief configure each plugin named in the list with defaults & env."""
        for i in plugins:
            p = self.factory.get_publisher(i)
            if strict and not p:
                raise ValueError(f"MultiPublisher unable to construct plugin {i}")
            self.add(p)

    def _config_from_env(self, env_name: str, strict: bool):
        """@brief configure with list following env_name.split(":")"""
        env_val = os.getenv(env_name, "")
        if env_val is None or len(env_val):
            return
        plugins = env_val.split(":")
        self._config_from_list(plugins, strict)

    def __init__(self, strict: bool, plugins: str|list[str]|dict|None):
        """! @param strict x
            @param plugins
        """
        self._version = "1.0.0"
        self.defaults = None
        self.paused = False
        self.plugin_prefix = None
        self.strict = strict
        self.pvec : [Publisher] = []
        from . import factory # break import loop
        self.factory = factory.Factory
        if not plugins:
            return
        if isinstance(plugins, str):
            self._config_from_env(plugins, strict)
            return
        if isinstance(plugins, list):
            if len(list):
                self._config_from_list(plugins, strict)
            else:
                self._config_from_env("ADC_MULTI_PUBLISHER_NAMES", strict)
            return
        if isinstance(plugins, dict):
            self._config_from_dict(plugins, strict)
            return
        raise ValueError("plugins argument of unexpected type: {plugins}")

    def version(self) -> str:
        """ @return the version of the MultiPublisher"""
        return self._version

    def add(self, publisher: Publisher) -> None:
        """ @param Add publisher to the dispatch list"""
        if not publisher:
            return None
        self.pvec.append(publisher)
        return None

    def publish(self, b: builder.Builder) -> int:
        """! @param b builder to publish via all configured publishers.

            @return count of publishers for which publish() returns an error.
        """
        if self.paused:
            return 0
        err = 0
        for pub in self.pvec:
            e = pub.publish(b)
            if e:
                err += 1
                log.logger.debug("Publish failed for plugin %s", pub.name())
        return err

    def terminate(self) -> None:
        """! finalize() all configured publishers"""
        for pub in self.pvec:
            pub.finalize()
        self.pvec = []

    def pause(self) -> None:
        """! pause() all configured publishers"""
        print(f"PAUSING {len(self.pvec)} PUBLISHERS")
        for pub in self.pvec:
            pub.pause()
        self.paused = True

    def resume(self) -> None:
        """! resume() all configured publishers"""
        print(f"RESUMING {len(self.pvec)} PUBLISHERS")
        for pub in self.pvec:
            pub.resume()
        self.paused = False
