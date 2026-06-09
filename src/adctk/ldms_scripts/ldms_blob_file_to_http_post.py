# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
#! /usr/bin/env python3
# usagei: see $0 --help
# stream json forwarding to adc server tool
#
# input file format is a tuple of matching files:
# x.DAT.$date : records are OFFSET size; well formed data is null-byte delimited.
# x.TYPE.$date : records are chars. types are 's' string, 'j' json
# x.OFFSET.$date : records are little-endian uint64_t
# x.TIMING.$date : records are pairs of little-endian uint64_t, r[0] = seconds, r[1] microsecond
#
# requires argparse with BooleanOptionalAction (py>=3.9)
#
##### begin UC Irvine portion of code #############################################
r"""
Split up a file and yield its pieces based on some line terminator.

Usage looks like:
    $ /usr/local/cpython-3.6/bin/python3
    Python 3.6.0 (default, Apr 22 2017, 09:17:19)
    [GCC 5.4.0 20160609] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import readline0
    >>> file_ = open('/etc/shells', 'r')
    >>> for line in readline0.readline0(file_=file_, separator=b'\n'):
    ...     print(line)
    ...
    b'# /etc/shells: valid login shells'
    b'/bin/sh'
    b'/bin/dash'
    b'/bin/bash'
    b'/bin/rbash'
    >>>

Of course separator need not be a newline; it defaults to a null byte.
"""

# This software is the proprietary property of The Regents of the University of California ("The Regents") Copyright (c)
# 1993-2006 The Regents of the University of California, Irvine campus. All Rights Reserved.

# Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.

# Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with the distribution.

# Neither the name of The Regents nor the names of its contributors may be used to endorse or promote products derived
# from this software without specific prior written permission.

# The end-user understands that the program was developed for research purposes and is advised not to rely exclusively
# on the program for any reason.

# THE SOFTWARE PROVIDED IS ON AN "AS IS" BASIS, AND THE REGENTS AND CONTRIBUTORS HAVE NO OBLIGATION TO PROVIDE
# MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS. THE REGENTS AND CONTRIBUTORS SPECIFICALLY DISCLAIM ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, EXEMPLARY OR CONSEQUENTIAL DAMAGES, INCLUDING BUT NOT LIMITED TO PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSE OF USE, DATA OR PROFITS, OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND UNDER ANY
# THEORY OF LIABILITY WHETHER IN CONTRACT, STRICT LIABILITY OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
import re
import sys
import typing

def readline0(file_: typing.Union[typing.BinaryIO, int] = sys.stdin.buffer, separator: bytes = b'\0', blocksize: int = 2 ** 16):
    # pylint: disable=W1401
    # W1401: We really do want a null byte
    """
    Instantiate Readline0 class and yield what we get back.

    file_ defaults to sys.stdin, separator defaults to a null, and blocksize defaults to 64K.
    """
    readline0_obj = Readline0(file_, separator, blocksize)
    # FIXME: This should become a yield from eventually.
    for line in readline0_obj.sequence():
        yield line


