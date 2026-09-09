# Copyright 2026 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import adctk
import io
import base64
import zlib
import struct

def get_png_mime():
    """Generates a grid png."""
    png_header = b'\x89PNG\r\n\x1a\n'
    height = 128
    width=128
    ihdr_data = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = b'IHDR' + ihdr_data
    ihdr_crc = struct.pack("!I", zlib.crc32(ihdr_chunk))
    ihdr = struct.pack("!I", len(ihdr_data)) + ihdr_chunk + ihdr_crc

    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # Filter type 0 for each scanline row
        for x in range(width):
            color = 255 if ((x // 16) + (y // 16)) % 2 == 0 else 0
            raw_data.extend([color, color, color]) # R, G, B bytes
    idat_data = zlib.compress(raw_data)
    idat_chunk = b'IDAT' + idat_data
    idat_crc = struct.pack("!I", zlib.crc32(idat_chunk))
    idat = struct.pack("!I", len(idat_data)) + idat_chunk + idat_crc
    iend_chunk = b'IEND'
    iend_crc = struct.pack("!I", zlib.crc32(iend_chunk))
    iend = struct.pack("!I", 0) + iend_chunk + iend_crc
    x = png_header + ihdr + idat + iend
    return f"{base64.b64encode(x).decode('utf-8')}"

#*! \file adcHelloWorld.py
#  This demonstrates using the adctk.factory API to build and publish a message.
#  The message sent includes the bare minimum, plus hello world and host data
#  and a trivial mime-encoded png.

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
    avail = f.get_publisher_names()
    print(f"available publishers are: {avail}")
    print(f'ADC_MULTI_PUBLISHER_NAMES is: {os.getenv("ADC_MULTI_PUBLISHER_NAMES")}')

    # create a message and add header
    b = f.get_builder()
    b.add_header_section("cxx_demo_1")

    # add an application-defined payload to the message
    app_data = f.get_builder()
    app_data.add("hello", "world")
    img = get_png_mime()
    app_data.add_mime("grid1", "image/png", "base64", "test.png", img)
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
