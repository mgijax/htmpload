#!/usr/local/bin/python
#
# Program: makeIMPCStrains.py
#
# Original Author: sc
#
# Purpose:
#
#	To load new IMPC Strains into:
#
#	PRB_Strain
#	PRB_Strain_Marker
#	ACC_Accession
#	VOC_Annot
#	MGI_Note/MGI_NoteChunk
#
#
# Usage:
#	makeIMPCStrains.py
#
# Envvars:
#
# Inputs:
#
#	A tab-delimited file in the format:
#
#       1. Strain Name
#       2. MGI Allele ID 
#       3. Strain Type
#       4. Strain Species
#       5. Standard
#       6. Created By
#       7. Mutant ES Cell line of Origin note
#       8. Colony ID Note
#       9. Strain Attributes
#
# Outputs:
#
#       BCP files:
#       PRB_Strain.bcp                  master Strain records
#       PRB_Strain_Marker.bcp           
#       VOC_Annot.bcp			strain attributes
#	ACC_Accession.bcp		strain MGI ID
#       MGI_Note/MGI_NoteChunk          MCL of origin & colony ID  notes
#
#       Diagnostics file of all input parameters and SQL commands
#       Error file
#
# Exit Codes:
#
# Assumes:
#
#	That no one else is adding records to the database.
#
# History
#
# sc	08/29/2014
#	- TR11674 IMPC/HDP II project
#

import sys
import os
import db
import mgi_utils
import loadlib

# globals

user = os.environ['MGD_DBUSER']
passwordFileName = os.environ['MGD_DBPASSWORDFILE']
mode = os.environ['STRAINMODE']
inputFileName = os.environ['STRAIN_INPUT_FILE']
logDir = os.environ['LOGDIR']
outputDir = os.environ['OUTPUTDIR']

DEBUG = 0		# if 0, not in debug mode
TAB = '\t'		# tab
CRT = '\n'		# carriage return/newline

bcpon = 1		# bcp into the database?  default is yes.

diagFile = ''		# diagnostic file descriptor
errorFile = ''		# error file descriptor
inputFile = ''		# file descriptor
strainFile = ''         # file descriptor
markerFile = ''         # file descriptor
accFile = ''            # file descriptor
annotFile = ''          # file descriptor
noteFile = ''           # file descriptor
noteChunkFile = ''      # file descriptor

strainTable = 'PRB_Strain'
markerTable = 'PRB_Strain_Marker'
accTable = 'ACC_Accession'
annotTable = 'VOC_Annot'
noteTable = 'MGI_Note'
noteChunkTable = 'MGI_NoteChunk'

strainFileName = outputDir + '/' + strainTable + '.bcp'
markerFileName = outputDir + '/' + markerTable + '.bcp'
accFileName = outputDir + '/' + accTable + '.bcp'
annotFileName = outputDir + '/' + annotTable + '.bcp'
noteFileName = outputDir + '/' + noteTable + '.bcp'
noteChunkFileName = outputDir + '/' + noteChunkTable + '.bcp'

diagFileName = ''	# diagnostic file name
errorFileName = ''	# error file name

strainKey = 0           # PRB_Strain._Strain_key
strainmarkerKey = 0	# PRB_Strain_Marker._StrainMarker_key
accKey = 0              # ACC_Accession._Accession_key
mgiKey = 0              # ACC_AccessionMax.maxNumericPart
annotKey = 0
noteKey = 0             # MGI_Note._Note_key

isPrivate = 0
isGeneticBackground = 0
NULL = ''

mgiTypeKey = 10		# ACC_MGIType._MGIType_key for Strains
mgiPrefix = "MGI:"
alleleTypeKey = 11	# ACC_MGIType._MGIType_key for Allele
markerTypeKey = 2       # ACC_MGIType._MGIType_key for Marker
mgiNoteObjectKey = 10   # MGI_Note._MGIType_key
mgiNoteSeqNum = 1       # MGI_NoteChunk.sequenceNum
mgiImpcColonyIdKey = 1012   # MGI_Note._NoteType_key
mgiMutantOriginTypeKey = 1038   # MGI_Note._NoteType_key

