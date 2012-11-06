#!/bin/sh
#
#  makeAnnotation.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that creates the Annotations.
#
#  Usage:
#
#      makeAnnotation.sh
#
#  Env Vars:
#
#      See the configuration file (CONFIG)
#
#  Inputs:  None
#
#  Outputs:
#
#      - Log file (${LOG_DIAG})
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal error occurred
#
#  Assumes:  Nothing
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Source the configuration file to establish the environment.
#      2) Verify that the input file exists.
#      3) Establish the log file.
#      4) Call makeAnnotation.py to create the annotation file.
#
#  Notes:  None
#
###########################################################################

cd `dirname $0`

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
# Create the HTMP/Annotation input file for the annotload
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Create the HTMP/Annotation file (makeAnnotation.sh)" | tee -a ${LOG}
./makeAnnotation.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create the HTMP/Annotation file (makeAnnotation.sh)" | tee -a ${LOG}
    exit 1
fi

#
# Run the annotload-er
# Make sure you cd into the output directory
# since the annotload-er puts its output files into
# the current-working-directory
#
cd ${OUTPUTDIR}
echo "" >> ${LOG}
date >> ${LOG}
echo "Call annotload.py (makeAnnotation.sh)" | tee -a ${LOG}
${ANNOTLOAD}/annotload.csh ${ANNOTCONFIG} mp 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call annotload.py (makeAnnotation.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
