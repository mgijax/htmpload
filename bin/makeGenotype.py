#!/usr/local/bin/python
#
#  makeGenotype.py
###########################################################################
#
#  Purpose:
#
#      This script will read the data in the HTMP input file to:
#
#      1) verify the Genotype information in the input file
#
#      2) create new Genotype records, if necessary
#
#	Only genotypes that are created or modified by the 
#	    HTMP 'createdBy' user can be used otherwise a new Genotype
#	    will be added.
#	Genotypes that are created or modified by a curator *cannot* be used
#
#  Usage:
#
#      makeGenotype.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#    	   LOG_DIAG
#    	   LOG_CUR
#    	   HTMP_INPUT_FILE
#    	   HTMPDUP_INPUT_FILE
#    	   HTMPERROR_INPUT_FILE
#    	   HTMPUNIQ_INPUT_FILE
#    	   GENOTYPE_INPUT_FILE
#    	   CREATEDBY
#    	   JNUMBER
#
#  Inputs:
#
#      High Throughput MP file ($HTMP_INPUT_FILE)
#
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
#  Outputs:
#
#
#      input data that was merged (duplicates)
#      HTMPDUP_INPUT_FILE
#	  field 1-11
#
#      input data with errors
#      HTMPERROR_INPUT_FILE
#	  field 1-11
#
#      these output files contain the genotype # so that we can associate
#      the genotype fields (4,5,6,7,10) with the appropriate genotype ID
#
#      HTMPUNIQ_INPUT_FILE
#         field 0: Unique Genotype Sequence Number 
#	  field 1-11
#
#      GENOTYPE_INPUT_FILE
#	  input for genotypeload-er + genotype #
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
#      3) Verify Genotype
#      4) If new Genotype is needed, write to GENOTYPE_INPUT_FILE
#      5) Close files.
#
#  Notes:  None
#
#  08-15-2014	sc
#	- TR11674 - HDP-2/IMPC project
#	- make generic - factor proprietary sanger code out into preprocessor
#
#  09/04/2012	lec
#	- TR10273
#
###########################################################################

import sys 
import os
import db
import loadlib
import sourceloadlib
import alleleloadlib

# LOG_DIAG
# LOG_CUR
logDiagFile = None
logCurFile = None

# HTMP_INPUT_FILE
htmpInputFile = None

# HTMPDUP_INPUT_FILE
htmpDupFile = None

# HTMPERROR_INPUT_FILE
htmpErrorFile = None

# HTMPUNIQ_INPUT_FILE
HTMPFile = None

# GENOTYPE_INPUT_FILE
genotypeFile = None

# file pointers
fpLogDiag = None
fpLogCur = None
fpHTMPInput = None
fpHTMPDup = None
fpHTMPError = None
fpHTMP = None
fpGenotype = None

# see genotypeload/genotypeload.py for format
genotypeLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n'

# defaults
conditional = 'no'
existsAs = 'Mouse Line'
compound = 'Not Applicable'
generalNote = ''
privateNote = ''
createdBy = ''
jnumber = ''

loaddate = loadlib.loaddate

errorDisplay = '''

***********
error:%s
line: %s
field: %s
%s
'''

