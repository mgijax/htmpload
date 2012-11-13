#!/bin/sh

#
# makeOMIMTest.sh
#
# run OMIM annotations
# input file: mgi_omimload.txt
#

cd `dirname $0`

CONFIG=$1
OMIMCONFIG=${HTMPLOAD}/test/omimload.config.test

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
if [ ! -f ${OMIMCONFIG} ]
then
    echo "Missing configuration file: ${OMIMCONFIG}"
    exit 1
fi

#
# Establish the log file.
#
LOG=${LOG_DIAG}

#
# Run the annotload-er test
# Make sure you cd into the output directory
# since the annotload-er puts its output files into
# the current-working-directory
#
cd ${OUTPUTDIR}
echo "" >> ${LOG}
date >> ${LOG}
echo "Call annotload.py (makeOMIMTest.sh)" | tee -a ${LOG}
cp ${HTMPLOAD}/test/mgi_omimload_test.txt ${INPUTDIR}/mgi_omimload.txt
${ANNOTLOAD}/annotload.csh ${OMIMCONFIG} mp 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call annotload.py (makeOMIMTest.sh)" | tee -a ${LOG}
    exit 1
fi

#
# reload the MRK_OMIM_Cache
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call mrkomim.csh (makeOMIMTest.sh)" | tee -a ${LOG}
${MRKCACHELOAD}/mrkomim.csh 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call annotload.py (makeOMIMTest.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
