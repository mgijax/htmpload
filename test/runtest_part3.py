#!/usr/local/bin/python
#
#  runtest_part3.py
###########################################################################
#
#  Purpose:
#
#  Usage:
#
#      runtest_part3.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#	LOG_TEST
#	HTMPUNIQ_INPUT_FILE
#	HTMPDUP_INPUT_FILE
#
# VerifyAnnotHom : Find the genotype (should be homozygous). 
#	Verify Allele1=Allele2.  
#	Verify MCL1=MCL2 where they exist. 
#	Verify the MP annotation is associated and has the given Sex value.
#
# VerifyAnnotHet : Find the genotype (should be heterozygous). 
#	Verify Allele1. Verify Allele2 is wild type.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
# VerifyAnnotHemi : Find the genotype (should be hemizygous x-linked). 
#	Verify Allele1. Verify Allele2 = null.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
# VerifyAnnotIndet : Find the genotype (should be indeterminate). 
#	Verify Allele1. Verify Allele2 = null.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
# SexNA : Find the correct genotype, details don.t really matter.
#	Find the MP annotation. Verify the sex value = NA.  
#	This covers several cases we need to verify were handled correctly.
#
#  Inputs:
#
#      Sanger  file ($HTMPUNIQ_INPUT_FILE)
#
#       field 0: Genotype Order
#       field 1: Phenotyping Center (ex. 'WTSI')
#       field 2: Annotation Center (ex. 'WTSI')
#       field 3: ES Cell
#       field 4: MP ID
#       field 5: MGI Allele ID
#       field 6: Allele State (ex. 'Hom', 'Het', 'Hemi', '')
#       field 7: Allele Symbol
#       field 8: MGI Marker ID
#       field 9: Evidence Code (ex. 'EXP')
#       field 10: Strain Name
#       field 11: Gender ('Female', 'Male', 'Both')
#       field 12: Human-readable test infomration
#       field 13: SQL-Test Name
#
#      Sanger file ($HTMPDUP_INPUT_FILE)
#	same as Sanger BioMart file
#
#  Outputs:
#
#      LOG_TEST
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
#      5) Close files.
#
#  Notes:  None
#
#  10/24/2012	lec
#	- TR10273
#
###########################################################################

import sys 
import os
import db
import loadlib

# LOG_TEST
logTestFile = None

# HTMPUNIQ_INPUT_FILE
sangerFile = None

# HTMPDUP_INPUT_FILE
sangerDupFile = None

# file pointers
fpLogTest = None
fpSanger = None
fpSangerDup = None

lineNum = 0
mutantID = ''
mpID = ''
alleleID = ''
alleleState = ''
alleleSymbol = ''
markerID = ''
gender = ''
testName = ''
testPassed = 'fail'
query = ''

#
# test passed (pass, fail)
# testName
# line number
# MP
# Allele Symbol
# Marker
# Allele 1
# MCL 1
# Allele State
# Gender
#
testDisplay = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n'

# add check of Allele Detail Display
checkAlleleDetailDisplay = '''
	and exists (select 1 from MGI_Note n
		where n._MGIType_key = 12
		and n._NoteType_key = 1018
		and n._Object_key = g._Genotype_key)
	'''

# add check of MP header
checkMPHeader = ''

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global logTestFile, sangerFile, sangerDupFile
    global fpLogTest, fpSanger, fpSangerDup

    logTestFile = os.getenv('LOG_TEST')
    sangerFile = os.getenv('HTMPUNIQ_INPUT_FILE')
    sangerDupFile = os.getenv('HTMPDUP_INPUT_FILE')

    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not logTestFile:
        print 'Environment variable not set: LOG_TEST'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not sangerFile:
        print 'Environment variable not set: HTMPUNIQ_INPUT_FILE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not sangerDupFile:
        print 'Environment variable not set: HTMPDUP_INPUT_FILE'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpLogTest = None
    fpSanger = None
    fpSangerDup = None

    db.useOneConnection(1)

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpLogTest, fpSanger, fpSangerDup

    #
    # Open the Log Test file.
    #
    try:
        fpLogTest = open(logTestFile, 'a+')
    except:
        print 'Cannot open file: ' + logTestFile
        return 1

    #
    # Open the Sanger/BioMart file
    #
    try:
        fpSanger = open(sangerFile, 'r')
    except:
        print 'Cannot open file: ' + sangerFile
        return 1

    #
    # Open the Sanger/Dup file
    #
    try:
        fpSangerDup = open(sangerDupFile, 'r')
    except:
        print 'Cannot open file: ' + sangerDupFile
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

    if fpLogTest:
        fpLogTest.close()

    if fpSanger:
        fpSanger.close()

    if fpSangerDup:
        fpSangerDup.close()

    db.useOneConnection(0)

    return 0


