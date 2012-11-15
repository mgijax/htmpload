#!/bin/sh

#
# makeAnnotationTest.sh
#
# run additional MP & OMIM annotations
# input file:  mgi_annotload.txt
#

cd `dirname $0`

CONFIG=$1
ANNOTCONFIG=${HTMPLOAD}/test/annotload.config.test

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
# Run the annotload-er test
# Make sure you cd into the output directory
# since the annotload-er puts its output files into
# the current-working-directory
#
cd ${OUTPUTDIR}
echo "" >> ${LOG}
date >> ${LOG}
echo "Call annotload.py (makeAnnotationTest.sh)" | tee -a ${LOG}
cp ${HTMPLOAD}/test/mgi_annotload_test.txt ${INPUTDIR}/mgi_annotload.txt
${ANNOTLOAD}/annotload.csh ${ANNOTCONFIG} mp 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call annotload.py (makeAnnotationTest.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
