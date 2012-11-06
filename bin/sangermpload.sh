#!/bin/sh
#
#  sangerload.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the entire Sanger load process.
#
#  Usage:
#
#      sangerload.sh
#
#  Env Vars:
#
#      See the configuration file (sangerload.config)
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
#      2) Establish the log file.
#      3) Copy the Sanger input file to the Sanger/Input directory
#      4) Call makeGenotype.sh to make a Genotype-input file for the genotypeload & run genotypeload-er
#      5) Call makeAnnotation.sh to make a Annotation-input file for the annotload & run annotload-er
#
#  Notes:  None
#
###########################################################################

cd `dirname $0`

if [ $# -ge 2 ]
then
    CONFIG=$1
    ANNOTCONFIG=$2
    RUNNING="sangerload_test.sh"
else
    CONFIG=${HTMPLOAD}/sangermpload.config
    ANNOTCONFIG=${HTMPLOAD}/annotload.config
    RUNNING="sangerload.sh"
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
#  Source the DLA library functions.
#

if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${LOG}
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${LOG}
    exit 1
fi

#
# Establish the log file.
#
LOG=${LOG_DIAG}
rm -rf ${LOG}
touch ${LOG}

#
# createArchive
#
echo "archiving..." >> ${LOG}
date >> ${LOG}
preload ${OUTPUTDIR}
rm -rf ${OUTPUTDIR}/*.diagnostics
rm -rf ${OUTPUTDIR}/*.error
echo "archiving complete" >> ${LOG}
date >> ${LOG}

#
# copy input file into working directory
# sort by column 7 (allele name)
#
echo "coping input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${HTMP_INPUT_FILE}
sort -t"	" -k7,7 -k6,6 -k4,4 ${INPUTFILE} > ${HTMP_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying input file completed"

#
# Create the Genotype
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotype.sh (${RUNNING})" | tee -a ${LOG}
./makeGenotype.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeGenotype.sh (${RUNNING})"

#
# Create the Annotation
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeAnnotation.sh (${RUNNING})" | tee -a ${LOG}
./makeAnnotation.sh ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeAnnotation.sh (${RUNNING})"

#
# Run reports
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Run reports runReports.sh (${RUNNING})" | tee -a ${LOG}
./runReports.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "runReports.sh (${RUNNING})"

#
# run postload cleanup and email logs
#
shutDown
exit 0
