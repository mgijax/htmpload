#!/bin/sh

#
# runtest_part1.csh
#
# run the htmpload using a test file as input
# input file: ??mpload.txt
#

cd `dirname $0`

# config files
CONFIG=$1
# ${HTMPLOAD}/bin/sangermpload.csh, ${HTMPLOAD}/bin/eurompload.sh, etc.
HTMPLOADSH=$2
ANNOTCONFIG=$3

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
if [ ! -f ${ANNOTCONFIG} ]
then
    echo "Missing configuration file: ${ANNOTCONFIG}"
    exit 1
fi

#
# Establish the log file.
#
LOG=${LOG_DIAG}

#
# HTMP Test
#
# input file: mgi_??mpload.txt
# contains both genotypes and MP annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "HTMP Test (${CONFIG})" | tee -a ${LOG}
${HTMPLOADSH} ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call ${HTMPLOADSH} for ${CONFIG}" | tee -a ${LOG}
    exit 1
fi

exit 0
