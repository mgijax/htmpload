#!/usr/local/bin/python
#
#  makeIMPC.py
###########################################################################
#
#  Purpose:
#
#      This script will parse IMPC and IMITS input files to
#      create a High-Throughput MP input file
#
#  Usage:
#      makeIMPC.py
#
#  Env Vars:
#	See the configuration file (impcmpload.config)
#
#  Inputs:
#
#   IMPC/Pheontypes/MP input file (SOURCE_COPY_INPUT_FILE from impcmpload.config)
#   This is a json format file
#   1. Phenotyping Centre
#   2. MGI Allele ID
#   3. Zygosity
#   4. Allele Symbol
#   5. Strain Name
#   6. MGI Strain ID
#   7. MGI Marker ID
#   8. Gender
#   9. Colony ID
#
#   IMPC/LacZ input file (SOURCE_COPY_INPUT_FILE from impclaczload.config)
#   This is a json format file
#   1.  Phenotyping Center
#   2.  MGI Allele ID
#   3.  Allele State
#   4.  Allele Symbol
#   5.  Strain Name
#   6.  MGI Strain ID
#   7.  MGI Marker ID
#   8.  Marker Symbol
#   9.  Gender
#   10. Colony ID
#
#   IMITS input file (IMITS_COPY_INPUT_FILE)
#   This is a imits/tsv (tab-delimited) file
#   1. Marker Symbol
#   2. MGI Marker ID
#   3. Colony Name
#   4. ES Cell Name 
#   5. Colony Background Strain
#   6. Production Centre
#   7. Production Consortium
#   8. Phenotyping Centre
#   9. Phenotyping Consortium Centre
#   10. Productin Centre
#   11. Allele Symbol
#
#  Outputs:
#
#   htmpload format (HTMP_INPUT_FILE):
#   1.  Phenotyping Center 
#   2.  Interpretation (Annotation) Center 
#   3.  Mutant ES Cell ID
#   4.  MP ID (Phenotypes/MP only)
#   5.  MGI Allele ID
#   6.  Allele State 
#   7.  Allele Symbol
#   8.  MGI Marker ID
#   9.  Evidence Code 
#   10. Strain Name
#   11. Gender 
#   12. Colony ID
#
#   IMPC strainload format file (STRAIN_INPUT_FILE)
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
#      0:  Successful completion
#      1:  An exception occurred
#
#  Implementation:
#      This script will perform following steps:
#       1) initialize - get values from the environment, load lookups
#	2) open input/output files
#	3) parse the IMITS File into a data structure
#	4) parse the IMPC File into an intermediate file
#	5) create HTMP Load format file from IMPC/IMITS data
#	6) close input/output files
#
#  Notes: 
#
#  US5 refers to
#	http://mgiwiki/mediawiki/index.php/sw:IMPC_htmpload#Strains
#	http://prodwww.informatics.jax.org/all/wts_projects/11600/11674/Strains_Info/StrainProcessing_IMPC_v4.docx
#
#  03/30/2016
#	- TR12273/use new IMITS report input file to verify IMPC colony/marker
#	  and to find production_centre and es_cell_name. the json IMITS file
#	  is incorrect. using mirror_wget/www.mousephenotype.org instead.
#	- added 'parseIMPCLacZFile' for parsing IMPC/LacZ input file
#
#  12/08/2015	lec
#	- TR12070 epic
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

db.setTrace(True)
db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

# load type
isMP = 0
isLacZ = 0

# strain constants
species = 'laboratory mouse'
standard = '1'
createdBy = 'htmpload'

# htmp file constants
evidenceCode = 'EXP'

# the data interpretation center property value for IMPC
interpretationCenter = 'IMPC'

# Input 
impcFile = None
impcFileInt = None
impcFileDup = None
imitsFile = None

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
fpIMITS = None
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

# {errorNum:[msg1, msg2, ...], ...}
errorDict = {}

# IMITS colony id mapped to IMITS attributes
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

# map all new strains to their strain lines 
#{strainName:[set of strain lines], ...}
newStrainDict = {}

