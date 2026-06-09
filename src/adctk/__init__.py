# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
# pylint: disable=line-too-long
##! @package adctk
# @brief Application Data Collection: Structured logging for scientific computing.
# @mainpage Application Data Collection (Python)
#
# @section purpose Purpose (why)
# The ADC project aims to provide workflow metadata collection for all scientific computing environments and workflow stages.
# Here 'metadata' means small, structured descriptions of:
#  - what is planned (such as a campaign of multiple jobs, or in a single job being submitted)
#  - what is happening (such as the data sizes and features in an individual execution or rank of a parallel execution)
#  - what has happened (such as scalar progress indicators or final results)
#
# These *complement* large data flows such as:
#  - time-series hardware metrics (papi, LDMS)
#  - call-profiling data (caliper, kokkos, gprof, ...)
#  - lists of particle or geometric entities and associated engineering or physics data (hdf5, netcdf, exodus, commercial CAD formats)
#  .
# The metadata logged is intended for analysis during or after the current workflow step to allow:
#   - other tooling to influence subsequent steps, such as compute resource selection.
#   - users to track workflow progress.
#   - performance analysts to correlate and predict performance based on simulation metadata.
#   - software developers and managers to prioritize feature work based on usage.
#   - software agents to detect when system performance is below expectations.
#
# @section data Output (what)
# ADC produces *semi-structured*, extensible json messages. Some json objects have standardized names and contents; these
# are included in a message if a convenience function is called to add them to the message. If specific
# names are present, the associated values have standard origins.
# Other objects have minimally defined fields, with the rest of the fields being up to the application.
# Where common json libraries exist, the application may also attach arbitrary json objects to a message; this support
# varies by implementation language. The @ref adctk.builder.Builder "adctk.Builder" provides a rich set of convenience functions for constructing
# and customizing ADC messages that capture scientific programming data types.
#
# @section environments Environments (where)
# Scientific workflows span desktop, server, and cluster environments. Critical information
# is usually added (or first exposed) at each stage. Linux environments are directly supported
# as well as Windows environments connected through Java.
#
# @section bindings Languages (how)
# Initially, Python, C++, and Java are supported, and likely this will expand to C, Fortran and JavaScript.
# Documented here is the Python standard library-based binding based on Python 3.10.
# This binding follows the Factory pattern (@ref adctk.factory.Factory "adctk.Factory"). The factory provides json builder objects and publisher objects.
#
#
# Interface support for later Pythons is anticipated, as Python and Numpy support for
# basic character and numerical types evolves.
#
# @section Using adctk
# - import adctk
#
# @section publishers Performance
# The data collected is published as the application runs, and is fully labeled with
# data types for downstream interpretation up to decades into the future.
#
# A variety of plugins implement the @ref adctk.publisher.Publisher "adctk.Publisher" interface
# to ensure transmission performance and overhead demands are met
# for each scientific environment. Messages can be sent directly to the REST-based infrastructure, or
# (in HPC scenarios) routed through any bus which can support json (such as syslog, LDMS, or a cache file).
#
# @section apilist Just show me the code:
# APIs:
# - @ref adctk.factory.Factory "adctk.Factory"
# - @ref adctk.builder.Builder "adctk.Builder"
# - @ref adctk.publisher.Publisher "adctk.Publisher"
#
# Examples:
# - @ref simpleDemo.py demonstrates instrumenting a trivial program.
#
""" ADCTK API module"""
from .builder import APISequenceError
from .builder import Builder
from .publisher import Publisher
from .publisher import MultiPublisher
from .factory import Factory
from .adc_types import ScalarType
from .adc_types import KeyType
from .adc_types import Field
from .adc_version import AdcVersion
