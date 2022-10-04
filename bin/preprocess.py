#!/opt/python3.7/bin/python3
#  preprocess.py
###########################################################################
#
#  Purpose:
#
#      This script will parse input files to
#      create a High-Throughput MP input file
#
#  Usage:
#      preprocess.py
#
#  Env Vars:
#	See the configuration file (impcmpload.config)
#
#  Inputs:
#
#   IMPC - This is a json format file 
#	SOURCE_COPY_INPUT_FILE from impcmpload.config
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
#   IMPC/LacZ - This is a json format file
#	SOURCE_COPY_INPUT_FILE from impclaczload.config
#   1.  Phenotyping Center
#   2.  MGI Allele ID
#   3.  Allele State
#   4.  Allele Symbol
#   5.  Strain Name
#   6.  MGI Strain ID (not used)
#   7.  MGI Marker ID
#   8.  Marker Symbol
#   9.  Gender
#   10. Colony ID
#
#   GENTAR input file - tab delimited
#	 GENTAR_COPY_INPUT_FILE from impcmpload.config and impclaczload.config
#   This is a gentar/tsv (tab-delimited) file
#   1. Marker Symbol
#   2. MGI Marker ID
#   3. Colony Name
#   4. ES Cell Name 
#   5. Colony Background Strain
#   6. MGI Strain ID
#   7. Production Centre
#   etc   
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
#   strainload format file (STRAIN_INPUT_FILE)

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
#	3) check for provider
#	4) parse input files using appropriate parsing function to
#	  create intermediate file
#	5) interate over intermediate file to create HTMP Load format file 
#	6) close input/output files
#
#  Notes: 
#
# sc    01/11/21
#       - TR13457 htmpload load failure - due to resource_name and strain_name not in some json records
#       put all json attributes in try catch block and report/skip if missing
#
#  US5 refers to
#	http://mgiwiki/mediawiki/index.php/sw:IMPC_htmpload#Strains
#	http://prodwww.informatics.jax.org/all/wts_projects/11600/11674/Strains_Info/StrainProcessing_IMPC_v4.docx
#
# sc   02/17/2017
#       - TR12488 Mice Crispies project
#
#  03/30/2016
#	- TR12273/use new GENTAR report input file to verify IMPC colony/marker
#	  and to find production_centre and es_cell_name. the json GENTAR file
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
import json
import string
import Set
import db
import time

#db.setTrace(True)

CRT = '\n'
TAB = '\t'

# load type
isIMPC = 0
isLacZ = 0

# strain constants
species = 'laboratory mouse'
standard = '1'
createdBy = 'htmpload'

# htmp file constants
evidenceCode = 'EXP'

# Input 
inputFile = None
inputFileInt = None
inputFileDup = None
gentarFile = None

# Outputs 

htmpFile = None
strainFile = None
logDiagFile = None
logCurFile = None
htmpErrorFile = None
htmpSkipFile = None

# file pointers
fpInput = None
fpInputintWrite = None
fpInputintRead = None
fpInputdup = None
fpGENTAR = None
fpHTMP = None
fpStrain = None
fpLogDiag = None
fpLogCur = None
fpHTMPError = None
fpHTMPSkip = None

errorDisplay = '''

***********
errMsg: %s
%s
'''

# data structures

# {errorNum:[msg1, msg2, ...], ...}
errorDict = {}

# GENTAR colony id mapped to GENTAR attributes
# {colonyId:'productionCtr|mutantID|markerID', ...}
colonyToMCLDict = {}

# colony ID to strain Name from the database
colonyToStrainNameDict = {}

# strain name mapped to colony id; colony id can be empty
strainNameToColonyIdDict = {}
multiStrainNameList = []

# strain name mapped to genotype in the database
strainNameToGenotypeDict = {}

# private strain names so we can report when we find one
privateStrainList = []

# allele MGI ID from the database mapped to attributes
# {mgiID:Allele object, ...}
allelesInDbDict = {}
mclInDbDict = {} # uses same query as allelsInDbDict {mclId:[allele1, ...], ...}

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

# List of configured referenceStrains
inputStrainList = []

# Reference Strain to input strain mapping from configuration
referenceStrainDict = {}

# Reference strain template for creating strain nomen from configuration
strainTemplateDict = {}

# Reference strain type from configuration
strainTypeDict = {}

# Reference strain attributes from configuration
strainAttribDict = {}

# uniq set of strain lines written to strainload input file
strainLineList = []

