#!/bin/sh

#
# makeAnnotationTest.sh
#
# run additional MP & OMIM annotations
# input file:  mgi_annotload_test.txt
#
# USES ANNOTATION LOADER IN "APPEND" MODE
# SO IF YOU WANT TO RE-LOAD, SO NEED TO ADD A DELETE SCRIPT
# TO DELETE THESE ANNOTATIONS WITHOUT DELETING THE OTHER
# ANNOTATIONS.  MAY HAVE TO USE A DIFFERENT USER.
#

cd `dirname $0`

CONFIG=${SANGERMPLOAD}/test/sangermpload.config.test
ANNOTCONFIG=${SANGERMPLOAD}/test/annotload.append.config.test

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
cp ${SANGERMPLOAD}/test/mgi_annotload_test.txt ${INPUTDIR}/mgi_annotload.txt
${ANNOTLOAD}/annotload.csh ${ANNOTCONFIG} mp 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call annotload.py (makeAnnotationTest.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
