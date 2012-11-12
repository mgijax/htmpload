#!/bin/sh

#
# runtest_part1.csh
#
# run the sangermpload using a test file as input
# input file: sangermpload_test.txt
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
# Sanger Test
#
# input file: mgi_sangermpload_test.txt
# contains both genotypes and MP annotations
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Sanger Test...(sangerload_test.sh)" | tee -a ${LOG}
cp ${HTMPLOAD}/test/mgi_sangermpload_test.txt ${INPUTDIR}
${HTMPLOAD}/bin/sangermpload.sh ${CONFIG} ${ANNOTCONFIG} 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call sangermpload.sh (sangermpload_test.sh)" | tee -a ${LOG}
    exit 1
fi

#
# Adding Genotype
#
# input file: mgi_genotypeload_test.txt
#
echo "" >> ${LOG}
date >> ${LOG}
echo "Call makeGenotypeTest.sh (sangerload_test.sh)" | tee -a ${LOG}
./makeGenotypeTest.sh 2>&1 >> ${LOG}
STAT=$?
if [ ${STAT} -ne 0 ]
then
    echo "Error: Call makeGenotypeTest.sh (sangermpload_test)" | tee -a ${LOG}
    exit 1
fi

exit 0
