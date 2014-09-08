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
#   htmpload format ($HTMP_INPUT_FILE):
#
#   1.  Phenotyping Center 
#   2.  Interpretation (Annotation) Center 
#   3.  ES Cell
#   4.  MP ID
#   5.  MGI Allele ID
#   6.  Allele State 
#   7.  Allele Symbol
#   8.  MGI Marker ID
#   9.  Evidence Code 
#   10. Strain Name
#   11. Gender 
#
#    IMPC strainload format file (${STRAIN_INPUT_FILE}
#
#    1. Strain Name
#    2. MGI Allele ID 
#    3. Strain Type
#    4. Strain Species
#    5. Standard 
#    6. Created By
#    7. Mutant ES Cell line of Origin note
#    8. Colony ID Note
#    9. Strain Attributes
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
#       1) initialize - get values from the environment, load lookup
#	    structures from the database
#	2) open input/output files
#	3) parse the iMits2 File into a data structure
#	4) parse the IMPC File into an intermediate file
#	5) create HTMP Load format file from IMPC/iMits2 data
#	6) close input/output files
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
import string
import Set
import db
import time

# strain constants
species = 'laboratory mouse'
standard = '1'
createdBy = 'htmpload'

# Input 
impcFile = None
impcFileInt = None
impcFileDup = None
imits2File = None

# Outputs 

htmpFile = None
strainFile = None
logDiagFile = None
logCurFile = None
htmpErrorFile = None
htmpSkipFile = None

# file pointers
fpIMPC = None
fpIMPCintWrite = None
fpIMPCintRead = None
fpIMPCdup = None
fpImits2 = None
fpHTMP = None
fpStrain = None
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

# iMits2 colony id mapped to iMits2 attributes
# {colonyId:'productionCtr|mutantID|markerID', ...}
colonyToMCLDict = {}

# colony ID to strain Name from the database
colonyToStrainNameDict = {}

# strain name mapped to colony id; colony id can be empty
strainNameToColonyIdDict = {}

# allele MGI ID from the database mapped to attributes
# {mgiID:Allele object, ...}
allelesInDbDict = {}

# unique key from input data mapped to error code, for strain processing
uniqStrainProcessingDict = {}

# processing center mapped to lab code from database
procCtrToLabCodeDict = {}

# Expected MGI ID to strain info mapping from configuration
strainInfoMapping = os.environ['STRAIN_INFO']

# Strain MGI ID to  strain raw prefix mapping from configuration
strainRawPrefixDict = {}

# Strain MGI ID to strain prefix mapping from configuration
strainPrefixDict = {}

# Strain MGI ID to strain template for creating strain nomen from configuration
strainTemplateDict = {}

# Strain MGI ID to strain type from configuration
strainTypeDict = {}

# Strain MGI ID to strain attributes from configuration
strainAttribDict = {}

#
# convenience object for allele information 
#
class Allele:
    def __init__(self, alleleID,    # string - allele  MGI ID
	    alleleSymbol,           # string - allele symbol
	    markerID, 		    # string - marker MGI ID
	    mutantIDs):		    # list - mcl IDs
	self.a = alleleID
	self.s = alleleSymbol
        self.m = markerID
	self.c = mutantIDs
