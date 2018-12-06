#!/bin/sh
#
#  htmpload.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the HTMP/MP load process.
#
Usage="Usage: htmpload.sh *load.config annotload.config"
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
#      3) Copy the HTMP input file to the HTMP/Input directory
#      4) Call makeGenotype.sh to make a Genotype-input file for the genotypeload & run it
#      5) Call makeAnnotation.sh to make a Annotation-input file for the annotload & run it
#
#  Notes:  None
#
###########################################################################
cd `dirname $0`
LOG=`pwd`/htmpload.log
rm -rf ${LOG}


if [ $# -lt 2 ]
then
    echo ${Usage}
    exit 1
fi

CONFIG_COMMON=../common.config
CONFIG=$1
ANNOTCONFIG=$2

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

if [ -f ${CONFIG} ]
then
    . ${CONFIG}
else
    echo "Missing configuration file: ${CONFIG}"
    exit 1
fi

# Just check the annotation load config
if [ ! -f ${ANNOTCONFIG} ]
then
    echo "Missing configuration file: ${ANNOTCONFIG}"
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
# createArchive including OUTPUTDIR, startLog, getConfigEnv
# sets "JOBKEY"
preload ${OUTPUTDIR}

#
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${INPUTDIR}/lastrun
if [ -f ${LASTRUN_FILE} ]
then
    if test ${LASTRUN_FILE} -nt ${SOURCE_INPUT_FILE}; then
       echo "" >> ${LOG_CUR} 2>&1
       echo "LOAD SKIPPED: No new input file: ${SOURCE_INPUT_FILE}" >> ${LOG_CUR} 2>&1
       STAT=0
       checkStatus ${STAT} "LOAD SKIPPED: No new input file ${SOURCE_INPUT_FILE}"
       shutDown
       exit 0
    fi
fi

#
# remove the genotypeload and annotload diagnostics and error files
# copy source input file
#
echo "copying source input file..." >> ${LOG_DIAG}
date >> ${LOG_DIAG}
rm -rf ${OUTPUTDIR}/*.diagnostics
rm -rf ${OUTPUTDIR}/*.error
rm -rf ${SOURCE_COPY_INPUT_FILE}
cp ${SOURCE_INPUT_FILE} ${SOURCE_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying provider input file"

# run pre-processor to create HTMP_INPUT_FILE
#
./preprocess.sh ${CONFIG} 2>&1 >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "Running preprocess.sh ${CONFIG}"

#
# sort the pre-processed file
# sort by column 7 (allele name)
# sort by column 6 (allele state)
# sort by column 4 (mp id)
#
echo "sorting pre-processed file ${HTMP_INPUT_FILE} ..." >> ${LOG_DIAG}
date >> ${LOG_DIAG}
sort -o ${HTMP_INPUT_FILE} -t"	" -k7,7 -k6,6 -k4,4 ${HTMP_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "sorting pre-processed file"

#
# Create Genotypes
#
echo "" >> ${LOG_DIAG}
date >> ${LOG_DIAG}
./makeGenotype.sh ${CONFIG} 2>&1 >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "makeGenotype.sh ${CONFIG}"

#
# Create the Annotation, if ANNOTCONFIG file exists
#
echo "" >> ${LOG_DIAG}
date >> ${LOG_DIAG}
./makeAnnotation.sh ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "makeAnnotation.sh ${CONFIG}"

#
# Run reports if defined for this provider
#
if [ "${REPORT_SCRIPT_SUFFIX}" != "" ]
then

    reportScript=runReports_${REPORT_SCRIPT_SUFFIX}
    echo "" >> ${LOG_DIAG}
    date >> ${LOG_DIAG}
    ./${reportScript} ${CONFIG} 2>&1 >> ${LOG_DIAG}
    STAT=$?
    checkStatus ${STAT} "runReports_${REPORT_SCRIPT_SUFFIX} ${CONFIG}"
fi

#
# Touch the "lastrun" file to note when the load was run.
#
touch ${LASTRUN_FILE}

#
# run postload cleanup and email logs
#
shutDown
exit 0
