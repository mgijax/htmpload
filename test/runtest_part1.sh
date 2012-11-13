#!/bin/sh

#
# runtest_part1.csh
#
# run the htmpload using a test file as input
# input file: ??mpload.txt
# loads both genotypes and mp annotations
#
# run additional genotypes
# input file: mgi_genoload.txt
# loads genotypes only
#

cd `dirname $0`

# config files
CONFIG=$1
# ${HTMPLOAD}/bin/sangermpload.csh, ${HTMPLOAD}/bin/eurompload.sh, etc.
HTMPLOADSH=$2
ANNOTCONFIG=$3

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
# input file: mgi_??mpload.txt
# contains both genotypes and MP annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "HTMP Test (${CONFIG})" | tee -a ${LOG}
cp ${INPUTFILE} ${INPUTDIR}
${HTMPLOADSH} ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call ${HTMPLOADSH} for ${CONFIG}" | tee -a ${LOG}
    exit 1
fi

#
# Adding Genotype
#
# extra input file: mgi_genotypeload.txt
#
if [ ${ADDEXTRAGENO} = 1 ]
then
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotypeTest.sh (${CONFIG})" | tee -a ${LOG}
./makeGenotypeTest.sh ${CONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeGenotypeTest.sh (${HTMPLOADSH} for ${CONFIG})" | tee -a ${LOG}
    exit 1
fi
fi

exit 0