#
# Purpose: Initialization  of variable with values from the environment
#	load lookup structures from the database
# Returns: 1 if environment variable not set
# Assumes: Nothing
# Effects: opens a database connection
# Throws: Nothing
#
def initialize():
    global impcFile, impcFileInt, impcFileDup, imits2File, htmpFile, strainFile
    global logDiagFile, logCurFile, htmpErrorFile, htmpSkipFile
    global allelesInDbDict, procCtrToLabCodeDict, strainInfoDict
    global strainPrefixDict, strainTemplateDict, strainTypeDict
    global colonyToStrainNameDict, strainNameToColonyIdDict

    impcFile = os.getenv('SOURCE_COPY_INPUT_FILE')
    impcFileInt = '%s_int' % impcFile
    impcFileDup = '%s_dup' % impcFile
    imits2File = os.getenv('IMITS2_COPY_INPUT_FILE')
    htmpFile = os.getenv('HTMP_INPUT_FILE')
    strainFile = os.getenv('STRAIN_INPUT_FILE')
    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    htmpSkipFile = os.getenv('HTMPSKIP_INPUT_FILE')

    #print 'impcFile: %s' % impcFile
    #print 'impcFileInt: %s' % impcFileInt
    #print 'imits2File: %s' % imits2File
    #print 'htmpFile: %s' % htmpFile
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

    # In Progress, Approved and Autoload allele status
    # Targeted allele type
    # preferred MGI IDs
    db.useOneConnection(1)
    db.sql('''select distinct a1.accid as alleleMgiID, a2.accid as markerMgiID, 
	    ll.symbol as aSymbol, ll._Allele_key
	into #a
	from ACC_Accession a1, ACC_Accession a2, ALL_Allele ll
	where ll._Allele_Status_key in (847111, 847114, 3983021)
	and ll._Allele_Type_key = 847116
	and ll._Allele_key = a1._Object_key
	and a1._MGIType_key = 11
	and a1.preferred = 1
	and a1.prefixPart = 'MGI:'
	and ll._Marker_key = a2._Object_key
	and a2._MGIType_key = 2
	and a2.preferred = 1
	and a2.prefixPart = 'MGI:' ''', None)

    db.sql('create index idx1 on #a(_Allele_key)', None)

    results = db.sql('''select distinct a.*, a1.accid as mclID
	from #a a, ACC_Accession a1, ALL_Allele_CellLine ac
	where a._Allele_key *= ac._Allele_key
	and ac._MutantCellLine_key *= a1._Object_key
	and a1._MGIType_key = 28
	and a1.preferred = 1''', 'auto')
    for r in results:
	a =  r['alleleMgiID']
	s = r['aSymbol']
	m = r['markerMgiID']
	c = r['mclID']
	if allelesInDbDict.has_key(a):
	    allelesInDbDict[a].c.append(c)
	else:
	    allelesInDbDict[a] = Allele(a, s, m, [c])
   
    # load production center/labcode mapping 
    results = db.sql('''select term, abbreviation
	from VOC_Term
	where _Vocab_key = 98''', 'auto')

    for r in results:
	procCtrToLabCodeDict[r['term']] = r['abbreviation']

    # load strain mappings from config
    tokens = map(string.strip, string.split(strainInfoMapping, ','))
    for t in tokens:
	pStrain, pID, rStrain, rTemplate, pType, pAttr = string.split(t, '|')
	strainRawPrefixDict[pID] = pStrain
	strainPrefixDict[pID] = rStrain
	strainTemplateDict[pID] = rTemplate
	strainTypeDict[pID]  = pType
	strainAttribDict[pID] = pAttr

    # load colony code to strain ID mappings
    # colony id note will never be longer than 255 char
    # strain types 'coisogenic' and 'Not Specified'
    results = db.sql('''select s.strain, nc.note as colonyID
	from PRB_Strain s, MGI_Note n, MGI_NoteChunk nc
	where s._StrainType_key in (3410530, 3410535)
	and s._Strain_key *= n._Object_key
	and n._NoteType_key = 1012
	and n._MGIType_key = 10
	and n._Note_key *= nc._Note_key ''', 'auto')
    for r in results:
	cID =  r['colonyID']
	if cID == None:
	    cID = ''
	cID = string.strip(cID)
	if cID != '':
	    colonyToStrainNameDict[cID] = r['strain']
	strainNameToColonyIdDict[r['strain']] = cID
    db.useOneConnection(0)
    return rc


#
# Purpose: Open input/output files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#

