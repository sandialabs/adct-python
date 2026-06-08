# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import os
import stat
import errno
import socket
import getpass
import time
import pathlib
import tempfile
from . import builder
from . import publisher
from . import log

_defaults = {"DIRECTORY": ".",
             "RANK": "",
             "DEBUG": "0" }

#pylint: disable-next=too-many-instance-attributes
class MultiFilePublisher(publisher.Publisher):
    """! This plugin generates writes each message to the configured file, with
  \\<adct-json>\\</adct-json> delimiters surrounding it.

  The output directory is "." by default, but may be overriden with
  a full path defined in env("ADC_MULTIFILE_PLUGIN_DIRECTORY").
  The resulting mass of files can be reduced independently later
  by concatenating all files in the tree or more selectively
  with a single call to the consolidate_multifile_logs() function.

  Multiple independent multifile publishers may be created; exact filenames
  are not user controlled, to avoid collisions. Likewise there is no append
  mode.

  DIR/$user/[$adc_wfid.]H_$host.P$pid.T$start.p$publisherptr/$application.R$rank.XXXXXX

  Files opened will remain opened until the publisher is finalized.

  Debug output (to stderr) is enabled if
  env("ADC_MULTIFILE_PLUGIN_DEBUG") is a number other than 0.

    Environment Variables
    - ADC_MULTIFILE_PLUGIN_DIRECTORY
    - ADC_MULTIFILE_PLUGIN_RANK empty, integer, or name of another variable to find integer rank in.
    - ADC_MULTIFILE_PLUGIN_DEBUG

    @ingroup pub_impl
    """
    _name = "multifile"
    _version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.defaults = _defaults
        self.paused = False
        self.plugin_prefix = "ADC_MULTIFILE_PLUGIN_"
        self.debug = 0
        self.fname = None
        self.fdir = None # composed from user, host, time, pid, wfid, selfpointer
        self.topdir = None # from DIRECTORY env
        self.user = getpass.getuser()
        self.host = socket.gethostname()
        self.pid = str(os.getpid())
        self.rank = None
        self.abspath = None
        self.fappend = False
        self.app_out = {}
        self.mode = None

    def config(self, **kwargs) -> int:
        """The config options for the file plugin are directory=<directory>,
           file=<leafname>, append="true" and debug=<int>.
           If not specified, then the environment variables ADC_MULTIFILE_PLUGIN_*
           are checked, where * is DIRECTORY, FILE, and DEBUG.
        """
        try:
            self.topdir = self._get(kwargs, "DIRECTORY")
            self.debug = int( self._get(kwargs, "DEBUG") )
            self.rank = self._get(kwargs, "RANK")
            if self.rank:
                try:
                    irank = int(self.rank)
                except ValueError:
                    indirect = os.getenv(self.rank)
                    if indirect:
                        try:
                            irank = int(indirect)
                            self.rank = str(irank)
                        except ValueError:
                            log.logger.error("adctk.Publisher.get_timeout_defaults: unable to "\
                                  "convert %s to int from %s%s",
                                  self.rank, self.plugin_prefix,"RANK")

            wfid = os.getenv("ADC_WFID")
            if wfid:
                wname = "wfid_" + wfid + "."
            else:
                wname = ""
            t = time.monotonic_ns()
            sec = str(t // 1000000000)
            nsec = str(t % 1000000000)
            start = ".".join((sec, nsec))
            self.fdir = (self.topdir + "/" + self.user + "/" + wname +
                "H_" + self.host +".P" + self.pid + ".T" + start +
                ".p" + hex(id(self)) )
            if self.debug > 0:
                log.logger.info("multifile plugin configured")
            self.mode = publisher.Publisher.Mode.INIT
            return 0
        except: # fixme: catch more specific exceptions here instead of global
            log.logger.error("adctk.MultiFilePublisher.config: invalid options or "+
                "environment ADC_MULTIFILE_PLUGIN_* values")
            return 1

    def _create_directory_like(self, newdir, dirlike):
        """Create a directory and use dirlik perms. parent of newdir must exist"""
        likestat = os.stat(dirlike)
        likemode = stat.S_IMODE(likestat.st_mode)
        os.mkdir(newdir)
        os.chmod(newdir, likemode)

    def _create_directories(self):
        # return if fdir exists already
        fdir = pathlib.Path( self.fdir)
        if fdir.exists():
            if fdir.is_dir():
                return
            raise NotADirectoryError(f"{fdir}: cannot replace file of the same name")
        # if dirname(fdir) exists already, make last subdir
        bdir = fdir.parent
        if bdir.exists():
            if bdir.is_dir():
                self._create_directory_like(fdir, bdir)
                return
            raise NotADirectoryError(f"{bdir}: cannot make subdirectory in a file")
        # if topdir/user/ exists already, create rest w/perm, sticky from user/
        du_path = pathlib.Path(self.topdir)
        du_path = du_path / self.user
        if du_path.exists():
            if du_path.is_dir():
                self._create_directory_like(self.fdir, du_path)
                return
            raise NotADirectoryError(f"{du_path}: cannot replace file of the same name")
        # create whole tree at self.topdir
        pathlib.Path(self.topdir).mkdir(mode=0o1750)
        self._create_directory_like(du_path, self.topdir)
        self._create_directory_like(fdir, self.topdir)

    def _create_stream(self, app):
        """allocate file or None in app_out table. If allocated, truncated opened ug+rw"""
        if app in self.app_out:
            return
        try:
            (fd, n) = tempfile.mkstemp(dir=self.fdir, prefix=f"{app}.R{self.rank}.", text=False)
            os.close(fd)
            self.app_out[app] = open(n, "wb")
            cperm = os.stat(n).st_mode
            os.chmod(n, cperm | stat.S_IRGRP | stat.S_IWGRP )
        except IOError as e:
            self.app_out[app] = None

    def initialize(self) -> int:
        # pylint: disable=too-many-return-statements
        if self.state == publisher.Publisher.State.ERR:
            return errno.ENOTRECOVERABLE
        if self.mode == publisher.Publisher.Mode.CONFIG:
            self.config()
        if self.mode != publisher.Publisher.Mode.INIT:
            return errno.EINVAL
        if self.state == publisher.Publisher.State.ERR:
            log.logger.error("adctk.MultiFilePublisher.initialize: unexpected 'state' found.")
            return errno.ENOTRECOVERABLE
        checkdir = pathlib.Path(self.fdir)
        dirmade = False
        try:
            self._create_directories()
            dirmade = True
        except NotADirectoryError:
            log.logger.error("adctk.MultiFilePublisher.initialize: An existing "\
                "file cannot be converted to a directory in path %s", self.fdir)
            self.state = publisher.Publisher.State.ERR
            return errno.EEXIST
        except PermissionError:
            log.logger.error("adctk.MultiFilePublisher.initialize: permission denied "\
                    "along path %s", self.fdir)
            self.state = publisher.Publisher.State.ERR
            return errno.EPERM
        except OSError as e:
            log.logger.error("adctk.MultiFilePublisher.initialize: unexpected OSError")
            self.state = publisher.Publisher.State.ERR
            return errno.EIO
        if not dirmade:
            self.state = publisher.Publisher.State.ERR
            return errno.EINVAL
        try:
            # make sure we can write into target location
            with tempfile.NamedTemporaryFile(dir=self.fdir, prefix=".test",
                     mode="w+b", encoding="utf-8") as f:
                f.write("test")
            self.mode = publisher.Publisher.Mode.PUB_OR_FINAL
            return 0
        except (FileNotFoundError, PermissionError, IsADirectoryError, IOError, OSError) as e:
            log.logger.error("adctk.MultiFilePublisher.initialize: unable to open file in %s : %s",
                             self.fdir, e)
            self.state = publisher.Publisher.State.ERR
            return errno.EBADF

    def publish(self, b: builder.Builder) -> int:
        if self.paused:
            return 0
        if self.state != publisher.Publisher.State.OK:
            return 1
        if self.mode != publisher.Publisher.Mode.PUB_OR_FINAL:
            return 2
        app = b.get_value_string("/header/application")
        if not app:
            log.logger.error("adctk.MultiFilePublisher.publish: cannot publish "\
                            "without /header/application")

            log.logger.info("adctk.MultiFilePublisher.publish: received %s", b.serialize())
            log.logger.info("adctk.MultiFilePublisher.publish: has sections %s",
                             b.get_section_names())
            return 1
        self._create_stream(app)
        try:
            message = f"<adct-json>{b.serialize()}</adct-json>\n"
            if self.app_out[app]:
                self.app_out[app].write(message.encode('utf-8'))
        except (FileNotFoundError, PermissionError, IsADirectoryError, IOError, OSError):
            self.state = publisher.Publisher.State.ERR
            log.logger.error("adctk.MultiFilePublisher.publish: write failed to %s", self.app_out[app].name)
            self.app_out[app].close()
            return 1
        return 0

    def finalize(self) -> None:
        self.state = publisher.Publisher.State.OK
        self.paused = False
        self.mode = publisher.Publisher.Mode.CONFIG
        for app, f in self.app_out.items():
            if f:
                f.close()
                self.app_out[app] = None
        self.app_out = {}
