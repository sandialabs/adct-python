#! /bin/bash
module purge
module load aue/gdb
rm -rf test.outputs adc.file_plugin.log
mkdir test.outputs
. ./test-env-publishers
export ADC_MULTI_PUBLISHER_DEBUG=1
export ADC_MULTIFILE_PLUGIN_DEBUG=1
env |grep ADC
echo starting...
test_adctk_builder > >(tee test.outputs/stdout.log) 2> >(tee test.outputs/stderr.log)
#test_adctk_builder |tee test.outputs/test_adctk_builder.out
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
