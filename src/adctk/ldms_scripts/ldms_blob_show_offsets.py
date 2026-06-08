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
def main():
    files=sys.argv[1:]
    for i in files:
        script = "od -A d -t u8 -j8 -w8 {} |sed -e 's/[0-9,A-F,a-f]* *//'".format(i)
        subprocess.call(script, shell=True)

if __name__ == '__main__':
    main()
