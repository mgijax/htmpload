#!/usr/local/bin/python
#
#  makeEuropheno.py
###########################################################################
#
#  Purpose:
#
#      This script will use the records in the Europheno input file to:
#
#      1) create a High-Throughput MP input file
#
#  Usage:
#
#      makeEuropheno.py
#
#  Env Vars:
#
#      The following environment variables are set by the configuration
#      file that is sourced by the wrapper script:
#
#	   BIOMART_INPUT_FILE
#    	   HTMP_INPUT_FILE
#
#  Inputs:
#
#      Europheno file ($BIOMART_INPUT_FILE)
#
#       field 1: ES Cell
#       field 2: MP ID
#       field 3: MGI Allele ID
#       field 4: Allele State (zygosity: 0/'Het', 1/'Hom', 2/'Hemi')
#       field 5: Allele Symbol
#       field 6: MGI Marker ID
#       field 7: Strain ID
#       field 8: Gender ('Female', 'Male')
#
#  Outputs:
#
#	High Throughput MP file ($HTMP_INPUT_FILE):
#
#       field 1: Phenotyping Center ('Europhenome')
#       field 2: Annotation Center ('Europhenome')
#       field 3: ES Cell
#       field 4: MP ID
#       field 5: MGI Allele ID
#       field 6: Allele State (zygosity: 0/'Het', 1/'Hom', 2/'Hemi')
#       field 7: Allele Symbol
#       field 8: MGI Marker ID
#       field 9: Evidence Code ('EXP')
#       field 10: Strain Name
#       field 11: Gender ('Female', 'Male', 'Both')
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
#      3) Morph the Europhenome input file into a Hight-Throughput MP input file
#      4) Close files.
#
#  Notes:  None
#
#  10/29/2012	lec
#	- TR10273
#
###########################################################################

import sys 
import os

# BIOMART_INPUT_FILE
biomartFile = None

# HTMP_INPUT_FILE
htmpFile = None

# file pointers
fpBiomart = None
fpHTMP = None

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def initialize():
    global biomartFile, htmpFile
    global fpBiomart, fpHTMP

    biomartFile = os.getenv('BIOMART_INPUT_FILE')
    htmpFile = os.getenv('HTMP_INPUT_FILE')

    rc = 0

    #
    # Make sure the environment variables are set.
    #
    if not biomartFile:
        print 'Environment variable not set: BIOMART_INPUT_FILE'
        rc = 1

    # Make sure the environment variables are set.
    #
    if not htmpFile:
        print 'Environment variable not set: HTMP_INPUT_FILE'
        rc = 1

    #
    # Initialize file pointers.
    #
    fpBiomart = None
    fpHTMP = None

    return rc


#
# Purpose: Open files.
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def openFiles():
    global fpBiomart, fpHTMP

    #
    # Open the Europheno/Biomart file
    #
    try:
        fpBiomart = open(biomartFile, 'r')
    except:
        print 'Cannot open file: ' + biomartFile
        return 1

    #
    # Open the Europheno file with genotype sequence #
    #
    try:
        fpHTMP = open(htmpFile, 'w')
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

    if fpBiomart:
        fpBiomart.close()

    if fpHTMP:
        fpHTMP.close()

    return 0


#
# Purpose: Read the Europheno file and re-format it to create a High-Throughpug MP input file
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Nothing
# Throws: Nothing
#
def createHTMPfile():

    phenotypingCenter = 'Europhenome'
    annotationCenter = 'Europhenome'
    evidenceCode = 'EXP'

    for line in fpBiomart.readlines():

        tokens = line[:-1].split('\t')

	mutantID = tokens[0]
	mpID = tokens[1]
        alleleID = alleleID2 = tokens[2]
        alleleState = tokens[3]
        alleleSymbol = tokens[4]
        markerID = tokens[5]
	#strainID = tokens[6]
	strainID = ''
        gender = tokens[7]

	if alleleState == '0':
	    alleleState = 'Het'
	elif alleleState == '1':
	    alleleState = 'Hom'
	elif alleleState == '2':
	    alleleState = 'Hemi'
	else:
	    alleleState = 'Indeterminate'

        fpHTMP.write(phenotypingCenter + '\t'  + \
                     annotationCenter + '\t'  + \
	             mutantID + '\t'  + \
	             mpID + '\t'  + \
                     alleleID + '\t'  + \
                     alleleState + '\t'  + \
                     alleleSymbol + '\t'  + \
                     markerID + '\t'  + \
		     evidenceCode + '\t'  + \
	             strainID + '\t'  + \
                     gender + '\n')

    return 0

#
#  MAIN
#

if initialize() != 0:
    sys.exit(1)

if openFiles() != 0:
    sys.exit(1)

if createHTMPfile() != 0:
    closeFiles()
    sys.exit(1)

closeFiles()
sys.exit(0)

