#!/bin/sh

#
# runtest_part3.sh
#
# compare input file to sybase data
#

cd `dirname $0`

CONFIG=${SANGERMPLOAD}/test/sangermpload.config.test

#
# Make sure the configuration file exists and source it.
#
if [ -f ${CONFIG} ]
then
    . ${CONFIG}
else
    echo "Missing configuration file: ${CONFIG}"
    exit 1
fi

#
# Establish the log file.
#
rm -rf ${LOG_TEST}
LOG=${LOG_TEST}

echo "" >> ${LOG}
date >> ${LOG}
echo "Run Test...(runtest_part3.sh)\n" | tee -a ${LOG}
./runtest_part3.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: runtest_part3.py (runtest_part3.sh)" | tee -a ${LOG}
    exit 1
fi

rm -rf ${LOG_TEST_SORTED}
sort ${LOG_TEST} > ${LOG_TEST_SORTED}

exit 0