# convenience object for allele information 
#
class Allele:
    def __init__(self, alleleID,    # str.- allele  MGI ID
            alleleSymbol,           # str.- allele symbol
            markerID, 		    # str.- marker MGI ID
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
    global inputFile, inputFileInt, inputFileDup, gentarFile, htmpFile
    global strainFile, logDiagFile, logCurFile, htmpErrorFile, htmpSkipFile
    global allelesInDbDict, mclInDbDict, procCtrToLabCodeDict, phenoCtrList
    global strainInfoDict, referenceStrainDict, strainTemplateDict, strainTypeDict
    global colonyToStrainNameDict, strainNameToColonyIdDict, strainNameToGentypeDict
    global privateStrainList, isIMPC, isLacZ, loadType

    inputFile = os.getenv('SOURCE_COPY_INPUT_FILE')
    inputFileInt = '%s_int' % inputFile
    inputFileDup = '%s_dup' % inputFile
    htmpFile = os.getenv('HTMP_INPUT_FILE')
    strainFile =  os.getenv('STRAIN_INPUT_FILE')
    logDiagFile = os.getenv('LOG_DIAG')
    logCurFile = os.getenv('LOG_CUR')
    htmpErrorFile = os.getenv('HTMPERROR_INPUT_FILE')
    htmpSkipFile = os.getenv('HTMPSKIP_INPUT_FILE')
    loadType = os.getenv('LOADTYPE')
    #print 'loadType: %s' % loadType
    rc = 0

    #
    # determine load type (LOADTYPE)
    # 
    if loadType == 'impc':
        isIMPC = 1
    elif loadType == 'lacz':
        isLacZ = 1
    else:
        print('Environment variable not set: LOADTYPE')
        rc = 1
    if isIMPC or isLacZ:
        gentarFile = os.getenv('GENTAR_COPY_INPUT_FILE')
    #
    # Make sure the environment variables are set.
    #
    if not inputFile:
        print('Environment variable not set: SOURCE_COPY_INPUT_FILE')
        rc = 1

    if (loadType == 'impc' or loadType == 'lacz') and not gentarFile:
        print('Environment variable not set: GENTAR_COPY_INPUT_FILE')
        rc = 1

    if not htmpFile:
        print('Environment variable not set: HTMP_INPUT_FILE')
        rc = 1

    if not htmpErrorFile:
        print('Environment variable not set: HTMPERROR_INPUT_FILE')
        rc = 1

    if not htmpSkipFile:
        print('Environment variable not set: HTMPSKIP_INPUT_FILE')
        rc = 1

    #
    # Allele Status where _vocab_key = 37
    # In Progress (847111)
    # Approved  (847114)
    # Autoload  (3983021)
    # Allele Types where _vocab_key = 38
    # preferred MGI IDs
    #

    db.useOneConnection(1)

    #
    # start: alleles with mutant cell lines
    #	Targeted (847116)
    #   Endonuclease-mediated (11927650)
    #

        #where ll._Allele_Status_key in (847111, 847114, 3983021)
    db.sql('''select distinct a1.accid as alleleMgiID, a2.accid as markerMgiID, 
            ll.symbol as aSymbol, ll._Allele_key
        into temporary table all_withmcl
        from ACC_Accession a1, ACC_Accession a2, ALL_Allele ll
        where ll._Allele_Status_key in (847111, 847114, 3983021)
        and ll._Allele_Type_key in (847116, 11927650)
        and ll._Allele_key = a1._Object_key
        and a1._MGIType_key = 11
        and a1.preferred = 1
        and a1.prefixPart = 'MGI:'
        and ll._Marker_key = a2._Object_key
        and a2._MGIType_key = 2
        and a2.preferred = 1
        and a2.prefixPart = 'MGI:' 
        and exists (select 1 from ALL_Allele_CellLine ac where ll._Allele_key = ac._Allele_key)
        ''', None)

    db.sql('create index idx_targeted on all_withmcl(_Allele_key)', None)

    #
    # select Alleles with Mutant Cell Lines
    #
    #results = db.sql('''
    #	select distinct a.*, a1.accid as mclID
#	from all_withmcl a, ALL_Allele_CellLine ac, ACC_Accession a1
#	where a._Allele_key = ac._Allele_key
#	and ac._MutantCellLine_key = a1._Object_key
#	and a1._MGIType_key = 28
#	and a1.preferred = 1
#	''', 'auto')
    results = db.sql('''
        select distinct a.*, c.cellLine as mclID
        from all_withmcl a, ALL_Allele_CellLine ac, ALL_CellLine c
        where a._Allele_key = ac._Allele_key
        and ac._MutantCellLine_key = c._CellLine_key''', 'auto')
        
    for r in results:
        a = r['alleleMgiID']
        s = r['aSymbol']
        m = r['markerMgiID']
        c = r['mclID']
        if a in allelesInDbDict:
            allelesInDbDict[a].c.append(c)
        else:
            allelesInDbDict[a] = Allele(a, s, m, [c])
        if c not in mclInDbDict:
            mclInDbDict[c] = []
        mclInDbDict[c].append(s)

    # end: alleles with mutant cell lines
   
    # start: alleles without mutant cell lines
    #

    db.sql('''select distinct a1.accid as alleleMgiID, a2.accid as markerMgiID, 
            ll.symbol as aSymbol, ll._Allele_key
        into temporary table all_nomcl
        from ACC_Accession a1, ACC_Accession a2, ALL_Allele ll
        where ll._Allele_Status_key in (847111, 847114, 3983021)
        and ll._Allele_Type_key in (847116, 11927650)
        and ll._Allele_key = a1._Object_key
        and a1._MGIType_key = 11
        and a1.preferred = 1
        and a1.prefixPart = 'MGI:'
        and ll._Marker_key = a2._Object_key
        and a2._MGIType_key = 2
        and a2.preferred = 1
        and a2.prefixPart = 'MGI:' 
        and not exists (select 1 from ALL_Allele_CellLine ac where ll._Allele_key = ac._Allele_key)
        ''', None)

    db.sql('create index idx_endo on all_nomcl(_Allele_key)', None)

    results = db.sql('select distinct * from all_nomcl', 'auto')
    for r in results:
        a = r['alleleMgiID']
        s = r['aSymbol']
        m = r['markerMgiID']
        c = ''
        if a in allelesInDbDict:
            allelesInDbDict[a].c.append(c)
        else:
            allelesInDbDict[a] = Allele(a, s, m, [c])

    # end: alleles without mutant cell lines

    # load production center/labcode mapping 
    results = db.sql('select term, abbreviation from VOC_Term where _Vocab_key = 98', 'auto')
    print('loading procCtrToLabCodeDict')
    for r in results:
        print('term: %s abbrev: %s' % (r['term'], r['abbreviation']))
        procCtrToLabCodeDict[r['term']] = r['abbreviation']

    # load list of phenotyping centers in the database
    results = db.sql('select term from VOC_Term where _Vocab_key = 99', 'auto')
    for r in results:
        phenoCtrList.append(r['term'])

    # load strain mappings from config
    # original:
    # tokens = map(string.strip, string.split(strainInfoMapping, ','))

    # after 2to3, does not work in script, works in inter interp
    # tokens = list(map(str.strip, str.split(strainInfoMapping, ',')))

    # this does not work in the script, but works in the inter interp
    #tokens = list(map(str.strip, strainInfoMapping.split(',')))
    # for the hell of it:
    #tokens = list(map(str.strip(), strainInfoMapping.split(',')))

    # this works too with list comprehension
    #tokens = [x.strip() for x in strainInfoMapping.split(',')]
    tokens = list(map(lambda str : str.strip(), strainInfoMapping.split(',')))
    for t in tokens:
        #iStrain, rID, rStrain, rTemplate, rType, rAttr = str.split(t, '|')
        iStrain, rID, rStrain, rTemplate, rType, rAttr = t.split('|')
        inputStrainList.append(iStrain)
        referenceStrainDict[iStrain] = rStrain
        strainTemplateDict[iStrain] = rTemplate
        strainTypeDict[iStrain]  = rType
        strainAttribDict[iStrain] = rAttr

    #
    # load colony code to strain ID mappings
    # strain types 'coisogenic' and 'Not Specified'
    # strain  may not contain a colony id/will be reported later
    #
    # remove private strain constraint
    results = db.sql('''
        select s.strain, trim(n.note) as colonyID
        from PRB_Strain s, MGI_Note n
        where s._StrainType_key in (3410530, 3410535, 6508969) 
        and s._Strain_key = n._Object_key
        and n._NoteType_key = 1012
        and n._MGIType_key = 10
        ''', 'auto')

    for r in results:
        # HIPPO US146
        # colony ids can be a pipe delimited str.e.g. 'BL3751|BL3751_TCP'
        cIDs =  r['colonyID'].strip()
        strain = r['strain']
        cIDList = []
        if cIDs != None:
            cIDList = list(map(str.strip, cIDs.split('|')))
        # HIPPO 6/2016 handle multi strains/colony ID
        for cID in cIDList:
            if not cID in colonyToStrainNameDict:
                 colonyToStrainNameDict[cID] = [] 
            colonyToStrainNameDict[cID].append(strain)
        # 5/2017 multi strain check addition: 4c1b2
        if strain in strainNameToColonyIdDict:
            multiStrainNameList.append(strain)
        else:
            # HIPPO 6/2016 - handle multi colonyIDs/strain
            strainNameToColonyIdDict[strain] = cIDList

    # load strain name to genotype mappings
    # remove private strain constraint
    results = db.sql('''select distinct s.strain, cl.cellLine, a.accid  as alleleID
        from PRB_Strain s, GXD_Genotype g, GXD_AllelePair ap, ALL_CellLine cl, ACC_Accession a
        where s._Strain_key != -1
        and s.standard = 1
        and g._Strain_key = s._Strain_key
        and g._Genotype_key = ap._Genotype_key
        and ap._MutantCellline_key_1 is not null
        and ap._MutantCellline_key_1 = cl._CellLine_key
        and ap._Allele_key_1 = a._Object_key
        and a._MGIType_key = 11
        and a._LogicalDB_key = 1
        and a.preferred = 1
        and a.prefixPart = 'MGI:' ''', 'auto')

    for r in results:
        # Check 4c1a
        s = r['strain']
        c = r['cellLine']
        a = r['alleleID']
        if s not in strainNameToGenotypeDict:
            strainNameToGenotypeDict[s] = []
        strainNameToGenotypeDict[s].append([a, c])

    results = db.sql('''select strain
            from PRB_Strain
            where private = 1''', 'auto')
    for r in results:
        privateStrainList.append(r['strain'])

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
    global fpInput, fpGENTAR, fpHTMP, fpStrain
    global fpInputintWrite, fpInputdup
    global fpLogDiag, fpLogCur, fpHTMPError, fpHTMPSkip

    #
    # Open the input file
    #
    try:
        fpInput = open(inputFile, 'r')
    except:
        print('Cannot open file: ' + inputFile)
        return 1

    #
    # Open the intermediate file
    #
    try:
        fpInputintWrite = open(inputFileInt, 'w')
    except:
        print('Cannot open file: ' + inputFileInt)
        return 1

    #
    # Open the intermediate Dup file
    #
    try:
        fpInputdup = open(inputFileDup, 'w')
    except:
        print('Cannot open file: ' + inputFileDup)
        return 1

    #
    # Open the GENTAR file
    #
    if loadType == 'impc' or loadType == 'lacz':
        try:
            fpGENTAR = open(gentarFile, 'r')
        except:
            print('Cannot open file: ' + gentarFile)
            return 1

    #
    # Open the htmp output file 
    #
    try:
        fpHTMP = open(htmpFile, 'w')
    except:
        print('Cannot open file: ' + htmpFile)
        return 1

    #
    # Open the strain output file
    #
    try:
        fpStrain = open(strainFile, 'w')
    except:
        print('Cannot open file: ' + strainFile)
        return 1

    #
    # Open the Log Diag file.
    #
    try:
        fpLogDiag = open(logDiagFile, 'a+')
    except:
        print('Cannot open file: ' + logDiagFile)
        return 1

    #
    # Open the Log Cur file.
    #
    try:
        fpLogCur = open(logCurFile, 'a+')
        fpLogCur.write('\n\n######################################\n')
        fpLogCur.write('########## Preprocess Log ##############\n')
        fpLogCur.write('######################################\n\n')

    except:
        print('Cannot open file: ' + logCurFile)
        return 1

    #
    # Open the Error file
    #
    try:
        fpHTMPError = open(htmpErrorFile, 'w')
    except:
        print('Cannot open file: ' + htmpErrorFile)
        return 1

    #
    # Open the Skip file
    #
    try:
        fpHTMPSkip = open(htmpSkipFile, 'w')
    except:
        print('Cannot open file: ' + htmpSkipFile)
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

    if fpInput:
        fpInput.close()

    if fpGENTAR:
        fpGENTAR.close()

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
    if isError:
        fpHTMPError.write(line)

    return 0

#
# Purpose: parse GENTAR report (tab-delimited) file into a data structure
# Returns: 0
# Assumes: fpGENTAR exists 
# Effects: Nothing
# Throws: Nothing
#
def parseGENTARFile():
    global colonyToMCLDict

    print('Parsing GENTAR, creating lookup: %s'  % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))

    for line in fpGENTAR.readlines():

        tokens = line[:-1].split('\t')

        if tokens[0] == 'Marker Symbol':
            continue

        markerID = tokens[1]
        colonyID = tokens[2]
        mutantID = tokens[3]
        productionCtr = tokens[6] # moved from col 6 to 7 in Jan 2020
                                  # found while testing py 2to3

        # map the colony id to productionCtr, mutantID and markerID
        value = '%s|%s|%s' % (productionCtr, mutantID, markerID)

        # if we find a dup, just print for now to see what we get 
        if colonyID in colonyToMCLDict and colonyToMCLDict[colonyID] == value:
            #print('Dup colony ID record: %s|%s' (colonyID, value))
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
    global fpInputintWrite, fpInputdup
    
    jFile = json.load(fpInput)

    # the data interpretation center property value for IMPC
    interpretationCenter = 'IMPC'
    lineSet = set([])

    for f in jFile['response']['docs']:

        try:
            resourceName = f['resource_name']
        except:
            resourceName = ''

        try:
            phenotypingCenter = f['phenotyping_center']
        except:
            phenotypingCenter = ''

        try:
            mpID = f['mp_term_id']
        except:
            mpID = ''

        try:
            alleleID = alleleID2 = f['allele_accession_id']
        except:
            continue  # this was original to load, I did not change to report and skip
        try:
            alleleState = f['zygosity']
        except:
            alleleState = ''

        try:
            alleleSymbol = f['allele_symbol']
        except:
            alleleSymbol = ''

        try:
            inputStrain = f['strain_name']
        except:
            inputStrain = ''

        try:
            markerID = f['marker_accession_id']
        except:
            markerID = ''

        try:
            gender = f['sex']
        except:
            gender = ''

        try:
            colonyID = f['colony_id']
        except:
            colonyID = ''

        # line representing data from the IMPC input file 
        # no productionCenter
        # no mutant ID
        line = resourceName + '\t' + \
             phenotypingCenter + '\t' + \
             interpretationCenter + '\t' + \
             '\t' + \
             '\t' + \
             mpID + '\t' + \
             alleleID + '\t' + \
             alleleState + '\t' + \
             alleleSymbol + '\t' + \
             inputStrain + '\t' + \
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
                inputStrain == '' or \
                markerID == '' or  \
                gender == '' or \
                colonyID == '':
            fpHTMPSkip.write(line)
            continue

        # lineSet assures dups are filtered out
        if line in lineSet:
            fpInputdup.write(line)
            continue

        lineSet.add(line)

    for line in lineSet:
        fpInputintWrite.write(line)

    fpInputintWrite.close()
    fpInputdup.close()

    return 0