class Readline0(object):
    # pylint: disable=R0902
    # R0902: We really do need lots of instance attributes
    """Yield a series of blocks, separated by separator."""

    # This class assumes that there will be a null once in a while.  If you feed it with a huge block of data that has
    # no nulls (line separators), woe betide you.
    def __init__(self, file_: typing.Union[typing.BinaryIO, int], separator: bytes, blocksize: int) -> None:
        """Initialize."""
        self.file_ = file_
        self.blocksize = blocksize

        self.have_fraction = False
        self.fraction = b''

        self.separator = separator

        self.fields: typing.List[bytes] = []

        self.yieldno = 0

        self.bang = b'!'
        self.metapattern = b'([^!]*)!|([^!]+)$'
        self.buffer_ = b''
        self.separator = separator

        # bytes objects have a split method, but it doesn't work, at least not in Python 3.1.2.  But the re module
        # works with bytes, so we use that.

        self.pattern = re.sub(self.bang, self.separator, self.metapattern)

        self.at_eof = False

    @classmethod
    def handle_field_pairs(
            cls,
            field_pairs: typing.List[typing.Tuple[bytes, bytes]],
    ) -> typing.Tuple[typing.List[bytes], bool, bytes]:
        """Pick apart the pairs from our regex split and return the correct values."""
        regular_fields = []
        have_fraction = False
        fraction = b''

        for field_pair in field_pairs:
            if field_pair[0]:
                if field_pair[1]:
                    # They're both not zero length - that's an error
                    raise AssertionError('Both field_pair[0] and field_pair[1] are non-empty')
                else:
                    # The first is not zero length, the second is zero length
                    regular_fields.append(field_pair[0])
            else:
                if field_pair[1]:
                    # the first is zero length, the second is not zero length
                    if have_fraction:
                        raise AssertionError('Already have a fraction')
                    fraction = field_pair[1]
                    have_fraction = True
                else:
                    # they're both zero length - this is legal for !! - yield one or the other but not both
                    assert field_pair[0] == field_pair[1]
                    regular_fields.append(field_pair[0])

        return regular_fields, have_fraction, fraction

    def get_fields(self) -> None:
        """Read a block, chop it up into fields - taking into account any leftover partial field."""
        if isinstance(self.file_, int):
            tail_block: bytes = os.read(self.file_, self.blocksize)
        else:
            # assume we have a file-like object
            tail_block = self.file_.read(self.blocksize)

        if tail_block:
            self.at_eof = False
        else:
            self.at_eof = True

        if self.have_fraction:
            block = self.fraction + tail_block
            self.fraction = b''
            self.have_fraction = False
        else:
            block = tail_block

        field_pairs = re.findall(self.pattern, block)
        regular_fields, self.have_fraction, self.fraction = self.handle_field_pairs(field_pairs)

        # we put the fields in reverse order so we can repeatedly pop efficiently
        regular_fields.reverse()

        self.fields = regular_fields

    def sequence(self) -> typing.Iterator[bytes]:
        """Generate each field (line) in turn."""
        while True:
            if not self.fields:
                self.get_fields()
            while self.fields:
                yield self.fields.pop()
            if self.at_eof:
                if self.have_fraction:
                    yield self.fraction
                break

############################################################################
##### end UC Irvine portion of code ########################################

import sys
import os.path
import array
import json
import binascii
import argparse
import traceback
from adctk.publishers.http_publisher import HttpPublisher
from adctk.publishers.debug_file_publisher import DebugFilePublisher

class Blob:
    def __init__(self, index, databytes, timestamp, stype='s'):
        self.index = index; # record number in input, excluding magic
        self.data = databytes
        self.timestamp = timestamp ; # tuple (sec, usec)
        self.stype = stype

class BlobScanner:
    def add(self, blob):
        """ add a Blob to the scanner """
        raise ValueError("Blob scanner doesn't implement add")