# processing center mapped to lab code from database
procCtrToLabCodeDict = {}

# list of phenotyping centers in the database
phenoCtrList = []

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

# uniq set of strain lines written to strainload input file
strainLineList = []

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
    global impcFile, impcFileInt, impcFileDup, imitsFile, htmpFile, strainFile
    global logDiagFile, logCurFile, htmpErrorFile, htmpSkipFile
    global allelesInDbDict, procCtrToLabCodeDict, phenoCtrList, strainInfoDict
    global strainPrefixDict, strainTemplateDict, strainTypeDict
    global colonyToStrainNameDict, strainNameToColonyIdDict
    global isMP, isLacZ

    impcFile = os.getenv('SOURCE_COPY_INPUT_FILE')
    impcFileInt = '%s_int' % impcFile
    impcFileDup = '%s_dup' % impcFile
    imitsFile = os.getenv('IMITS_COPY_INPUT_FILE')
    htmpFile = os.getenv('HTMP_INPUT_FILE')
    strainFile = os.getenv('STRAIN_INPUT_FILE')
    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    htmpSkipFile = os.getenv('HTMPSKIP_INPUT_FILE')
    loadType = os.getenv('LOADTYPE')

    rc = 0

    #
    # determine load type (LOADTYPE)
    # 
    if loadType == 'mp':
    	isMP = 1
    elif loadType == 'lacz':
    	isLacZ = 1
    else:
        print 'Environment variable not set: LOADTYPE'
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not impcFile:
        print 'Environment variable not set: SOURCE_COPY_INPUT_FILE'
        rc = 1

    if not imitsFile:
        print 'Environment variable not set: IMITS_COPY_INPUT_FILE'
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

    #
    # Allele Status where _vocab_key = 37
    # In Progress (847111)
    # Approved  (847114)
    # Autoload  (3983021)
    #
    # Allele Types where _vocab_key = 38
    # Targeted  (847116)
    # Endonuclease-mediated (11927650)
    #
    # preferred MGI IDs
    #

    db.useOneConnection(1)

    db.sql('''select distinct a1.accid as alleleMgiID, a2.accid as markerMgiID, 
	    ll.symbol as aSymbol, ll._Allele_key
	into temporary table all_tmp
	from ACC_Accession a1, ACC_Accession a2, ALL_Allele ll
	where ll._Allele_Status_key in (847111, 847114, 3983021)
	and ll._Allele_Type_key in (847116)
	and ll._Allele_key = a1._Object_key
	and a1._MGIType_key = 11
	and a1.preferred = 1
	and a1.prefixPart = 'MGI:'
	and ll._Marker_key = a2._Object_key
	and a2._MGIType_key = 2
	and a2.preferred = 1
	and a2.prefixPart = 'MGI:' 
	''', None)

    db.sql('create index idx1 on all_tmp(_Allele_key)', None)

    #
    # select alleles and their mutant cell line ids
    # alleles may not contain a mutant cell line/will be reported later
    #
    results = db.sql('''
    	select distinct a.*, a1.accid as mclID
	from all_tmp a
	LEFT OUTER JOIN ALL_Allele_CellLine ac ON (
			a._Allele_key = ac._Allele_key
		)
	INNER JOIN ACC_Accession a1 ON (
	       ac._MutantCellLine_key = a1._Object_key
		and a1._MGIType_key = 28
		and a1.preferred = 1
		)
	''', 'auto')

    for r in results:
	a = r['alleleMgiID']
	s = r['aSymbol']
	m = r['markerMgiID']
	c = r['mclID']
	if a in allelesInDbDict:
	    allelesInDbDict[a].c.append(c)
	else:
	    allelesInDbDict[a] = Allele(a, s, m, [c])
   
    # load production center/labcode mapping 
    results = db.sql('select term, abbreviation from VOC_Term where _Vocab_key = 98', 'auto')
    for r in results:
	procCtrToLabCodeDict[r['term']] = r['abbreviation']

    # load list of phenotyping centers in the database
    results = db.sql('select term from VOC_Term where _Vocab_key = 99', 'auto')
    for r in results:
	phenoCtrList.append(r['term'])

    # load strain mappings from config
    tokens = map(string.strip, string.split(strainInfoMapping, ','))
    for t in tokens:
	pStrain, pID, rStrain, rTemplate, pType, pAttr = string.split(t, '|')
	strainRawPrefixDict[pID] = pStrain
	strainPrefixDict[pID] = rStrain
	strainTemplateDict[pID] = rTemplate
	strainTypeDict[pID]  = pType
	strainAttribDict[pID] = pAttr

    #
    # load colony code to strain ID mappings
    # strain types 'coisogenic' and 'Not Specified'
    # strain  may not contain a colony id/will be reported later
    #

    results = db.sql('''
        select s.strain, trim(nc.note) as colonyID
	from PRB_Strain s 
		LEFT OUTER JOIN MGI_Note n ON (
			s._Strain_key = n._Object_key
			and n._NoteType_key = 1012
			and n._MGIType_key = 10
			)
		INNER JOIN MGI_NoteChunk nc ON (
			n._Note_key = nc._Note_key 
			)
	where s._StrainType_key in (3410530, 3410535, 6508969) 
		and s.private = 0
	''', 'auto')

    for r in results:
	# HIPPO US146
	# colony ids can be a pipe delimited string e.g. 'BL3751|BL3751_TCP'
        cIDs =  string.strip(r['colonyID'])
        str = r['strain']
	#print 'cIDs: %s' % cIDs
	#print 'str: %s' % str
	cIDList = []
	if cIDs != None:
	    #cIDList = string.split(cIDs, '|')
	    cIDList = map(string.strip, string.split(cIDs, '|'))
	    #print 'cIDList:%s' % cIDList
	# HIPPO 6/2016 handle multi strains/colony ID
	for cID in cIDList:
	    if not cID in colonyToStrainNameDict:
		 colonyToStrainNameDict[cID] = [] 
	    colonyToStrainNameDict[cID].append(str)
	# HIPPO 6/2016 - handle multi colonyIDs/strain
	strainNameToColonyIdDict[str] = cIDList

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
    global fpIMPC, fpIMITS, fpHTMP, fpStrain
    global fpIMPCintWrite, fpIMPCdup
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

    #
    # Open the IMITS file
    #
    try:
        fpIMITS = open(imitsFile, 'r')
    except:
        print 'Cannot open file: ' + imitsFile
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
	fpLogCur.write('\n\n######################################\n')
	fpLogCur.write('########## makeIMPC Log ##############\n')
	fpLogCur.write('######################################\n\n')

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

    if fpIMITS:
	fpIMITS.close()

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
# Purpose: Log a message to the diagnostic log, optionally
#	write a line to the error file. Write to error Dict
#	which is used to sort errors and will be written to 
#	curation log later
# Returns: 0
# Assumes: file descriptors exist
# Effects: Nothing
# Throws: Nothing
#
def logIt(msg, line, isError, typeError):
    global errorDict

    logit = errorDisplay % (msg, line)
    fpLogDiag.write(logit)
    if not typeError in errorDict:
	errorDict[typeError] = []
    errorDict[typeError].append(logit)
    #fpLogCur.write(logit)
    if isError:
	fpHTMPError.write(line)

    return 0

