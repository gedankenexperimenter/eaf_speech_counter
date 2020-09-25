
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

# if we fix tier names
# tier_names = ['FA1', 'FA2','CHI']#code_num,on_off, context, code
ignore_tier_names=['code_num','on_off', 'context', 'code']

# Tiers to exclude from CDS, ADS, and BOTH totals:
xds_exluded_tiers = ['EE1', 'CHI']

# Tiers to report separate from other tiers:
segregated_tiers = ['EE1']

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
    tier_dictionary=defaultdict(list)
    grand_total=0
    print('File Name: {}'.format(os.path.basename(file_path)))
    # Initialize the elan file
    eafob = pympi.Elan.Eaf(file_path)

    # get the name of all the tiers available in the EAF file
    if len(tier_names) is 0:
        tier_names = eafob.get_tier_names()
    print(tier_names)

    #loop over all the Tiers
    for ort_tier in tier_names:
        # If the tier is present we can loop through the annotation data
        if ort_tier in eafob.get_tier_names():
        # ignore sub tiers as they have @
        # only take tiers which have subtiers
            if "@" in ort_tier or ort_tier in ignore_tier_names:
                # just getting the 2nd part of the  lex@CHI
                if len(ort_tier.split('@'))>=2:
                    if ort_tier.split('@')[1] not in tier_names_targets:
                        tier_names_targets.append(ort_tier.split('@')[1])

    #sort the tier names 
    tier_names_targets.sort()
    # sys.argv[2] has the name of the output file 
    # all writes are appended to the file
    with open(sys.argv[2], "a") as writingFile:
        writingFile.write('FileName,TierName,')
        #write the name of all the tiers
        for tier_name in tier_names_targets:
            writingFile.write(tier_name+",")
            for annotation in eafob.get_annotation_data_for_tier(tier_name):
                tier_dictionary[tier_name].append(str(annotation[0]) +"-"+ str(annotation[1]))
                #print(str(annotation[1]) +"-"+ str(annotation[0]))
        writingFile.write("ADS,CDS,BOTH,TotalOverlap,Total\n")
        
        overlap_list=[]
        keylist = tier_dictionary.keys()
        keylist.sort()
        for key in keylist:
            total_time=0
            writingFile.write(os.path.basename(file_path).replace(".eaf","")+","+key+",")
            print(key+":",end='')
            intersection_dict = dict()
            total_intersection=0
            keylist2 = tier_dictionary.keys()
            keylist2.sort()
            for key2 in keylist2:
                if key2 in segregated_tiers:
                    if key2 == key:
                        for value in tier_dictionary[key]:
                            begin = int(value.split('-')[0])
                            end   = int(value.split('-')[1])
                            total_time += end - begin
                    writingFile.write("0,")
                    continue
                intersection_dict[key2]=0
                for value in tier_dictionary[key]:
                    
                    value_original_begin=int(value.split('-')[0])
                    value_original_end=int(value.split('-')[1])
                    if key2 == key:
                        total_time += value_original_end-value_original_begin
                    else:
                        #check other tiers
                        
                        for value2 in tier_dictionary[key2]:
                            value_target_end = int(value2.split('-')[1])
                            value_target_begin = int(value2.split('-')[0])
                            
                            if value_target_begin<value_original_end and value_target_begin >= value_original_begin:
                                
                                if value_target_end <= value_original_end :
                                    
                                    intersection_dict[key2]+=value_target_end-value_target_begin
                                    
                                else:
                                    
                                    intersection_dict[key2]+=value_original_end - value_target_begin
                                    
                            #target's end is encompassed by the original's begin and end
                            elif value_target_end>value_original_begin and value_target_end <= value_original_end :
                                #which one is larger? target's begin or original's
                                #reverse logic as larger time needs to get subtracted
                                if value_target_begin <= value_original_begin :
                                    intersection_dict[key2]=intersection_dict[key2]+value_target_end-value_original_begin
                                    
                                else:
                                    intersection_dict[key2]+=value_target_end-value_target_begin
                                
                            if value_original_begin >= value_target_begin and value_original_end <= value_target_end:
                                
                                intersection_dict[key2]+=value_original_end-value_original_begin
                                
                if key2 != key:  
                    #only add the overlapping time once.
                    if (key2+"-"+key not in overlap_list) and (key+"-"+key2 not in overlap_list):
                        overlap_list.append(key2+"-"+key)
                        writingFile.write(str(intersection_dict[key2])+",") 
                        total_intersection+= intersection_dict[key2]
                        print(key2+"-"+str(intersection_dict[key2])+",",end='')
                    else:
                        writingFile.write("0,")

                else:
                    writingFile.write("0,")


            #ads cds part
            ads = 0
            cds = 0
            both=0
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
                ads = 0
                cds = 0
                both=0
            writingFile.write(str(ads) + "," + str(cds)+","+str(both)+",")

            if key not in xds_exluded_tiers and key not in segregated_tiers:
                ads_total+=ads
                cds_total+=cds
                both_total+=both
            
            
            total_time -=total_intersection
            if key not in segregated_tiers:
                total_intersection_accross += total_intersection
                grand_total += total_time
            writingFile.write(str(total_intersection)+","+str(total_time)+"\n")
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
