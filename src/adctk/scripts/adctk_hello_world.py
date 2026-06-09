# Copyright 2026 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import adctk
#*! \file adcHelloWorld.py
#  This demonstrates using the adctk.factory API to build and publish a message.
#  The message sent includes the bare minimum, plus hello world and host data.

#! \addtogroup examples
#  @{

#!
# \brief adctk python hello world without hard-coded publisher choices.
def main() -> int:
    """!
    @brief adctk python hello world without hard-coded publisher choices.
    """

    # create a factory
    f = adctk.Factory()

    # create a message and add header
    b = f.get_builder()
    b.add_header_section("cxx_demo_1")

    # add an application-defined payload to the message
    app_data = f.get_builder()
    app_data.add("hello", "world")
    b.add_app_data_section(app_data)

    # add environment chunks of interest on at least the first message in production
    b.add_host_section(all_hs=True)

    # could add lots of other sections, as needed.

    print(f'adc pub version: {adctk.Publisher.API_VERSION["version"]}' )
    print(f'adc builder version: {adctk.Builder.API_VERSION["version"]}' )

    # create publishers following runtime environment variables and defaults.
    # Do not tolerate failures in a testing environment.
    mp = f.get_multi_publisher(strict=True, plugins=[])

    # send built message b to all publishers
    err = mp.publish(b)
    if err:
        print(f"got {err} publication errors." )

    # do some work

    # send the final status updating the header to get the needed new timestamp and uuid
    b.add_exit_data_section(0, "all good in python", None)
    b.add_header_section("cxx_demo_1")
    err = mp.publish(b)
    if err:
        print(f"got {err} publication errors." )

    # clean up all publishers
    mp.terminate()

    # the next block is skipped pending implementation of get_multifile_log_path
    # the next block is skipped pending implementation of consolidate_multifile_logs
    if False:
        # may need to sleep here to give local fs a chance to catch up
        # dir/user/[wfid.].host.Ppid.Tstarttime.pptr/application.Rrank.XXXXXX
        # -->
        # dir/user/consolidated.[wfid].adct-json.multi.xml
        path = os.getenv("ADC_MULTIFILE_PLUGIN_DIRECTORY")
        wfid = os.getenv("ADC_WFID")
        ## pattern = adctk.get_multifile_log_path(path, wfid)

        old_paths = []
        ## new_files = adctk.consolidate_multifile_logs(pattern, old_paths)
        new_files = []
        if len(old_paths):
            for i in old_paths:
                print(f"consolidating from: {i}")
                if False:
                    try:
                        os.remove(i) # we could delete the merged files.
                    except FileNotFoundError:
                        pass
            for i in new_files:
                print(f"consolidated to: {i}" )
        else:
            print("no consolidation done.")

    return 0

#! @}
#! @}

if __name__ == "__main__":
    main()
