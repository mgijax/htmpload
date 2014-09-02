#!/usr/local/bin/python
#
#  makeSanger.py
###########################################################################
#
#  Purpose:
#
#      This script will parse Sanger input file to
#      create a High-Throughput MP input file
#
#  Usage:
#
#      makeSanger.py
#
#  Env Vars:
#
#	See the configuration file (sangermpload.config)

#  Inputs:
#
#      Sanger input file (${SOURCE_COPY_INPUT_FILE})
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
#  08/15/2014	sc
#	- TR11674
#
###########################################################################

import sys 
import os
import string

# Input 
sangerFile = None

# Outputs 
htmpFile = None
logDiagFile = None
logCurFile = None
htmpErrorFile = None
htmpSkipFile = None

# file pointers
# Inputs
fpSanger = None
# Outputs
fpHTMP = None
fpLogDiag = None
fpLogCur = None
fpHTMPError = None
fpHTMPSkip = None

errorDisplay = '''

***********
error:%s
line: %s
field: %s
%s
'''

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global sangerFile, htmpFile
    global logDiagFile, logCurFile, htmpErrorFile, htmpSkipFile

    sangerFile = os.getenv('SOURCE_COPY_INPUT_FILE')
    htmpFile = os.getenv('HTMP_INPUT_FILE')
    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    htmpSkipFile = os.getenv('HTMPSKIP_INPUT_FILE')
    print 'sangerFile: %s' % sangerFile
    print 'htmpFile: %s' % htmpFile
    print 'htmpErrorFile: %s' % htmpErrorFile
    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not sangerFile:
        print 'Environment variable not set: SOURCE_COPY_INPUT_FILE'
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
    global fpSanger, fpHTMP
    global fpLogDiag, fpLogCur, fpHTMPError, fpHTMPSkip

    #
    # Open the Sanger file
    #
    try:
        fpSanger = open(sangerFile, 'r')
    except:
        print 'Cannot open file: ' + sangerFile
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
	fpLogCur.write('\n\nmakeSanger Log\n\n')
    except:
        print 'Cannot open file: ' + logCurFile
        return 1

    #
    # Open the Error file
    #
    try:
        fpHTMPError = open(htmpErrorFile, 'w')
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
    if fpSanger:
        fpSanger.close()

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
# Purpose: Read Sanger input file and re-format it to create a 
#    High-Throughpug MP input file
# Returns: 0
# Assumes: input/output files exist and have been opened
# Effects: writes to the file system
# Throws: Nothing
#
def createHTMPfile():
    # all Strains will use 'Not Specified'
    strainName = 'Not Specified'
    lineNum = 0
    for line in fpSanger.readlines():
	lineNum += 1
 	error = 0

	tokens = line[:-1].split('\t')
	print 'line %s: %s ' % (lineNum, line)
	phenotypingCenter = tokens[0]
	print 'phenotypingCenter ' + phenotypingCenter
        annotationCenter = tokens[1]
	print 'annotationCenter ' + annotationCenter
        mutantID = tokens[2]
	print 'mutantID: %s' % mutantID
	mutantID2 =  mutantID
        mpID = tokens[3]
        alleleID = tokens[4]
	alleleID2 = alleleID
        alleleState = tokens[5]
        alleleSymbol = tokens[6]
        markerID = tokens[7]
	evidenceCode = tokens[8]
        gender = tokens[10]
	remaining = ''
	if len(tokens) > 10:
	    remaining = tokens[11:]
	remaining = string.join(remaining, '\t')

        # skip - checking allele symbol and mpID before checking the pheno
	# and annot centers is required, so factored them out of makeGenotype
        if alleleSymbol.find('not yet available') >= 0:
            fpHTMPSkip.write(line)
            continue

        # skip if no MP annotation ID
        if mpID == '':
            fpHTMPSkip.write(line)
            continue

        if phenotypingCenter not in ['WTSI', 'Europhenome']:
            logit = errorDisplay % (phenotypingCenter, lineNum, '1', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

        if annotationCenter not in ['WTSI', 'Europhenome']:
            logit = errorDisplay % (annotationCenter, lineNum, '2', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

        if gender not in ('Male', 'Female', 'Both', ''):
            logit = errorDisplay % (gender, lineNum, '11', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	
        # if error, continue to next line
        if error:
            fpHTMPError.write(line)
            continue

        #
	# format allele state
        # blank = Indeterminate
        # Hom => Homozygous
        # Het => Heterozygous
        #

        if alleleState == '':
            alleleState = 'Indeterminate'
	alleleState = alleleState.replace('Hom', 'Homozygous')
        alleleState = alleleState.replace('Het', 'Heterozygous')
	alleleState = alleleState.replace('Hemi', 'Hemizygous')
        line = phenotypingCenter + '\t' + \
                     annotationCenter + '\t' + \
                     mutantID + '\t' + \
                     mpID + '\t' + \
                     alleleID + '\t' + \
                     alleleState + '\t' + \
                     alleleSymbol + '\t' + \
                     markerID + '\t' + \
                     evidenceCode + '\t' + \
                     strainName + '\t' + \
                     gender 
	if remaining != '':
	    line = line + '\t' + remaining + '\n'
	else:
	    line = line + '\n'
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

