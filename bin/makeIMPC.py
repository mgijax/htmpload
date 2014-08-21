#!/usr/local/bin/python
#
#  makeIMPC.py
###########################################################################
#
#  Purpose:
#
#      This script will parse IMPC and iMits input files to
#      create a High-Throughput MP input file
#
#  Usage:
#
#      makeIMPC.py
#
#  Env Vars:
#
#	See the configuration file (impcmpload.config)

#  Inputs:
#
#      IMPC input file (${SOURCE_COPY_INPUT_FILE})
#
#	This is a json format file
#
#      IMITS2 input file (${IMITS2_COPY_INPUT_FILE})
#
#	This file is fetched from the iMits2 biomart
#
#  Outputs:
#
#	High Throughput MP file ($HTMP_INPUT_FILE):
#
#       field 1: Phenotyping Center 
#       field 2: Interpretation (Annotation) Center 
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
#      1) 
#      2) 
#      3) 
#      4) 
#
#  Notes: 
#
#  08/12/2014	sc
#	- TR11674
#
###########################################################################

import sys 
import os
import simplejson as json
import Set

# Input 
impcFile = None
imits2File = None

# Outputs 
htmpFile = None
logDiagFile = None
logCurFile = None
htmpErrorFile = None
htmpSkipFile = None

# file pointers
fpIMPC = None
fpImits2 = None
fpHTMP = None
fpLogDiag = None
fpLogCur = None
fpHTMPError = None
fpHTMPSkip = None

errorDisplay = '''

***********
error:%s
%s
'''

# data structures
colonyToMCLDict = {}

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global impcFile, imits2File, htmpFile
    global logDiagFile, logCurFile, htmpErrorFile, htmpSkipFile

    impcFile = os.getenv('SOURCE_COPY_INPUT_FILE')
    imits2File = os.getenv('IMITS2_COPY_INPUT_FILE')
    htmpFile = os.getenv('HTMP_INPUT_FILE')
    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    htmpSkipFile = os.getenv('HTMPSKIP_INPUT_FILE')

    print 'impcFile: %s' % impcFile
    print 'imits2File: %s' % imits2File
    print 'htmpFile: %s' % htmpFile
    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not impcFile:
        print 'Environment variable not set: SOURCE_COPY_INPUT_FILE'
        rc = 1

    if not imits2File:
        print 'Environment variable not set: IMITS2_COPY_INPUT_FILE'
        rc = 1

    if not htmpFile:
        print 'Environment variable not set: HTMP_INPUT_FILE'
        rc = 1

    if not htmpErrorFile:
        print 'Environment variable not set: HTMPERROR_INPUT_FILE'
        rc = 1

    if not htmpSkipFile:
        print 'Environment variable not set: HTMPSKIP_INPUT_FILE'
        rc = 1

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#

def openFiles():
    global fpIMPC, fpImits2, fpHTMP
    global fpLogDiag, fpLogCur, fpHTMPError, fpHTMPSkip
    #
    # Open the IMPC file
    #
    try:
        fpIMPC = open(impcFile, 'r')
    except:
        print 'Cannot open file: ' + impcFile
        return 1

    #
    # Open the iMits2 file
    #
    try:
        fpImits2 = open(imits2File, 'r')
    except:
        print 'Cannot open file: ' + imits2File
        return 1

    #
    # Open the output file 
    #
    try:
	print 'htmpfile: %s' % htmpFile
        fpHTMP = open(htmpFile, 'w')
    except:
        print 'Cannot open file: ' + htmpFile
        return 1

    #
    # Open the Log Diag file.
    #
    try:
        fpLogDiag = open(logDiagFile, 'a+')
    except:
        print 'Cannot open file: ' + logDiagFile
        return 1

    #
    # Open the Log Cur file.
    #
    try:
        fpLogCur = open(logCurFile, 'a+')
    except:
        print 'Cannot open file: ' + logCurFile
        return 1

    #
    # Open the Error file
    #
    try:
        fpHTMPError = open(htmpErrorFile, 'a+')
    except:
        print 'Cannot open file: ' + htmpErrorFile
        return 1

    #
    # Open the Skip file
    #
    try:
        fpHTMPSkip = open(htmpSkipFile, 'w')
    except:
        print 'Cannot open file: ' + htmpSkipFile
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
    global fpIMPC, fpImits2, fpHTMP
    if fpIMPC:
        fpIMPC.close()

    if fpImits2:
	fpImits2.close()

    if fpHTMP:
        fpHTMP.close()

    if fpLogDiag:
        fpLogDiag.close()

    if fpLogCur:
        fpLogCur.close()

    if fpHTMPError:
        fpHTMPError.close()

    if fpHTMPSkip:
        fpHTMPSkip.close()

    return 0


