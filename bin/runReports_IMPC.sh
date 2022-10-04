#!/bin/sh
#
#  runReports_IMPC.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that runs reports.
#
#  Usage:
#
#      runReports_IMPC.sh
#
#  Env Vars:
#
#      See the configuration file (htmpmpload.config)
#
#  Inputs:  None
#
#  Outputs:
#
#      - Log file (${LOG_DIAG})
#      - Log file (${LOG_CUR})
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
#      4) Generate some reports.
#
#  Notes:  None
#
###########################################################################
cd `dirname $0`

if [ $# -lt 1 ]
then
    echo ${Usage}
    exit 1
fi

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

echo "" >> ${LOG}
date >> ${LOG}
echo "Create GENTAR/IMPC Colony ID Discrepancy Report (runReports_IMPC.py)" | tee -a ${LOG}
${PYTHON} ./runReports_IMPC.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create GENTAR/IMPC Colony ID Discrepancy Report (runReports_IMPC.py))" | tee -a ${LOG}
    exit 1
fi
echo "" >> ${LOG}
date >> ${LOG}

exit 0