#
# Purpose: parse IMITS report (tab-delimited) file into a data structure
# Returns: 0
# Assumes: fpIMITS exists 
# Effects: Nothing
# Throws: Nothing
#
def parseIMITSFile():
    global colonyToMCLDict

    print 'Parsing IMITS, creating lookup: %s'  % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))

    for line in fpIMITS.readlines():

        tokens = line[:-1].split('\t')

	if tokens[0] == 'Marker Symbol':
	    continue

	markerID = tokens[1]
	colonyID = tokens[2]
	mutantID = tokens[3]
	colonyBackgroun = tokens[4] # not used
	productionCtr = tokens[5]

        # map the colony id to productionCtr, mutantID and markerID
        value = '%s|%s|%s' % (productionCtr, mutantID, markerID)

        # if we find a dup, just print for now to see what we get 
        if colonyID in colonyToMCLDict and colonyToMCLDict[colonyID] == value:
            #print 'Dup colony ID record: %s|%s' (colonyID, value)
            continue

        colonyToMCLDict[colonyID] = value

    return 0

#
# Purpose: parse IMPC/MP json file into intermediate file
#	lines with missing data reported to the skip file
#	duplicate entries in json file collapsed
# Returns: 1 if file cannot be opened, else 0
# Assumes: json file descriptor has been created
# Effects: writes intermediate file to file system
# Throws: Nothing
#
def parseIMPCFile():
    global fpIMPCintWrite, fpIMPCdup
    
    #print 'creating json object: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    jFile = json.load(fpIMPC)
    #print 'done creating json object: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))

    lineSet = set([])

    for f in jFile['response']['docs']:

	try:
        	mpID = f['mp_term_id']
        except:
		mpID = ''
        resourceName = f['resource_name']
	phenotypingCenter = f['phenotyping_center']
        alleleID = alleleID2 = f['allele_accession_id']
        alleleState = f['zygosity']
        alleleSymbol = f['allele_symbol']
        strainName = f['strain_name']
        strainID = f['strain_accession_id']
        markerID = f['marker_accession_id']
        gender = f['sex']
        colonyID = f['colony_id']

        # line representing data from the IMPC input file 
	line = resourceName + '\t' + \
	     phenotypingCenter + '\t' + \
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
        if resourceName == '' or \
	 	phenotypingCenter == '' or \
	        mpID == '' or \
		alleleID == '' or \
            	alleleState == '' or \
		alleleSymbol == '' or \
		strainName == '' or \
            	strainID == '' or \
		markerID == '' or  \
		gender == '' or \
            	colonyID == '':
            fpHTMPSkip.write(line)
            continue

        # lineSet assures dups are filtered out
	if line in lineSet:
	    fpIMPCdup.write(line)
	    continue

        lineSet.add(line)

    for line in lineSet:
	fpIMPCintWrite.write(line)

    fpIMPCintWrite.close()
    fpIMPCdup.close()

    return 0

