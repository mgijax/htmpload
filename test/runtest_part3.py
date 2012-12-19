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
# SexF : Find the correct genotype, details don't really matter.
#	Find the MP annotation. Verify the sex value = Female.  
#	This covers several cases we need to verify were handled correctly.
#
# SexM : Find the correct genotype, details don't really matter.
#	Find the MP annotation. Verify the sex value = Male.  
#	This covers several cases we need to verify were handled correctly.
#
# Germline: transmission = 'Germline' and Reference in ('J:165965', 'J:175295')
#
# CellLine: transmission = 'Cell Line'
#
# Chimeric: transmission = 'Chimeric' and Reference not in ('J:165965', 'J:175295')
#
# NotApplicable: transmission = 'Not Applicable'
#
# NotSpecified: transmission = 'Not Specified'
#
# GermlineOld: transmission = 'Germline' and Reference not in ('J:165965', 'J:175295')
#
# Used-FC: Allele contains Used-FC Reference
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
usedfc = ''
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
# Used-FC
#
testDisplay = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n'

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
	    testName = ''

        if len(testName) == 0:
	    testName = 'automated test'

        if testName == 'automated test':

	    if alleleState == 'Hom':
	        verifyAnnotHom()
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

	elif testName == 'SexF':
	    verifySexF()

	elif testName == 'SexM':
	    verifySexM()

	elif testName == 'Germline':
	    verifyGermline()

	elif testName == 'CellLine':
	    verifyCellLine()

	elif testName == 'Chimeric':
	    verifyChimeric()

	elif testName == 'NotSpecified':
	    verifyNotSpecified()

	elif testName == 'NotApplicable':
	    verifyNotApplicable()

	elif testName == 'GermlineOld':
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
	    (testPassed, 'duplicate genotypes', '', '', '', '', '', '', '', '', '', ''))
    else:
	for r in results:
	    alleleSymbol = r['alleleSymbol']
	    markerID = r['markerID']
	    alleleID = r['alleleID']
	    mutantID = r['mutantID']
	    alleleStatus = r['alleleState']
            fpLogTest.write(testDisplay % \
	        (testPassed, 'duplicate genotypes', '', '', \
                 alleleSymbol, markerID, alleleID, mutantID, \
                 alleleState, '', '', '', ''))

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
         alleleState, gender, '', ''))

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
         alleleState, gender, '', ''))

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
         alleleState, gender, '', ''))

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
         alleleState, gender, '', ''))

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
         alleleState, gender, '', ''))

    return 0

#
# SexF : Find the correct genotype, details don't really matter.
#	Find the MP annotation. Verify the sex value = Female.  
#	This covers several cases we need to verify were handled correctly.
#
def verifySexF():

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
	and p.value = 'F'
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
         alleleState, gender, '', ''))

    return 0

#
# SexM : Find the correct genotype, details don't really matter.
#	Find the MP annotation. Verify the sex value = Male.  
#	This covers several cases we need to verify were handled correctly.
#
def verifySexM():

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
	and p.value = 'M'
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
         alleleState, gender, '', ''))

    return 0

#
# Germline:
#
# Allele contains Germ Line Transmission = Germline (3982951)
# Allele contains Transmission Reference = see references above
# Allele contains Used-FC Reference = see references above
#
def verifyGermline():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa, 
	     BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982951)
     	and g._Marker_key = ma._Object_key
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and g._Allele_key = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
	and exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Transmission')
	and exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Used-FC')
	''' % (markerID, alleleID)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, transmission, usedfc))

    return 0

#
# CellLine:
#
# Allele contains Germ Line Transmission = CellLine (3982953)
# Allele contains Transmission Reference = see references above
# Allele contains Used-FC Reference = see references above
#
def verifyCellLine():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa, 
	     BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982953)
     	and ma._MGIType_key = 2
     	and ma._LogicalDB_key = 1
     	and ma.accID = '%s'
     	and g._Allele_key = aa1._Object_key
     	and aa1._MGIType_key = 11
     	and aa1._LogicalDB_key = 1
     	and aa1.accID = '%s'
	and not exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Transmission')
	and exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Used-FC')
	''' % (markerID, alleleID)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	(testPassed, testName, lineNum, \
         mpID, alleleSymbol, markerID, alleleID, mutantID, \
         alleleState, gender, transmission, usedfc))

    return 0

#
# Chimeric:
#
# Allele contains Germ Line Transmission = Chimeric (3982952)
#
def verifyChimeric():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa, 
	     BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982952)
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
         alleleState, gender, transmission, usedfc))

    return 0

#
# NotSpecified:
#
# Allele contains Germ Line Transmission = Not Specified (3982954)
#
def verifyNotSpecified():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa, 
	     BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982954)
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
         alleleState, gender, transmission, usedfc))

    return 0

#
# NotApplicable:
#
# Allele contains Germ Line Transmission = Not Applicable (3982955)
#
def verifyNotApplicable():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa, 
	     BIB_Citation_Cache c, ACC_Accession ma, ACC_Accession aa1
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and aa._Transmission_key in (3982955)
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
         alleleState, gender, transmission, usedfc))

    return 0

#
# Used-FC1:
#
# Allele contains Genotype/MP Annotation to J: but Allele does not contain Used-FC reference
#
def verifyUsedFC1():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and exists (select 1 from VOC_Annot a, VOC_Evidence e, ACC_Accession r
		where g._Genotype_key = a._Object_key
		and a._AnnotType_key = 1002
		and a._Annot_key = e._Annot_key
		and e._Refs_key = r._Object_key
		and r._MGIType_key = 1
		and r.prefixPart = 'J:'
		and r.accID = '%s')
	and not exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Used-FC'
		and v.jnumID = '%s')
	''' % (jnum, jnum)

    #print query
    results = db.sql(query, 'auto')
    if len(results) == 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	    (testPassed, 'all MP Annotations contain a Used-FC reference', '', '', '', '', '', '', '', '', '', ''))

    return 0

#
# Used-FC2:
#
# Allele that contains Used-FC reference to J: also contains Genotype/MP Annotation
#
def verifyUsedFC2():

    global mutantID, mpID, alleleID, alleleState, alleleSymbol
    global markerID, gender, transmission, usedfc
    global testName, testPassed, query

    query = '''
	select g._Allele_key
	from GXD_AlleleGenotype g, ALL_Allele aa
	where g._Allele_key = aa._Allele_key
	and aa.isWildType = 0
	and exists (select 1 from VOC_Annot a, VOC_Evidence e, ACC_Accession r
		where g._Genotype_key = a._Object_key
		and a._AnnotType_key = 1002
		and a._Annot_key = e._Annot_key
		and e._Refs_key = r._Object_key
		and r._MGIType_key = 1
		and r.prefixPart = 'J:'
		and r.accID = '%s')
	and exists (select 1 from MGI_Reference_Allele_View v
		where aa._Allele_key = v._Object_key
		and v.assocType = 'Used-FC'
		and v.jnumID = '%s')
	''' % (jnum, jnum)

    #print query
    results = db.sql(query, 'auto')
    if len(results) > 0:
        testPassed = 'pass'

    fpLogTest.write(testDisplay % \
	    (testPassed, 'all Used-FC contain at least one MP annotation', '', '', '', '', '', '', '', '', '', ''))

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

if verifyUsedFC1() != 0:
    closeFiles()
    sys.exit(1)

if verifyUsedFC2() != 0:
    closeFiles()
    sys.exit(1)

if htmpTest() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

