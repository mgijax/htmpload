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
Usage="Usage: makeIMPC.sh config"
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
#  08/12/2014   sc
#       - TR11674
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
# Create the IMPC HTMP input files
#
echo "" >> ${LOG}
date >> ${LOG}
./makeIMPC.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: creating the IMPC HTMP input file (makeIMPC.py)" | tee -a ${LOG}
    exit 1
fi

#
# Create the IMPC HTMP strains
#
echo "" >> ${LOG}
date >> ${LOG}
./makeIMPCStrains.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create the IMPC HTMP strains (makeIMPC.py)" | tee -a ${LOG}
    exit 1
fi

exit 0
