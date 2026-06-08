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
import array
import numpy

#from adctk.log import logger
from . import adc_version
from . import adc_types
from . import log

# pylint: disable=W0212
# pylint: disable=C0302

def get_modules(submodules=False):
    """!## Returns a dictionary of name:path pairs.
    Ignores builtin and binary modules.
    """
    mods = {}
    basemods = sys.stdlib_module_names
    for name, obj in sys.modules.items():
        if hasattr(obj, '__file__') and obj.__file__ is not None:
            path = os.path.abspath(obj.__file__)
            if not name in basemods:
                if submodules:
                    mods[name] = path
                    continue
                parts = name.split(".")
                for i in parts:
                    if i.startswith("_"):
                        break
                else: # for-else
                    mods[name] = path
    return mods

def get_libs():
    """! Returns a list of name for shared libs open
    input example to match:
    7ffff7dcd000-7ffff7dfc000 r-xp 00000000 00:17 134223798                  /usr/lib64/ld-2.28.so.*
    """
    pid = os.getpid()
    path = f"/proc/{pid}/maps"
    with open(path, "r", encoding='utf-8') as maps:
        lines = maps.readlines()
    libs = set()
    for e in lines:
        if " r-xp " in e and ".so" in e:
            libs.add(e.split()[-1])
    return list(sorted(libs))

def get_lscpu():
    """get stringified json from lscpu. The result is not cached (offline core changes)"""
    try:
        r = subprocess.run(["lscpu", "-J"],
                capture_output=True,
                text=True,
                check=True
        )
        return r.stdout
    except subprocess.CalledProcessError:
        return "{}"

_gpu_json: dict|None = None
def get_gpu_data():
    """get structure about gpus that can be jsonified"""
    global _gpu_json # pylint: disable=W0603
    if not _gpu_json is None:
        return _gpu_json
    _gpu_json = {}
    try:
        r = subprocess.run("lspci -vmm |grep -B1 -A 6 -i '3d controller'",
                shell=True,
                capture_output=True,
                text=True,
                check=True
        )
    except subprocess.CalledProcessError:
        # expected to fail if lspci not installed or gpu records not found
        return _gpu_json
    gpu_count = 0
    vendor: list[str] = []
    device: list[str] = []
    rev: list[str] = []
    numa_node: list[int] = [] # int32
    for line in r.stdout.splitlines():
        if line[0] == '-':
            continue
        cp = line.split(":", 1)
        name = cp[0]
        if name == "Class":
            cname = cp[1].strip()
            if cname == "3D controller":
                gpu_count += 1
            continue
        if name == "Vendor":
            vendor.append(cp[1].strip())
            continue
        if name == "Device":
            device.append(cp[1].strip())
            continue
        if name == "Rev":
            rev.append(cp[1].strip())
            continue
        if name == "NUMANode":
            numa_node.append(int(cp[1].strip()))
            continue
    sz = gpu_count
    if sz != len(vendor) or sz != len(device) or sz != len(rev) or sz != len(numa_node):
        log.logger.error("add_host_section:get_gpu_data: size mismatch")
        return _gpu_json
    _gpu_json["gpu_count"] = gpu_count
    gpu_list = []
    for i in range(0,gpu_count):
        gpu_block = {"gpu_number": i,
                "numa_node": numa_node[i],
                "vendor": vendor[i],
                "device": device[i],
                "rev": rev[i]
                }
        gpu_list.append(gpu_block)
    _gpu_json["gpulist"] = gpu_list
    return _gpu_json

_numa_json: dict|None = None
def get_numa_hardware():
    """get object tree for numa_hardware. do data collection exactly once"""
    global _numa_json # pylint: disable=W0603
    if _numa_json:
        return _numa_json
    _numa_json = {}
    try:
        r = subprocess.run("numactl -H",
                shell=True,
                capture_output=True,
                text=True,
                check=True
        )
    except subprocess.CalledProcessError:
        # expected to fail if lspci not installed or gpu records not found
        return _numa_json
    numa_node_count = 0
    cpulist: list[str] = []
    sizes: list[int] = [] # int64
    for line in r.stdout.splitlines():
        if line[0] == '-':
            continue
        cp = line.split(":", 1)
        name = cp[0]
        if  name == "available":
            numa_node_count = int(cp[1].split()[0])
            continue
        if name[-4:] == "cpus":
            cpulist.append(cp[1].strip())
            continue
        if name[-4:] == "size":
            i = cp[1].split()[0]
            sizes.append(int(i))
            continue
        if name[-4:] == "nces":
            # distances
            break
    sz = numa_node_count
    if not sz or len(sizes) != sz or len(cpulist) != sz:
        return _numa_json
    node_list = []
    for i in range(0,numa_node_count):
        node_list.append({"node_number": i,
                "node_megabytes": sizes[i],
                "cpu_list": cpulist[i]
                })
    _numa_json["node_list"] = node_list
    return _numa_json

_midata = {}
def get_meminfo(n, update=False):
    """! get fields that would appear in the procps 'free' utility.  """
    if update or len(_midata) == 0:
        with open("/proc/meminfo","r", encoding='utf-8') as meminfo:
            lines = meminfo.readlines()
        for i in lines:
            name,val = i.split(":")
            _midata[name.strip()] = int(val.split()[0].strip())
        _midata["MemUsed"] = _midata["MemTotal"] - _midata["MemFree"]
        _midata["SwapUsed"] = _midata["SwapTotal"] - _midata["SwapFree"]
        _midata["CachedAll"] = _midata["Cached"] + _midata["SReclaimable"]
        if _midata["MemAvailable"] > _midata["MemTotal"]:
            _midata["MemAvailable"] = _midata["MemFree"]
            # work around container misreporting.
            # documented in procps utility 'free'
    if n in _midata:
        return _midata[n]
    return 0

