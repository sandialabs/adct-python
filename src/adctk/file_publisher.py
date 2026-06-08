# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import errno
import pathlib
from . import builder
from . import publisher
from . import log

_defaults = {"DIRECTORY": ".",
             "FILE": "adc.file_plugin.log",
             "DEBUG": "0",
             "APPEND": "false" }

#pylint: disable-next=too-many-instance-attributes
class FilePublisher(publisher.Publisher):
    """! This plugin generates and writes each message to the configured file, with
  \\<adct-json>\\</adct-json> delimiters surrounding it.
  The output directory is "." by default, but may be overriden with
  a full path defined in env("ADC_FILE_PLUGIN_DIRECTORY").
  The file name is adc.file_plugin.log by default, and may be overridden
  with a path name in env("ADC_FILE_PLUGIN_FILE").
  The file is overwritten when the file_plugin is created, unless
  env("ADC_FILE_PLUGIN_APPEND") is "true".
  Debug output (normally to stderr) is enabled if
  env("ADC_FILE_PLUGIN_DEBUG") is a number greater than 0.

    Multiple independent file publishers may be created; if the same file name
    and directory are used for distinct instances, output file content
    is undefined.

  Environment Variables:
  - ADC_FILE_PLUGIN_DIRECTORY
  - ADC_FILE_PLUGIN_FILE
  - ADC_FILE_PLUGIN_APPEND
  - ADC_FILE_PLUGIN_DEBUG

    @ingroup pub_impl
    """
    _name = "file"
    _version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = _defaults
        self.paused = False
        self.plugin_prefix = "ADC_FILE_PLUGIN_"
        self.debug = 0
        self.fname = None
        self.fdir = None
        self.abspath = None
        self.fappend = False
        self.out = None

    def config(self, **kwargs) -> int:
        """The config options for the file plugin are directory=<directory>,
           file=<leafname>, append="true" and debug=<int>.
           If not specified, then the environment variables ADC_FILE_PLUGIN_*
           are checked, where * is DIRECTORY, FILE, APPEND, and DEBUG.
        """
        try:
            self.fappend =  self._get_bool(kwargs, "APPEND")
            self.fdir = self._get(kwargs, "DIRECTORY")
            self.fname = self._get(kwargs, "FILE")
            self.debug = int( self._get(kwargs, "DEBUG") )
            if self.debug > 0:
                log.logger.info("file plugin configured")
            self.mode = publisher.Publisher.Mode.INIT
            return 0
        except ValueError as e:
            log.logger.error("adctk.Filepublisher.Publisher.config: invalid options"\
                    "or environment %s* values: %s", self.plugin_prefix, e)
            return 1

    def initialize(self) -> int:
        # pylint: disable=too-many-return-statements
        if self.state == publisher.Publisher.State.ERR:
            return errno.ENOTRECOVERABLE
        if self.mode == publisher.Publisher.Mode.CONFIG:
            self.config()
        if self.mode != publisher.Publisher.Mode.INIT:
            return errno.EINVAL
        if self.state == publisher.Publisher.State.ERR:
            log.logger.error("adctk.FilePublisher.initialize: unexpected 'state' found.")
            return errno.ENOTRECOVERABLE
        checkdir = pathlib.Path(self.fdir)
        dirmade = False
        try:
            checkdir.mkdir(parents=True, exist_ok=True)
            dirmade = True
        except FileExistsError:
            log.logger.error("adctk.FilePublisher.initialize: An existing file cannot be "\
                    "converted to a directory in path %s", self.fdir)
            self.state = publisher.Publisher.State.ERR
            return errno.EEXIST
        except PermissionError:
            log.logger.error("adctk.FilePublisher.initialize: permission denied "\
                    "along path %s", self.fdir)
            self.state = publisher.Publisher.State.ERR
            return errno.EPERM
        except OSError as e:
            log.logger.error("adctk.FilePublisher.initialize: unexpected OSError. %s", e)
            self.state = publisher.Publisher.State.ERR
            return errno.EIO
        if not dirmade:
            self.state = publisher.Publisher.State.ERR
            return errno.EINVAL
        self.abspath = (pathlib.Path(self.fdir) / self.fname).absolute()
        if self.fappend:
            filemode = "ab"
        else:
            filemode = "wb"
        try:
            # pylint: disable-next=consider-using-with
            self.out = open(self.abspath, filemode)
            if self.out is None:
                self.state = publisher.Publisher.State.ERR
                return errno.EBADF
            self.mode = publisher.Publisher.Mode.PUB_OR_FINAL
            return 0
        except (FileNotFoundError, PermissionError, IsADirectoryError, IOError, OSError):
            log.logger.error("adctk.FilePublisher.initialize: unable to open %s", self.abspath)
            self.state = publisher.Publisher.State.ERR
            self.out = None
            return errno.EBADF

    def publish(self, b: builder.Builder) -> int:
        if self.paused:
            return 0
        if self.state != publisher.Publisher.State.OK:
            return 1
        if self.mode != publisher.Publisher.Mode.PUB_OR_FINAL:
            return 2
        if self.out is None:
            return 3
        try:
            message = f"<adct-json>{b.serialize()}</adct-json>\n"
            self.out.write(message.encode('utf-8'))
        except (FileNotFoundError, PermissionError, IsADirectoryError, IOError, OSError):
            self.state = publisher.Publisher.State.ERR
            log.logger.error("adctk.FilePublisher.publish: write failed to %s", self.abspath)
            self.out.close()
            self.out = None
        return 0

    def finalize(self) -> None:
        self.state = publisher.Publisher.State.OK
        self.paused = False
        self.mode = publisher.Publisher.Mode.CONFIG
        if self.out:
            self.out.close()
            self.out = None
