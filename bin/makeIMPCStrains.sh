#!/bin/sh
#
#  makeIMPCStrains.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that creates the 
#	IMPC strains - Used for development only
#
Usage="Usage: makeIMPCStrains.sh  config"
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
#      4) Call makeHTMPStrain.py to create the htmp load file.
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
LOG=${STRAINLOG}

if [ -f ${LOG} ]
then
    rm -rf ${LOG}
fi
touch ${LOG}

#
# Create the IMPC HTMP input file
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Create IMPC strains (makeIMPCStrain.py)" | tee -a ${LOG}
./makeIMPCStrains.py 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Create IMPC HTMP strain (makeIMPCStrain.py)" | tee -a ${LOG}
    exit 1
fi
echo "" >> ${LOG}
date >> ${LOG}

exit 0
