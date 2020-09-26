
from __future__ import print_function
import sys
import glob  # Import glob to easily loop over files
import pympi  # Import for EAF file read
import warnings
from collections import defaultdict
#from pathlib import Path
import os

# removing warnings
warnings.filterwarnings("ignore")

class AnnotationRecord:
    def __init__(self, tier, start_time, end_time, value):
        self.tier       = tier
        self.start_time = int(start_time)
        self.end_time   = int(end_time)
        self.value      = value

    def duration(self):
        return self.end_time - self.start_time

    def overlap(self, other):
        first_end = min(self.end_time, other.end_time)
        last_start = max(self.start_time, other.start_time)
        if first_end > last_start:
            return first_end - last_start
        else:
            return 0


# if we fix tier names
# tier_names = ['FA1', 'FA2','CHI']#code_num,on_off, context, code
ignore_tier_names=['code_num', 'on_off', 'context', 'code']

#if the output file exists, delete it!
if os.path.isfile(sys.argv[2]):
    os.remove(sys.argv[2])


ads_total=0
cds_total=0
both_total=0
grand_total_accross=0
total_intersection_accross=0
adjusted_total_accross=0
# loop over all the EAF files in the output folder
for file_path in glob.glob('{}/*.eaf'.format(sys.argv[1])):
    tier_names = []
    tier_names_targets = []
    tier_dictionary = defaultdict(list)
    annotation_records = []
    grand_total = 0
    print('File Name: {}'.format(os.path.basename(file_path)))
    # Initialize the elan file
    eafob = pympi.Elan.Eaf(file_path)

    # get the name of all the tiers available in the EAF file
    tier_names = eafob.get_tier_names()
    print(tier_names)

    #loop over all the Tiers
    for ort_tier in tier_names:
        if ort_tier in ignore_tier_names:
            continue
        # if "@" not in ort_tier:
        #     tier_names_targets.append(ort_tier)
        #     continue
        tier_name = ort_tier.split('@')[-1]
        if tier_name and tier_name not in tier_names_targets:
            tier_names_targets.append(tier_name)

    #sort the tier names 
    tier_names_targets.sort()

    cds_totals = defaultdict(int)
    ads_totals = defaultdict(int)
    bds_totals = defaultdict(int)
    for tier_name in tier_names_targets:
        if tier_name in ignore_tier_names:
            continue
        for annotation in eafob.get_annotation_data_for_tier(tier_name):
            (start_time, end_time, value) = annotation[:3]
            annotation_records.append(
                AnnotationRecord(tier_name, start_time, end_time, value))

    for full_tier_name in tier_names:
        if "xds@" not in full_tier_name:
            continue
        tier_name = full_tier_name.split('@')[-1]
        for annotation in eafob.get_annotation_data_for_tier(full_tier_name):
            (start_time, end_time, value) = annotation[:3]
            if value == "C" or value == "T":
                cds_totals[tier_name] += end_time - start_time
            elif value == "A":
                ads_totals[tier_name] += end_time - start_time
            elif value == "B":
                bds_totals[tier_name] += end_time - start_time

    for tier_name in tier_names_targets:
        print(tier_name + ".CDS: " + str(cds_totals[tier_name]))
        print(tier_name + ".ADS: " + str(ads_totals[tier_name]))
        print(tier_name + ".Both: " + str(bds_totals[tier_name]))

    duration_total = 0
    overlap_total = 0

    overlap_matrix = dict()
    for tier_name in tier_names_targets:
        overlap_matrix[tier_name] = defaultdict(int)
        # for tn2 in tier_names_targets:
        #     overlap_matrix[tn1][tn2] = 0

    duration_totals = defaultdict(int)
    for i, ar1 in enumerate(annotation_records, start = 1):
        duration_totals[ar1.tier] += ar1.duration()
        duration_total += ar1.duration()
        for ar2 in annotation_records[i:]:
            overlap_duration = ar1.overlap(ar2)
            overlap_matrix[ar1.tier][ar2.tier] += overlap_duration
            overlap_total += overlap_duration
            # overlap_matrix[ar2.tier][ar1.tier] += overlap_duration

    for t1 in tier_names_targets:
        print(t1 + " total: " + str(duration_totals[t1]))
        for t2 in tier_names_targets:
            print(t1 + "." + t2 + ": " + str(overlap_matrix[t1][t2]))

    print("Total Duration: " + str(duration_total))
    print("Total Overlap:  " + str(overlap_total))
    print("Final Duration: " + str(duration_total - overlap_total))

    # sys.argv[2] has the name of the output file 
    # all writes are appended to the file
    with open(sys.argv[2], "a") as writingFile:
        writingFile.write('FileName,TierName,')
        #write the name of all the tiers
        for tier_name in tier_names_targets:
            writingFile.write(tier_name + ",")
            for annotation in eafob.get_annotation_data_for_tier(tier_name):
                tier_dictionary[tier_name].append(str(annotation[0]) + "-" + str(annotation[1]))
                #print(str(annotation[1]) +"-"+ str(annotation[0]))
        writingFile.write("ADS,CDS,BOTH,TotalOverlap,Total\n")
        
        overlap_list=[]
        keylist = tier_dictionary.keys()
        keylist.sort()
        for key in keylist:
            total_time = 0
            writingFile.write(os.path.basename(file_path).replace(".eaf", "") + "," + key + ",")
            print(key+":",end='')
            intersection_dict = dict()
            total_intersection = 0
            keylist2 = tier_dictionary.keys()
            keylist2.sort()
            for key2 in keylist2:
                intersection_dict[key2] = 0
                for value in tier_dictionary[key]:
                    
                    v1_begin = int(value.split('-')[0])
                    v1_end   = int(value.split('-')[1])
                    if v1_end < v1_begin:
                        print("Error: duration negative")
                    if key2 == key:
                        total_time += v1_end - v1_begin

                    else:
                        #check other tiers
                        for value2 in tier_dictionary[key2]:
                            v2_begin = int(value2.split('-')[0])
                            v2_end   = int(value2.split('-')[1])

                            # first_end = min(v1_end, v2_end)
                            # last_begin = max(v1_begin, v2_begin)
                            # if (last_begin < first_end):
                            #     intersection_dict[key2] += first_end - last_begin
                            
                            if v2_begin < v1_end and v2_begin >= v1_begin:
                                if v2_end <= v1_end:
                                    intersection_dict[key2] += v2_end - v2_begin
                                    #print(key + " -- " + key2 + str(v2_end - v2_begin))
                                else:
                                    intersection_dict[key2] += v1_end - v2_begin
                                    
                            #target's end is encompassed by the original's begin and end
                            elif v2_end > v1_begin and v2_end <= v1_end:
                                #which one is larger? target's begin or original's
                                #reverse logic as larger time needs to get subtracted
                                if v2_begin <= v1_begin:
                                    intersection_dict[key2] += v2_end - v1_begin
                                else:
                                    # this code is unreachable; covered above.
                                    intersection_dict[key2] += v2_end - v2_begin

                            elif v1_begin >= v2_begin and v1_end <= v2_end:
                                intersection_dict[key2] += v1_end - v1_begin

                if key2 != key:  
                    #only add the overlapping time once.
                    if (key2 + "-" + key not in overlap_list) and (key+"-"+key2 not in overlap_list):
                        overlap_list.append(key2 + "-" + key)
                        writingFile.write(str(intersection_dict[key2])+",") 
                        total_intersection += intersection_dict[key2]
                        print(key2 + "-" + str(intersection_dict[key2]) + ",", end = '')
                    else:
                        writingFile.write("0,")

                else:
                    writingFile.write("0,")


            #ads cds part
            ads  = 0
            cds  = 0
            both = 0
            try:
                if eafob.get_annotation_data_for_tier('xds@' + key):
                    for annnotate in eafob.get_annotation_data_for_tier('xds@' + key):
                        if annnotate[2] == 'C' :
                            cds += annnotate[1]-annnotate[0]
                        elif annnotate[2] == 'T':
                            cds += annnotate[1]-annnotate[0]
                        elif annnotate[2] == 'A':
                            ads += annnotate[1]-annnotate[0]
                        elif annnotate[2] == 'B':
                            both +=annnotate[1]-annnotate[0]
            except:
                #since there are not method for checkign whether a  certain tier exists or not
                ads  = 0
                cds  = 0
                both = 0
            writingFile.write(str(ads) + "," + str(cds) + "," + str(both) + ",")
            ads_total += ads
            cds_total += cds
            both_total += both
            
            
            total_time -= total_intersection
            total_intersection_accross += total_intersection
            writingFile.write(str(total_intersection)+","+str(total_time)+"\n")
            grand_total += total_time
            print("total " + str(total_time))
        writingFile.write(",")    
        for tier_name in (tier_names_targets):
                writingFile.write(",")
        writingFile.write(",,,")
        writingFile.write("Grand Total,"+str(grand_total)+",")
        if grand_total<10*60*60*1000:
            writingFile.write("Resample\n")
        grand_total_accross+=grand_total
        
with open(sys.argv[2], "a") as writingFile:
    writingFile.write("Grand Total,Grand Adjusted Total, ADS, CDS, BOTH\n");
    writingFile.write(str(grand_total_accross+total_intersection_accross)+","+str(grand_total_accross)+","+ str(ads_total)+","+ str(cds_total)+","+ str(both_total)+"\n");
    #break  # for one file
