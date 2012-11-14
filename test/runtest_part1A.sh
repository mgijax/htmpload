#!/bin/sh

#
# run additional genotypes
# input file: mgi_genoload.txt
# loads genotypes only
#

cd `dirname $0`

# config files
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
# Adding Genotype
#
# extra input file: mgi_genotypeload.txt
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotypeTest.sh (${CONFIG})" | tee -a ${LOG}
./makeGenotypeTest.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeGenotypeTest.sh ({CONFIG})" | tee -a ${LOG}
    exit 1
fi

exit 0