# Purpose: parse IMPC/LacZ json file into intermediate file
# Returns: 0
# Assumes: json file descriptor has been created
# Effects: writes intermediate file to file system
# Throws: Nothing
#
def parseIMPCLacZFile():
    global fpIMPCintWrite, fpIMCPdup

    print 'Parsing IMPC/LacZ input file: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    jFile = json.load(fpIMPC)

    lineSet = set([])
    sGroupValList = []
    totalCt = 0
    notExpCt = 0
    nopasId = 0
    rcdWrittenCt = 0

    for f in jFile['response']['docs']:

	totalCt += 1
	sGroup = f['biological_sample_group']

	if sGroup.lower() != 'experimental':
	    if sGroup not in sGroupValList:
		sGroupValList.append(sGroup)
	    notExpCt += 1
	    continue

	phenotypingCenter = f['phenotyping_center']
	alleleID = f['allele_accession_id']
	alleleState = f['zygosity']
        alleleSymbol = f['allele_symbol']
        strainName = f['strain_name']
        strainID = f['strain_accession_id']
        markerID = f['gene_accession_id']
        markerSymbol = f['gene_symbol']
        gender = f['sex']
        colonyID = f['colony_id']

	download_url = f['download_url'] 
	jpeg_url = f['jpeg_url']  
	full_resolution_file_path = f['full_resolution_file_path']  
	parameter_name  = f['parameter_name']  
	parameter_stable_id  = f['parameter_stable_id']  

	try:
	   parameter_association_stable_id = f['parameter_association_stable_id'] 
	except:
	    # skip if no parameter_association_stable_id
	    nopasId += 1
	    continue
	try: 
	    parameter_association_name = f['parameter_association_name'] 
	except:
	    parameter_association_name = []

	try:
	    parameter_association_value = f['parameter_association_value'] 
	except:
	    parameter_association_value = []

        # line representing data from the IMPC input file
        line = phenotypingCenter + '\t' + \
             '\t' + \
             alleleID + '\t' + \
             alleleState + '\t' + \
             alleleSymbol + '\t' + \
             strainName + '\t' + \
             strainID + '\t' + \
             markerID + '\t' + \
             gender + '\t' + \
             colonyID + '\n'

        # skip if blank field in IMPC data and report to the skip file
        if phenotypingCenter == '' or \
                alleleID == '' or \
                alleleState == '' or \
                alleleSymbol == '' or \
                strainName == '' or \
                strainID == '' or \
                markerID == '' or  \
                gender == '' or \
                colonyID == '':
            fpHTMPSkip.write(line)
            continue

	lineSet.add(line)

    for line in lineSet:
	fpIMPCintWrite.write(line)
	rcdWrittenCt += 1

    fpIMPCintWrite.close()
    fpIMPCdup.close()

    print 'notExpCt: %s' % notExpCt
    print 'nopasId: %s' % nopasId
    print 'non experimental values: %s' % sGroupValList
    print 'total records written: %s' % rcdWrittenCt
    print 'totalCt: %s' % totalCt

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
    global uniqStrainProcessingDict, newStrainDict
    
    #print 'doUniqStrainChecks key: %s' % uniqStrainProcessingKey
    #print 'doUniqStrainChecks line: %s' % line

    dupStrainKey = 0

    if uniqStrainProcessingKey in uniqStrainProcessingDict.keys():
	uniqStrainProcessingDict[uniqStrainProcessingKey].append(line)
	dupStrainKey = 1

    #print 'dupStrainKey: %s' % dupStrainKey
    # unpack the key into attributes

    alleleID, alleleSymbol, strainName, strainID, markerID, colonyID, mutantID, imitsProdCtr = \
    	string.split(uniqStrainProcessingKey, '|') 

    rawStrainName = strainName

    # Production Center Lab Code Check US5 doc 4c2
    if not imitsProdCtr in procCtrToLabCodeDict:
	if dupStrainKey == 0:
	    msg = 'Production Center not in MGI (voc_term table): %s' % imitsProdCtr
	    logIt(msg, line, 1, 'prodCtrNotInDb')
	    uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
	    #print '%s returning "error"' % msg
	    return 'error'
	else: # we've seen this key already, just return 'error'
	    #print 'returning "error"' 
            return 'error'

    # Prefix Strain check #1/#2 US5 doc 4c3
    if dupStrainKey == 0 and not (strainID in strainRawPrefixDict and \
	strainRawPrefixDict[strainID] == strainName):
	# This is just a check - the strain name will be determined outside this block
	msg = 'Strain ID/Name discrepancy, "Not Specified" used : %s %s' % (strainID, strainName)
	logIt(msg, line, 0, 'strainIdNameDiscrep')
	uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
	#print '%s returning "Not Specified"' % msg
	return 'Not Specified'
    
    # strain name construction US5 doc 4c4
    # if we find a strain root use the template to create strain name

    if strainID in strainPrefixDict:
	strainRoot = strainPrefixDict[strainID]
	labCode = procCtrToLabCodeDict[imitsProdCtr]
	# if strainPrefixDict has key strainID so does strainTemplateDict
	strainTemplate = strainTemplateDict[strainID]
	strainName = strainTemplate % (strainRoot, alleleSymbol, labCode)
        #print 'calculated strain name: %s' % strainName
    else:  # otherwise use 'Not Specified'
	#strainName = 'Not Specified'
	#print 'cannot calc strain name returning "Not Specified"'
	return 'Not Specified'

    # Constructed strain name match to strain in db US5 4c5
    # Not Specified strain will not have colonyID in db
    # if there is a colony ID at this point we know it doesn't match
    # because we didn't find it in check US5 4c1

    if strainName in strainNameToColonyIdDict and \
    		strainNameToColonyIdDict[strainName] != []:

	dbColonyIdList =  strainNameToColonyIdDict[strainName]
	msg = 'MGI/database colony ID(s) %s for strain %s does not match IMPC colony id %s' % \
		(string.join(dbColonyIdList), strainName, colonyID)
	
	uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
	
	return 'error'
    
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

    if strainLine not in strainLineList:
	strainLineList.append(strainLine)

    # save all the new strains with their strain lines for later checking
    # and writing to bcp file
    # HIPPO project US146 'Report cases where there are multiple colonyIDs 
    # in the input file for a new strain.'
    if not strainName in newStrainDict:
	newStrainDict[strainName] = set([])
    newStrainDict[strainName].add(string.strip(strainLine))
    
    return strainName

