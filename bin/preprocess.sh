#!/bin/sh
#
#  preprocess.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that parses an input file
#	to create a common format HTMP load file and create strains
#	It is a convenience script for development.
#
Usage="Usage: preprocess.sh config"
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
#      4) Call makeHTMP.py to create the htmp load file.
#
#  Notes:  
#
# sc   02/17/2017
#       - TR12488 Mice Crispies project
#
#  08/12/2014   sc
#       - TR11674
#
###########################################################################
BINDIR=`pwd`
cd ${BINDIR}/..
echo `pwd`

if [ $# -lt 1 ]
then
    echo ${Usage}
    exit 1
fi

CONFIG_COMMON=`pwd`/common.config

cd ${BINDIR}

CONFIG=$1

#
# Make sure the configuration files exist and source
#
if [ -f ${CONFIG_COMMON} ]
then
    . ${CONFIG_COMMON}
else
    echo "Missing configuration file: ${CONFIG_COMMON}"
    exit 1
fi

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
echo "LOG: ${LOG}"
touch ${LOG}
if [ "${IMITS_INPUT_FILE}" != "" ]
then
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
fi

#
# Create the HTMP input files
#
echo "" >> ${LOG}
date >> ${LOG}
echo 'calling preprocess.py'
${PYTHON} ./preprocess.py 2>&1 >> ${LOG}
PREPROCESS_STAT=$?
if [ ${PREPROCESS_STAT} -eq 1 ]
then
    echo "Error: creating the HTMP input file (preprocess.py)" | tee -a ${LOG}
    exit 1
fi

#
# Create the HTMP strains
#
echo "" >> ${LOG}
date >> ${LOG}
echo 'calling makeStrains.py'
${PYTHON} ./makeStrains.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -eq 1 ]
then
    echo "Error: Creating the HTMP strains (makeStrains.py)" | tee -a ${LOG}
    exit 1
fi

exit ${PREPROCESS_STAT}
