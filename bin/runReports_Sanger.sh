#!/bin/sh
#
#  runReports_Sanger.sh
###########################################################################
#
#  Purpose:
#
#      This script is a wrapper around the process that runs reports.
#
#  Usage:
#
#      runReports_Sanger.sh
#
#  Env Vars:
#
#      See the configuration file (htmpmpload.config)
#
#  Inputs:  None
#
#  Outputs:
#
#      - Log file (${LOG_DIAG})
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
#      2) Verify that the input file exists.
#      3) Establish the log file.
#      4) Generate some reports.
#
#  Notes:  None
#
###########################################################################

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

htmpSource=`/usr/bin/wc -l < ${SOURCE_INPUT_FILE}`
echo '' >> ${LOG_CUR}
echo 'Source file (contains all rows):' >> ${LOG_CUR}
echo '   ' ${htmpSource} >> ${LOG_CUR}

htmpSkip=`/usr/bin/wc -l < ${HTMPSKIP_INPUT_FILE}`
echo 'Source file (skipped):' >> ${LOG_CUR}
echo '-- ' ${htmpSkip} >> ${LOG_CUR}

htmpDup=`/usr/bin/wc -l < ${HTMPDUP_INPUT_FILE}`
echo 'Source file (duplicates):' >> ${LOG_CUR}
echo '-- ' ${htmpDup} >> ${LOG_CUR}

htmpError=`/usr/bin/wc -l < ${HTMPERROR_INPUT_FILE}`
echo 'Source file (errors):' >> ${LOG_CUR}
echo '-- ' ${htmpError} >> ${LOG_CUR}

htmpMGD=`/usr/bin/wc -l < ${HTMPUNIQ_INPUT_FILE}`
echo 'Source file (contains MP-annotated rows only):' >> ${LOG_CUR}
echo '== ' ${htmpMGD} >> ${LOG_CUR}

#
# $htmpSkip + $htmpDup + $htmpError + $htmpMGD ==> htmpSource
#
totalHTMP=`expr $htmpSkip + $htmpDup + $htmpError + $htmpMGD`
if [ $totalHTMP -ne $htmpSource ]
then
echo 'ERROR:  Source does **not** equal skip + duplicates + errors + MP-annotations ' >> ${LOG_CUR}
else
echo 'SUCCESSFUL:  Source equals skip + duplicates + errors + MP-annotations ' >> ${LOG_CUR}
fi

#
# annotations
#
annotInput=`/usr/bin/wc -l < ${ANNOT_INPUT_FILE}`
echo '' >> ${LOG_CUR}
echo 'MGI-format Annotation: ' ${annotInput} >> ${LOG_CUR}
echo 'MGI-format Annotation file: ' ${ANNOT_INPUT_FILE} >> ${LOG_CUR}

annotOutput=`/usr/bin/wc -l < ${OUTPUTDIR}/mgi_annotload.txt.VOC_Annot.bcp`
echo 'Annotations loaded into MGD: ' ${annotOutput} >> ${LOG_CUR}

if [ $htmpMGD -ne $annotInput ]
then
echo 'ERROR:  check log file: ' ${LOGDIR}/htmp_annot.log >> ${LOG_CUR}
fi

if [ $annotInput -ne $annotOutput ]
then
echo 'ERROR:  check error file: ' ${OUTPUTDIR}/mgi_annotload.txt.*.error >> ${LOG_CUR}
fi

#
# genotypes
#
genotypeInput1=`/usr/bin/wc -l < ${GENOTYPE_INPUT_FILE}`
echo '' >> ${LOG_CUR}
echo 'MGI-format Genotype: ' ${genotypeInput1} >> ${LOG_CUR}
echo 'MGI-format Genotype file: ' ${GENOTYPE_INPUT_FILE} >> ${LOG_CUR}

genotypeInput2=`/usr/bin/wc -l < ${GENOTYPELOAD_OUTPUT}`
echo 'Genotype input: ' ${genotypeInput2} >> ${LOG_CUR}

genotypeOutput=`/usr/bin/wc -l < ${OUTPUTDIR}/mgi_genotypeload.txt.GXD_Genotype.bcp`
echo 'Genotype loaded into MGD: ' ${genotypeOutput} >> ${LOG_CUR}

if [ $genotypeInput1 -ne $genotypeInput2 ]
then
echo 'ERROR:  check file: ' ${LOGDIR}/htmp_annot.log >> ${LOG_CUR}
fi

exit 0