#
# Purpose: resolves the IMPC alleleState term to MGI alleleState term
# Returns: string 'error' if IMPC alleleState not recognized, else resolved alleleState
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
	logIt(msg, line, 1, 'alleleState')
	return  'error'

    return alleleState

#
# Purpose: checks if IMPC colony ID maps to IMITS colony ID
# Returns: 1 if not IMITS colony ID for IMPC colony ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def checkColonyID(colonyID, line):

    if not colonyID in colonyToMCLDict:
	msg='No IMITS colony id for %s' % colonyID
	logIt(msg, line, 1, 'colonyID')
	return 1

    return 0

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

    elif gender.lower() == 'no_data':
	# will be converted to NA laster in makeAnnotation.py
	gender = ''
    elif gender.lower() == 'both':
	# will be converted to NA laster in makeAnnotation.py
	gender = 'Both'
    else:
	msg = 'Unrecognized gender %s' % gender
	logIt(msg, line, 1, 'gender')
	return 'error'

    return gender 

#
# Purpose: check the IMPC phenotyping center for existence in the database
# Returns: string 'error' IMPC center not recognized, else center
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def checkPhenoCtr(phenoCtr, line):

    if phenoCtr not in phenoCtrList:
        msg = 'Unrecognized phenotyping center %s' % phenoCtr
        logIt(msg, line, 1, 'phenoCtr')
        return 'error'

    return phenoCtr