class BlobReader:
    def __init__(self, path, blobScanner=None):
        """Parse DAT file named by path and matching aux files.
Apply blobScanner to each blob.

If blobScanner is not supplied, the entire data file gets loaded into memory
and the list self.blobs gets populated. This temporarily requires memory
size at least 2*(the DAT file size).

If blobScanner is supplied, individual blobs are loaded, scanned, and dropped.
"""
        if sys.byteorder != 'little':
            raise ValueError("this script does not work on bigendian platforms")
        self.filepath_name = path
        self.filetime = '0'
        self.filesuff = None
        self.time_least = 0 ; # least timestamp file entry for any blob
        self.time_minexp = 0 ; # least time expected based on filename timestamp
        self.blobs = []
        try:
            parts = path.split(".")
            self.filetime = parts[-1]
            self.time_minexp = int(self.filetime) - 70 ; # one minuteish margin for long delivery
            self.filesuff = parts[-2]
            self.fileprefix = ".".join(parts[0:len(parts)-2]) ; # strip .DAT.$timestamp
            #self.filetiming_name = ".".join([self.fileprefix, "TIMING", self.filetime])
            self.filetiming_name = ".".join([self.fileprefix, "noTIMING", self.filetime])
            self.filetiming_always__name = ".".join([self.fileprefix, "TIMING", self.filetime])
            self.filestype_name = ".".join([self.fileprefix, "TYPE", self.filetime])
            self.fileoffset_name = ".".join([self.fileprefix, "OFFSET", self.filetime])
        except:
            raise ValueError("bad path for BlobReader: %s. expecting *.DAT.$timestamp format" % path)

        self.datfile = open(self.filepath_name, "rb")
        self.stypefile = None
        try:
            self.stypefile = open(self.filestype_name, "rb")
        except:
            pass # BlobReader __init__ TYPE file not found is ok. assume data is json
        try:
            self.timingfile = open(self.filetiming_name, "rb")
        except:
            self.timingfile = None
        try:
            self.offsetfile = open(self.fileoffset_name, "rb")
        except:
            self.offsetfile = None
        self.stype = None
        self.timing = None
        self.offset = None
        if self.stypefile:
            self.stype = self.stypefile.read()
            self.stype_fsize = os.path.getsize(self.filestype_name)
            #self.stype.fromfile(self.stypefile, self.stype_fsize)
            magic = str(self.stype[0:7], 'utf-8')
            if magic != "blobtyp":
                raise ValueError("non-type data in %s." % self.filestype_name)
            self.stype = str(self.stype[8:], 'utf-8').strip()
        if self.timingfile:
            self.timing = array.array('Q')
            self.timing_fsize = os.path.getsize(self.filetiming_name)
            if (self.timing_fsize % 16) != 8:
                raise ValueError("timing data in %s is not a multiple of 16 bytes + 8." % self.filetiming_name)
            self.timing.fromfile(self.timingfile, self.timing_fsize//8)
            magic = self.timing[0] ; # "blobtim" as le binary expected
            if magic != 0x6d6974626f6c62:
                raise ValueError("non-timing data in %s %x." % (self.filetiming_name , magic))
            self.timing.pop(0)
        if self.offsetfile:
            self.offset = array.array('Q')
            self.offset_fsize = os.path.getsize(self.fileoffset_name)
            if (self.offset_fsize % 8) != 0:
                raise ValueError("offset data in %s is not a multiple of 8 bytes." % self.fileoffset_name)
            self.offset.fromfile(self.offsetfile, self.offset_fsize//8)
            magic = self.offset[0] ; # "bloboff" as le binary expected
            if magic != 0x66666f626f6c62:
                raise ValueError("non-offset data in %s." % self.fileoffset_name)
            self.offset.pop(0)
        if blobScanner:
            pass # BlobReader __init__ blobScanner argument not yet supported
        else:
            if not self.offset:
                self.blobs = self.datfile.read().split(b'\x00')[1:-1] ; # skip magic
                blen = len(self.blobs)
                while i > 0:
                    i -= 1
                    inp = self.blobs[i].decode('utf-8').rstrip()
                    if len(inp) < 2:
                        self.blobs.pop[i]
                # print("split on nul")
                # print("len 0 ", str(len(self.blobs[0])))
                # print("len last ", str(len(self.blobs[-1])))
                # print("len last-1 ", str(len(self.blobs[-2])))
            else:
                for i in readline0(self.datfile):
                    inp = i.decode('utf-8').rstrip()
                    if len(inp) >= 2:
                        self.blobs.append(inp)
                self.blobs.pop(0) ; # remove magic
                # print("readline-iter")
                # print("len 0 ", str(len(self.blobs[0])))
                # print("len last ", str(len(self.blobs[-1])))
                # print("len last-1 ", str(len(self.blobs[-2])))

def process_file(fn, url, completed_dir, retry_dir, error_dir, log_dir, retry, validate):
    """ @return maximum error code seen in add function calls. if > 1,
    file retry later may be useful."""
    br = BlobReader(fn)
    pf = PostFilter(br, url, completed_dir, retry_dir, error_dir, log_dir, validate)
    if br.timing:
        print("total timing: %d " % (len(br.timing)//2))
        # print("%g %s" % (0, br.timing[0]+1e-6*br.timing[1]))
        # print("%g %s" % (-1, br.timing[-4]+1e-6*br.timing[-3]))
    if br.offset:
        print("total offsets: %d " % len(br.offset))
        # print("%d %s" % (0, br.offset[0]))
        # print("%d %s" % (-1, br.offset[-1]))
    if br.stype:
        print("total types: %d " % len(br.stype))
        # print("%d %c" % (0, br.stype[0]))
        # print("%d %c" % (-1, br.stype[-1]))
    if len(br.blobs):
        print("total blobs: %d " % (len(br.blobs)))
        # print("%d %s" % (0, br.blobs[0]))
        # print("%d %s" % (-1, br.blobs[-1]))
    nb = len(br.blobs)
    if br.timing and len(br.timing)//2 != nb:
        print("timing data %d not same size as blobs %d" % (len(br.timing)//2, nb))
    if br.offset and len(br.offset) != nb:
        print("offset data %d not same size as blobs %d" % (len(br.offset), nb))
    if br.stype and len(br.stype) != nb:
        print("type data %d not same size as blobs %d" % (len(br.stype), nb))
    #
    maxerr = 0
    result = 0
    lineno = 0
    for i in range(0, len(br.blobs)):
        lineno = 0
        try:
            bl = br.blobs[i]
            if br.stype and i < len(br.stype):
                t = br.stype[i]
            else:
                # halfassed check for json string
                if bl[0] == '{' and bl[-1] == '}':
                    t = 'j'
                else:
                    t = 's'
            if br.timing:
                try:
                    ts = (br.timing[2*i], br.timing[2*i +1])
                except:
                    ts = (int(br.filetime), 0)
            else:
                    ts = (int(br.filetime), 0)
            b = Blob(i, bl, ts, t)
            result = pf.add(b)
            if result > maxerr:
                maxerr = result
        except Exception as error:
            print("Unable to process blob ", str(i), " ", type(error).__name__, "-", error)
            traceback.print_exception(error)
            print("Blob: ",bl)
    # relocate file
    if maxerr < 2:
        pf.move_files(fn, completed_dir, "DONE") ; # either completed or unpostable
    else:
        pf.move_files(fn, retry_dir, "RETRY")
    pf.finish()
    return maxerr

def handle_request_status(returned_data):
    status_code = returned_data.status_code
    if status_code < 200 or status_code > 300:
          logger.error(f"Status Code: {status_code}, Message: {returned_data.raw}")
          raise HttpStatusCodeError(status_code)
    logger.info(f"Posting successful with status Code: {status_code}")


class PostFilter(BlobScanner):
    def __init__(self, breader, url, completed_dir, retry_dir, error_dir, log_dir, validate):
        self.breader = breader 
        self.fn = breader.filepath_name
        self.bname = os.path.basename(self.fn)
        self.url = url
        self.retry_dir = retry_dir
        self.completed_dir = completed_dir
        self.error_dir = error_dir
        self.log_dir = log_dir
        self.validate = validate
        if retry_dir:
            os.makedirs(retry_dir, exist_ok=True)
            self.rname = "/".join((retry_dir, self.bname + ".retry"))
            try:
                self.rfile = open(self.rname, "w")
            except Exception as error:
                print("Unable to open retry file for ", self.bname, " in ", retry_dir, " err ",type(error).__name__, "-", error)
                self.rfile = None
        if completed_dir:
            os.makedirs(completed_dir, exist_ok=True)
            self.pname = "/".join((completed_dir, self.bname + ".completed"))
            self.pfile = open(self.pname, "w")
        if error_dir:
            os.makedirs(error_dir, exist_ok=True)
            self.ename = "/".join((error_dir, self.bname + ".errors"))
            self.efile = open(self.ename, "w")
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            self.lname = "/".join((log_dir, self.bname + ".log"))
            self.lfile = open(self.lname, "w")
        if url:
            if url[0] == "/":
                print("Writing to file", url);
                self.publisher = DebugFilePublisher(url)
            else:
                print("Writing to server", url);
                self.publisher = HttpPublisher(url)
        else:
            print("Writing to default server");
            self.publisher = HttpPublisher()

    def add(self, b):
        """@return 0 if published, 1 if message is not json, 2 if a retry may be needed"""
        if b.stype != 'j':
            # print("# non-json (%s) line %s" % (b.stype, b.data))
            if self.error_dir:
                print("{}\n".format(b.index), file=self.efile)
            if self.log_dir:
                print("non-json line at index ", str(b.index), ": ", b.data, file=self.lfile)
            return 1
        if self.validate:
            try:
                js = json.loads(b.data)
            except Exception as error:
                # print("# broken json line %d %s" % (b.index, b.data))
                if self.error_dir:
                    print("line {}: broken {}".format(b.index, b.data), file=self.efile)
                    print(error, file=self.efile)
                if self.log_dir:
                    print("invalid json line at index ", str(b.index), file=self.lfile)
                return 1
        status = self.publisher.publish_str(b.data)
        if type(status) is int:
            if status == 0:
                if self.completed_dir:
                    print("{}".format(b.index), file=self.pfile)
                return 0
            else:
                if self.retry_dir:
                    print("line {}: {}".format(b.index, status), file=self.rfile)
                return 2
        else:
            status_code = status.status_code
            if status_code in [200, 201, 202]:
                if self.completed_dir:
                    print("line {}: {}: {}".format(b.index, status_code, status.json()), file=self.pfile)
                if self.log_dir:
                    print("line {}: {}".format(b.index, status), file=self.lfile)
                return 0
            # everything else goes to retry until we understand better redirects, etc
            if self.retry_dir:
                print("line {}: {}".format(b.index, status_code), file=self.rfile)
            if self.log_dir:
                print("line {}: {}".format(b.index, status), file=self.lfile)
            return 2

    def finish(self):
        if self.log_dir:
            p = self.lfile.tell()
            self.lfile.close()
            if p == 0:
                os.unlink(self.lname)
        if self.completed_dir:
            p = self.pfile.tell()
            self.pfile.close()
            if p == 0:
                os.unlink(self.pname)
        if self.retry_dir:
            p = self.rfile.tell()
            self.rfile.close()
            if p == 0:
                os.unlink(self.rname)
        if self.error_dir:
            p = self.efile.tell()
            self.efile.close()
            if p == 0:
                os.unlink(self.ename)

    def move_files(self, datfile, destdir, disposition):
        if not os.path.exists(datfile) or not os.path.exists(destdir):
            if self.log_dir:
                print("Error: file {} or destination {} disappeared. Cannot move file.".format(datfile, destdir), file=self.lfile)
            return 1
        if os.path.dirname(datfile) == destdir:
            if self.log_dir:
                print("Warning: file {} and destination {} are same directory. Move request ignored.".format(datfile, destdir), file=self.lfile)
            return 0
        os.replace(datfile, os.path.join(destdir, os.path.basename(datfile)));
        # print("Debug: file {} moved to {}".format(datfile, destdir), file=self.lfile)
        otherfiles = [self.breader.filetiming_always__name, self.breader.filestype_name, self.breader.fileoffset_name]
        for f in otherfiles:
            if os.path.exists(f):
                os.replace(f, os.path.join(destdir, os.path.basename(f)));
                # print("Debug: file {} moved to {}".format(f, destdir), file=self.lfile)

def main():
    parser = argparse.ArgumentParser(description="Generate ADC web posts from ldms json stream files.")
    parser.add_argument("--url", default=None, help="where to post messages (or full path for debug output)")
    try:
        parser.add_argument("--validate", default=False, help="verify input is well-formed json before posting", action=argparse.BooleanOptionalAction)
        parser.add_argument("--retry", default=False, help="whether to publish the retry indices found in retry-dir files instead of all indices", action=argparse.BooleanOptionalAction)
    except:
        print("Need python with argparse.BooleanOptionalAction; usually py >= 3.9")
        return 1
    parser.add_argument("--completed-dir", default=None, help="where to put index numbers of messages that the server accepted that were not json.")
    parser.add_argument("--retry-dir", default=None, help="where to put index numbers and files of json messages the server was unavailable for or unhappy with.")
    parser.add_argument("--error-dir", default=None, help="where to log index numbers of json messages that provoked errors")
    parser.add_argument("--log-dir", default=None, help="log file directory")
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    if args.retry:
        print("ERROR: retry not implemented yet")
        sys.exit(1)
    if args.completed_dir and not os.path.isdir(args.completed_dir):
        print("ERROR: completed-dir %s missing" % args.completed_dir)
        sys.exit(1)
    if args.retry_dir and not os.path.isdir(args.retry_dir):
        print("ERROR: retry-dir %s is missing" % args.retry_dir)
        sys.exit(1)
    if args.error_dir and not os.path.isdir(args.error_dir):
        print("ERROR: error-dir %s is missing" % args.error_dir)
        sys.exit(1)
    if args.log_dir and not os.path.isdir(args.log_dir):
        print("ERROR: log-dir %s is missing" % args.log_dir)
        sys.exit(1)
    for f in args.files:
        if args.validate:
            print("with validation");
        print("Processing " + f)
        if not args.completed_dir:
            compdir = os.path.join(os.path.dirname(f),"COMPLETED")
        else:
            compdir = args.completed_dir
        if not args.retry_dir:
            retdir = os.path.join(os.path.dirname(f),"RETRY")
        else:
            retdir = args.retry_dir
        # Given the output naming conventions, retdir, compdir can be the same, though this might
        # make future glob processing really slow.
        # files cannot be processed in place unless it is a retry run (which is not yet implemented)
        maxerr = process_file(f, args.url, compdir, retdir, args.error_dir, args.log_dir, args.retry, args.validate)
        if maxerr < 2:
            print("Processed {}".format(f))
        else:
            print("Retry maybe needed for {} in {}: maxerr {}".format(os.path.basename(f), retdir, maxerr))

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