#
# key = str(markerKey) + str(alleleKey) + str(alleleState) + str(strainKey)
# value = genotypeOrder
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
    global logDiagFile, logCurFile
    global htmpInputFile, htmpDupFile, htmpErrorFile, HTMPFile
    global genotypeFile, createdBy, jnumber

    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpInputFile = os.getenv('HTMP_INPUT_FILE')
    htmpDupFile = os.getenv('HTMPDUP_INPUT_FILE')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    HTMPFile = os.getenv('HTMPUNIQ_INPUT_FILE')
    genotypeFile = os.getenv('GENOTYPE_INPUT_FILE')
    createdBy = os.getenv('CREATEDBY')
    jnumber = os.getenv('JNUMBER')

    rc = 0

    #
    # Make sure the environment variables are set.
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

    #
    # Make sure the environment variables are set.
    #
    if not htmpInputFile:
        print 'Environment variable not set: INPUTDIR/HTMP_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not htmpDupFile:
        print 'Environment variable not set: HTMPDUP_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not htmpErrorFile:
        print 'Environment variable not set: HTMPERROR_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not HTMPFile:
        print 'Environment variable not set: HTMP_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not genotypeFile:
        print 'Environment variable not set: GENOTYPE_INPUT_FILE'
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
    global fpHTMPInput, fpHTMPDup, fpHTMPError, fpHTMP
    global fpGenotype

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
    # Open the HTMP input file
    #
    try:
        fpHTMPInput = open(htmpInputFile, 'r')
    except:
        print 'Cannot open file: ' + htmpInputFile
        return 1

    #
    # Open the Dup file
    #
    try:
        fpHTMPDup = open(htmpDupFile, 'w')
    except:
        print 'Cannot open file: ' + htmpDupFile
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
    # Open the file with genotype sequence #
    #
    try:
        fpHTMP = open(HTMPFile, 'w')
    except:
        print 'Cannot open file: ' + HTMPFile
        return 1

    #
    # Open the genotype file.
    #
    try:
        fpGenotype = open(genotypeFile, 'w')
    except:
        print 'Cannot open genotype file: ' + genotypeFile
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

    if fpHTMPInput:
        fpHTMPInput.close()

    if fpHTMPDup:
        fpHTMPDup.close()

    if fpHTMPError:
        fpHTMPError.close()

    if fpHTMP:
        fpHTMP.close()

    if fpGenotype:
        fpGenotype.close()

    db.useOneConnection(0)

    return 0


