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
# SexNA : Find the correct genotype, details don't really matter.
#	Find the MP annotation. Verify the sex value = NA.  
#	This covers several cases we need to verify were handled correctly.
#
# CellLine: transmission = 'Cell Line'
#
# Germline: transmission = 'Germline' and Reference in ('J:165965', 'J:175295')
#
# Chimeric: transmission = 'Chimeric' and Reference not in ('J:165965', 'J:175295')
#
# NotApplicable: transmission = 'Not Applicable'
#
# NotSpecified: transmission = 'Not Specified'
#
# GermlineOld: transmission = 'Germline' and Reference not in ('J:165965', 'J:175295')
#
#  Inputs:
#
#      HTMP file ($HTMPUNIQ_INPUT_FILE)
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
htmpFile = None

# file pointers
fpLogTest = None
fpHTMP = None

lineNum = 0
mutantID = ''
mpID = ''
alleleID = ''
alleleState = ''
alleleSymbol = ''
markerID = ''
gender = ''
transmission = 'Germline'
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
# Germline Transmission
#
testDisplay = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n'

# add check of Allele Detail Display
checkAlleleDetailDisplay = '''
	and exists (select 1 from MGI_Note n
		where n._MGIType_key = 12
		and n._NoteType_key = 1018
		and n._Object_key = g._Genotype_key)
	'''

# add check of MP header
checkMPHeader = ''

createdby = os.environ['CREATEDBY']
jnum = os.environ['JNUMBER']

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global logTestFile, htmpFile
    global fpLogTest, fpHTMP

    logTestFile = os.getenv('LOG_TEST')
    htmpFile = os.getenv('HTMPUNIQ_INPUT_FILE')

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
    if not htmpFile:
        print 'Environment variable not set: HTMPUNIQ_INPUT_FILE'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpLogTest = None
    fpHTMP = None

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
    global fpLogTest, fpHTMP

    #
    # Open the Log Test file.
    #
    try:
        fpLogTest = open(logTestFile, 'a+')
    except:
        print 'Cannot open file: ' + logTestFile
        return 1

    #
    # Open the HTMP/BioMart file
    #
    try:
        fpHTMP = open(htmpFile, 'r')
    except:
        print 'Cannot open file: ' + htmpFile
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

    if fpHTMP:
        fpHTMP.close()

    db.useOneConnection(0)

    return 0


#
# Purpose: Process the HTMP Test Input File
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def htmpTest():

    global lineNum
    global mutantID, mpID, alleleID, alleleState, alleleSymbol, markerID, gender
    global testName, testPassed, query

    lineNum = 0

    for line in fpHTMP.readlines():

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

	try:
	    testName = tokens[13]
        except:
	    testName = 'automated test'

        if testName == 'automated test':

	    if alleleState == 'Hom':
	        verifyAnnotHom()
		verifyGermline()
	    elif alleleState == 'Het':
	        verifyAnnotHet()
	    elif alleleState == 'Hemi':
	        verifyAnnotHemi()
	    else:
	        verifyAnnotIndet()

##	    else:
##		testPassed = 'pass'
##		testName = 'No Test Performed'
##		fpLogTest.write(testDisplay % \
##		    (testPassed, testName, lineNum, \
##                     mpID, alleleSymbol, markerID, alleleID, mutantID, \
##                     alleleState, gender))
##	        continue

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

	elif testName == 'Germline':
	    verifyGermline()

    return 0

#
# VerifyGenotype
#	- check if there are duplicate genotypes created by the HTMP load
#
def verifyGenotype():

    global testPassed

    query = '''
        select ap._Marker_key, ap._Allele_key_1, ap._Allele_key_2, 
	       ap._MutantCellLine_key_1, ap._MutantCellLine_key_2, ap._PairState_key
	into #allelepair
        from GXD_Genotype g, GXD_AllelePair ap, MGI_User u
        where g._Genotype_key = ap._Genotype_key
        and g._CreatedBy_key = u._User_key
	and u.login = '%s'
        group by _Marker_key, _Allele_key_1, _Allele_key_2, _MutantCellLine_key_1, _MutantCellLine_key_2, _PairState_key
        having count(*) > 1
	''' % (createdby)

    #print query
    db.sql(query, 'None')

    query2 = '''
	select a.symbol as alleleSymbol, ma.accID as markerID, aa.accID as alleleID,
		mcl.accID as mutantID, t.term as alleleState
	from #allelepair ap, ALL_Allele a, ACC_Accession ma, ACC_Accession aa, ACC_Accession mcl, VOC_Term t
	where ap._Allele_key_1 = a._Allele_key
     	and ap._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ap._Allele_key_1 = aa._Object_key
     	and aa._MGIType_key = 11
     	and aa._LogicalDB_key = 1
     	and ap._MutantCellLine_key_1 = mcl._Object_key
     	and mcl._MGIType_key = 28
	and ap._PairState_key = t._Term_key
	'''

    #print query2
    results = db.sql(query2, 'auto')
    if len(results) == 0:
        testPassed = 'pass'

        fpLogTest.write(testDisplay % \
	    (testPassed, 'duplicate genotypes', 0, 0, 0, 0, 0, 0, 0, 0, 0))
    else:
	for r in results:
	    alleleSymbol = r['alleleSymbol']
	    markerID = r['markerID']
	    alleleID = r['alleleID']
	    mutantID = r['mutantID']
	    alleleStatus = r['alleleState']
            fpLogTest.write(testDisplay % \
	        (testPassed, 'duplicate genotypes', 0, 0, \
                 alleleSymbol, markerID, alleleID, mutantID, \
                 alleleState, 0, 0))

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
             ACC_Accession mp, MGI_User u
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
	and g._CreatedBy_key = u._User_key
	and u.login = '%s'
	%s
	''' % (mclQuery1, markerID, alleleID, alleleID, mpID, createdby, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, 0))

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
             ACC_Accession mp, MGI_User u,
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
	and g._CreatedBy_key = u._User_key
	and u.login = '%s'
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, createdby, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, 0))

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
             ACC_Accession mp, MGI_User u
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
	and g._CreatedBy_key = u._User_key
	and u.login = '%s'
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, createdby, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, 0))

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
             ACC_Accession mp, MGI_User u
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
	and g._CreatedBy_key = u._User_key
	and u.login = '%s'
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, createdby, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, 0))

    return 0

#
# SexNA : Find the correct genotype, details don't really matter.
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
             ACC_Accession mp, MGI_User u
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
	and g._CreatedBy_key = u._User_key
	and u.login = '%s'
	%s
	''' % (mclQuery1, markerID, alleleID, mpID, createdby, mclQuery2)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, 0))

    return 0

#
# Germline: transmission = 'Germline' and Reference in ('J:165965', 'J:175295')
#
def verifyGermline():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, VOC_Annot a, VOC_Evidence e,
	     ALL_Allele aa, BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Genotype_key = a._Object_key
	and a._AnnotType_key = 1002
	and g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982951)
	and a._Annot_key = e._Annot_key
	and e._Refs_key = c._Refs_key
	and c.jnumID in ('J:165965', 'J:175295')
     	and g._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and g._Allele_key = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
	''' % (markerID, alleleID)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, transmission))

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if verifyGenotype() != 0:
    closeFiles()
    sys.exit(1)

if htmpTest() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