#
# Purpose: Read the IMPC and iMits2 files and re-format it to create a 
#    High-Throughpug MP input file
# Returns: 0
# Assumes: input/output files exist and have been opened
# Effects: writes to the file system
# Throws: Nothing
#
def createHTMPfile():
    global colonyToMCLDict

    # list of unique lines in the input
    lineSet = set([])

    # create lookup mapping imits2 colony id to MCL ID
    for line in fpImits2.readlines():
	tokens = line[:-1].split('\t')
	mutantID = tokens[3]
	colonyID = tokens[5]
	colonyToMCLDict[colonyID] = mutantID

    # Parse IMPC
    # Static values:
    interpretationCenter = 'IMPC'
    evidenceCode = 'EXP'
    strainName = 'Not Specified'  # for now
    print 'creating json object'
    jFile = json.load(fpIMPC)
    print 'done creating json object'
    for f in jFile['response']['docs']:
	# exclude europhenome for now
	# 8/20 - decided to restrict to impc data via mirror_wget
	#if f['resource_name'] == 'EuroPhenome':
	#    continue

	error = 0

	phenotypingCenter = f['phenotyping_center']
	mpID = f['mp_term_id']
	alleleID = alleleID2 = f['allele_accession_id']
	alleleState = f['zygosity']
	alleleSymbol = f['allele_symbol']
	markerID = f['marker_accession_id']
	gender = f['sex']
	colonyID = f['colony_id']

	# line representing data from the input file for reporting
	reportLine = phenotypingCenter + '\t' + \
                     interpretationCenter + '\t' + \
                     mutantID + '\t' + \
                     mpID + '\t' + \
                     alleleID + '\t' + \
                     alleleState + '\t' + \
                     alleleSymbol + '\t' + \
                     markerID + '\t' + \
                     evidenceCode + '\t' + \
                     strainName + '\t' + \
                     gender + '\t' + \
		     colonyID + '\n'

	# skip if no MP annotation ID
        if phenotypingCenter == '' or mpID == '' or alleleID == '' or \
	    alleleState == '' or markerID == '' or  gender == '' or \
	    colonyID == '':
            fpHTMPSkip.write(reportLine)
            continue

	if not colonyToMCLDict.has_key(colonyID):
	    msg='No imits2 colony id for %s' % colonyID
	    logit = errorDisplay % (msg, reportLine) 
	    fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	if alleleState.lower() == 'heterozygote':
	    alleleState = 'Heterozygous'
	elif alleleState.lower() == 'homozygote':
	    alleleState = 'Homozygous'
	elif alleleState.lower() == 'hemizygote':
	    alleleState = 'Hemizygous'
	else:
	    msg = 'Unrecognized allele state %s' % alleleState
	    logit = errorDisplay % (msg, reportLine)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	if gender.lower() == 'male':
	    gender = 'Male'
	elif gender.lower() == 'female':
	    gender = 'Female'
	else:
	    msg = 'Unrecognized gender %s' % gender
	    logit = errorDisplay % (msg, reportLine)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	# if error, continue to next line
        if error:
            fpHTMPError.write(reportLine)
            continue

	# now resolve the  colony id to the mutantID in the iMits2 data
	mutantID = colonyToMCLDict[colonyID]

	# line containing resolved data for writing to load input file
        line = phenotypingCenter + '\t' + \
                     interpretationCenter + '\t' + \
                     mutantID + '\t' + \
                     mpID + '\t' + \
                     alleleID + '\t' + \
                     alleleState + '\t' + \
                     alleleSymbol + '\t' + \
                     markerID + '\t' + \
                     evidenceCode + '\t' + \
                     strainName + '\t' + \
                     gender + '\t' + \
		     colonyID + '\n'
	lineSet.add(line)
    for line in lineSet:
	fpHTMP.write(line)
    return 0

#
#  MAIN
#

print 'initialize'
if initialize() != 0:
    sys.exit(1)
print 'openFiles'
if openFiles() != 0:
    sys.exit(1)
print 'createHTMPfile'
if createHTMPfile() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