def openFiles():
    global fpIMPC, fpImits2, fpHTMP, fpStrain
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
    # Open the htmp output file 
    #
    try:
	#print 'htmpfile: %s' % htmpFile
        fpHTMP = open(htmpFile, 'w')
    except:
        print 'Cannot open file: ' + htmpFile
        return 1


    #
    # Open the strain output file
    #
    try:
        #print 'strainfile: %s' % strainFile
        fpStrain = open(strainFile, 'w')
    except:
        print 'Cannot open file: ' + strainFile
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
	fpLogCur.write('\n\n makeIMPC Log\n\n')
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
# Returns: 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def closeFiles():
    if fpIMPC:
        fpIMPC.close()

    if fpImits2:
	fpImits2.close()

    if fpHTMP:
        fpHTMP.close()

    if fpStrain:
        fpStrain.close()

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
# Purpose: Log a message to the diagnostic and curation logs, optionally
#	write a line to the error file
# Returns: 0
# Assumes: file descriptors exist
# Effects: Nothing
# Throws: Nothing
#

def logIt(msg, line, isError):
    logit = errorDisplay % (msg, line)
    fpLogDiag.write(logit)
    fpLogCur.write(logit)
    if isError:
	fpHTMPError.write(line)
    return 0

#
# Purpose: parse iMits2 file into a data structure
# Returns: 0
# Assumes: fpImits2 exists 
# Effects: Nothing
# Throws: Nothing
#

def parseImits2File():
    global  colonyToMCLDict

    print 'Parsing iMits2, creating lookup: %s'  % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    # create lookup mapping iMits2 colony id to MCL ID
    # US5 - add production center and marker MGI ID
    # US5 - skip if any attributes don't exist
    for line in fpImits2.readlines():
        tokens = line[:-1].split('\t')
        productionCtr = tokens[0]
        mutantID = tokens[3]
        markerID = tokens[4]
        colonyID = tokens[5]

        # if any of the attributes are empty, skip, (majority of records
        # have some blank attributes; too many to bother reporting)
        if productionCtr == '' or mutantID == '' or markerID == '' or \
                colonyID == '':
            continue

        # map the colony id to productionCtr, mutantID and markerID
        value = '%s|%s|%s' % (productionCtr, mutantID, markerID)

        # if we find a dup, just print for now to see what we get
        if colonyToMCLDict.has_key(colonyID) and \
                colonyToMCLDict[colonyID] == value:
            #print 'Dup colony ID record: %s|%s' (colonyID, value)
            continue
        colonyToMCLDict[colonyID] = value
    return 0

#
# Purpose: parse IMPC json file into intermediate file
#	lines with missing data reported to the skip file
#	duplicate entries in json file collapsed
# Returns: 1 if file cannot be opened, else 0
# Assumes: json file descriptor has been created
# Effects: writes intermediate file to file system
# Throws: Nothing
#
def parseJsonFile():
    global fpIMPCintWrite, fpIMPCdup
    
    #
    # Open the intermediate IMPC file
    #
    try:
        fpIMPCintWrite = open(impcFileInt, 'w')
    except:
        print 'Cannot open file: ' + impcFileInt
        return 1

    #
    # Open the intermediate IMPC Dup file
    #
    try:
        fpIMPCdup = open(impcFileDup, 'w')
    except:
        print 'Cannot open file: ' + impcFileDup
        return 1

    #print 'creating json object: %s' % \
        time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    jFile = json.load(fpIMPC)
    #print 'done creating json object: %s' % \
        #time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))

    lineSet = set([])
    for f in jFile['response']['docs']:
        # exclude europhenome for now
        # 8/20 - decided to restrict to impc data via mirror_wget
        #if f['resource_name'] == 'EuroPhenome':
        #    continue

        phenotypingCenter = f['phenotyping_center']
        mpID = f['mp_term_id']
        alleleID = alleleID2 = f['allele_accession_id']
        alleleState = f['zygosity']
        alleleSymbol = f['allele_symbol']
        strainName = f['strain_name']
        strainID = f['strain_accession_id']
        markerID = f['marker_accession_id']
        gender = f['sex']
        colonyID = f['colony_id']

        # line representing data from the IMPC input file 
	line = phenotypingCenter + '\t' + \
             mpID + '\t' + \
             alleleID + '\t' + \
             alleleState + '\t' + \
             alleleSymbol + '\t' + \
             strainName + '\t' + \
             strainID + '\t' + \
             markerID + '\t' + \
             gender + '\t' + \
             colonyID + '\n'

        # skip if blank field in IMPC data and report to the skip file
        if phenotypingCenter == '' or mpID == '' or alleleID == '' or \
            alleleState == '' or alleleSymbol == '' or strainName == '' or \
            strainID == '' or markerID == '' or  gender == '' or \
            colonyID == '':
            # 8/22 - None
            fpHTMPSkip.write(line)
            continue

        # lineSet assures dups are filtered out
	if line in lineSet:
	    fpIMPCdup.write(line)
        lineSet.add(line)

    for line in lineSet:
	fpIMPCintWrite.write(line)

    fpIMPCintWrite.close()
    fpIMPCdup.close()

    return 0

