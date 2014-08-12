#!/bin/sh
#
#  makeIMPC.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that creates the 
#	IMPC HTMP file
#
#  Usage:
#
#      makeIMPC.sh
#
#  Env Vars:
#
#      See the configuration file (impcload.config)
#
#  Inputs:  None
#
#  Outputs:
#
#      - Log file (${LOG})
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
#      4) Call makeHTMP.py to create the htmp load file.
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
#  Source the DLA library functions.
#

if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a
${LOG}
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a
${LOG}
    exit 1
fi

#
# Establish the log file.
#
LOG=${LOG}


#
# copy input files into working directory
#
echo "copying IMPC input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${SOURCE_COPY_INPUT_FILE}
cp ${IMPC_INPUT_FILE} ${IMPC_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying IMPC input file completed"

echo "copying iMits2 input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${SOURCE_COPY_INPUT_FILE}
cp ${IMITS2_INPUT_FILE} ${IMITS2_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying iMits2 input file completed"

#
# Create the IMPC HTMP input file
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Create the IMPC HTMP input file (makeIMPC.py)" | tee -a ${LOG}
./makeIMPC.py #2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create the IMPC HTMP input file (makeIMPC.py)" | tee -a ${LOG}
    exit 1
fi

exit 0