class APISequenceError(Exception):
    """! Exception raised when functions in an api are called out of sequence"""
    def __init__(self, msg):
        self.message = msg
        super().__init__(self.message)

# pylint: disable=R0904
class Builder():
    """! ADC Toolkit message and subsection construction class.

    Use of the Builder ensures that adctk messages:
    - meet the schema definitions for commonly defined sections and the required header.
    - capture the correct data typing information for application-defined fields.
    Presently, some of the functions only work as intended on Linux platforms, as
    they examine /proc.

    @ingroup builder_impl
    """
    def __init__(self):
        self._sections: dict[Builder]  = {}
        # dict of key/values defined by add directly on this builder
        self._d: dict[dict] = {}

    API_VERSION = adc_version.AdcVersion()._dict()

    def _set_attr(self, name, value):
        self._d[name] = value

    def _get_attr(self, name):
        if name in self._d:
            return self._d[name]
        return None

    def _find_path(self, obj, path):
        """look up value in nested string-named structures using /-delimited path"""
        parts = path.strip("/").split("/")
        ### print(f"DEB: looking for parts {parts} from path {path} in {obj}")
        for p in parts:
            if p in obj:
                obj = obj[p]
            else:
                return None
        return obj

    def get_value(self, path_full: str) -> adc_types.Field:
        """! @brief get the existing named nested field in the builder.

            @param path_full a simple json path such as /a/b/c which resolves to
                   a value added via one of the add* functions.
            @return the field description, with kt==k_none if not found.
            If the value was not set via this interface, k_none may be returned.
            Leading / is optional in path_full.

        """
        field = adc_types.Field()
        path = path_full.strip('/')
        ### print(f"DEB: searching for {path_full} ({path}) in {json.dumps(self._d)} and sections {self._sections.keys()}")
        pos = path.find('/')
        if pos == -1:
            name = path
        else:
            name = path[:pos]
        ### print(f"DEB: searching for name {name}")
        kt = self._kind(name)
        ### print(f"DEB: got kt {kt}")
        child = path[pos:]
        jit = None
        match kt:
            case adc_types.KeyType.k_none:
                ### print(f"DEB: none {adc_types.KeyType.k_none}")
                ### print(f"DEB: return empty field; 0")
                return field
            case adc_types.KeyType.k_section:
                ### print(f"DEB: section {adc_types.KeyType.k_section}")
                ### print(f"DEB: recurse to section {name}")
                return self._sections[name].get_value(child)
            case adc_types.KeyType.k_value:
                ### print(f"DEB: value {adc_types.KeyType.k_value}")
                jit = self._d[name]
                if not jit:
                    ### print(f"DEB: return empty field; 1")
                    return field
        field.kt = kt
        if isinstance(jit, dict):
            ### print(f"DEB: dict {jit}")
            v = None
            if "value" in jit:
                v = jit["value"]
            if "type" in jit and isinstance(jit["type"], str):
                type_name = jit["type"]
            else:
                return field # not defined by api
            if len(type_name):
                if "container_type" in jit:
                    c = jit["container_type"]
                else:
                    c = None
                st = adc_types.scalar_from_json(type_name)
                field.st = st
                field.data = v
                if c:
                    field.container = c
                ### print(f"DEB: return populated field; 2")
                return field
        if isinstance(jit, str):
            field.st = adc_types.ScalarType.cp_cstr
            field.data = jit
            ### print(f"DEB: return loose field; 3 str")
            return field
        if isinstance(jit, bool):
            field.st = adc_types.ScalarType.cp_bool
            field.data = jit
            ### print(f"DEB: return loose field; 4 bool")
            return field
        if isinstance(jit, float):
            field.st = adc_types.ScalarType.cp_f64
            field.data = jit
            ### print(f"DEB: return loose field; 5 float")
            return field
        if isinstance(jit, int):
            if adc_types.fits_int64(jit):
                field.st = adc_types.ScalarType.cp_int64
                field.data = jit
                ### print(f"DEB: return populated field; 6 int")
                return field
            if adc_types.fits_uint64(jit):
                field.st = adc_types.ScalarType.cp_uint64
                field.data = jit
                ### print(f"DEB: return loose field; 7 uint")
                return field
            field.st = adc_types.ScalarType.cp_number_str
            field.data = jit
            ### print(f"DEB: return loose field; 8 bigint")
            return field
        if isinstance(jit, decimal.Decimal):
            field.st = adc_types.type_to_scalar(type(jit), jit)
            field.data = jit
            ### print(f"DEB: return loose field; 9 Decimal")
            return field
        field.data = jit
        field.st = adc_types.type_to_scalar(type(jit), jit)
        ### print(f"DEB: return populated field; 10 generic")
        return field

    def get_value_string(self, path: str):
        """! @brief get the existing named nested scalar string value.

        @param path a simple json path such as /a/b/c which resolves to
               a value added via one of the add* functions.
        @return None if the path is not matched or is not a string of some sort.
        """
        field = self.get_value(path)
        if (not field or field.kt != adc_types.KeyType.k_value or
                (field.container and len(field.container))):
            return None
        match field.st:
            case adc_types.ScalarType.cp_cstr  | \
                adc_types.ScalarType.cp_json_str  | \
                adc_types.ScalarType.cp_yaml_str  | \
                adc_types.ScalarType.cp_xml_str  | \
                adc_types.ScalarType.cp_json  | \
                adc_types.ScalarType.cp_path  | \
                adc_types.ScalarType.cp_number_str:
                return field.data
            case _:
                return None

    def get_value_int64(self, path: str):
        """! @brief get the existing named nested scalar int64-equivalent value.

        @param path a simple json path such as /a/b/c which resolves to
               a value added via one of the add* functions.
        @return None if the path is not matched or int64_max if it is
               not int64 compatible.
        """
        field = self.get_value(path)
        if not field or field.kt != adc_types.KeyType.k_value or len(field.data) != 1:
            return None
        i = numpy.iinfo(numpy.int64).max
        match field.st:
            case adc_types.ScalarType.cp_bool:
                if field.data:
                    return 1
                return 0
            case adc_types.ScalarType.cp_char32  | \
                adc_types.ScalarType.cp_char16  | \
                adc_types.ScalarType.cp_char:
                return ord(field.data)
            case adc_types.ScalarType.cp_int8  | \
                adc_types.ScalarType.cp_int16  | \
                adc_types.ScalarType.cp_int32  | \
                adc_types.ScalarType.cp_int64:
                return field.data
            case _:
                return i

    def get_value_uint64(self, path: str):
        """! @brief get the existing named nested scalar uint64-equivalent value.

        @param path a simple json path such as /a/b/c which resolves to
               a uint64-equivalent value added via one of the add* functions.
        @return None if the path is not matched or uint64_max if it is
               not uint64 compatible.
        """
        field = self.get_value(path)
        if not field or field.kt != adc_types.KeyType.k_value or len(field.data) != 1:
            return None
        i = numpy.iinfo(numpy.uint64).max
        match field.st:
            case adc_types.ScalarType.cp_bool:
                if field.data:
                    return 1
                return 0
            case adc_types.ScalarType.cp_char32  | \
                adc_types.ScalarType.cp_char16  | \
                adc_types.ScalarType.cp_char:
                return ord(field.data)
            case adc_types.ScalarType.cp_uint8  | \
                adc_types.ScalarType.cp_uint16  | \
                adc_types.ScalarType.cp_uint32  | \
                adc_types.ScalarType.cp_uint64:
                return field.data
            case _:
                return i

    def __json__(self):
        print("CALLED __json__?")
        return self._flatten()

    def _flatten(self, depth=0) -> dict:
        """! @brief Get a dictionary tree-copy constructed from keys and sections.

         Changes made to the returned dictionary are not reflected in
         the Builder instance.
        """
        d = copy.deepcopy(self._d)
        for name,section in self._sections.items():
            d[name] = section._flatten(depth=depth+1)
        return d

    def add_header_section(self, application_name: str):
        """! @brief Create or replace the 'header' section using application_name.

        To reuse a Builder object for a new message, call add_header_section on it again
        before sending it to publish again."""
        header = Header(application_name)
        self.add_section("header", header)

    # arg names map 1:1 to c++ bit flags
    # pylint: disable=R0913 disable=R0917
    def add_host_section(self, osinfo=False, ramsize=False,
                        env=False, cpu=False, gpu=False, numa=False, all_hs=False):
        """! Add the 'host' section, with optional subgroups of properties.

        builder.add_host_section(os=True, ramsize=True, env=True, cpu=True, gpu=True, numa=True)
        is equivalent to builder.add_host_section(all_hs=True)
        """
        if all_hs:
            osinfo=True
            ramsize=True
            env=True
            cpu=True
            gpu=True
            numa=True
        host = Host(osinfo, ramsize, env, cpu, gpu, numa)
        self.add_section("host", host)

    def add_app_data_section(self, app_data: 'Builder'):
        """! Create the "app_data" section with data defined by the application writer.

            It is recommended that any relationship identifiers to previous jobs or higher
            level environments goes in app_data, unless supported by add_workflow_section,
            add_slurm_section or other normalized sections.

            Example:
             app_data = Factory.get_builder();
             app_data.add("saw_id", getenv("SAW_WORKFLOW_ID");
             builder.add_app_data_section(app_data)
        """

        if isinstance(app_data, Builder):
            self.add_section("app_data", app_data)
        else:
            raise TypeError("argument app_data must be of type adctk.Builder")

    def add_model_data_section(self, model_data: 'Builder'):
        """!  @brief populate application run-time physics (re)configuration or
            result to "model_data" section.
            For example initial or changes in mesh or particle decomp go here.
        """
        if isinstance(model_data, Builder):
            self.add_section("model_data", model_data)
        else:
            raise TypeError("argument model_data must be from type adctk.Builder")

    def add_code_section(self, tag: str, version: 'Builder',
                        code_details: 'Builder|None' = None):
        """! Add the 'code' section, with user-specified version subsection and
        optional code_details section describing things which do not normally
        vary with invocation.

        Automatic contents include tag, base program, full path, loaded modules
        and shared libraries.
        Shared libraries detected may vary with invocation if LD_LIBRARY_PATH
        or related environment settings change.
        """
        fullpath = sys.executable
        basename = os.path.basename(fullpath)
        libs = get_libs()
        mods = get_modules()
        if code_details:
            if isinstance(code_details, Builder):
                d = code_details._flatten()
                c = { "name": tag,
                        "program": basename,
                        "path": fullpath,
                        "version": version._flatten(),
                        "libs": libs,
                        "modules": mods,
                        "details": d }
            else:
                raise TypeError("argument status_details must be from type adctk.Builder")
        else:
            c = { "name": tag,
                    "program": basename,
                    "path": fullpath,
                    "version": version._flatten(),
                    "libs": libs}
        self.add_section("code", c)

    def add_code_configuration_section(self, build_details: 'Builder'):
        """ @brief Populate build/install "configuration" information such as options enabled

            @param build_details option list.
        """
        if build_details:
            if isinstance(build_details, Builder):
                self.add_section("code_configuration", build_details)
            else:
                raise TypeError("argument build_details must be from type adctk.Builder")
        else:
            raise TypeError("argument build_details must not be None")

    def add_exit_data_section(self, return_code: 'int|str',
                            status: str, status_details: 'Builder|None' = None):
        """! @brief populate "exit_data" section with return code and status string
             & user provided details.

             @param return_code numeric value of exit status
             @param status one-line summary of the execution
             @param status_details any final or summary results of interest to application
             users or developers.
        """
        if status_details:
            if isinstance(status_details, Builder):
                d = status_details._flatten()
                ed = { "return_code": str(return_code), "status": status, "details": d }
            else:
                raise TypeError("argument status_details must be from type adctk.Builder")
        else:
            ed = { "return_code": str(return_code), "status": status }
        self.add_section("exit_data", ed)

    def add_memory_usage_section(self):
        """! @brief Populate "memory_usage" section with current host /proc/meminfo data
            in the style of free(1).

            Values included are:
            mem_total mem_used mem_free mem_shared
            mem_buffers mem_cache mem_available
            swap_total swap_used swap_free
        """
        memory = Memory()
        self.add_section("memory_usage", memory)

    def get_section(self, name: str) -> 'Builder|None':
        """! @brief get the existing named section.

            @return the section, or an empty pointer if it doesn't exist.
        """
        if name in self._sections:
            return self._sections[name]
        return None

    def get_section_names(self) -> 'list[str]':
        """! @brief Get the names of sections

             @return list of names, or an empty list.
         """
        return self._sections.keys()

    def add_mpi_section(self, name, communicator, rank:bool = False,
                        size:bool = False, mpi_name:bool = False,
                        hostlist:bool = False, rank_host:bool = False,
                        ver:bool = False, lib_ver:bool = False,
                        mpiall:bool = False, local:bool = False):
        """! Unimplemented: python with mpi is not yet supported."""
        if mpiall:
            local = True
            hostlist = True
            rank_host = True
        if local:
            rank = True
            size = True
            mpi_name = True
            ver = True
            lib_ver = True
        b = Builder()
        # fixme: shall we assume add_mpi_section items from mpi4py communicator?
        # check that communicator is the type from mpi4py.
        # default to 1-rank assumptions
        if rank:
            b._set_attr("mpi_rank", 0)
        if size:
            b._set_attr("mpi_size", 1)
        if mpi_name:
            b._set_attr("mpi_name", "unimplemented")
        if ver:
            # major.minor
            b._set_attr("mpi_version", "unimplemented")
        if lib_ver:
            # vmajor.vminor.vrelease...
            b._set_attr("mpi_library_version", "unimplemented")
        if rank_host:
            b._set_attr("mpi_rank_host", [])
        if hostlist:
            b._set_attr("mpi_hostlist", [])
        self.add_section("mpi_comm_" + name, b)

    def add_gitlab_ci_section(self):
        """! @brief Add gitlab_ci environment variable dictionary.

            The section added is named "gitlab_ci".
            The variables collected from env() are:
            - ci_runner_id
            - ci_runner_version
            - ci_project_id
            - ci_project_name
            - ci_server_fqdn
            - ci_server_version
            - ci_job_id
            - ci_job_started_at
            - ci_pipeline_id
            - ci_pipeline_source
            - ci_commit_sha
            - gitlab_user_login

            Where the values are strings from the corresponding env() values.
        """
        gitlab_ci_names = [
            "CI_RUNNER_ID",
            "CI_RUNNER_VERSION",
            "CI_PROJECT_ID",
            "CI_PROJECT_NAME",
            "CI_SERVER_FQDN",
            "CI_SERVER_VERSION",
            "CI_JOB_ID",
            "CI_JOB_STARTED_AT",
            "CI_PIPELINE_ID",
            "CI_PIPELINE_SOURCE",
            "CI_COMMIT_SHA",
            "GITLAB_USER_LOGIN"
        ]
        b = Builder()
        for i in gitlab_ci_names:
            v = os.getenv(i)
            if v:
                b._set_attr(i.lower(), v)
            else:
                b._set_attr(i.lower(), "")
        self.add_section("gitlab_ci", b)

    def add_workflow_section(self, wfid: str|None =None, parent: str|None =None,
                            children: list[str]|str|None =None):
        """! @brief add data from adc_wfid_ environment variables.

            The section name is "adc_workflow".

            The env variables collected are:
            wfid: ADC_WFID
            wfid_parent: $ADC_WFID_PARENT
            wfid_path: $ADC_WFID_PATH

            The suggested format of an adc workflow identifier (wfid) is as:
                uuid -v1 -F STR
            run at the appropriate scope.
            For example, when starting numerous processes with mpi under slurm,
            in the sbatch script before launching anything else do:
                export ADC_WFID=$(uuid -v1 -F STR)
            and then make sure it gets propagated to all the processes via the launch
            mechamism. This ties all the messages from mpi ranks together in adc.

            Where a workflow parent (such as an agent launching multiple slurm jobs)
            can,
                export ADC_WFID_PARENT=$(uuid -v1 -F STR)
            and then make sure this value is propagated to the slurm environments.

            Where possible (requires coordination at all workflow levels)
                export ADC_WFID_PATH=(higher_level_wfid_path)/$ADC_WFID
            the entire task hierarchy identifier can be collected.
        """

        b = Builder()
        for n,e in [
                ( "wfid", "ADC_WFID"),
                ( "wfid_parent", "ADC_WFID_PARENT"),
                ( "wfid_path", "ADC_WFID_PATH")
            ]:
            v = os.getenv(e)
            if v:
                b._set_attr(n, v)
            else:
                b._set_attr(n, "")
        cenv = os.getenv("ADC_WFID_CHILDREN")
        if cenv:
            echildren = list(filter(None,cenv.split(":")))
            b._set_attr("wfid_children", echildren)
        # now override from arguments anything found in the environment
        if children:
            if isinstance(children, list):
                clist = []
                for i in children:
                    if isinstance(i, str) and len(i):
                        clist.append(i)
                b._set_attr("wfid_children", echildren)
            if isinstance(children, str):
                echildren = list(filter(None, children.split(":")))
                b._set_attr("wfid_children", echildren)
        if parent and len(parent):
            b._set_attr("wfid_parent", parent)
        if wfid and len(wfid):
            b._set_attr("wfid", parent)
        self.add_section("adc_workflow", b)

    def add_workflow_children(self, child_uuids: collections.abc.Iterable[str]):
        """! @brief Add list of child uuids to "adc_workflow" section
            after add_workflow_section has been called. This call is optional.

            This call may be repeated if necessary, incrementally building the child list.
            wfid_children: [ user defined list of ids ]

            Where a workflow can track its immediate children, it may substantially
            improve downstream workflow analyses if the child items can be captured.
            The result appears in the resulting json as
                wfid_children: $ADC_WFID_CHILDREN
        """
        wsec = self.get_section("adc_workflow")
        if wsec:
            cl = wsec._get_attr("wfid_children")
            if cl:
                if isinstance(cl, list):
                    for i in child_uuids:
                        if isinstance(i, str) and not i in cl:
                            cl.append(i)
                    wsec._set_attr("wfid_children", cl)
                else:
                    raise TypeError("adc_workflow.wfid_children found but isn't an array (?)")
            else:
                cl = []
                for i in child_uuids:
                    if isinstance(i, str) and not i in cl:
                        cl.append(i)
                wsec._set_attr("wfid_children", cl)
        else:
            raise APISequenceError("add_workflow_children called before add_workflow")

    def add_slurm_section(self, output_vars: collections.abc.Iterable[str]|None = None):
        """! @brief Add slurm output environment variable dictionary elements.

            The section added is named "slurm".

            The variables collected from env() are:
            - cluster: SLURM_CLUSTER_NAME
            - job_id: SLURM_JOB_ID
            - num_nodes: SLURM_JOB_NUM_NODES
            - dependency: SLURM_JOB_DEPENDENCY

            Where the values are strings from the corresponding env() values.
        """
        b = Builder()
        for n,e in [
            ( "cluster", "SLURM_CLUSTER_NAME"),
            ( "job_id", "SLURM_JOB_ID"),
            ( "num_nodes", "SLURM_JOB_NUM_NODES"),
            ( "dependency", "SLURM_JOB_DEPENDENCY") ]:
            v = os.getenv(e)
            if v:
                b._set_attr(n, v)
            else:
                b._set_attr(n, "")
        for e in output_vars:
            if isinstance(e,str):
                v = os.getenv(e)
                if v:
                    b._set_attr(e, v)
                else:
                    b._set_attr(e, "")
        self.add_section("slurm", b)

    def add_section(self, name: str,
                section: 'Builder|collections.abc.Mapping[str,...]'):
        """! @brief Add or replace a user-defined, named section.

        Using a string-keyed dictionary instead of a Builder is allowed but is
        not recommended for numeric or path or markup data because
        this omits variable type information needed for correct extraction in
        languages other than python.
        An exception occurs replacing a key/value pair with a section is attempted.
        """
        if name in self._d:
            raise TypeError("attempting to replace a key/value with a section. Not Allowed. {}: {}".format(name, section))
        if isinstance(section, Builder) and isinstance(name, str):
            self._sections[name] = section
        elif isinstance(section, collections.abc.Mapping):
            b = Builder()
            for i,j in section.items():
                if isinstance(i, str):
                    if isinstance(j,Builder):
                        b.add_section(i, j)
                    else:
                        b._set_attr(i,j)
            self._sections[name] = b
        else:
            raise TypeError("arguments name,section must be of types str," +
                f"adctk.Builder,Mapping not {type(name)},{type(section)}")

    def serialize(self) -> str:
        """! @brief get json string of the builder.

        Items within builder must already be json compatible; custom
        encoders/decoders for json to handle numpy and complex correctly
        are not provided.
        """
        p = self._flatten()
        # pprint.pprint(self)
        return json.dumps(p)

    # pylint: disable=R0914 disable=R0915 disable=R0912
    def add(self, name: str, value: any, value_type=None):
        """! @brief add named item and its datatype information to the builder.

         Supported value types are
         - built-ins: int, float, complex, bool, str
         - standard:  decimal, numpy.ndarray (as 1-d list and dimensions if
          originally multidimensional)
         - character types:  Python often wraps non-python applications; where
          the developer knows a python string represents a single character,
          the optional value_type parameter can be passed to disambiguate.
          Supported value_type options are (signed)"char",(unsigned)"char8",
          (signed)"char16",(signed)"char32"
         - lower-precision types:  Python often wraps non-python applications; where
          the developer knows a python number represents something smaller than
          64-bit, the optional value_type parameter can be passed to disambiguate.
          Supported numeric value_type options are int8, int16,int32, uint8,
          uint16, uint32,  f32.
          (signed)"char16",(signed)"char32"
         - any value not explicitly supported which can be converted to a
          json string will be.

         Any value not explicitly supported which cannot be converted to
         a json string will be silently ignored.

         Notes:
         - int is represented as type int64 if possible and number_str if too big.
    
        """
        if name is None or value is None:
            raise ValueError("add: name and value cannot be None")
        t = type(value)
        print(f"\nadd {name} {t}")
        if isinstance(t, Builder):
            self.add_section(name, value)
            return
        if isinstance(value, bool):
            self._set_attr(name,
                    { "type": adc_types.scalar_to_json(adc_types.type_to_scalar(t)),
                        "value": value })
            return
        if isinstance(value, float):
            if not value_type:
                ### print(f"DEB: float {value}")
                self._set_attr(name,
                        { "type": adc_types.scalar_to_json(adc_types.type_to_scalar(t, value)),
                            "value": value })
                return
            if value_type in ["f32", "f64"]:
                self._set_attr(name,
                        { "type": adc_types.scalar_to_json(adc_types.scalar_from_json(value_type)),
                            "value": value })
                return
            raise ValueError("add: value_type option for float value must be f32 or f64")
        if isinstance(value, str):
            if not value_type:
                ### print(f"DEB: value_type string")
                self._set_attr(name,
                        { "type": adc_types.scalar_to_json(adc_types.type_to_scalar(t)),
                            "value": value })
                return
            if value_type in ["char", "char16", "char32", "char8"]:
                ### print(f"DEB: value_type {value_type}")
                self._set_attr(name,
                        { "type": adc_types.scalar_to_json(adc_types.scalar_from_json(value_type)),
                            "value": value })
                return
            raise ValueError("add: value_type option for str value must be one of: char, char16, char32, char8")
        if t == complex:
            self._set_attr(name,
                    { "type": adc_types.scalar_to_json(adc_types.type_to_scalar(t, value)),
                        "value": [value.real, value.imag] })
            return
        if t == int:
            if not value_type:
                jtname = adc_types.scalar_to_json(adc_types.type_to_scalar(int, value))
                if adc_types.fits_int64(value):
                    self._set_attr(name, { "type": jtname, "value": value })
                else:
                    self._set_attr(name, { "type": jtname, "value": str(value) })
                return
            if value_type in ["int16", "int32", "int8", "uint8", "uint16", "uint32", "int64"]:
                ### print(f"DEB: value_type {value_type}")
                self._set_attr(name,
                        { "type": adc_types.scalar_to_json(adc_types.scalar_from_json(value_type)),
                            "value": value })
                return
            raise ValueError("add: value_type option for int value must be one of: int16, int32, int8, uint8, uint16, uint32, int64")
        if isinstance(value, decimal.Decimal):
            jtname = adc_types.scalar_to_json(adc_types.type_to_scalar(t))
            self._set_attr(name, { "type": jtname, "value": str(value) })
            return
        if type(value).__module__ == numpy.__name__:
            st = adc_types.scalar_from_numpy(value.dtype)
            if st == adc_types.ScalarType.cp_none:
                raise ValueError(f"add: unknown scalar type for {value.dtype}")
            jtype = adc_types.scalar_to_json(st)
            if isinstance(value, numpy.ndarray):
                if value.flags['F_CONTIGUOUS']:
                    rowcol = 'F'
                else:
                    rowcol = 'C'
                shape = list( value.shape )
                list_value = adc_types.get_list_format(value, st)
                self._set_attr(name, {"type": "array_"+jtype,
                    "value": list_value, "container_type": "ndarray", "order": rowcol,
                    "shape": shape})
                return
            match value:
                case numpy.float64() | numpy.float32() | numpy.float16():
                    self._set_attr(name, {"type": jtype, "value": \
                        float(numpy.format_float_scientific(value, unique=True)) , "BUG":"TRUE"} )
                case numpy.int64() | numpy.int32() | numpy.int16() | numpy.int8() | \
                     numpy.uint32() | numpy.uint16() | numpy.uint8() |numpy.bool():
                    self._set_attr(name, {"type": jtype, "value": int(value) } )
                case numpy.bool():
                    self._set_attr(name, {"type": jtype, "value": bool(value) } )
                case numpy.str_() | numpy.bytes_():
                    self._set_attr(name, {"type": jtype, "value": value.tostring() } )
                    # fixme numpy str_, bytes_ conversion may need work.
                case numpy.uint64():
                    self._set_attr(name, {"type": jtype, "value": value.tostring() })
                case numpy.complex64() | numpy.complex128():
                    self._set_attr(name, {"type": jtype, "value": [ \
                         float(numpy.format_float_scientific(value.real, unique=True)), \
                         float(numpy.format_float_scientific(value.imag, unique=True))] })
                case numpy.complex192() | numpy.complex256():
                    self._set_attr(name, {"type": jtype, "value": [ \
                        numpy.format_float_scientific(value.real, unique=True), \
                        numpy.format_float_scientific(value.imag, unique=True)] } )
                case _:
                    msg = f"add: item {name} contains unserializable numpy type." + \
                            f"({type(value)})" + \
                            "  consider add() on a type conversion to work around this."
                    print(dir(type(value).__module__ ))
                    print(dir( numpy.__name__))
                    print(dir(value))
                    raise ValueError(msg)
            return # from all matched setattr
        if isinstance(value, list|collections.abc.Set|tuple):
            depth = 0
            maxdepth=[0]
            it = adc_types.get_common_scalar(value, depth, maxdepth)
            pname = value.__class__.__name__
            if it != adc_types.ScalarType.cp_none:
                list_value = adc_types.get_list_format(value, it)
                if maxdepth[0] == 1:
                    cname = "vector"
                    pname = value.__class__.__name__
                    jt = "array_" + adc_types.scalar_to_json(it)
                    self._set_attr(name, {"type": jt,
                        "value": list_value, "container_type": cname, "python": pname})
                    return
                # this isn't documented in json spec; fixme-spec
                cname = "nested_list"
                major = "row" # fixme: use in setattr call? need test cases
                self._set_attr(name, {"type": adc_types.scalar_to_json(it),
                    "value": list_value, "container_type": cname, "major": major})
                return
            # if we had a 'warn-untyped-items' mode, it would warn here.
            try:
                tmp = json.dumps(value)
                self._set_attr(name,
                        {"type": adc_types.scalar_to_json(adc_types.ScalarType.cp_json),
                        "value": tmp, "python": pname})
                return
            except TypeError as orig_exception:
                msg = f"add: item {name} contains unserializable types." + \
                        " Use add() on individual elements to work around this."
                raise ValueError(msg) from orig_exception
        elif isinstance(value, array.array):
            it = adc_types.typecode_to_scalar(value)
            if it != adc_types.ScalarType.cp_none:
                list_value = value.tolist()
                if it == adc_types.ScalarType.cp_number_str:
                    list_value = [str(v) for v in list_value]
                cname = "vector"
                pname = f"array.array('{value.typecode}')"
                jt = "array_" + adc_types.scalar_to_json(it)
                self._set_attr(name, {"type": jt,
                    "value": list_value, "container_type": cname, "python": pname})
                return
            msg = f"add: array.array {name} contains unserializable types. how?!"
            raise ValueError(msg)
        else:
            # if we had a 'warn-untyped-items' mode, it would warn here.
            ### print(f"DEB: warn-untyped-items: {name}")
            pname = value.__class__.__name__
            try:
                tmp = json.dumps(value)
                self._set_attr(name,
                        {"type": adc_types.scalar_to_json(
                            adc_types.ScalarType.cp_json),
                        "value": value, "python": pname})
                return
            except TypeError as orig_exception:
                msg = f"add: item {name} contains unserializable types." + \
                        " Use add() on individual elements to work around this."
                raise ValueError(msg) from orig_exception

    def add_path(self, name, path:str ):
        """! Add string file path."""
        if path is None or isinstance(path, str):
            self._set_attr(name,
                    { "type": adc_types.scalar_to_json(adc_types.ScalarType.cp_path),
                    "value": path })
        else:
            raise ValueError("add_path: path must be a string")

    def add_json_string(self, name: str, js: str ):
        """! Add stringified json"""
        if js is None or isinstance(js, str):
            self._set_attr(name,
                    { "type": adc_types.scalar_to_json(
                        adc_types.ScalarType.cp_json_str),
                    "value": js })
        else:
            raise ValueError("add_json_string: json must be a string")

    def add_yaml_string(self, name: str, yaml: str ):
        """! Add stringified yaml"""
        if yaml is None or isinstance(yaml, str):
            self._set_attr(name,
                    { "type": adc_types.scalar_to_json(
                        adc_types.ScalarType.cp_yaml_str),
                    "value": yaml })
        else:
            raise ValueError("add_yaml_string: yaml must be a string")

    def add_xml_string(self, name: str, xml: str ):
        """! Add stringified xml"""
        if xml is None or isinstance(xml, str):
            self._set_attr(name,
                    {"type": adc_types.scalar_to_json(adc_types.ScalarType.cp_xml_str),
                    "value": xml })
        else:
            raise ValueError("add_xml_string: xml must be a string")

    def add_number_string(self, name: str, dec: decimal.Decimal ):
        """! Add stringified number of arbitrary precision"""
        decstr = str(dec)
        self._set_attr(name,
                    {"type": adc_types.scalar_to_json(adc_types.ScalarType.cp_number_str),
                    "value": decstr })

    def add_epoch(self, name, epoch: int):
        """! add unix epoch seconds (gettimeofday)"""
        self._set_attr(name, { "type": adc_types.scalar_to_json(
            adc_types.ScalarType.cp_epoch),
            "value": epoch })

    def add_mime(self, name:str, mime_type:str, encoding:str, file_name:str, data: str):
        """! @brief add a string encoded object (e.g. image)

            @param name the name in the message of this field
            @param mime_type e.g. "image/png"
            @param encoding e.g. "base64"
            @param file_name e.g. "origin.png"
            @param data character array of the encoded object.
        """
        if not name or not mime_type or not encoding or not file_name or not data:
            return
        self._set_attr(name, { "type": adc_types.scalar_to_json(
            adc_types.ScalarType.cp_mime),
            "mimetype": mime_type,
            "encoding": encoding,
            "filename": file_name,
            "value": data })


    def add_array_typed_string( self, name, st: adc_types.ScalarType,
            strings: collections.abc.Iterable[str]):
        """! Add string group tagged with scalar type.

        @param st the ScalarType
        @param strings a one-dimensional string group
        @param name the field name.
        @exception ValueError if strings cannot be converted.
        """
        jtname = adc_types.scalar_to_json(adc_types.type_to_scalar(st))
        maxdepth = [0]
        jt = adc_types.get_common_scalar(strings, 0, maxdepth)
        if not adc_types.is_string_type(jt):
            raise ValueError("add_array_typed_string: strings argument must be strings only")
        if maxdepth[0] > 1:
            raise ValueError("add_array_typed_string: strings argument must be one-dimensional")
        data = adc_types.get_list_format(strings)
        self._set_attr(name, {"type": "array_"+jtname, "value": data,
            "container_type": "vector", "python": strings.__class__.__name__})

    def _kind(self, name: str) -> adc_types.KeyType:
        """ return the type that name resolves to in this builder."""
        if name in self._sections:
            ### print(f"DEB: name {name} found in _sections")
            return adc_types.KeyType.k_section
        if name in self._d:
            ### print(f"DEB: name {name} found in _d")
            return adc_types.KeyType.k_value
        ### print(f"DEB: name {name} not found")
        return adc_types.KeyType.k_none

    @staticmethod
    def BasicBuilder(app_name: str) -> 'Builder':
        """! DEPRECATED"""
        # pylint: disable=C0103
        b = Builder()
        b.add_header_section(app_name)
        return b

