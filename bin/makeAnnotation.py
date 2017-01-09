#!/usr/local/bin/python
#
#  makeAnnotation.py
###########################################################################
#
#  Purpose:
#
#      This script will read the data in the HTMP input file to:
#
#      1) verify some Annotation information in the input file(s)
#
#      2) create Annotation input file for annotload-er
#
#  Usage:
#
#      makeAnnotation.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#    	   LOG_DIAG
#    	   LOG_CUR
#    	   INPUTDIR
#    	   HTMPUNIQ_INPUT_FILE
#	   GENOTYPELOAD_OUTPUT
#    	   ANNOT_INPUT_FILE
#    	   CREATEDBY
#    	   JNUMBER
#
#  Inputs:
#
#      High Throughput MP file ($HTMPUNIQ_INPUT_FILE))
#
#       field 0: Unique Genotype Sequence Number
#       field 1: Phenotyping Center 
#       field 2: Annotation Center 
#       field 3: ES Cell
#       field 4: MP ID
#       field 5: MGI Allele ID
#       field 6: Allele State 
#       field 7: Allele Symbol
#       field 8: MGI Marker ID
#       field 9: Evidence Code 
#       field 10: Strain Name
#       field 11: Gender 
#
#      Genotype file ($GENOTYPELOAD_OUTPUT)
#
#	field 0: Unique Genotype Sequence Number
#	field 1: Genotype ID
#	field 2+: see genotypeload-er
#
#  Outputs:
#
#      ANNOT_INPUT_FILE
#	  input for annotload-er
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  An exception occurred
#
#  Assumes:  Nothing
#
#  Implementation:
#
#      This script will perform following steps:
#
#      1) Initialize variables.
#      2) Open files.
#      3) Verify Annotation files(s)
#      4) Write Annotations to ANNOT_INPUT_FILE
#      5) Close files.
#
#  Notes:  None
#
#  09/04/2014	sc
#	- TR11674 HDP-2 project add interpretation and phenotyping
#	    center properties
#
#  09/17/2012	lec
#	- TR10273/new
#
###########################################################################

import sys 
import os
import db
import loadlib

# LOG_DIAG
# LOG_CUR
# OUTPUTDIR
logDiagFile = None
logCurFile = None

# HTMPUNIQ_INPUT_FILE
htmpFile = None

# GENOTYPELOAD_OUTPUT
genotypeFile = None

# ANNOT_INPUT_FILE
annotFile = None

# file pointers
fpLogDiag = None
fpLogCur = None
fpHTMP = None
fpGenotype = None
fpAnnot = None

# see annotload/annotload.py for format
annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t%s\n'

#
# properties
# sex-specifity (_vocab_key = 86)
# wtsi-high-throughput link (_vocab_key = 87)
# the properties will be stored in the same evidence record (_annotevidence_key)
#
#propertiesLine = 'MP-Sex-Specificity&=&%s&==&MP-HTLink-WTSI&=&http://www.sanger.ac.uk/mouseportal/'
#'MP-Sex-Specificity&=&%s'
propertiesLine = 'MP-Sex-Specificity&=&%s&==&Data Interpretation Center&=&%s&==&Phenotyping Center&=&%s&==&Resource Name&=&%s'

# defaults
inferredFrom = ''
qualifier = ''
createdBy = ''
jnumber = ''
notes = ''

loaddate = loadlib.loaddate

errorDisplay = '''

***********
error:%s
line: %s
field: %s
%s
'''

