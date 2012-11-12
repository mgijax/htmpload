#!/bin/sh
#
#  makeEuropheno.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that creates the Europhenome HTMP file
#
#  Usage:
#
#      makeEuropheno.sh
#
#  Env Vars:
#
#      See the configuration file (europhenompload.config)
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
#      4) Call makeEuropheno.py to create the association file.
#
#  Notes:  None
#
###########################################################################

cd `dirname $0`

CONFIG=$1

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
# Create the Europhenome/HTMP input file
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Create the Europhenome/HTMP input file (makeEuropheno.sh)" | tee -a ${LOG}
./makeEuropheno.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create the Europhenome/HTMP input file (makeEuropheno.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