qualifierKey = 615427	# nomenclature

strainDict = {}      	# dictionary of types for quick lookup
strainTypesDict = {}    # dictionary of types for quick lookup
colonyIdDict = {}	# dictionary of strain keys mapped to note keys
speciesDict = {}      	# dictionary of species for quick lookup

cdate = mgi_utils.date('%m/%d/%Y')	# current date
 
# Purpose: prints error message and exits
# Returns: nothing
# Assumes: nothing
# Effects: exits with exit status
# Throws: nothing

def exit(
    status,          # numeric exit status (integer)
    message = None   # exit message (string)
    ):

    if message is not None:
        sys.stderr.write('\n' + str(message) + '\n')
 
    try:
        diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.close()
        errorFile.close()
	inputFile.close()
    except:
        pass

    db.useOneConnection(0)
    sys.exit(status)
 
# Purpose: process command line options
# Returns: nothing
# Assumes: nothing
# Effects: initializes global variables
#          calls showUsage() if usage error
#          exits if files cannot be opened
# Throws: nothing

def init():
    global diagFile, errorFile, inputFile, errorFileName, diagFileName
    global strainFile, markerFile, accFile, annotFile
    global noteFile, noteChunkFile
 
    db.useOneConnection(1)
    db.set_sqlUser(user)
    db.set_sqlPasswordFromFile(passwordFileName)
 
    fdate = mgi_utils.date('%m%d%Y')	# current date
    head, tail = os.path.split(inputFileName) 
    diagFileName = logDir + '/' + tail + '.' + fdate + '.diagnostics'
    errorFileName = logDir + '/' + tail + '.' + fdate + '.error'

    try:
        diagFile = open(diagFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % diagFileName)
		
    try:
        errorFile = open(errorFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % errorFileName)
		
    try:
        inputFile = open(inputFileName, 'r')
    except:
        exit(1, 'Could not open file %s\n' % inputFileName)

    try:
        strainFile = open(strainFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % strainFileName)

    try:
        markerFile = open(markerFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % markerFileName)

    try:
        accFile = open(accFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % accFileName)

    try:
        noteFile = open(noteFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % noteFileName)

    try:
        noteChunkFile = open(noteChunkFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % noteChunkFileName)

    try:
        annotFile = open(annotFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % annotFileName)

    # Log all SQL
    db.set_sqlLogFunction(db.sqlLogAll)

    # Set Log File Descriptor
    db.set_sqlLogFD(diagFile)

    diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
    diagFile.write('Server: %s\n' % (db.get_sqlServer()))
    diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))

    errorFile.write('Start Date/Time: %s\n\n' % (mgi_utils.date()))

    return

# Purpose: verify processing mode
# Returns: nothing
# Assumes: nothing
# Effects: if the processing mode is not valid, exits.
#	   else, sets global variables
# Throws:  nothing

def verifyMode():

    global DEBUG

    if mode == 'preview':
        DEBUG = 1
        bcpon = 0
    elif mode != 'load':
        exit(1, 'Invalid Processing Mode:  %s\n' % (mode))


# Purpose:  verify Species
# Returns:  Species Key if Species is valid, else 0
# Assumes:  nothing
# Effects:  verifies that the Species exists either in the Species dictionary or the database
#	writes to the error file if the Species is invalid
#	adds the Species and key to the Species dictionary if the Species is valid
# Throws:  nothing

def verifySpecies(
    species, 	# Species (string)
    lineNum	# line number (integer)
    ):

    global speciesDict

    if len(speciesDict) == 0:
        results = db.sql('select _Term_key, term from VOC_Term where _Vocab_key = 26', 'auto')

        for r in results:
	    speciesDict[r['term']] = r['_Term_key']

    if speciesDict.has_key(species):
            speciesKey = speciesDict[species]
    else:
            errorFile.write('Invalid Species (%d) %s\n' % (lineNum, species))
            speciesKey = 0

    return speciesKey

