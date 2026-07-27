# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
"""! @package docstring
builder module comment
"""

import json
import typing # pylint: disable=unused-import
import decimal
import copy
import platform
import sys
import os
import getpass
import uuid
import datetime
import time
import collections.abc
import subprocess
import pprint
import numpy

import adctk
#from adctk.log import logger
#from . import adc_version
#from . import adc_types
#from . import log

def add_test_types(prefix: str, builder: adctk.Builder):
    """! add an instance of all supported scalar types, with the supplied prefix scalars"""
    name = prefix + str.__name__
    val = "string"
    builder.add(name, val)
    for j,suff in [(0,"z"), (1, "one"), ("10000000000000000001","L")]:
        for t in (bool, int, float, decimal.Decimal):
            name = prefix + t.__name__ + "_" + suff
            val = t(j)
            builder.add(name, val)
    # vectory things
    builder.add(prefix + 'sset', set(["a","b"]))
    builder.add(prefix + 'iset', set([1,2]))
    builder.add(prefix + 'fset', set([1.1,2.1]))
    builder.add(prefix + 'Ffset', frozenset([1.1,2.1]))
    builder.add(prefix + 'slist', ["a","b"])
    builder.add(prefix + 'ilist', [1,2])
    builder.add(prefix + 'flist', [1.1,2.1])
    builder.add(prefix + 'stuple', ("a","b"))
    builder.add(prefix + 'ituple', (1,2))
    builder.add(prefix + 'ftuple', (1.1,2.1))
    # dictionary
    builder.add(prefix + 'dict', { "i":1, "f":1.1, "s": "complex(1.1,2.1)" } )
    # numpy
    ntypes = [
            numpy.bool,
            numpy.int8,
            numpy.int16,
            numpy.int32,
            numpy.int64,
            numpy.uint8,
            numpy.uint16,
            numpy.uint32,
            numpy.uint64,
            numpy.float16,
            numpy.float32,
            numpy.float64,
            numpy.complex64,
            numpy.complex128
        ]
    for dt in ntypes:
        builder.add("numpy_"+prefix + numpy.dtype(dt).name, numpy.zeros((2),\
                dtype=dt))
        builder.add("numpy_"+prefix + numpy.dtype(dt).name + "_2C",
                numpy.asarray([[1,2],[3,4]], dtype=dt))
        builder.add("numpy_"+prefix + numpy.dtype(dt).name + "_2F",
                numpy.asarray([[1,2],[3,4]], dtype=dt, order='F'))
    ntypes = [
            numpy.complex64,
            numpy.complex128,
            numpy.complex256
        ]
    for dt in ntypes:
        r = numpy.arange(1,13, dtype=dt)
        r.imag = r.real / 20.0
        builder.add("numpy_"+prefix + numpy.dtype(dt).name + "_Z",
                numpy.zeros((2), dtype=dt))
        builder.add("numpy_"+prefix + numpy.dtype(dt).name + "_2C",
                r.reshape((3,4), order='C', copy=True))
        builder.add("numpy_"+prefix + numpy.dtype(dt).name + "_2F",
                r.reshape((3,4), order='F', copy=True))


def main():
    bb = adctk.Builder.BasicBuilder("test_app_python")
    #print(bb)
    #print("did basicbuildeR")

    bb.add_gitlab_ci_section()
    env_extra=["SNLCLUSTER", "SNLNETWORK", "SNLSYSTEM", "SNLOS"]
    bb.add_slurm_section(env_extra)

    bb.add_host_section(all_hs=True)

    builddetails = adctk.Builder()
    bb.add_code_configuration_section(builddetails)

    vers = adctk.Builder()
    codedetails = adctk.Builder()
    bb.add_code_section("nemjoin", vers, codedetails)

    appdata = adctk.Builder()
    appdata.add("stage", "init")
    appdata.add("mydict", {"function":"test"})
    bb.add_app_data_section(appdata)

    modeldata = adctk.Builder()
    bb.add_model_data_section(modeldata)

    bb.add_memory_usage_section()

    statusdetails = adctk.Builder()
    bb.add_exit_data_section(11, "fault", statusdetails)

    # do we support mpi4py here, or provide example extension instead
    # bb.add_mpi_section(self, "world", communicator, local=True):

    bb.add_workflow_section()
    # pretend we got uuids of some spawned work processes
    kids = [str(uuid.uuid4()), str(uuid.uuid4())]
    bb.add_workflow_children(kids)

    bs = bb.serialize()
    #print(x)
    add_test_types("foo_", bb)
    pprint.pprint(bb._d)
    bs = bb.serialize()
    with open("foo_dump","w", encoding='utf-8') as f:
        print(bs, file=f)

if __name__ == "__main__":
    main()