#
# Purpose: do strain checks on a set of attributes representing a unique
#	strain in the input
# Returns: 1 if error, else 0
# Assumes: file descriptors exist
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def doUniqStrainChecks(uniqStrainProcessingKey, line):
    global uniqStrainProcessingDict

    # set defaults
    error = 0
    uniqStrainProcessingDict[uniqStrainProcessingKey] = 0
    
    # unpack the key into attributes
    alleleID, alleleSymbol, strainName, strainID, markerID, colonyID, mutantID, imits2ProdCtr = string.split(uniqStrainProcessingKey, '|') 

    # Allele/MCL Object Identity/Consistency Check US5 doc 4b
    if allelesInDbDict.has_key(alleleID):
	dbAllele = allelesInDbDict[alleleID]

	msg=[]
	# US5 doc 4b2
	if alleleSymbol != dbAllele.s:
	    msg.append('Allele symbol: %s does not match database symbol: %s' \
		% (alleleSymbol, dbAllele.s))
	    error = 1
	if markerID != dbAllele.m:
	    msg.append('Marker ID: %s does not match database marker ID: %s' % \
		(markerID, dbAllele.m))
	    error = 1
	if mutantID not in dbAllele.c:
	    msg.append('Mutant ID: %s not associated with %s in database' % \
		(mutantID, alleleID))
	    error = 1
	msg = string.join(msg)
    else: # US5 doc 4b2
	# 15 cases in impc.json e.g. NULL-114475FCF4
	msg = 'Allele not in the database: %s' % alleleID
	error = 1
    if error == 1:
	logIt(msg, line, 1)
	uniqStrainProcessingDict[uniqStrainProcessingKey] = 1
	return 1

    # Production Center Lab Code Check US5 doc 4c2
    if not procCtrToLabCodeDict.has_key(imits2ProdCtr):
	msg = 'Production Center not in database: %s' % imits2ProdCtr
	logIt(msg, line, 1)
	uniqStrainProcessingDict[uniqStrainProcessingKey] = 1
	return 1

    # Prefix Strain check #1/#2 US5 doc 4c3
    if not (strainRawPrefixDict.has_key(strainID) and \
	strainRawPrefixDict[strainID] == strainName):

	# This is just a check - the strain name will be determined
	# outside this function
	msg = 'Strain ID/Name discrepancy, "Not Specified" used : %s %s' % \
	    (strainID, strainName)
	logIt(msg, line, 0)
	return 1
    ######################################################
    
    # strain name construction US5 doc 4c4
    # if we find a strain root use the template to create strain name
    if strainPrefixDict.has_key(strainID):
	strainRoot = strainPrefixDict[strainID]
	labCode = procCtrToLabCodeDict[imits2ProdCtr]
	# if strainPrefixDict has key strainID so does strainTemplateDict
	strainTemplate = strainTemplateDict[strainID]
	strainName = strainTemplate % \
	    (strainRoot, alleleSymbol, labCode)
    else:  # otherwise use 'Not Specified'
	strainName = 'Not Specified'

    # Constructed strain name match to strain in db US5 4c5
    # Not Specified strain will not have colonyID in db
    # if there is a colony ID at this point we know it doesn't match
    # because we didn't find it in check US5 4c1
    # NEED TO TEST THIS CHECK, no colony ids in db now
    if strainName != 'Not Specified' and \
	    strainNameToColonyIdDict.has_key(strainName) and \
	    strainNameToColonyIdDict[strainName] != '':

	dbColonyID =  strainNameToColonyIdDict[strainName]
	msg = 'Database colony ID %s for strain %s does not match IMPC colony id %s' % (dbColonyID, strainName, colonyID)
	logit(msg, line, 1)
	return 1
    strainType = strainTypeDict[strainID]
    attributes = strainAttribDict[strainID]
    attributes = attributes.replace(':', '|')
    strainLine = strainName + '\t' + \
	alleleID + '\t' + \
	strainType + '\t' + \
	species + '\t' + \
	standard + '\t' + \
	createdBy + '\t' + \
	mutantID + '\t' + \
	colonyID + '\t' + \
	attributes + '\n'
    #print 'strainLine: %s' % strainLine
    fpStrain.write(strainLine)
    uniqStrainProcessingDict[uniqStrainProcessingKey] = strainName
    return