#
# Purpose: Read the HTMP file to verify the Genotypes or create new 
#	     Genotype input file
# Returns: 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def getGenotypes():

    global genotypeOrderDict

    lineNum = 0
    genotypeOrder = 1

    currentMP = ''
    prevMP = ''
    prevRow = ''
    prevGender = ''

    #
    # grab/save existing genotypes
    #
    db.sql('''
        select a.accID, ap.*, t.term
	into #genotypes
        from GXD_Genotype g, GXD_AllelePair ap, 
             ACC_Accession a, GXD_AllelePair app, VOC_Term t, 
	     MGI_User u1, MGI_User u2
        where g._Genotype_key = a._Object_key
        and a._MGIType_key = 12
        and a._LogicalDB_key = 1
        and a.preferred = 1
	and g.isConditional = 0
        and g._Genotype_key = ap._Genotype_key
        and g._Genotype_key = app._Genotype_key
        and ap._PairState_key = t._Term_key
        and t._Vocab_key = 39
        and g._CreatedBy_key = u1._User_key
	and u1.login = '%s'
        and g._ModifiedBy_key = u2._User_key
	and u2.login = '%s'
	''' % (createdBy, createdBy), None)
        #/*and g._Strain_key = %s */
	#''' % (strainKey, createdBy, createdBy), None)

    db.sql('''create index idx1 on #genotypes(_Marker_key)''', None)

    for line in fpHTMPInput.readlines():

	error = 0
	lineNum = lineNum + 1

	#print lineNum, line

        tokens = line[:-1].split('\t')

	genotypeID = ''

	phenotypingCenter = tokens[0]
	annotationCenter = tokens[1]

	mutantID = tokens[2]
	mutantID2 = mutantID
	mpID = tokens[3]
        alleleID = tokens[4]
	alleleID2 = alleleID
        alleleState = tokens[5]
        alleleSymbol = tokens[6]
        markerID = tokens[7]
	strainName= tokens[9]
        gender = tokens[10]

	# marker

	if len(markerID) > 0:
            markerKey = loadlib.verifyMarker(markerID, lineNum, fpLogDiag)
        else:
	    markerKey = 0

        if markerKey == 0:
            logit = errorDisplay % (markerID, lineNum, '8', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	# allele

	if len(alleleID) > 0:
            alleleKey = loadlib.verifyObject(alleleID, 11, None, lineNum, fpLogDiag)
        else:
	    alleleKey = 0

        if alleleKey == 0:
            logit = errorDisplay % (alleleID, lineNum, '5', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1
	
	# mutant

	if len(mutantID) > 0:
	    mutantKey = alleleloadlib.verifyMutnatCellLineByAllele(mutantID, alleleKey, lineNum, fpLogDiag)
        else:
	    mutantKey = 'null'

        if mutantKey == 0:
            logit = errorDisplay % (mutantID, lineNum, '3', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
            error = 1

	strainID = sourceloadlib.verifyStrainID(strainName, 0, fpLogDiag)
	strainKey = sourceloadlib.verifyStrain(strainName, 0, fpLogDiag)

	# if allele is 'Heterzygous', then marker must have a wild-type allele
        if alleleState == 'Heterozygous':

	    #
	    # for heterzygous, allele 2 = the wild type allele 
	    #    (marker symbol + '<+>')
	    # find the wild type allele accession id
	    #

	    querySQL = '''
		select awt.accID
			from ALL_Allele wt, ACC_Accession awt
			where wt._Marker_key = %s
			and wt.name = 'wild type'
			and wt._Allele_key = awt._Object_key
		        and awt._MGIType_key = 11
		        and awt._LogicalDB_key = 1
		        and awt.preferred = 1
		''' % (markerKey)

	    print querySQL
	    results = db.sql(querySQL, 'auto')
	    for r in results:
		# found the wild type, so set it
		alleleID2 = r['accID']
		mutantID2 = ''

	    if alleleID == alleleID2:
                logit = errorDisplay % (markerID, lineNum, '8', line)
	        logit = logit + 'no wild type allele exists for this marker'
                fpLogDiag.write(logit)
                fpLogCur.write(logit)
                error = 1

        # if error, continue to next line
        if error:
	    fpHTMPError.write(line)
            continue

	# verify that the Allele ID matches the Allele Symbol
	# currently, this is not an error...just an FYI 
	if len(alleleID) > 0:

		checkAllele = '''
			select a.*
			from ALL_Allele a, ACC_Accession aa
			where a.symbol = '%s'
			and a._Allele_key = aa._Object_key
			and aa._MGIType_key = 11
			and aa.accID = '%s'
			''' % (alleleSymbol, alleleID)

		results = db.sql(checkAllele, 'auto')
		if len(results) == 0:
		    checkAllele = '''
			select a.symbol
			from ALL_Allele a, ACC_Accession aa
			where a._Allele_key = aa._Object_key
			and aa._MGIType_key = 11
			and aa.accID = '%s'
			''' % (alleleID)
		    results = db.sql(checkAllele, 'auto')
		    for r in results:
		        print alleleID, alleleSymbol, r['symbol']

	#
	# check alleleState
	#

        if alleleState == 'Homozygous':

	    querySQL = '''
		select g.accID
			from #genotypes g
			where g._Marker_key = %s
			and g._Allele_key_1 = %s
			and g._Allele_key_2 = %s
			and g._MutantCellLine_key_1 = %s
			and g._MutantCellLine_key_2 = %s
			and g.term = '%s'
		''' % (markerKey, alleleKey, alleleKey, mutantKey, mutantKey, alleleState)

	    #print querySQL
	    results = db.sql(querySQL, 'auto')
	    for r in results:
		genotypeID = r['accID']

        elif alleleState == 'Heterozygous':

	    #
	    # for heterzygous, allele 2 = the wild type allele 
	    #   (marker symbol + '<+>')
	    # find the wild type allele accession id
	    #

	    querySQL = '''
		select g.accID
			from #genotypes g
			where g._Marker_key = %s
			and g._Allele_key_1 = %s
			and g._Allele_key_2 != %s
			and g._MutantCellLine_key_1 = %s
			and g._MutantCellLine_key_2 = null
			and g.term = '%s'
		''' % (markerKey, alleleKey, alleleKey, mutantKey, alleleState)

	    #print querySQL
	    results = db.sql(querySQL, 'auto')
	    for r in results:
		genotypeID = r['accID']

	elif alleleState in ('Hemizygous', 'Indeterminate'):

	    alleleID2 = ''
	    mutantID2 = ''

	    if alleleState == 'Hemizygous':
	        querySQL = '''select chromosome 
			from MRK_Marker 
			where _Marker_key = %s''' % markerKey
	        results = db.sql(querySQL, 'auto')
	        for r in results:
		    if r['chromosome'] == 'X':
		        alleleState = 'Hemizygous X-linked'
		    elif r['chromosome'] == 'Y':
		        alleleState = 'Hemizygous Y-linked'
		    else:
            		logit = errorDisplay % (alleleState, lineNum, '6', line)
			logit = logit + 'pair state %s does not match chromosome %s' % (alleleState, r['chromosome'])
            		fpLogDiag.write(logit)
            		fpLogCur.write(logit)
	    		error = 1
			break

	    querySQL = '''
		select g.accID
			from #genotypes g
			where g._Marker_key = %s
			and g._Allele_key_1 = %s
			and g._Allele_key_2 = null
			and g._MutantCellLine_key_1 = %s
			and g._MutantCellLine_key_2 = null
			and g.term = '%s'
		''' % (markerKey, alleleKey, mutantKey, alleleState)

	    #print querySQL
	    results = db.sql(querySQL, 'auto')
	    for r in results:
		genotypeID = r['accID']

	else:
            logit = errorDisplay % (alleleState, lineNum, '6', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
	    error = 1

        # if error, continue to next line
        if error:
	    fpHTMPError.write(line)
            continue

	#
	# check genotype unique-ness
	#

	dupGeno = 0
	useOrder = str(genotypeOrder)

	#
	# set uniqueness
	# isConditional is always 0, so we do not need to specify this value
	#
	key = str(markerKey) + str(alleleKey) + str(alleleState) + \
		str(strainKey) + str(mutantKey)
	if genotypeOrderDict.has_key(key):
	    dupGeno = 1
	    useOrder = str(genotypeOrderDict[key])

	#
	# check for duplicate gender within the same annotation
	# assumes that the duplicates are next to each other in the input file
	# if 2 consecutive rows are the same (based on genotype order & MP)
	#    then: set the prevRow male/female to 'both'
	#    write the prevRow
	#    do not write the current row (the duplicate) by setting prevMP = ''
	#
	currentMP = useOrder + mpID

	if currentMP == prevMP:
	    # if current gender != previous gender, then merge as "Both" (NA)
	    # else leave gender as is
	    if gender != prevGender:
	        prevRow = prevRow.replace('Male', 'Both')
	        prevRow = prevRow.replace('Female', 'Both')
	    fpHTMP.write(prevRow)
	    prevMP = ''
	else:
	    if prevMP != '':
	        fpHTMP.write(prevRow)
	    elif lineNum > 1:
	        fpHTMPDup.write(prevRow)
            prevMP = currentMP
	    prevRow = useOrder + '\t' + line
	    prevGender = gender

	if dupGeno:
	    continue

	# save genotype order
        genotypeOrderDict[key] = genotypeOrder

	#
	# add to genotype mgi-format file
	#
	fpGenotype.write(genotypeLine % (\
		genotypeOrder, genotypeID, strainID, strainName, \
		markerID, alleleID, mutantID, alleleID2, mutantID2, \
		conditional, existsAs, generalNote, privateNote, alleleState, \
		compound, createdBy))

	genotypeOrder = genotypeOrder + 1

    # don't forget the last row
    fpHTMP.write(prevRow)

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

print 'get genotypes'
if getGenotypes() != 0:
    closeFiles()
    sys.exit(1)

print 'close files'
closeFiles()
sys.exit(0)