# Purpose: parse IMPC/LacZ json file into intermediate file
# Returns: 0
# Assumes: json file descriptor has been created
# Effects: writes intermediate file to file system
# Throws: Nothing
#
def parseIMPCLacZFile():
    global fpInputintWrite, fpIMCPdup

    print('Parsing IMPC/LacZ input file: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
    jFile = json.load(fpInput)
    resourceName = 'IMPC' 
    interpretationCenter = 'IMPC' 
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
        inputStrain = f['strain_name']
        markerID = f['gene_accession_id']
        markerSymbol = f['gene_symbol']
        gender = f['sex']
        colonyID = f['colony_id']

        download_url = f['download_url'] 
        jpeg_url = f['jpeg_url']  
        #full_resolution_file_path = f['full_resolution_file_path']  
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

        # line representing data from the IMPC LacZ input file
        # no productionCenter
        # no mutant ID
        # no MP ID
        line =  resourceName + '\t' + \
             phenotypingCenter + '\t' + \
             interpretationCenter + '\t' + \
             '\t' + \
             '\t' + \
             '\t' + \
             alleleID + '\t' + \
             alleleState + '\t' + \
             alleleSymbol + '\t' + \
             inputStrain + '\t' + \
             markerID + '\t' + \
             gender + '\t' + \
             colonyID + '\n'

        # skip if blank field in IMPC data and report to the skip file
        if phenotypingCenter == '' or \
                alleleID == '' or \
                alleleState == '' or \
                alleleSymbol == '' or \
                inputStrain == '' or \
                markerID == '' or  \
                gender == '' or \
                colonyID == '':
            fpHTMPSkip.write(line)
            continue

        lineSet.add(line)

    for line in lineSet:
        fpInputintWrite.write(line)
        rcdWrittenCt += 1

    fpInputintWrite.close()
    fpInputdup.close()

    print('notExpCt: %s' % notExpCt)
    print('nopasId: %s' % nopasId)
    print('non experimental values: %s' % sGroupValList)
    print('total records written: %s' % rcdWrittenCt)
    print('totalCt: %s' % totalCt)

    return 0

#
# Purpose: determine if the input genotype(s) match the database genotypes for a given strain
# Returns: 1 if a genotype doesn't match
#	0 if all genotypes match OR no genotype for strain in database
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#

def checkGenotype(strainName, inputAlleleID, inputMutantID, line, uniqStrainProcessingKey, caller):
    if strainName in strainNameToGenotypeDict: # check genotype
        genotypeList = strainNameToGenotypeDict[strainName]
        for genotype in genotypeList: # [allele, mcl]
             dbAlleleID = genotype[0]
             dbMutantID = genotype[1]
             if dbAlleleID != inputAlleleID or dbMutantID != inputMutantID:
                # when strain matches the database directly
                if caller == 'uniqStrainProcessing':
                    msg = 'Strain name match in database: %s Genotype mismatch: MGI/database AlleleID: %s Input AlleleID: %s, MGI/database MutantID: %s Input MutantID: %s'  % (strainName, dbAlleleID, inputAlleleID, dbMutantID, inputMutantID)
                    uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
                else: 
                    # when atrain is matched with a colony ID
                    msg = 'Strain name match via colony ID: %s Genotype mismatch: MGI/database AlleleID: %s Input AlleleID: %s, MGI/database MutantID: %s Input MutantID: %s'  % (strainName, dbAlleleID, inputAlleleID, dbMutantID, inputMutantID)
                    #logIt(msg, line, 1, 'cIDmatchGenoMismatch')
                    uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
                return 1
    return 0   # no genotype for strain OR all genotypes for strain match

#
# Purpose: determine if constructed strain is a private strain in the database
# Returns: 1 if strain is private
#       0 if strain is not private
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def checkPrivateStrain(strainName, line, uniqStrainProcessingKey, caller):
    if strainName in privateStrainList:
        if caller  == 'uniqStrainProcessing':
            msg = 'Strain name match to private strain in database: %s ' % (strainName)
            uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
        else:
            # when atrain is matched with a colony ID
            msg = 'Strain name match to private strain via colony ID: %s '  % (strainName)
            uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
        return 1
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
    
    dupStrainKey = 0

    if uniqStrainProcessingKey in list(uniqStrainProcessingDict.keys()):
        uniqStrainProcessingDict[uniqStrainProcessingKey].append(line)
        dupStrainKey = 1

    # unpack the key into attributes
    inputAlleleID, alleleSymbol, inputStrain, markerID, colonyID, inputMutantID, prodCtr = \
        str.split(uniqStrainProcessingKey, '|') 
    # Production Center Lab Code Check US5 doc 4c2
    print('doUniqStrainChecks prodCtr: %s' % prodCtr)
    if not prodCtr in list(procCtrToLabCodeDict.keys()):
        if dupStrainKey == 0:
            msg = 'Production Center not in MGI (voc_term table): %s' % prodCtr
            logIt(msg, line, 1, 'prodCtrNotInDb')
            uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
            
            return 'error'
        else: # we've seen this key already, just return 'error'
            return 'error'

    # Input Strain check #1/#2 US5 doc 4c3
    if dupStrainKey == 0 and inputStrain not in inputStrainList:

        # This is just a check - the strain name will be determined outside this block
        msg = 'Input Strain not configured, "Not Specified" used : %s' % (inputStrain)
        logIt(msg, line, 0, 'inputStrainNotConfigured')
        uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
        
        return 'Not Specified'
    
    # strain name construction US5 doc 4c4
    # if we find a strain root use the template to create strain name

    if inputStrain in referenceStrainDict:
        strainRoot = referenceStrainDict[inputStrain]
        labCode = procCtrToLabCodeDict[prodCtr]
        # if referenceStrainDict has key inputStrain so does strainTemplateDict
        strainTemplate = strainTemplateDict[inputStrain]
        strainName = strainTemplate % (strainRoot, alleleSymbol, labCode)
        
    else:  # otherwise use 'Not Specified'
        return 'Not Specified'

    # 4c1b2 Strain name match to multiple strains
    if strainName in multiStrainNameList:
        msg = 'Multiple strain objects in MGI for strain %s' % strainName
        uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]

        return 'error'

    # Constructed strain name match to strain in db US5 4c5
    # Not Specified strain will not have colonyID in db
    # if there is a colony ID at this point we know it doesn't match
    # because we didn't find it in check US5 4c1

    if strainName in strainNameToColonyIdDict and \
                strainNameToColonyIdDict[strainName] != []:

        dbColonyIdList =  strainNameToColonyIdDict[strainName]
        msg = 'MGI/database colony ID(s) %s for strain %s does not match colony id %s' % \
                (''.join(dbColonyIdList), strainName, colonyID)
        
        uniqStrainProcessingDict[uniqStrainProcessingKey] = [msg, line]
        
        return 'error'
    # check for private strain
    if checkPrivateStrain(strainName, line, uniqStrainProcessingKey, 'uniqStrainProcessing') == 1:
        return 'error'
    # QC the genotype
    if checkGenotype(strainName, inputAlleleID, inputMutantID, line,  uniqStrainProcessingKey, 'uniqStrainProcessing') == 1:
        return 'error'

    strainType = strainTypeDict[inputStrain]
    attributes = strainAttribDict[inputStrain]
    attributes = attributes.replace(':', '|')

    strainLine = strainName + '\t' + \
        inputAlleleID + '\t' + \
        strainType + '\t' + \
        species + '\t' + \
        standard + '\t' + \
        createdBy + '\t' + \
        inputMutantID + '\t' + \
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
    newStrainDict[strainName].add(str.strip(strainLine))
    
    return strainName

