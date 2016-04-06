#!/bin/sh
#
#  htmploadlacz.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the HTMP/LacZ load process.
#
Usage="Usage: htmploadlacz.sh *load.config"
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
#
#  Notes:  None
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
rm -rf ${LOG}
rm -rf ${LOG_CUR}
touch ${LOG}
touch ${LOG_CUR}

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
# createArchive
#
echo "archiving..." >> ${LOG}
date >> ${LOG}
preload ${OUTPUTDIR}
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
echo "copying source input file..." >> ${LOG}
date >> ${LOG}
rm -rf ${OUTPUTDIR}/*.diagnostics
rm -rf ${OUTPUTDIR}/*.error
rm -rf ${SOURCE_COPY_INPUT_FILE}
cp ${SOURCE_INPUT_FILE} ${SOURCE_COPY_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "copying IMPC/LacZ input file"

# run pre-processor to create HTMP_INPUT_FILE
#
./makeIMPC.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "Running makeIMPC.sh ${CONFIG}"

#
# sort the pre-processed file
# sort by column 7 (allele name)
# sort by column 6 (allele state)
#
echo "sorting pre-processed file ${HTMP_INPUT_FILE} ..." >> ${LOG}
date >> ${LOG}
sort -o ${HTMP_INPUT_FILE} -t"	" -k7,7 -k6,6 ${HTMP_INPUT_FILE}
STAT=$?
checkStatus ${STAT} "sorting pre-processed file"

#
# Create Genotypes
#
echo "" >> ${LOG}
date >> ${LOG}
./makeGenotype.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "makeGenotype.sh ${CONFIG}"

#
# Run reports
#
reportScript=runReports_${REPORT_SCRIPT_SUFFIX}
echo "" >> ${LOG}
date >> ${LOG}
./${reportScript} ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
checkStatus ${STAT} "runReports_${REPORT_SCRIPT_SUFFIX} ${CONFIG}"

#
# Touch the "lastrun" file to note when the load was run.
#
touch ${LASTRUN_FILE}

#
# run postload cleanup and email logs
#
shutDown
exit 0
