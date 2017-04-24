#!/bin/sh
#
#  runMpLoads.sh
###########################################################################
#
#  Purpose:
#
#      This script runs the MP annotation loads
#
Usage=runMpLoads.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:  None
#
#  Outputs:
#
#      - Log file (${LOG_DIAG})
#      - Log file (${LOG_PROC})
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
#      2) Establish the log file.
#      3) Run all the MP/Genotype annotation loads
#      4) Call postMP.sh to load new annotation headers, etc
#
#  Notes:  None
#
###########################################################################
cd `dirname $0`

CONFIG_COMMON=../common.config

. ${CONFIG_COMMON}

SCRIPT_NAME=`basename $0`

LOG=${POSTMPLOGDIR}/${SCRIPT_NAME}.log
rm -f ${LOG}
touch ${LOG}

echo "$0" >> ${LOG}
env | sort >> ${LOG}

ANNOTCONFIG=${HTMPLOAD}/annotload.config
DMDDCONFIG=${HTMPLOAD}/dmddmpload.config
IMPCCONFIG=${HTMPLOAD}/impcmpload.config

date | tee -a ${LOG}
echo 'Run DMDD MP Load' | tee -a ${LOG}
${HTMPLOAD}/bin/htmpload.sh ${DMDDCONFIG} ${ANNOTCONFIG}

date | tee -a ${LOG}
echo 'Run IMPC MP Load' | tee -a ${LOG}
${HTMPLOAD}/bin/htmpload.sh ${IMPCCONFIG} ${ANNOTCONFIG}

date | tee -a ${LOG}
echo 'Run Post MP Process' | tee -a ${LOG}
${HTMPLOAD}/bin/postMP.py

date >> ${LOG}

exit 0
