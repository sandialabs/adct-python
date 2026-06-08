# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""! @package factory
Factory implementation module

@defgroup pub_impl Publisher implementation classes
@defgroup factory_impl Factory class
@defgroup builder_impl Builder class
"""

import typing
from . import publisher
from . import builder
from . import adc_version
from . import log
from . import debug_file_publisher
from . import file_publisher
from . import http_publisher
from . import ldms_publisher
from . import multifile_publisher
from . import none_publisher
#from . import script_publisher
from . import stdout_publisher
from . import syslog_publisher

def _get_subclasses(cls):
    """Find subclasses of cls"""
    return set(cls.__subclasses__()).union(
        [sub for cl in cls.__subclasses__() for sub in _get_subclasses(cl)])

class Factory:
    """! @brief factory for adctk api objects.

    @ingroup factory_impl
    """
    _publishers = {}

    API_VERSION = adc_version.AdcVersion()._dict()

    @staticmethod
    def get_builder() -> builder.Builder:
        """! @brief Create an empty builder object or subobject for an adctk message.

            @return an empty message builder object"""
        return builder.Builder()

    @staticmethod
    def get_publisher_names() -> list[str]:
        """! @brief Get the names of publishers available.

            @return the names of publishers available.
        The "none", "stdout", "file", "multifile", "syslog", and "script" publishers
        are always available in Linux environments.
        """
        if not Factory._publishers:
            for cls in _get_subclasses(publisher.Publisher):
                Factory._publishers[cls._name] = cls
        return Factory._publishers.keys()

    @staticmethod
    def get_publisher(name: str, options: dict[str] =None) -> publisher.Publisher|None:
        """! Get a configured instance of the named publisher type.

            @param name one of the elements found with get_publisher_names().
            @param options a map of option names and their values; plugins will
                silently ignore unused options. publisher.config(options)
                and initialize will be called unless options is None.
                To apply a default configuration, give the empty {} instead of None.
            @return a publisher instance, or None if the name is unavailable.
        """
        if name in Factory.get_publisher_names():
            x = Factory._publishers[name]()
            if x:
                if not options:
                    return x
                x.config(options)
                x.initialize()
                return x
        return None

    @staticmethod
    def get_multi_publisher(strict=False,
        plugins: str|list[str]|dict|None =None) -> publisher.MultiPublisher:
        """! Get a MultiPublisher for use or manually populating.

            MultiPublisher provides a convenient way to publish on multiple
            publishers without duplicate calls to a publish() function.
            Options:

            @param strict If strict=True, a failure to construct any named
            publisher will return None instead of a multipublisher, otherwise
            failed or unknown publishers will be silently ignored.

            @param plugins can be one of:
            - None, which then constructs plugins using the name list from
              env("ADC_MULTI_PUBLISHER_NAMES") and their environment-defined
              or default options.
              If ADC_MULTI_PUBLISHER_NAMES is unset, an empty MultiPublisher ready
              to configure is returned.
            - A string naming an alternative environment variable to ADC_MULTI_PUBLISHER_NAMES.
                E.g. a library foo may use FOO_MULTI_PUBLISHER_NAMES.
            - A list of names from among those returned by get_publisher_names,
              where each named plugin is configured from environment-defined or
              default options. An empty list is treated as None.
            - A dictionary of dictionaries, where the top keys are plugin names and
              the dictionary values are as documented in each plugin.

          Empty example: add individual configured publisher to result.
            mp = get_multi_publisher()
            mp.add(...)

          From environment ADC_MULTI_PUBLISHER_NAMES example
            m1 = get_multi_publisher(plugins=[])
            m1.add(...)

          From environment MY_APP_MULTI_PUBLISHER_NAMES example
            m1 = get_multi_publisher(plugins="MY_APP_MULTI_PUBLISHER_NAMES")
            m1.add(...)

          Configure several plugins using environment
            m2 = get_multi_publisher(plugins=["stdout","http"])

          Configure several plugins using environment and option overrides
            m3 = get_multi_publisher(plugins={"stdout":{},
                                              "http":{"port": "8443", "url": "localhost"}})

        """
#       try:
        return publisher.MultiPublisher(strict, plugins)
#       except:
#           return None

    def __init__(self):
        pass # Factory.__init__ nothing to do
