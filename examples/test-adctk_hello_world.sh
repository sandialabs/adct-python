#! /bin/bash
module purge
module load aue/gdb
rm -rf test.outputs adc.file_plugin.log
mkdir test.outputs
. ./test-env-publishers
export ADC_MULTI_PUBLISHER_DEBUG=1
export ADC_MULTIFILE_PLUGIN_DEBUG=1
env |grep ADC |grep CURL
env |grep ADC |grep MULTI_PUB
echo starting...
adctk_hello_world > >(tee test.outputs/hello-world.stdout.log) 2> >(tee test.outputs/hello-world.stderr.log)
if test -s ./adc.file_plugin.log; then
	echo "got ./adc.file_plugin.log"
else
	echo "no ./adc.file_plugin.log"
fi
if test -s test.outputs/out.file.log; then
	echo got test.outputs/out.file.log
else
	echo "no test.outputs/out.file.log"
fi
sleep 1 ; # catch up with nfs delays
if test -s ./test.outputs/script; then
	echo "got test.outputs/script"
else
	echo "no test.outputs/script"
fi
