#!/bin/sh

#
# runtest_part2.csh
#
# run additional MP annotations & OMIM annotations
# these files use genotype ids created from runtest_part1.csh
# so they must be synchronized
#

cd `dirname $0`

# config files
CONFIG=$1
ANNOTCONFIG=$2

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
LOG=${LOG_DIAG}

#
# Adding MP Annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeAnnotationTest.sh (${CONFIG})" | tee -a ${LOG}
./makeAnnotationTest.sh ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeAnnotationTest.sh (${CONFIG} ${ANNOTCONFIG})" | tee -a ${LOG}
    exit 1
fi

#
# Adding OMIM Annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeOMIMTest.sh (${CONFIG})" | tee -a ${LOG}
./makeOMIMTest.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeOMIMTest.sh (${CONFIG})" | tee -a ${LOG}
    exit 1
fi

exit 0
