# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
#! /bin/bash
# usage $0 OFFSET_FILES
# for i in $*; do
#	od -A d -t u8 -j 8 -w8 $i |sed -e 's/[0-9,A-F,a-f]* *//'
#done
import subprocess
import sys
import pathlib
def main():
    files=sys.argv[1:]
    for i in files:
        if pathlib.Path(i).is_file():
            script = f"od -A d -t u8 -j8 -w8 {i} |sed -e 's/[0-9,A-F,a-f]* *//'"
            subprocess.call(script, shell=True)

if __name__ == '__main__':
    main()