#
# Purpose: Process the Sanger Test Input File
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def sangerTest():

    global lineNum
    global mutantID, mpID, alleleID, alleleState, alleleSymbol, markerID, gender
    global testName, testPassed, query

    lineNum = 0

    for line in fpSanger.readlines():

	lineNum = lineNum + 1

        tokens = line[:-1].split('\t')

	testPassed = 'fail'

	mutantID = tokens[3]
	mpID = tokens[4]
        alleleID = tokens[5]
        alleleState = tokens[6]
        alleleSymbol = tokens[7]
        markerID = tokens[8]
	gender = tokens[11]
	testName = tokens[13]

	if len(testName) == 0:
	    testPassed = 'pass'
	    testName = 'No Test Performed'
            fpLogTest.write(testDisplay % \
		(testPassed, testName, lineNum, \
                 mpID, alleleSymbol, markerID, alleleID, mutantID, \
                 alleleState, gender))
	    continue
	elif testName == 'VerifyAnnotHom':
	    verifyAnnotHom()
	elif testName == 'VerifyAnnotHet':
	    verifyAnnotHet()
	elif testName == 'VerifyAnnotHemi':
	    verifyAnnotHemi()
	elif testName == 'VerifyAnnotIndet':
	    verifyAnnotIndet()
	elif testName == 'SexNA':
	    verifySexNA()

    return 0

#
# VerifyAnnotHom : Find the genotype (should be homozygous). 
#	Verify Allele1=Allele2.  
#	Verify MCL1=MCL2 where they exist. 
#	Verify the MP annotation is associated and has the given Sex value.
#
def verifyAnnotHom():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender 
    global testName, testPassed, query

    if len(mutantID) > 0:
        mclQuery1 = ',ACC_Accession mcla1, ACC_Accession mcla2'
	mclQuery2 = '''
	    and ap._MutantCellLine_key_1 = mcla1._Object_key 
	    and mcla1.accID = '%s'
	    and ap._MutantCellLine_key_2 = mcla2._Object_key 
	    and mcla2.accID = '%s'
	    ''' % (mutantID, mutantID)
    else:
	mclQuery1 = ''
	mclQuery2 = '''
	    and ap._MutantCellLine_key_1 = null
	    and ap._MutantCellLine_key_2 = null
	    '''

    query = '''
	select g._Genotype_key
	from GXD_Genotype g, GXD_AllelePair ap,
     	     ACC_Accession ma, ACC_Accession aa1, ACC_Accession aa2,
             VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p, 
             ACC_Accession mp
	     %s
     	where g._Strain_key = -1
     	and g._Genotype_key = ap._Genotype_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and ap._Allele_key_1 = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
     	and ap._Allele_key_2 = aa2._Object_key
     	and aa2._MGIType_key = 11
     	and aa2._LogicalDB_key = 1
     	and aa2.accID = '%s'
	and ap._PairState_key = 847138
        and g._Genotype_key = a._Object_key
        and a._AnnotType_key = 1002
        and a._Term_key = mp._Object_key
        and mp.accID = '%s'
        and a._Annot_key = e._Annot_key
        and e._AnnotEvidence_key = p._AnnotEvidence_key
        and p._PropertyTerm_key = 8836535
	%s
	''' % (mclQuery1, markerID, alleleID, alleleID, mpID, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender))

    return 0