#
# Purpose: compares IMPC marker ID to IMITS marker ID
# Returns: 1 if IMITS marker ID not the same as IMITS marker ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def compareMarkers(markerID, imitsMrkID, line):

    if markerID != imitsMrkID:
	# US5 doc 4a2
        # 8/22 all match
        # test file:
        #  imits.mp.tsv.no_marker_id_match_mgi104848_to_mgi2442056_line_1982
	msg='No Marker ID match. IMPC: %s IMITS: %s' % (markerID, imitsMrkID)
	logIt(msg, line, 1, 'noMrkIdMatch')
	return 1

    return 0
#
# Purpose: write all errors in errorDict to curation log
# Returns: Nothing
# Assumes: Nothing
# Effects: writes to curation log
# Throws: Nothing
#
def writeCuratorLog():
    # HIPPO - US146 write fatal errors first
    if 'newStrainMultiColId' in errorDict:
	fatal = errorDict['newStrainMultiColId']
	fpLogCur.write(string.join(fatal))

	# remove the fatal error from the dict so not repeated
	del errorDict['newStrainMultiColId']

    # report remaining error types to curator log
    for type in errorDict.keys():
	fpLogCur.write(string.join(errorDict[type]))

#
# Purpose: Read the IMPC and IMITS files and re-format it to create a 
#    High-Throughput MP input file
# Returns: 0
# Assumes: input/output files exist and have been opened
# Effects: writes to the file system
# Throws: Nothing
#
def createHTMPFile():
    
    # return code from this function
    returnCode = 0

    # Values to be calculated
    strainName = ''
    mutantID = ''

    # the htmp lines we will write to a file; some may get filtered out later
    htmpLineDict = {}

    # annotations that should be filtered out i.e not written to the htmp file
    noLoadAnnotList = []

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

        #print '\n\nNEW RECORD'
	#print 'line: %s' % line

	error = 0

	# We know this attributes are not blank - see parseJson
	resourceName, phenotypingCenter, mpID, alleleID, alleleState, alleleSymbol, \
		strainName, strainID, markerID, gender, colonyID = line[:-1].split('\t')

	returnVal = checkAlleleState(alleleState, line)
	if returnVal == 'error':
	    error = 1
	else: alleleState = returnVal

	returnVal= checkGender(gender, line)
	if returnVal == 'error':
            error = 1
	else: gender = returnVal
	
	returnVal= checkPhenoCtr(phenotypingCenter, line)
        if returnVal == 'error':
            error = 1

        # if alleleState, gender or phenotyping error, continue to next line
        if error:
            continue

	# verify the IMPC/colony_id with the IMITS/colonyName
	if checkColonyID(colonyID, line):
	    continue

	# verify the IMPC/markerID with the IMITS/marker ID
	# note that the IMITS file also provides the 'mutantID' (es cell line)
	imitsProdCtr, mutantID, imitsMrkID = string.split(colonyToMCLDict[colonyID], '|')

        if compareMarkers(markerID, imitsMrkID, line):
	    continue

	# Allele/MCL Object Identity/Consistency Check US5 doc 4b

	if alleleID in allelesInDbDict:

	    dbAllele = allelesInDbDict[alleleID]

	    # report this but don't exclude it
	    if alleleSymbol != dbAllele.s:
		msg = 'not a fatal error: Allele Symbol: %s does not match MGI-database symbol: %s' % \
			(alleleSymbol, dbAllele.s)
		logIt(msg, line, 1, 'alleleNotMatch')
		#error = 1

	    if markerID != dbAllele.m:
		msg = 'Marker ID: %s does not match MGI-database marker ID: %s' % (markerID, dbAllele.m)
		logIt(msg, line, 1, 'markerNotMatch')
		error = 1

	    if mutantID not in dbAllele.c:
		msg = 'Mutant ID: %s is not associated with %s in MGI-database' % (mutantID, alleleID)
		logIt(msg, line, 1, 'mutIdNotAssoc')
		error = 1

	else: # US5 doc 4b2
	    # 15 cases in impc.json e.g. NULL-114475FCF4
	    msg = 'Allele not in the MGI-database: %s' % alleleID
	    logIt(msg, line, 1, 'alleleNotInDb')
	    error = 1

	if error == 1:
	    continue

	#
	# Now do checks on the uniq strains in the input file
	#

	# key to determine uniq entries for strain processing
	uniqStrainProcessingKey = '%s|%s|%s|%s|%s|%s|%s|%s' % \
	    (alleleID, alleleSymbol, strainName, strainID, markerID, \
		colonyID, mutantID, imitsProdCtr)

	# resolve the colonyID to a strain in the database
	if colonyID in colonyToStrainNameDict:
	    # HIPPO US146 case #4
	    # multiple strains for a colony ID
	    if len(colonyToStrainNameDict[colonyID]) > 1:
		msg =  'Colony ID: %s associated with multiple strains in the database: %s' % (colonyID, string.join(colonyToStrainNameDict[colonyID], ', ') )
		logIt(msg, line, 1, 'colIdMultiStrains')
		continue
	    # if we get here we have a single strain
  	    strainName = colonyToStrainNameDict[colonyID][0]

	else:
	    #
	    # if strain not determined by colony ID first do checks on the 
	    #	uniq strains in the input file
	    #
	    # if key in the list, we've already processed this uniq record
	    # Note: key does not include MP ID, multi MP IDs/per uniq allele
	    # Nor does it include gender, multi gender per uniq allele

	    strainName = doUniqStrainChecks(uniqStrainProcessingKey, line)
	    
	# if all the checks passed write it out to the HTMP load format file
	if strainName == 'error':
	    # just print out for now for verification
            #print 'rejected Uniq strain check line%s' % line
	    continue

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
	     colonyID + '\t' + \
	     resourceName + '\n'

	#fpHTMP.write(htmpLine)

	# save the lines to a data structure with 'strain|colonyID' key
	# later we look for multiple colony IDs per strain and annotations
	# to load for just ONE colony ID. We DO NOT want to load annotations
	# for the rejected colony ID(s), we just want to report them
	key = '%s|%s' % (strainName, colonyID)
	if key not in htmpLineDict:
	    htmpLineDict[key] = []
	htmpLineDict[key].append(htmpLine)

    print 'reporting uniq strain processing errors'
    for key in uniqStrainProcessingDict.keys():
	msgList = uniqStrainProcessingDict[key]
	msg = msgList[0]
	for line in msgList[1:]:
	    if 'Strain ID/Name discrepancy' in msg:
		logIt(msg, line, 0, 'strainIdNameDiscrep')
	    else:
		logIt(msg, line, 1, 'strainIdNameDiscrep')
    #
    # HIPPO US146 - check for new strains with multiple colony ids
    #
    print 'reporting new strains with multi colony ids'
    for s in newStrainDict:
	# we have multi colony ids for this strain, pick one to load, report
	# the rest
	if len(newStrainDict[s]) > 1:
	    msg = 'New strain with multiple Colony IDs. Strain created, with Colony ID note:%s. Genotype and annotations not created. The following colonyID note(s) not created:'

            # get input lines for this new strain
            multiSet = newStrainDict[s]
            #print multiSet

	    # Add strain/cID(s) to the list whose genotypes/annotations we 
	    # will not load
            for line in list(multiSet):
                cID = string.split(line, '\t')[7]
                # this corresponds to the key in htmpLineDict
                key = '%s|%s' % (s, cID)
                #print 'adding %s to noLoadAnnotList\n' % key
                noLoadAnnotList.append(key)

	    # get a arbitrary line from the list, the strain will be loaded with
	    # this colony ID
	    strainToLoad = multiSet.pop()

	    # plug the colony ID which WAS loaded into the error message
	    msg = msg % string.split(strainToLoad)[8]

	    # write out the strain to load
	    fpStrain.write('%s%s' % (strainToLoad, '\n'))

	    # get the  lines with the remaining colony ids for the strain,
	    # report and exit 2
	    strainLines = string.join(multiSet, '\n')
	    returnCode = 2
	    logIt(msg, strainLines, 1, 'newStrainMultiColId')
	else:
	    # we have only one colony id, write the strain to the strain file
	    # its a set so convert to list to index
	    fpStrain.write('%s%s' % (list(newStrainDict[s])[0], '\n'))

    # write lines to the htmp file checking the noloadAnnotList first
    #print 'noLoadAnnotList: %s' % noLoadAnnotList
    for key in htmpLineDict:
	#print 'htmpLineDict key: "%s"' % key
	#print 'htmpLineDict lines: "%s"' % htmpLineDict[key]
	if key in noLoadAnnotList:
	    #print 'key "%s" in noLoadAnnotList' % key
	    continue
	#print 'adding line to HTMP file'
	for line in htmpLineDict[key]:
	    fpHTMP.write(line)

    # write errors to curation log
    print 'writing to curator log'
    writeCuratorLog()

    return returnCode

#
#  MAIN
#

print 'initialize: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if initialize() != 0:
    sys.exit(1)

print 'openFiles: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if openFiles() != 0:
    sys.exit(1)

print 'parseIMITSFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
if parseIMITSFile() != 0:
    sys.exit(1)

#
# process either IMPC/MP or IMPC/LacZ input file
#
if isMP:
    print 'parseIMPCFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    if parseIMPCFile() != 0:
        sys.exit(1)
elif isLacZ:
    print 'parseIMPCLacZFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
    if parseIMPCLacZFile() != 0:
        sys.exit(1)

print 'createHTMPFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
returnCode = createHTMPFile()
if returnCode != 0:
    closeFiles()
    sys.exit(returnCode)

closeFiles()
print 'done: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time()))
sys.exit(0)

