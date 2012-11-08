#!/bin/sh
#
#  europhenompload.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the entire Europhenome load process.
#
#  Usage:
#
#      europhenompload.sh
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
#      2) Establish the log file.
#      3) Copy the Europhenome input file to the Europhenome/Input directory
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
    RUNNING="europhenompload_test.sh"
else
    CONFIG=${HTMPLOAD}/europhenompload.config
    ANNOTCONFIG=${HTMPLOAD}/annotload.config
    RUNNING="europhenompload.sh"
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
rm -rf ${LOG_CUR}
touch ${LOG}
touch ${LOG_CUR}

#
# createArchive
#
echo "archiving..." >> ${LOG}
date >> ${LOG}
#preload ${OUTPUTDIR}
rm -rf ${OUTPUTDIR}/*.diagnostics
rm -rf ${OUTPUTDIR}/*.error
echo "archiving complete" >> ${LOG}
date >> ${LOG}

#
# copy input file into working directory
# sort by column 5 (allele name)
# sort by column 4 (allele state)
# sort by column 2 (mp id)
#
echo "coping input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${BIOMART_COPY_INPUT_FILE}
sort -t"	" -k5,5 -k4,4 -k2,2 ${BIOMART_INPUT_FILE} > ${BIOMART_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying input file completed"
exit 0

#
# Create the HTMP input file
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeEuropheno.sh (${RUNNING})" | tee -a ${LOG}
./makeEuropheno.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeEuropheno.sh (${RUNNING})"

#
# Check counts; if Biomart file count = HTMP file count, then OK
#
htmpBiomart=`/usr/bin/wc -l < ${BIOMART_COPY_INPUT_FILE}`
echo '\nBioMart file:' >> ${LOG_CUR}
echo '   ' ${htmpBiomart} >> ${LOG_CUR}
htmpMGD=`/usr/bin/wc -l < ${HTMP_INPUT_FILE}`
echo '\nHTMP file:' >> ${LOG_CUR}
echo '   ' ${htmpMGD} >> ${LOG_CUR}
if [ ${htmpBiomart} -ne ${htmpMGD} ]
then
echo 'ERROR:  Biomart does **not** equal HTMP file' >> ${LOG_CUR}
shutDown
exit 0
else
echo 'SUCCESSFUL:  Biomart equals HTMP file' >> ${LOG_CUR}
fi

#
# Create Genotypes
#
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