#
# VerifyAnnotHet : Find the genotype (should be heterozygous). 
#	Verify Allele1. Verify Allele2 is wild type.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
def verifyAnnotHet():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender
    global testName, testPassed, query

    if len(mutantID) > 0:
	mclQuery1 = ',ACC_Accession mcla1'
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = mcla1._Object_key 
		and mcla1.accID = '%s'
		''' % (mutantID)
    else:
	mclQuery1 = ''
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = null
		'''

    query = '''
	select g._Genotype_key
	from GXD_Genotype g, GXD_AllelePair ap,
     	     ACC_Accession ma, ACC_Accession aa1,
             VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p, 
             ACC_Accession mp,
	     ALL_Allele w
	     %s
     	where g._Strain_key = -1
     	and g._Genotype_key = ap._Genotype_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and ap._Allele_key_1 = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
	and ap._Allele_key_2 = w._Allele_key
	and w.isWildType = 1
	and ap._MutantCellLine_key_2 = null
	and ap._PairState_key = 847137
        and g._Genotype_key = a._Object_key
        and a._AnnotType_key = 1002
        and a._Term_key = mp._Object_key
        and mp.accID = '%s'
        and a._Annot_key = e._Annot_key
        and e._AnnotEvidence_key = p._AnnotEvidence_key
        and p._PropertyTerm_key = 8836535
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender))

    return 0

#
# VerifyAnnotHemi : Find the genotype (should be hemizygous x-linked). 
#	Verify Allele1. Verify Allele2 = null.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
def verifyAnnotHemi():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender 
    global testName, testPassed, query

    if len(mutantID) > 0:
        mclQuery1 = ',ACC_Accession mcla1'
        mclQuery2 = '''
		and ap._MutantCellLine_key_1 = mcla1._Object_key 
		and mcla1.accID = '%s'
		''' % (mutantID)
    else:
        mclQuery1 = ''
        mclQuery2 = '''
		and ap._MutantCellLine_key_1 = null
		'''

    query = '''
	select g._Genotype_key
	from GXD_Genotype g, GXD_AllelePair ap,
     	     ACC_Accession ma, ACC_Accession aa1,
             VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p, 
             ACC_Accession mp
	     %s
     	where g._Strain_key = -1
     	and g._Genotype_key = ap._Genotype_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and ap._Allele_key_1 = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
     	and ap._Allele_key_2 = null
	and ap._MutantCellLine_key_2 = null
	and ap._PairState_key in (847133, 847134)
        and g._Genotype_key = a._Object_key
        and a._AnnotType_key = 1002
        and a._Term_key = mp._Object_key
        and mp.accID = '%s'
        and a._Annot_key = e._Annot_key
        and e._AnnotEvidence_key = p._AnnotEvidence_key
        and p._PropertyTerm_key = 8836535
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender))

    return 0

#
# VerifyAnnotIndet : Find the genotype (should be indeterminate). 
#	Verify Allele1. Verify Allele2 = null.  
#	Verify MCL1 where it exists. Verify MCL2 = null. 
#	Verify the MP annotation is associated and has the given Sex value.
#
def verifyAnnotIndet():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender 
    global testName, testPassed, query

    if len(mutantID) > 0:
        mclQuery1 = ',ACC_Accession mcla1'
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = mcla1._Object_key 
		and mcla1.accID = '%s'
		''' % (mutantID)
    else:
	mclQuery1 = ''
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = null
		'''

    query = '''
	select g._Genotype_key
	from GXD_Genotype g, GXD_AllelePair ap,
     	     ACC_Accession ma, ACC_Accession aa1,
             VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p, 
             ACC_Accession mp
	     %s
     	where g._Strain_key = -1
     	and g._Genotype_key = ap._Genotype_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
    	and ap._Allele_key_1 = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
     	and ap._Allele_key_2 = null
	and ap._MutantCellLine_key_2 = null
	and ap._PairState_key = 847139
        and g._Genotype_key = a._Object_key
        and a._AnnotType_key = 1002
        and a._Term_key = mp._Object_key
        and mp.accID = '%s'
        and a._Annot_key = e._Annot_key
        and e._AnnotEvidence_key = p._AnnotEvidence_key
        and p._PropertyTerm_key = 8836535
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender))

    return 0

#
# SexNA : Find the correct genotype, details don.t really matter.
#	Find the MP annotation. Verify the sex value = NA.  
#	This covers several cases we need to verify were handled correctly.
#
def verifySexNA():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender 
    global testName, testPassed, query

    if len(mutantID) > 0:
        mclQuery1 = ',ACC_Accession mcla1'
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = mcla1._Object_key 
		and mcla1.accID = '%s'
		''' % (mutantID)
    else:
	mclQuery1 = ''
	mclQuery2 = '''
		and ap._MutantCellLine_key_1 = null
		'''

    query = '''
	select g._Genotype_key
	from GXD_Genotype g, GXD_AllelePair ap,
     	     ACC_Accession ma, ACC_Accession aa1,
             VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p, 
             ACC_Accession mp
	     %s
     	where g._Strain_key = -1
     	and g._Genotype_key = ap._Genotype_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and ap._Allele_key_1 = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
        and g._Genotype_key = a._Object_key
        and a._AnnotType_key = 1002
        and a._Term_key = mp._Object_key
        and mp.accID = '%s'
        and a._Annot_key = e._Annot_key
        and e._AnnotEvidence_key = p._AnnotEvidence_key
        and p._PropertyTerm_key = 8836535
	and p.value = 'NA'
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender))

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if sangerTest() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

