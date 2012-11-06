#!/bin/csh -f

#
# Delete all genotype/annotations created by 'scrum-dog' user (key = 1526).
# This will mean that new genotype MGI Ids may be created.
#

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
 
cat - <<EOSQL | doisql.csh $MGD_DBSERVER $MGD_DBNAME $0 | tee -a $LOG

use $MGD_DBNAME
go

select v._Annot_key
into #todelete1
from VOC_Evidence v
where v._CreatedBy_key = 1526
go

delete VOC_Annot
from #todelete1 d, VOC_Annot a
where d._Annot_key = a._Annot_key
go

select _Genotype_key
into #todelete2
from GXD_Genotype
where _CreatedBy_key = 1526
go

delete GXD_Genotype
from #todelete2 d, GXD_Genotype g
where d._Genotype_key = g._Genotype_key
go

checkpoint
go

end

EOSQL

date |tee -a $LOG