# Purpose:  verify Strain Type
# Returns:  Strain Type Key if Strain Type is valid, else 0
# Assumes:  nothing
# Effects:  verifies that the Strain Type exists either in the Strain Type dictionary or the database
#	writes to the error file if the Strain Type is invalid
#	adds the Strain Type and key to the Strain Type dictionary if the Strain Type is valid
# Throws:  nothing

def verifyStrainType(
    strainType, 	# Strain Type (string)
    lineNum		# line number (integer)
    ):

    global strainTypesDict

    if len(strainTypesDict) == 0:
        results = db.sql('select _Term_key, term from VOC_Term where _Vocab_key = 55', 'auto')

        for r in results:
	    strainTypesDict[r['term']] = r['_Term_key']

    if strainTypesDict.has_key(strainType):
            strainTypeKey = strainTypesDict[strainType]
    else:
            errorFile.write('Invalid Strain Type (%d) %s\n' % (lineNum, strainType))
            strainTypeKey = 0

    return strainTypeKey

# Purpose:  check for  Colony ID note for a strain
# Returns:  1 if strain has a colony ID in the database, else 0
# Assumes:  nothing
# Effects:  determines if a colony ID note exists for a Strain Type either the 
# 	Colony ID Strain dictionary or the database

def checkColonyNote(strainKey):
    global colonyIdDict
    if len(colonyIdDict)== 0:
        results = db.sql('''select _Note_key, _Object_key as strainKey
		from MGI_Note 
		where _MGIType_key = %s
		and _NoteType_key = %s''' % \
		    (mgiTypeKey, mgiImpcColonyIdKey), 'auto')
        for r in results:
            colonyIdDict[r['strainKey']] = r['_Note_key']
    if colonyIdDict.has_key(strainKey):
	return 1
    return 0
	
# Purpose:  verify Strain
# Returns:  Strain Key if Strain is valid, else 0
# Assumes:  nothing
# Effects:  verifies that the Strain exists either in the Strain dictionary or the database
#	writes to the error file if the Strain is invalid
#	adds the Strain and key to the Strain dictionary if the Strain Type is valid
# Throws:  nothing

def verifyStrain(
    strain, 	# Strain (string)
    lineNum	# line number (integer)
    ):

    global strainDict

    results = db.sql('select _Strain_key, strain from PRB_Strain where strain = "%s"' % (strain), 'auto')

    for r in results:
        strainDict[r['strain']] = r['_Strain_key']

    if strainDict.has_key(strain):
            strainExistKey = strainDict[strain]
            errorFile.write('Strain Already Exists (%d) %s\n' % (lineNum, strain))
    else:
            #errorFile.write('Invalid Strain (%d) %s\n' % (lineNum, strain))
            strainExistKey = 0

    return strainExistKey

# Purpose:  sets global primary key variables
# Returns:  nothing
# Assumes:  nothing
# Effects:  sets global primary key variables
# Throws:   nothing

def setPrimaryKeys():

    global strainKey, strainmarkerKey, accKey, mgiKey, annotKey, noteKey

    results = db.sql('select maxKey = max(_Strain_key) + 1 from PRB_Strain', 'auto')
    strainKey = results[0]['maxKey']

    results = db.sql('select maxKey = max(_StrainMarker_key) + 1 from PRB_Strain_Marker', 'auto')
    strainmarkerKey = results[0]['maxKey']

    results = db.sql('select maxKey = max(_Accession_key) + 1 from ACC_Accession', 'auto')
    accKey = results[0]['maxKey']

    results = db.sql('select maxKey = maxNumericPart + 1 from ACC_AccessionMax ' + \
        'where prefixPart = "%s"' % (mgiPrefix), 'auto')
    mgiKey = results[0]['maxKey']

    results = db.sql('select maxKey = max(_Annot_key) + 1 from VOC_Annot', 'auto')
    annotKey = results[0]['maxKey']

    results = db.sql('select maxKey = max(_Note_key) + 1 from MGI_Note', 'auto')
    noteKey = results[0]['maxKey']

