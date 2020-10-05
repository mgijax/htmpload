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
#
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
#
# 06/2017	sc
#	TR12579 & TR12508 - use colony ID as object identity for strain
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
import Set

db.setTrace(True)

# set to 1 for debug printout
DEBUG = 0

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
errMsg: %s
line: %s
field: %s
%s
'''

#
# key = str(markerKey) + str(alleleKey) + str(alleleState) + str(strainKey)  + str(mutantKey)
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
        print('Environment variable not set: LOG_DIAG')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not logCurFile:
        print('Environment variable not set: LOG_CUR')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not htmpInputFile:
        print('Environment variable not set: INPUTDIR/HTMP_INPUT_FILE')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not htmpDupFile:
        print('Environment variable not set: HTMPDUP_INPUT_FILE')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not htmpErrorFile:
        print('Environment variable not set: HTMPERROR_INPUT_FILE')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not HTMPFile:
        print('Environment variable not set: HTMP_INPUT_FILE')
        rc = 1

    #
    # Make sure the environment variables are set.
    #
    if not genotypeFile:
        print('Environment variable not set: GENOTYPE_INPUT_FILE')
        rc = 1

    db.useOneConnection(1)

    #
    # grab/save existing strains
    # include: strains with IMPC colony ids
    # include: "Not Specified" strain
    #
    # _Strain_key
    # strain
    # strain accession id
    # colonyID
    #

    db.sql('''
        select s._Strain_key, s.strain, a.accID as strainID, regexp_replace(regexp_replace(nc.note, '^\s+', ''), '\s+$', '') as colonyID
        into temporary table strains
        from PRB_Strain s, ACC_Accession a, MGI_Note n, MGI_NoteChunk nc
        where s._Strain_key = a._Object_key
        and a._MGIType_key = 10
        and a._LogicalDB_key = 1
        and a.preferred = 1
        and s._Strain_key = n._Object_key
        and n._NoteType_key = 1012
        and n._Note_key = nc._Note_key
        union
        select s._Strain_key, s.strain, a.accID as strainID, null
        from PRB_Strain s, ACC_Accession a
        where s._Strain_key = a._Object_key
        and a._MGIType_key = 10
        and a._LogicalDB_key = 1
        and a.preferred = 1
        and s._Strain_key = -1
        ''', 'auto')

    db.sql('create index idx1 on strains(strain)', None)
    db.sql('create index idx2 on strains(colonyID)', None)
    #
    # grab/save existing genotypes
    #
    #   genotype accession id
    #   allele pair state
    #   genotype/isConditional = 0
    #   genotype strain key
    #   genotype/created by = createdBy (in configuration, example: 'htmpload')
    #   allele key 1/2 : uses keys
    #   mutant cell line 1/2 : uses keys
    #
    # 6/17 - removed _ModifiedBy_key restriction i.e. curator can modify
    #   but still want to create new genotype if curator created.

    db.sql('''
        select a.accID, ap.*, t.term, g._Strain_key
        into temporary table genotypes
        from GXD_Genotype g, GXD_AllelePair ap,
             ACC_Accession a, VOC_Term t, MGI_User u1
        where g._Genotype_key = a._Object_key
        and a._MGIType_key = 12
        and a._LogicalDB_key = 1
        and a.preferred = 1
        and g.isConditional = 0
        and g._Genotype_key = ap._Genotype_key
        and ap._PairState_key = t._Term_key
        and t._Vocab_key = 39
        and g._CreatedBy_key = u1._User_key
        and u1.login = '%s'
        ''' % (createdBy), None)

    db.sql('create index idx3 on genotypes(_Marker_key)', None)

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
        print('Cannot open file: ' + logDiagFile)
        return 1

    #
    # Open the Log Cur file.
    #
    try:
        fpLogCur = open(logCurFile, 'a+')
        fpLogCur.write('\n\n######################################\n')
        fpLogCur.write('########## makeGenotype Log ##########\n')
        fpLogCur.write('######################################\n\n')

    except:
        print('Cannot open file: ' + logCurFile)
        return 1

    #
    # Open the HTMP input file
    #
    try:
        fpHTMPInput = open(htmpInputFile, 'r')
    except:
        print('Cannot open file: ' + htmpInputFile)
        return 1

    #
    # Open the Dup file
    #
    try:
        fpHTMPDup = open(htmpDupFile, 'w')
    except:
        print('Cannot open file: ' + htmpDupFile)
        return 1

    #
    # Open the Error file
    #
    try:
        fpHTMPError = open(htmpErrorFile, 'a+')
    except:
        print('Cannot open file: ' + htmpErrorFile)
        return 1

    #
    # Open the file with genotype sequence #
    #
    try:
        fpHTMP = open(HTMPFile, 'w')
    except:
        print('Cannot open file: ' + HTMPFile)
        return 1

    #
    # Open the genotype file.
    #
    try:
        fpGenotype = open(genotypeFile, 'w')
    except:
        print('Cannot open genotype file: ' + genotypeFile)
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
    
    # annotations organized by order/mpID
    # 'order' indicates uniq genotype
    # key = order + '|' + mpID
    # value = list of lines
    annotDict = {}

    for line in fpHTMPInput.readlines():

        if DEBUG:
            print('\nNEW LINE: ', line)

        error = 0
        lineNum = lineNum + 1

        tokens = line[:-1].split('\t')

        # sc 2/6/2016 - a subtlety:
        # if genotypeID  remains '', the genotype is not in the database
        # if it is assigned an ID from the database, it is still written to
        # the genotypeload input file because this file is used as input to the
        # annotation load.  The genotypeload will only create
        # a genotype if the genotypeID field is ''

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
        strainName = tokens[9]
        gender = tokens[10]
        colonyID = tokens[11]

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

        if DEBUG:
            print('    markerID: %s markerKey: %s' % (markerID, markerKey))

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

        if DEBUG:
            print('    alleleID: %s alleleKey: %s' % (alleleID, alleleKey))

        # mutant

        if len(mutantID) > 0:
           mutantKey = alleleloadlib.verifyMutnatCellLine(mutantID, lineNum, fpLogDiag)
           mutantKey2 = mutantKey
           mutantSQL = mutantSQL2 = '='

        else:
            mutantSQL = 'is'
            mutantKey = 'null'

        #
        # if the MCL in the input file does not match the Allele/MCL association in MGD,
        # (i.e. the mutantKey returned from the alleleloadlib lookup is null),
        # then add the Genotype with null MCLs (see TR12508).
        #
        if mutantKey == 0:
            mutantID = ''
            mutantID2 = ''
            #logit = errorDisplay % (mutantID, lineNum, '3', line)
            #fpLogDiag.write(logit)
            #fpLogCur.write(logit)
            #error = 1

        if DEBUG:
            print('    mutantID: %s mutantKey: %s' % (mutantID, mutantKey))

        # strain should have been added by the previous makeStrains.sh 
        # wrapper but in case it was not...
 
        strainID = ''
        strainKey = 0

        # NS strain does not have colony ID, so don't check
        if strainName == 'Not Specified':
            results = db.sql(''' select * from strains where strain = '%s' ''' % strainName, 'auto')
        else:
            results = db.sql(''' select * from strains where strain = '%s' and colonyID like'%%%s%%' ''' % (strainName, colonyID), 'auto')

        for r in results:
           strainID = r['strainID']
           strainKey = r['_Strain_key']

        if strainKey == 0:
            logit = errorDisplay % (strainName + '|' + colonyID, lineNum, '10', line)
            fpLogDiag.write(logit)
            fpLogCur.write(logit)
        if DEBUG:
            print('    strainName: %s strainID %s strainKey: %s\n' % (strainName, strainID, strainKey))

        # if allele is Heterzygous, then marker must have a wild-type allele
        if alleleState == 'Heterozygous':

            if DEBUG:
                print('    if allele is Heterzygous, then marker must have a wild-type allele, get it')
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

            if DEBUG:
                print(querySQL)

            results = db.sql(querySQL, 'auto')
            for r in results:
                # found the wild type, so set it
                alleleID2 = r['accID']
                mutantID2 = ''

            if DEBUG:
                print('    found wild type and alleleID2: %s mutantID2: %s' % (alleleID2, mutantID2))

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

        #
        # check alleleState
        #

        if DEBUG:
            print('\n    Check AlleleState:')

        if alleleState == 'Homozygous':

            if DEBUG:
                print('    Homozygous : querying to find genotype')

            querySQL = '''
                select g.accID
                        from genotypes g
                        where g._Marker_key = %s
                        and g._Allele_key_1 = %s
                        and g._Allele_key_2 = %s
                        and g._MutantCellLine_key_1 %s %s
                        and g._MutantCellLine_key_2 %s %s
                        and g.term = '%s'
                        and g._Strain_key = %s
                ''' % (markerKey, alleleKey, alleleKey, mutantSQL, mutantKey, mutantSQL, mutantKey, alleleState, strainKey)

            if DEBUG:
                print(querySQL)

            results = db.sql(querySQL, 'auto')

            if len(results) > 1:
                if DEBUG:
                    print('    More than one genotype - last one wins')
                    print('    %s' % results)

            for r in results:
                genotypeID = r['accID']

            if DEBUG:
                print('    genotypeID: %s' % genotypeID)

        elif alleleState == 'Heterozygous':

            #
            # for heterzygous, allele 2 = the wild type allele 
            #   (marker symbol + '<+>')
            # find the wild type allele accession id
            #

            if DEBUG:
                print('    Heterozygous : querying to find genotype')

            querySQL = '''
                select g.accID
                        from genotypes g
                        where g._Marker_key = %s
                        and g._Allele_key_1 = %s
                        and g._Allele_key_2 != %s
                        and g._MutantCellLine_key_1 %s %s
                        and g._MutantCellLine_key_2 is null
                        and g.term = '%s'
                        and g._Strain_key = %s
                ''' % (markerKey, alleleKey, alleleKey, mutantSQL, mutantKey, alleleState, strainKey)

            if DEBUG:
                print(querySQL)

            results = db.sql(querySQL, 'auto')

            if len(results) > 1:
                if DEBUG:
                    print('    More than one genotype - last one wins')
                    print('    %s' % results)

            for r in results:
                genotypeID = r['accID']

            if DEBUG:
                print('    genotypeID: %s' % genotypeID)

        elif alleleState in ('Hemizygous', 'Indeterminate'):

            if DEBUG:
                print('    querying to find genotype : ', alleleState)

            alleleID2 = ''
            mutantID2 = ''

            if alleleState == 'Hemizygous':

                querySQL = '''
                    select chromosome 
                        from MRK_Marker 
                        where _Marker_key = %s''' % markerKey

                results = db.sql(querySQL, 'auto')

                for r in results:

                    if r['chromosome'] == 'X':
                        alleleState = 'Hemizygous X-linked'
                        if DEBUG:
                            print('    ', alleleState)

                    elif r['chromosome'] == 'Y':
                        alleleState = 'Hemizygous Y-linked'
                        if DEBUG:
                            print('    ', alleleState)

                    else:
                        logit = errorDisplay % (alleleState, lineNum, '6', line)
                        logit = logit + 'pair state %s does not match chromosome %s' % (alleleState, r['chromosome'])
                        if DEBUG:
                            print('    ', logit)

                        fpLogDiag.write(logit)
                        fpLogCur.write(logit)
                        error = 1
                        break

            querySQL = '''
                select g.accID
                        from genotypes g
                        where g._Marker_key = %s
                        and g._Allele_key_1 = %s
                        and g._Allele_key_2 is null
                        and g._MutantCellLine_key_1 %s %s
                        and g._MutantCellLine_key_2 is null
                        and g.term = '%s'
                        and g._Strain_key = %s
                ''' % (markerKey, alleleKey, mutantSQL, mutantKey, alleleState, strainKey)
            
            if DEBUG:
                print(querySQL)

            results = db.sql(querySQL, 'auto')

            if len(results) > 1:
                if DEBUG:
                    print('    More than one genotype - last one wins')
                    print('    %s' % results)

            for r in results:
                genotypeID = r['accID']

            if DEBUG:
                print('    genotypeID: %s' % genotypeID)

        else:
            logit = errorDisplay % (alleleState, lineNum, '6', line)

            if DEBUG:
                print('    logging error:')
                print('    ' + errorDisplay % (alleleState, lineNum, '6', line))

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
        # duplicate genotypes WITHIN the input file, doesn't mean the genotype
        # isn't in the database

        dupGeno = 0
        useOrder = str(genotypeOrder)

        if DEBUG:
            print('    check genotype uniqueness')

        #
        # set uniqueness
        # isConditional is always 0, so we do not need to specify this value
        #
        key = str(markerKey) + str(alleleKey) + str(alleleState) + str(strainKey) + str(mutantKey)

        if DEBUG:
            print('    unique key is: %s' % key)

        if key in genotypeOrderDict:
            dupGeno = 1
            useOrder = str(genotypeOrderDict[key])
            if DEBUG:
                print('    duplicate genotype and order is: %s' % useOrder)

        # uniq genotype/mpID key
        currentMP = useOrder + '|' + mpID

        #### new code HDP-2 US161 support TR11792 ####
        # add line to dictionary by currentMP key for later processing
        if currentMP not in annotDict:
            annotDict[currentMP] = []
        annotDict[currentMP].append(line)

        if dupGeno:
            fpHTMPDup.write(line)
            continue

        #
        # save genotype order
        #
        if DEBUG:
            print('    saving genotype order genotypeOrderDict[%s] = %s' % (key, genotypeOrder))
        genotypeOrderDict[key] = genotypeOrder

        #
        # add to genotype mgi-format file
        #

        if DEBUG:
            print('    writing genotype to  genotype file')

        fpGenotype.write(genotypeLine % (\
                genotypeOrder, genotypeID, strainID, strainName, \
                markerID, alleleID, mutantID, alleleID2, mutantID2, \
                conditional, existsAs, generalNote, privateNote, alleleState, \
                compound, createdBy))

        genotypeOrder = genotypeOrder + 1

    #### new code HDP-2 US161 support TR11792 ####
    # iterate through annotDict

    for key in list(annotDict.keys()):
        order, mpID = key.split('|')
        lineList = annotDict[key]
        genderSet = set([])

        # get the gender for each line and add to the set
        for line in lineList:
            tokens = line.split('\t')
            genderSet.add(tokens[10])

        # if multi lines, the only difference is gender
        # just get the last (or only) line in the list; prepend the order number
        line = order + '\t' + line

        # if there are multi gender values in the set, update line to 'Both'
        if len(genderSet) > 1:
            # Don't bother to look at values. If already 'Both', we're golden
            # otherwise just update the line to 'Both'
            line = line.replace('Male', 'Both')
            line = line.replace('Female', 'Both')

        # now write out the line
        fpHTMP.write(line)

    return 0

#
#  MAIN
#

if DEBUG:
    print('initialize')

if initialize() != 0:
    sys.exit(1)

if DEBUG:
    print('open files')

if openFiles() != 0:
    sys.exit(1)

if DEBUG:
    print('get genotypes')

if getGenotypes() != 0:
    closeFiles()
    sys.exit(1)

if DEBUG:
    print('close files')

closeFiles()
sys.exit(0)