#
# Purpose: resolves the input alleleState term to MGI alleleState term
# Returns: str.'error' if input alleleState not recognized, else resolved alleleState
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs 
# Throws: Nothing
#
def checkAlleleState(alleleState, line):
    if alleleState in ['Heterozygous', 'Homozygous', 'Hemizygous']:
        # these are correct, just return them
        return alleleState

    # translate the allele state
    if alleleState.lower() == 'heterozygote':
        alleleState = 'Heterozygous'

    elif alleleState.lower() == 'homozygote':
        alleleState = 'Homozygous'

    elif alleleState.lower() == 'hemizygote':
        alleleState = 'Hemizygous'

    else:
        # report and skip if alleleState is unrecognized
        msg = 'Unrecognized allele state %s' % alleleState
        logIt(msg, line, 1, 'alleleState')
        return  'error'

    return alleleState

#
# Purpose: checks if IMPC colony ID maps to GENTAR colony ID
# Returns: 1 if not GENTAR colony ID for IMPC colony ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def checkColonyID(colonyID, line):

    if not colonyID in colonyToMCLDict:
        msg='No GENTAR colony id for %s' % colonyID
        logIt(msg, line, 1, 'colonyID')
        return 1

    return 0

#
# Purpose: resolves the input gender term to MGI gender term
# Returns: str.'error' if input gender not recognized, else resolved gender
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
        # will be converted to NA later in makeAnnotation.py
        gender = ''

    elif gender.lower() == 'both':
        # will be converted to NA later in makeAnnotation.py
        gender = 'Both'

    else:
        msg = 'Unrecognized gender %s, loaded as NA' % gender
        logIt(msg, line, 1, 'gender')
        gender = 'NA'

    return gender 

