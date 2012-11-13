#!/bin/sh

#
# makeGenotypeTest.sh
#
# run additional genotypes
# input file: mgi_genoload.txt
#

cd `dirname $0`

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
# Run the genotypeload-er test
# Make sure you cd into the output directory
# since the genotypeload-er puts its output files into
# the current-working-directory
#
cd ${OUTPUTDIR}
echo "" >> ${LOG}
date >> ${LOG}
echo "Call genotypeload.py (makeGenotypeTest.sh)" | tee -a ${LOG}
cp ${HTMPLOAD}/test/mgi_genotypeload_test.txt ${INPUTDIR}/mgi_genotypeload.txt
${GENOTYPELOAD}/bin/genotypeload.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call genotypeload.py (makeGenotypeTest.sh)" | tee -a ${LOG}
    exit 1
fi

exit 0
