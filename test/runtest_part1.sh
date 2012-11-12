#!/bin/sh

#
# runtest_part1.csh
#
# run the htmpload using a test file as input
# input file: ??mpload_test.txt
# loads both genotypes and mp annotations
#
# run additional genotypes
# input file: mgi_genoload_test.txt
# loads genotypes only
#

cd `dirname $0`

# config files
CONFIG=$1
ANNOTCONFIG=$2
# ${HTMPLOAD}/bin/sangermpload.csh, ${HTMPLOAD}/bin/eurompload.sh, etc.
HTMPLOADSH=$3

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
# Establish the log file.
#
LOG=${LOG_DIAG}

#
# HTMP Test
#
# input file: mgi_??mpload_test.txt
# contains both genotypes and MP annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "HTMP Test..." | tee -a ${LOG}
cp ${INPUTFILE} ${INPUTDIR}
${HTMPLOADSH} ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call ${HTMPLOADSH}" | tee -a ${LOG}
    exit 1
fi

#
# Adding Genotype
#
# input file: mgi_genotypeload_test.txt
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotypeTest.sh (${HTMPLOADSH})" | tee -a ${LOG}
./makeGenotypeTest.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeGenotypeTest.sh (${HTMPLOADSH})" | tee -a ${LOG}
    exit 1
fi

exit 0