class Memory(Builder):
    """! @brief Section for memory stats"""
    def __init__(self):
        super().__init__()
        self._set_attr("mem_total", get_meminfo("MemTotal", update=True))
        self._set_attr("mem_used", get_meminfo("MemUsed"))
        self._set_attr("mem_free", get_meminfo("MemFree"))
        self._set_attr("mem_shared", get_meminfo("Shmem"))
        self._set_attr("mem_buffers", get_meminfo("Buffers"))
        self._set_attr("mem_cache", get_meminfo("CachedAll"))
        self._set_attr("mem_available", get_meminfo("MemAvailable"))
        self._set_attr("swap_total", get_meminfo("SwapTotal"))
        self._set_attr("swap_used", get_meminfo("SwapUsed"))
        self._set_attr("swap_free", get_meminfo("SwapFree"))

# pylint: disable=R0913 disable=R0917
class Host(Builder):
    """! Section for host OS, with optional hardware details """
    def __init__(self, osinfo: bool, ramsize: bool, env: bool, cpu: bool, gpu: bool, numa: bool):
        super().__init__()
        ubuf = platform.uname()
        self._set_attr( "name", ubuf.node )
        if osinfo:
            self._set_attr("os_family", ubuf.system)
            self._set_attr("os_version", ubuf.release)
            self._set_attr("os_arch", ubuf.machine)
            self._set_attr("os_build", ubuf.version)
        if env:
            vlist = os.getenv("ADC_HOST_SECTION_ENV")
            if vlist:
                for e in vlist.split(":"):
                    if e and len(e):
                        x = os.getenv(e)
                        if x:
                            self._set_attr(e, x)
        if ramsize:
            self._set_attr("mem_total", get_meminfo("MemTotal"))
        if cpu:
            x = get_lscpu()
            self._set_attr("cpu", x)
        if gpu:
            x = get_gpu_data()
            self._set_attr("gpu", x)
        if numa:
            x = get_numa_hardware()
            self._set_attr("numa_hardware", x)

class Header(Builder):
    """! A class to build the header section
       with the application name given by user and default details.
    """
    def __init__(self, application: str):
        super().__init__()
        self._set_attr("adc_api_version", self.API_VERSION)
        y = time.time_ns()
        s = y // 1000000000
        ns = y % 1000000000
        ms = ns // 1000000
        self._set_attr("timestamp", f"{s}.{ns}")  # "sec.nanosec"
        dt = datetime.datetime.fromtimestamp(s)
        prefix = dt.strftime("%Y-%m-%dT%H:%M:%S.")
        suffix = dt.strftime("%z")
        ds = f"{prefix}{ms:03d}{suffix}"
        self._set_attr("datestamp", ds)  # string 8601 millis, tz
        self._set_attr("user", getpass.getuser())
        self._set_attr("uid", str(os.getuid()))
        self._set_attr("application" , application)
        self._set_attr("uuid", str(uuid.uuid4()))
        # print(f"CTOR:HEADER:{self.serialize()}")
