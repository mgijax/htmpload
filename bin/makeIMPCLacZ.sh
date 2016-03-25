#!/bin/sh
#
#  makeIMPCLacZ.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that creates the 
#	IMPC HTMP file
#
Usage="Usage: makeIMPCLacZ.sh config"
#
#  Env Vars:
#
#      See the configuration file 
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
#      4) Call makeIMPCLacz.py to create the htmp load file.
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

#
# copy imits2 input file into working directory
#
echo "copying iMits input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${IMITS_COPY_INPUT_FILE}
cp ${IMITS_INPUT_FILE} ${IMITS_COPY_INPUT_FILE}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: copying ${IMITS_INPUT_FILE} to ${IMITS_COPY_INPUT_FILE}" | tee -a ${LOG}
    exit 1
fi

#
# Create the IMPC Lacz input files
#
echo "" >> ${LOG}
date >> ${LOG}
pwd
./makeIMCPLacZ.py
#./makeIMCPLacZ.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: creating the IMPC LacZ input file (makeIMPCLacZ.py)" | tee -a ${LOG}
    exit 1
fi

#
# Create the IMPC HTMP strains
#
#echo "" >> ${LOG}
#date >> ${LOG}
#./makeIMPCLacZStrains.py 2>&1 >> ${LOG}
#STAT=$?
#if [ ${STAT} -ne 0 ]
#then
#    echo "Error: Create the IMPC HTMP strains (makeIMPCLacZ.py)" | tee -a ${LOG}
#    exit 1
#fi

exit 0
