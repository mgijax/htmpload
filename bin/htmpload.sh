#!/bin/sh 
#
#  htmpload.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the entire HTMP load process.
#
#  Usage:
#
#      htmpload.sh *load.config annotload.config
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
#      4) Call makeGenotype.sh to make a Genotype-input file for the 
#	    genotypeload & run it
#      5) Call makeAnnotation.sh to make a Annotation-input file for the 
#	    annotload & run it
#
#  Notes:  None
#
###########################################################################

cd `dirname $0`

CONFIG=$1
ANNOTCONFIG=$2

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
preload ${OUTPUTDIR}
rm -rf ${OUTPUTDIR}/*.diagnostics
rm -rf ${OUTPUTDIR}/*.error
echo "archiving complete" >> ${LOG}
date >> ${LOG}

#
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${INPUTDIR}/lastrun
if [ -f ${LASTRUN_FILE} ]
then
    if /usr/local/bin/test ${LASTRUN_FILE} -nt ${SOURCE_INPUT_FILE}; then
       echo "\nLOAD SKIPPED: No new input file: ${SOURCE_INPUT_FILE}" | tee a ${LOG_CUR}
       STAT=0
       checkStatus ${STAT} "LOAD SKIPPED: No new input file ${SOURCE_INPUT_FILE}"
       shutDown
       exit 0
    fi
fi

# REWORK THIS SECTION - either do it for only sanger or do it after preprocessor
# runs copying the old HTMP_INPUT_FILE to HTMP_INPUT_FILE_OLD for comparison
# after HTMP_INPUT_FILE built
#
# Verify the percentage between the old input file and the new input file
# If the percentage is < 90%, then abort the load
# If the percentage is >= 90%, then continue the load
#
# for testing:
#oldcount=4000
#newcount=2000
#
#echo "SOURCE_INPUT_FILE: ${SOURCE_INPUT_FILE}"
#if [ -f ${HTMP_INPUT_FILE} ]
#then
#oldcount=`/usr/bin/wc -l < ${HTMP_INPUT_FILE}`
#newcount=`/usr/bin/wc -l < ${SOURCE_INPUT_FILE}`
#thediff=`expr $newcount / $oldcount \* 100`
#if [ ${thediff} -lt 90 ]
    #then
    #    echo "\nLOAD SKIPPED: " >> ${LOG_CUR}
    #    echo "${SOURCE_INPUT_FILE}\n IS LESS THAN 90% OF\n ${HTMP_INPUT_FILE}\n" >> ${LOG_CUR}
    #    STAT=0
    #    checkStatus ${STAT} "LOAD SKIPPED: ${SOURCE_INPUT_FILE}\n IS LESS THAN 90% OF\n ${HTMP_INPUT_FILE}\n"
    #    shutDown
    #    exit 0
    #fi
#fi

echo "copying source input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${SOURCE_COPY_INPUT_FILE}
cp ${SOURCE_INPUT_FILE} ${SOURCE_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying IMPC input file"

# run pre-processor to create HTMP_INPUT_FILE
#
${PREPROCESSOR}
STAT=$?
checkStatus ${STAT} "Running ${PREPROCESSOR}"

#
# sort the pre-processed file
# sort by column 7 (allele name)
# sort by column 6 (allele state)
# sort by column 4 (mp id)
#
echo "sorting pre-processed file..." >> ${LOG}
date >> ${LOG}
sort -o ${HTMP_INPUT_FILE} -t"        " -k7,7 -k6,6 -k4,4 ${HTMP_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "sorting pre-processed file"

#
# Create Genotypes
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotype.sh" | tee -a ${LOG}
./makeGenotype.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeGenotype.sh ${CONFIG}"

#
# Create the Annotation
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeAnnotation.sh" | tee -a ${LOG}
./makeAnnotation.sh ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeAnnotation.sh ${CONFIG}"

#
# Run reports
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Run reports runReports.sh" | tee -a ${LOG}
./runReports.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "runReports.sh ${CONFIG}"

#
# Touch the "lastrun" file to note when the load was run.
#
touch ${LASTRUN_FILE}

#
# run postload cleanup and email logs
#
shutDown
exit 0
