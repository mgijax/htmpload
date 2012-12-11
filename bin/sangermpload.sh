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
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${INPUTDIR}/lastrun

if [ -f ${LASTRUN_FILE} ]
then
    if /usr/local/bin/test ${LASTRUN_FILE} -nt ${INPUTFILE}
    then
        echo "Input file has not been updated - skipping load" | tee -a ${LOG_PROC}
        STAT=0
        checkStatus ${STAT} 'Checking input file'
        shutDown
        exit 0
    fi
fi

#
# copy input file into working directory
# sort by column 7 (allele name)
# sort by column 6 (allele state)
# sort by column 4 (mp id)
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
