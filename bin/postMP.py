#
#  postMP.py
###########################################################################
#
#  Purpose:
#
#       1. load VOC_AnnotHeader with new MP annotations 
#	2. Update allele transmission
#	3. update used-FC references
#  Usage:
#      postMP.py
#
#  Env Vars:
#	See the configuration file (impcmpload.config)
#
#  Inputs:
#
#      a database
#
#  Outputs:
#
#     Updates a database
#    
#  Exit Codes:
#      0:  Successful completion
#      1:  An exception occurred
#
#  Implementation:
#      This script will is a do the annotation header part of the 
#	stored procedure ALL_postMP
#
#  Notes: 
#
#
#  04/20/2017	sc
#	- TR12556
#
###########################################################################

import sys 
import os
import string
import Set
import db
import time

#db.setTrace(True)
db.useOneConnection(1)
annotTypeKey = 1002 	# MP/Genotype
user = os.getenv('CREATEDBY')
jNums = "'212870', '240675'"

# for naming temp tables and indexes
ct = 1
results = db.sql('''select _User_key
        from MGI_User
        where login = '%s' ''' % user, 'auto')
modifiedByKey = results[0]['_User_key']

#
# update Annotation headers for loaded annotations
#

# delete from VOC_AnnotHeader
db.sql('''select _Object_key
    into temporary table toDelete
    from VOC_Annot v, VOC_Evidence e
    where  v._AnnotType_key = 1002
        AND v._Annot_key = e._Annot_key
        AND e._Refs_key in (%s)''' % (jNums ), None)

db.sql('''create index idx%s on toDelete(_Object_key)''' % ct, None)
ct += 1 # increment for index name

db.sql('''delete from VOC_AnnotHeader a
    using toDelete d
    where a._Object_key = d._Object_key
    and a._AnnotType_key = 1002''', None)

# add missing VOC_AnnotHeader records by annotation type
results =  db.sql('''SELECT DISTINCT v._Object_key as genotypeKey
    FROM VOC_Annot v
    WHERE v._AnnotType_key = %s
    AND NOT EXISTS (select 1 FROM VOC_AnnotHeader h
            WHERE v._AnnotType_key = h._AnnotType_key
            AND v._Object_key = h._Object_key)''' % annotTypeKey, 'auto')

for r in results:
    genotypeKey = r['genotypeKey']
    db.sql('''select * from VOC_processAnnotHeader (1001, %s, %s)''' % (annotTypeKey, genotypeKey) )
    db.commit()

#
# Update transmission status and used-FC references
#
for jNumKey in string.split(jNums, ','):
    jNumKey =  string.split(jNumKey,"'")[1]
        
    # Update transmission status 
    results = db.sql('''SELECT DISTINCT aa._Allele_key
        FROM GXD_AlleleGenotype g, VOC_Annot a, VOC_Evidence e, ALL_Allele aa
        WHERE g._Genotype_key = a._Object_key
        AND a._AnnotType_key = %s
        AND g._Allele_key = aa._Allele_key
        AND aa.isWildType = 0
        AND aa._Transmission_key in (3982952, 3982953)
        AND a._Annot_key = e._Annot_key
        AND e._Refs_key = %s''' % (annotTypeKey, jNumKey), 'auto')
    print 'Calling MGI_insertReferenceAssoc for Transmission reference associations for %s alleles for refsKey %s' % (len(results), jNumKey)
    for r in results:
        alleleKey = r['_Allele_key']
        db.sql(''' UPDATE ALL_Allele
            SET _Transmission_key = 3982951,
                _ModifiedBy_key = %s
                modification_date = now()
            WHERE _Allele_key = %s''' % (modifiedByKey, alleleKey), None)
        print '''select * from MGI_insertReferenceAssoc (1001, 11, %s, %s, 'Transmission')''' % (alleleKey, jNumKey)
        db.sql('''select * from MGI_insertReferenceAssoc (1001, 11, %s, %s, 'Transmission')''' % (alleleKey, jNumKey), None)
        db.commit()

    db.sql('''select distinct _Object_key as alleleKey
    into temporary table used%s
    from MGI_Reference_Assoc
    where _MGIType_key = 11 -- Allele
    and _RefAssocType_key = 1017 -- Used-FC
    and _Refs_key = %s''' % (ct, jNumKey), None)

    db.sql('''create index idx%s on used%s(alleleKey)''' % (ct, ct), None)

    results = db.sql('''SELECT DISTINCT aa._Allele_key
        FROM GXD_AlleleGenotype g, VOC_Annot a, VOC_Evidence e, ALL_Allele aa
        WHERE g._Genotype_key = a._Object_key
        AND a._AnnotType_key =  %s
        AND g._Allele_key = aa._Allele_key
        AND aa.isWildType = 0
        AND a._Annot_key = e._Annot_key
        AND e._Refs_key = %s''' % (annotTypeKey, jNumKey), 'auto')

    print 'Calling MGI_insertReferenceAssoc for Used-FC reference associations for %s alleles for refsKey %s' % (len(results), jNumKey)
    for r in results:
        alleleKey = r['_Allele_key']
        print '''select * from MGI_insertReferenceAssoc (1001, 11, %s, %s, 'Used-FC')''' % (alleleKey, jNumKey)
        db.sql('''select * from MGI_insertReferenceAssoc (1001, 11, %s, %s, 'Used-FC')''' % (alleleKey, jNumKey), None)
        db.commit()
    ct += 1 # increment for temp table/index name
#
#
db.useOneConnection(0) 
sys.exit(0)