# Purpose:  BCPs the data into the database
# Returns:  nothing
# Assumes:  nothing
# Effects:  BCPs the data into the database
# Throws:   nothing

def bcpFiles():

    bcpdelim = "|"

    if DEBUG or not bcpon:
        return

    strainFile.close()
    markerFile.close()
    accFile.close()
    annotFile.close()
    noteFile.close()
    noteChunkFile.close()

    bcpI = 'cat %s | bcp %s..' % (passwordFileName, db.get_sqlDatabase())
    bcpII = '-c -t\"|" -S%s -U%s' % (db.get_sqlServer(), db.get_sqlUser())
    truncateDB = 'dump transaction %s with truncate_only' % (db.get_sqlDatabase())

    bcp1 = '%s%s in %s %s' % (bcpI, strainTable, strainFileName, bcpII)
    bcp2 = '%s%s in %s %s' % (bcpI, markerTable, markerFileName, bcpII)
    bcp3 = '%s%s in %s %s' % (bcpI, accTable, accFileName, bcpII)
    bcp4 = '%s%s in %s %s' % (bcpI, annotTable, annotFileName, bcpII)
    bcp5 = '%s%s in %s %s' % (bcpI, noteTable, noteFileName, bcpII)

    for bcpCmd in [bcp1, bcp2, bcp3, bcp4, bcp5]:
	diagFile.write('%s\n' % bcpCmd)
	os.system(bcpCmd)
	db.sql(truncateDB, None)

    #
    # for MGI_NoteChunk use -t, -r to set field and line numbers
    # so that "\n" can exist in the "note" itself
    #
    bcpII = '-c -t\"&=&" -r"#=#\n" -S%s -U%s' % (db.get_sqlServer(), db.get_sqlUser())
    bcp6 = '%s%s in %s %s' % (bcpI, noteChunkTable, noteChunkFileName, bcpII)
    diagFile.write('%s\n' % bcp6)
    os.system(bcp6)
    db.sql(truncateDB, None)

    return

# colony ID note never longer than 255
def createColonyNote(strainKey, colonyNote, createdByKey):
    global noteKey

    noteFile.write('%s|%s|%s|%s|%s|%s|%s|%s\n' \
	% (noteKey, strainKey, mgiNoteObjectKey, mgiImpcColonyIdKey, \
	   createdByKey, createdByKey, cdate, cdate))

    noteChunkFile.write('%s&=&%s&=&%s&=&%s&=&%s&=&%s&=&%s#=#\n' \
	% (noteKey, 1, colonyNote, \
	    createdByKey, createdByKey, cdate, cdate))

    noteKey = noteKey + 1

# Purpose:  processes data
# Returns:  nothing
# Assumes:  nothing
# Effects:  verifies and processes each line in the input file
# Throws:   nothing