##############################################

#
# Purpose: resolves the IMPC alleleState term to MGI alleleState term
# Returns: string 'error' if IMPC alleleState not recognized, else resolved
#	    alleleState
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs 
# Throws: Nothing
#
def checkAlleleState(alleleState, line):
    # report and skip if either alleleState or gender is unrecognized
    if alleleState.lower() == 'heterozygote':
	alleleState = 'Heterozygous'
    elif alleleState.lower() == 'homozygote':
	alleleState = 'Homozygous'
    elif alleleState.lower() == 'hemizygote':
	alleleState = 'Hemizygous'
    else:
	# 8/22 all match
	msg = 'Unrecognized allele state %s' % alleleState
	logIt(msg, line, 1)
	return  'error'
    return alleleState

#
# Purpose: resolves the IMPC gender term to MGI gender term
# Returns: string 'error' IMPC gender not recognized, else resolved gender
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def checkGender(gender, line):

    if gender.lower() == 'male':
	gender = 'Male'
    elif gender.lower() == 'female':
	gender = 'Female'
    else:
	# 8/22 all match
	msg = 'Unrecognized gender %s' % gender
	logIt(msg, line, 1)
	return 'error'
    return gender 

#
# Purpose: checks if IMPC colony ID maps to iMits2 colony ID
# Returns: 1 if not iMits2 colony ID for IMPC colony ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def checkColonyID(colonyID, line):
    if not colonyToMCLDict.has_key(colonyID):
	msg='No iMits2 colony id for %s' % colonyID
	# 8/22 2 MFUN colony id records
	logIt(msg, line, 1)
	return 1
    return 0

#
# Purpose: compares IMPC marker ID to iMits2 marker ID
# Returns: 1 if iMits2 marker ID not the same as iMits2 marker ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def compareMarkers(markerID, imits2MrkID, line):
    if markerID != imits2MrkID:
	# US5 doc 4a2
        # 8/22 all match
        # test file:
        #  imits.mp.tsv.no_marker_id_match_mgi104848_to_mgi2442056_line_1982
	msg='No Marker ID match. IMPC: %s iMits2: %s' % \
	    (markerID, imits2MrkID)
	logIt(msg, line, 1)
	return 1
    return 0


