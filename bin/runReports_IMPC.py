#!/usr/local/bin/python
#
#  runReports_IMPC.py
###########################################################################
#
#  Purpose:
#
#      This script will query the database comparing IMPC and IMITS colony IDs
#
#  Usage:
#
#      runReports_IMPC.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#    	   LOG_DIAG
#    	   LOG_CUR
#
#  Inputs:
#
#
#  Outputs:
#
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
#
#  Notes:  None
#
#  09-02-2014	sc
#	- TR11674 - HDP-2/IMPC project
#
###########################################################################

import sys 
import os
import db
import string

# LOG_DIAG
# LOG_CUR
logDiagFile = None
logCurFile = None

# file pointers
fpLogDiag = None
fpLogCur = None

TAB = '\t'
CRT = '\n'

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global logDiagFile, logCurFile

    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    rc = 0
    #
    if not logDiagFile:
        print 'Environment variable not set: LOG_DIAG'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not logCurFile:
        print 'Environment variable not set: LOG_CUR'
        rc = 1

    db.useOneConnection(1)

    return rc


#
# Purpose: Open files.
# Returns: 1 if file cannot be opened, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpLogDiag, fpLogCur

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
	fpLogCur.write('\n***********\nIMPC/IMITS Colony ID Discrepancies\n\n')
	fpLogCur.write('Allele\tIMPC\tIMITs\n')
    except:
        print 'Cannot open file: ' + logCurFile
        return 1

    return 0


#
# Purpose: Close files.
# Returns: 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def closeFiles():

    if fpLogDiag:
        fpLogDiag.close()

    if fpLogCur:
        fpLogCur.close()

    db.useOneConnection(0)

    return 0

#
# Purpose: report discrepancies between IMITS allele colony ID and IMPC strain
#	colony ID
# Returns: 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def createColonyIdReport():
    imitsDict = {}
    results = db.sql('''select distinct nc1.note as imitsCID, a._Allele_key
	from MGI_Note n1, MGI_NoteChunk nc1, ALL_Allele a
	where n1._NoteType_key = 1041
	and n1._MGIType_key = 11
	and n1._Note_key = nc1._Note_key
	and n1._Object_key = a._Allele_key''', 'auto')

    for r in results:
	imitsDict[r['_Allele_key']] = string.strip(r['imitsCID'])

    results = db.sql('''select distinct nc1.note as impcCID, aa.accID, a._Allele_key
	from MGI_Note n1, MGI_NoteChunk nc1, ALL_Allele a, GXD_AllelePair ap, 
	    GXD_Genotype g, ACC_Accession aa
	where n1._NoteType_key = 1012
	and n1._MGIType_key = 10
	and n1._Note_key = nc1._Note_key
	and n1._Object_key = g._Strain_key
	and g._Genotype_key = ap._Genotype_key
	and ap._Allele_key_1 = a._Allele_key
	and a._Allele_key = aa._Object_key
	and aa._MGIType_key = 11
	and aa._LogicalDB_key = 1
	and aa.preferred = 1
	and aa.prefixPart = 'MGI:'
	order by aa.accID ''', 'auto')

    for r in results:
	alleleKey = r['_Allele_key']
	accID = r['accID']
	id = string.strip(r['impcCID'])
	if imitsDict.has_key(alleleKey):
	    if id not in imitsDict[alleleKey]:
		fpLogCur.write('%s\t%s\t%s\n' % (accID, id, imitsDict[alleleKey]))

    return 0
	
#
#  MAIN
#
print 'initialize'
if initialize() != 0:
    sys.exit(1)

print 'open files'
if openFiles() != 0:
    sys.exit(1)

print 'create colony id report'
if createColonyIdReport() != 0:
    closeFiles()
    sys.exit(1)

print 'close files'
closeFiles()
sys.exit(0)