# key = genotype order sequence number (system-generated)
# value = genotype ID
#
# this is used to match up the HTMP row with the Genotype-loader output
#
genotypeOrderDict = {}

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global logDiagFile, logCurFile, htmpFile, genotypeFile, annotFile
    global fpLogDiag, fpLogCur, fpHTMP, fpGenotype, fpAnnot
    global createdBy, jnumber

    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpFile = os.getenv('HTMPUNIQ_INPUT_FILE')
    genotypeFile = os.getenv('GENOTYPELOAD_OUTPUT')
    annotFile = os.getenv('ANNOT_INPUT_FILE')
    createdBy = os.getenv('CREATEDBY')
    jnumber = os.getenv('JNUMBER')

    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not htmpFile:
        print 'Environment variable not set: HTMPUNIQ_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not genotypeFile:
        print 'Environment variable not set: GENOTYPE_OUTPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not annotFile:
        print 'Environment variable not set: ANNOT_INPUT_FILE'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpLogDiag = None
    fpLogCur = None
    fpHTMP = None
    fpGenotype = None
    fpAnnot = None

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpLogDiag, fpLogCur, fpHTMP, fpGenotype, fpAnnot

    #
    # Open the Log Diag file; append to existing file
    #
    try:
        fpLogDiag = open(logDiagFile, 'a+')
    except:
        print 'Cannot open file: ' + logDiagFile
        return 1

    #
    # Open the Log Cur file; append to existing file
    #
    try:
        fpLogCur = open(logCurFile, 'a+')
    except:
        print 'Cannot open file: ' + logCurFile
        return 1

    #
    # Open the HTPM file with genotype sequence #; read-only
    #
    try:
        fpHTMP = open(htmpFile, 'r')
    except:
        print 'Cannot open file: ' + htmpFile
        return 1

    #
    # Open the Genotype file with genotype sequence # + genotype ID; ready-only
    #
    try:
        fpGenotype = open(genotypeFile, 'r')
    except:
        print 'Cannot open file: ' + genotypeFile
        return 1

    #
    # Open the annotation file; creating new output file
    #
    try:
        fpAnnot = open(annotFile, 'w')
    except:
        print 'Cannot open annotation file: ' + annotFile
        return 1

    return 0


#
# Purpose: Close files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def closeFiles():

    if fpLogDiag:
        fpLogDiag.close()

    if fpLogCur:
        fpLogCur.close()

    if fpHTMP:
        fpHTMP.close()

    if fpGenotype:
        fpGenotype.close()

    if fpAnnot:
        fpAnnot.close()

    return 0

#
# Purpose: Read the Genotype file and create genotypeOrderDict
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def readGenotypes():

    global genotypeOrderDict

    for line in fpGenotype.readlines():

#       field 0: Unique Genotype Sequence Number
#       field 1: Genotype ID

        tokens = line[:-1].split('\t')

	genotypeOrder = tokens[0]
	genotypeID = tokens[1]
	genotypeOrderDict[genotypeOrder] = []
	genotypeOrderDict[genotypeOrder].append(genotypeID)

    #print genotypeOrderDict
    return 0

#
# Purpose: Read the HTMP file and create an input file for the Annotation loader
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def getAnnotations():

    global genotypeOrderDict

    lineNum = 0

    for line in fpHTMP.readlines():

	error = 0
	lineNum = lineNum + 1

        tokens = line[:-1].split('\t')

	genotypeOrder = tokens[0]
	phenotypingCenter = tokens[1]
	annotationCenter = tokens[2]
	mpID = tokens[4]
	evidence = tokens[9]
	gender = tokens[11]
	resourceName = tokens[13]

	# skip any row that does not contain an MP annotation
	# makeIMPC needs to check for blank attributes

	if mpID == '':
	    continue

	# if genotype file does not exist
	if not genotypeOrderDict.has_key(genotypeOrder):
	    info = 'this genotype order does not exist in %s' % (genotypeFile)
            logit = errorDisplay % (genotypeOrder, lineNum, '0', info)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	if gender == 'Female':
	    gender = 'F'
	elif gender == 'Male':
	    gender = 'M'
	elif gender in ('Both', ''):
	    gender = 'NA'
	else:
            logit = errorDisplay % (gender, lineNum, '11', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

        # if error, contine to next line
        if error:
            continue

	#
	# let annotload-er do the rest of the data validation
	#

	genotypeID = genotypeOrderDict[genotypeOrder][0]
	properties = propertiesLine % (gender, annotationCenter, phenotypingCenter, resourceName)

	#
	# add to annotation mgi-format file
	#
	fpAnnot.write(annotLine % (\
		mpID, genotypeID, jnumber, evidence, inferredFrom, qualifier, \
		createdBy, loaddate, notes, properties))

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if readGenotypes() != 0:
    sys.exit(1)

if getAnnotations() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