def processFile():

    global strainKey, strainmarkerKey, accKey, mgiKey, annotKey, noteKey

    lineNum = 0
    # For each line in the input file

    for line in inputFile.readlines():

        lineNum = lineNum + 1

        # Split the line into tokens
        tokens = line[:-1].split('\t')

        try:
	    name = tokens[0]
	    alleleIDs = tokens[1]
	    strainType = tokens[2]
	    species = tokens[3]
	    isStandard = tokens[4]
	    createdBy = tokens[5]
	    mutantNote = tokens[6]
	    colonyNote = tokens[7]
	    annotations = tokens[8].split('|')
        except:
            exit(1, 'Invalid Line (%d): %s\n' % (lineNum, line))

	strainExistKey = verifyStrain(name, lineNum)
	strainTypeKey = verifyStrainType(strainType, lineNum)
	speciesKey = verifySpecies(species, lineNum)
	createdByKey = loadlib.verifyUser(createdBy, 0, errorFile)

	# if the strain exist, but with no colony id note, create one
	if strainExistKey > 0:
	    print 'strain in database : %s' % line
	    if (not checkColonyNote(strainExistKey) ):
		print 'colony note not in the database: %s' % colonyNote
		createColonyNote(strainExistKey, colonyNote, createdByKey)
		continue
	else: 
	    print 'strain not in database : %s' % line

	# if strain already exists and  verification failed on strain type, 
	# species or createdBy, skip the record
        if strainTypeKey == 0 or speciesKey == 0 \
		or createdByKey == 0:
            continue

        # if no errors, process
        strainFile.write('%d|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
            % (strainKey, speciesKey, strainTypeKey, name, isStandard, 
		isPrivate, isGeneticBackground, createdByKey, createdByKey, 
		    cdate, cdate))

	# if Allele found, resolve to Marker
	allAlleles = alleleIDs.split('|')

	for a in allAlleles:
		alleleKey = loadlib.verifyObject(a, alleleTypeKey, None, lineNum, errorFile)
	    	results = db.sql('select _Marker_key from ALL_Allele where _Allele_key = %s' % (alleleKey),  'auto')
		markerKey = results[0]['_Marker_key']

		markerFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
		    % (strainmarkerKey, strainKey, markerKey, alleleKey, 
			qualifierKey, createdByKey, createdByKey, cdate, cdate))
		strainmarkerKey = strainmarkerKey + 1

        # MGI Accession ID for the strain
	if isStandard == '1':
	    accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s|%s\n' \
	    % (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, strainKey, mgiTypeKey, 
	       createdByKey, createdByKey, cdate, cdate))
	    accKey = accKey + 1

        # storing data in MGI_Note/MGI_NoteChunk
        # Colony ID Note

        if len(colonyNote) > 0:
	    createColonyNote(strainKey, colonyNote, createdByKey)

        # storing data in MGI_Note/MGI_NoteChunk
        # Mutant Cell Line of Origin Note
        mgiNoteSeqNum = 1
        if len(mutantNote) > 0:

            noteFile.write('%s|%s|%s|%s|%s|%s|%s|%s\n' \
                % (noteKey, strainKey, mgiNoteObjectKey, mgiMutantOriginTypeKey, \
                   createdByKey, createdByKey, cdate, cdate))

            while len(mutantNote) > 255:
                noteChunkFile.write('%s&=&%s&=&%s&=&%s&=&%s&=&%s&=&%s#=#\n' \
                    % (noteKey, mgiNoteSeqNum, mutantNote[:255], createdByKey, createdByKey, cdate, cdate))
                mutantNote = mutantNote[255:]
                mgiNoteSeqNum = mgiNoteSeqNum + 1

            if len(mutantNote) > 0:
                #noteChunkFile.write('%s|%s|%s|%s|%s|%s|%s\n' \
                noteChunkFile.write('%s&=&%s&=&%s&=&%s&=&%s&=&%s&=&%s#=#\n' \
                    % (noteKey, mgiNoteSeqNum, mutantNote, createdByKey, createdByKey, cdate, cdate))

            noteKey = noteKey + 1

	#
        # Annotations
        #
	# _AnnotType_key = 1009 =  "Strain/Attributes"
	# _Qualifier_key = 1614158 =  null
	#

	for a in annotations:

	    # strain annotation type
	    annotTypeKey = 1009

	    # this is a null qualifier key
	    annotQualifierKey = 1614158

	    annotTermKey = loadlib.verifyTerm('', 27, a, lineNum, errorFile)
	    if annotTermKey == 0:
		continue

            annotFile.write('%s|%s|%s|%s|%s|%s|%s\n' \
              % (annotKey, annotTypeKey, strainKey, annotTermKey, annotQualifierKey, cdate, cdate))
            annotKey = annotKey + 1

        mgiKey = mgiKey + 1
        strainKey = strainKey + 1

    #	end of "for line in inputFile.readlines():"

    #
    # Update the AccessionMax value
    #

    if not DEBUG:
        db.sql('exec ACC_setMax %d' % (lineNum), None)

#
# Main
#

init()
verifyMode()
setPrimaryKeys()
processFile()
bcpFiles()
exit(0)