#
# Purpose: Read the IMPC and iMits2 files and re-format it to create a 
#    High-Throughput MP input file
# Returns: 0
# Assumes: input/output files exist and have been opened
# Effects: writes to the file system
# Throws: Nothing
#
def createHTMPfile():

    # Static values:
    interpretationCenter = 'IMPC'
    evidenceCode = 'EXP'

    # Values to be calculated
    strainName = ''
    mutantID = ''

    #
    # Open the intermediate IMPC file
    #
    try:
        fpIMPCintRead = open(impcFileInt, 'r')
    except:
        print 'Cannot open file: ' + impcFileInt
        return 1

    # 
    # Parse the intermediate file where 1) dups are removed 2) lines w/missing 
    #    data skipped
    #
    
    for line in fpIMPCintRead.readlines():
	error = 0
	# We know this attributes are not blank - see parseJson
	phenotypingCenter, mpID, alleleID, alleleState, alleleSymbol, strainName, strainID, markerID, gender, colonyID = line[:-1].split('\t')

	returnVal = checkAlleleState(alleleState, line)
	if returnVal == 'error':
	    error = 1
	else: alleleState = returnVal

	returnVal= checkGender(gender, line)
	if returnVal == 'error':
            error = 1
	else: gender = returnVal

        # if alleleState or gender error, continue to next line
        if error:
            continue

	#
	# US20/5 checks for strain processing
	# these checks short circuit i.e. only first one found reported
	#


        # Get the mutantID, production Ctr and markerID from the iMits2 data
	# US 5 doc 4a1
	# MFUN not in imits (2 impc records)
	if checkColonyID(colonyID, line):
	    continue

	imits2Data = colonyToMCLDict[colonyID]
	imits2ProdCtr, mutantID, imits2MrkID = string.split(
	    colonyToMCLDict[colonyID], '|')

        if compareMarkers(markerID, imits2MrkID, line):
	    continue
	#
	# Now do checks on the uniq strains in the input file
	#

	# key to determine uniq entries for strain processing
	uniqStrainProcessingKey = '%s|%s|%s|%s|%s|%s|%s|%s' % \
	    (alleleID, alleleSymbol, strainName, strainID, markerID, \
		colonyID, mutantID, imits2ProdCtr)

	# resolve the colonyID to a strain in the database, if we can
	# we'll use this strain
	if colonyToStrainNameDict.has_key(colonyID):
  	    strainName = colonyToStrainNameDict[colonyID]
	    #print 'found strain in db %s' % strainName
	    uniqStrainProcessingDict[uniqStrainProcessingKey] = strainName 
	else:
	    #print 'strain not found by colonyID %s' % colonyID
	    #
	    # if strain not determined by colony ID first do checks on the 
	    #	uniq strains in the input file
	    #

	    # if key in the list, we've already processed this uniq record
	    # Note: key does not include MP ID, multi MP IDs/per uniq allele
	    if uniqStrainProcessingKey not in uniqStrainProcessingDict.keys():
		 doUniqStrainChecks(uniqStrainProcessingKey, line)
	    
	# if all the checks passed write it out to the HTMP load format file
	if uniqStrainProcessingDict[uniqStrainProcessingKey] == 1:
	    # just print out for now for verification
            #print 'dup error line%s' % line
	    continue
	else:
	    strainName = uniqStrainProcessingDict[uniqStrainProcessingKey]
	htmpLine = phenotypingCenter + '\t' + \
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
	fpHTMP.write(htmpLine)
    return 0

#
#  MAIN
#

print 'initialize: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if initialize() != 0:
    sys.exit(1)
print 'openFiles: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if openFiles() != 0:
    sys.exit(1)
print 'parseImits2File: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if parseImits2File() != 0:
    sys.exit(1)
print 'parseJsonFile: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if parseJsonFile() != 0:
    sys.exit(1)
print 'createHTMPfile: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if createHTMPfile() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
print 'done: %s' % \
    time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
sys.exit(0)