#
# Purpose: check the input phenotyping center for existence in the database
# Returns: str.'error' input center not recognized, else center
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
# Purpose: compares IMPC marker ID to GENTAR marker ID
# Returns: 1 if GENTAR marker ID not the same as GENTAR marker ID
# Assumes: Nothing
# Effects: writes to error file and curation/diagnostic logs
# Throws: Nothing
#
def compareMarkers(markerID, gentarMrkID, line):

    if markerID != gentarMrkID:
        # US5 doc 4a2
        # 8/22 all match
        # test file:
        #  gentar.mp.tsv.no_marker_id_match_mgi104848_to_mgi2442056_line_1982
        msg='No Marker ID match. IMPC: %s GENTAR: %s' % (markerID, gentarMrkID)
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
        fpLogCur.write(''.join(fatal))

        # remove the fatal error from the dict so not repeated
        del errorDict['newStrainMultiColId']

    # report remaining error types to curator log
    for type in list(errorDict.keys()):
        fpLogCur.write(''.join(errorDict[type]))

#
# Purpose: Read the intermediate file and re-format it to create a 
#    High-Throughput MP input file
# Returns: 0
# Assumes: input/output files exist and have been opened
# Effects: writes to the file system
# Throws: Nothing
#
def createHTMPFile():
    
    # Values to be calculated
    strainName = ''
    mutantID = ''

    # the htmp lines we will write to a file; some may get filtered out later
    htmpLineDict = {}

    # annotations that should be filtered out i.e not written to the htmp file
    noLoadAnnotList = []

    #
    # Open the intermediate file
    #
    try:
        fpInputintRead = open(inputFileInt, 'r')
    except:
        print('Cannot open file: ' + inputFileInt)
        return 1

    # 
    # Parse the intermediate file where 1) dups are removed 2) lines w/missing 
    #    data skipped
    #
    
    for line in fpInputintRead.readlines():
        error = 0

        # IMPC - mutantID and productionCtr blank
        # Lacz - mutantID, productionCtr and mpID blank
        resourceName, phenotypingCenter, interpretationCenter, productionCtr, \
            mutantID, mpID, alleleID, alleleState, alleleSymbol, inputStrain, \
            markerID, gender, colonyID = line[:-1].split('\t')

        returnVal = checkAlleleState(alleleState, line)
        if returnVal == 'error':
            error = 1
        else: alleleState = returnVal

        gender= checkGender(gender, line)
        
        returnVal= checkPhenoCtr(phenotypingCenter, line)
        if returnVal == 'error':
            error = 1

        # if alleleState or phenotyping error, continue to next line
        if error:
            continue
        #
        # IMPC/LacZ only 
        #
        if isIMPC or isLacZ:
            # verify the IMPC/colony_id with the GENTAR/colonyName
            if checkColonyID(colonyID, line):
                continue

            # verify the IMPC/markerID with the GENTAR/marker ID
            # note that the GENTAR file also provides the 'mutantID' (es cell line)
            productionCtr, mutantID, gentarMrkID = str.split(colonyToMCLDict[colonyID], '|')
            print('productionCtr: %s from colonyToMCLDict[colonyID]' % (productionCtr))

            if compareMarkers(markerID, gentarMrkID, line):
                continue

        # Allele/MCL Object Identity/Consistency Check US5 doc 4b

        if alleleID in allelesInDbDict: # 4b2a

            dbAllele = allelesInDbDict[alleleID]

            # report this but don't exclude it
            if alleleSymbol != dbAllele.s:
                msg = 'Allele Symbol: %s does not match MGI symbol: %s' % (alleleSymbol, dbAllele.s)
                logIt(msg, line, 1, 'alleleNotMatch')
                error = 1

            if markerID != dbAllele.m:
                msg = 'Marker ID: %s does not match MGI marker ID: %s' % (markerID, dbAllele.m)
                logIt(msg, line, 1, 'markerNotMatch')
                error = 1

            # If input row has MCL, but that MCL is associated with a 
            # only a different allele in MGI than specified in the input file, 
            # report and skip
            if mutantID != '' and mutantID not in dbAllele.c and mutantID in mclInDbDict:
                dbAlleleList = mclInDbDict[mutantID]
                if alleleSymbol not in dbAlleleList:
                    msg = 'Mutant ID: %s is associated with different allele(s) in the database. Incoming allele: %s, DB Allele(s) %s' % (mutantID, alleleSymbol, ', '.join(dbAlleleList))
                    logIt(msg, line, 1, 'mclDiffAllele')
                    error = 1
            # If input row has MCL, but that MCL is not associated with 
            # the allele in MGI - report as non-fatal error, load data 
            # using null MCL for genotype
            elif mutantID != '' and mutantID not in dbAllele.c:
                msg = ' Mutant ID: %s is not associated with %s in MGI loading data with null-MCL' % (mutantID, alleleID)
                logIt(msg, line, 1, 'mutIdNotAssoc')
                mutantID = ''

        else: # US5 doc 4b2
            # 15 cases in impc.json e.g. NULL-114475FCF4
            msg = 'Allele not in MGI: %s' % alleleID
            logIt(msg, line, 1, 'alleleNotInDb')
            error = 1

        if error == 1:
            continue

        #
        # Now do checks on the uniq strains in the input file
        #

        # key to determine uniq entries for strain processing
        uniqStrainProcessingKey = '%s|%s|%s|%s|%s|%s|%s' % \
            (alleleID, alleleSymbol, inputStrain, markerID, \
                colonyID, mutantID, productionCtr)
        #print('uniqStrainPrcessingKey: %s' % uniqStrainProcessingKey)
        # resolve the colonyID to a strain in the database
        if colonyID in colonyToStrainNameDict:
            # HIPPO US146 case #4
            # multiple strains for a colony ID
            #print('colonyID: %s strains: %s' % (colonyID, colonyToStrainNameDict[colonyID]))
            if len(colonyToStrainNameDict[colonyID]) > 1:
                msg =  'Colony ID: %s associated with multiple strains in the database: %s' % (colonyID, ', '.join(colonyToStrainNameDict[colonyID]) )
                logIt(msg, line, 1, 'colIdMultiStrains')
                for c in colonyToStrainNameDict[colonyID]:
                    checkPrivateStrain(c, line, uniqStrainProcessingKey, 'colonyIdMatch')
                continue
            # if we get here we have a single strain
            strainName = colonyToStrainNameDict[colonyID][0]

            # check for private strain
            if checkPrivateStrain(strainName, line, uniqStrainProcessingKey, 'colonyIdMatch') == 1:
                continue

            # QC the genotype
            if checkGenotype(strainName, alleleID, mutantID, line, uniqStrainProcessingKey, 'colonyIdMatch') == 1:
                continue
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
            continue

        #htmpLine = phenotypingCenter + '\t' + \
        #     interpretationCenter + '\t' + \
        #     mutantID + '\t' + \
        #     mpID + '\t' + \
        #     alleleID + '\t' + \
        #     alleleState + '\t' + \
        #     alleleSymbol + '\t' + \
        #     markerID + '\t' + \
        #     evidenceCode + '\t' + \
        #     strainName + '\t' + \
        #     gender + '\t' + \
        #     colonyID + '\t' + \
        #     resourceName + '\n'
        htmpLine = '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % (phenotypingCenter, TAB, interpretationCenter, TAB, mutantID, TAB, mpID, TAB, alleleID, TAB, alleleState, TAB, alleleSymbol, TAB, markerID, TAB, evidenceCode, TAB, strainName, TAB, gender, TAB, colonyID, TAB, resourceName, CRT)
        #fpHTMP.write(htmpLine)

        # save the lines to a data structure with 'strain|colonyID' key
        # later we look for multiple colony IDs per strain and annotations
        # to load for just ONE colony ID. We DO NOT want to load annotations
        # for the rejected colony ID(s), we just want to report them
        key = '%s|%s' % (strainName, colonyID)
        if key not in htmpLineDict:
            htmpLineDict[key] = []
        htmpLineDict[key].append(htmpLine)

    for key in list(uniqStrainProcessingDict.keys()):
        msgList = uniqStrainProcessingDict[key]
        msg = msgList[0]
        for line in msgList[1:]:
            if 'Input Strain not configured' in msg:
                logIt(msg, line, 0, 'inputStrainNotConfigured')
            else:
                logIt(msg, line, 1, 'inputStrainNotConfigured')
    #
    # HIPPO US146 - check for new strains with multiple colony ids
    #
    for s in newStrainDict:
        # we have multi colony ids for this strain, pick one to load, report
        # the rest
        if len(newStrainDict[s]) > 1:
            msg = 'New strain with multiple Colony IDs. Strain created, with Colony ID note:%s. Genotype and annotations not created. The following colonyID note(s) not created:'

            # get input lines for this new strain
            multiSet = newStrainDict[s]

            # Add strain/cID(s) to the list whose genotypes/annotations we 
            # will not load
            for line in list(multiSet):
                cID = str.split(line, '\t')[7]
                # this corresponds to the key in htmpLineDict
                key = '%s|%s' % (s, cID)
                noLoadAnnotList.append(key)

            # get a arbitrary line from the list, the strain will be loaded with
            # this colony ID
            strainToLoad = multiSet.pop()

            # plug the colony ID which WAS loaded into the error message
            msg = msg % str.split(strainToLoad)[8]

            # write out the strain to load
            fpStrain.write('%s%s' % (strainToLoad, '\n'))

            # get the  lines with the remaining colony ids for the strain,
            # report
            strainLines = '\n'.join(multiSet)
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
    print('writing to curator log')
    writeCuratorLog()

    return 0

#
#  MAIN
#

print('initialize: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
if initialize() != 0:
    sys.exit(1)

print('openFiles: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
if openFiles() != 0:
    sys.exit(1)

if isIMPC or isLacZ:
    print('parseGENTARFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
    if parseGENTARFile() != 0:
        sys.exit(1)

#
# process either IMPC/MP, IMPC/LacZ input file
#
if isIMPC:
    print('parseIMPCFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
    if parseIMPCFile() != 0:
        sys.exit(1)
elif isLacZ:
    print('parseIMPCLacZFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
    if parseIMPCLacZFile() != 0:
        sys.exit(1)

print('createHTMPFile: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
returnCode = createHTMPFile()
if returnCode != 0:
    closeFiles()
    sys.exit(returnCode)

closeFiles()
print('done: %s' % time.strftime("%H.%M.%S.%m.%d.%y", time.localtime(time.time())))
sys.exit(0)
