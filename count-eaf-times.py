#!/usr/bin/env python
from __future__ import print_function

import argparse
import glob
import os
import sys
import warnings

from collections import defaultdict

import pympi  # Import for EAF file read


class Event:
    def __init__(self, timestamp, label, start=True, annotation=''):
        self.label      = label
        self.annotation = annotation
        self.timestamp  = timestamp
        if start:
            self.change =  1
        else:
            self.change = -1


class AnnotatedSegment:
    def __init__(self, tier, start_time, end_time, value):
        self.tier       = tier
        self.start_time = int(start_time)
        self.end_time   = int(end_time)
        self.value      = value

    def duration(self):
        return self.end_time - self.start_time

    def overlap(self, other):
        first_end  = min(self.end_time, other.end_time)
        last_start = max(self.start_time, other.start_time)
        if first_end > last_start:
            return first_end - last_start
        else:
            return 0

class OutputRecord:
    def __init__(self, file_id, label):
        self.file_id = file_id
        self.label = label
        self.data = defaultdict(int)

    def format(self, sep):
        total = ''
        if self.data['total'] != 0:
            total = str(self.data['total'])
        return sep.join([self.file_id,
                         self.label,
                         str(self.data['exclusive']),
                         str(self.data['cds']),
                         str(self.data['ads']),
                         str(self.data['both']),
                         total])

    @staticmethod
    def header(sep):
        return sep.join(['File', 'Tier(s)', 'Exclusive', 'CDS', 'ADS', 'BOTH', 'Total'])


def get_records(eaf, tiers):
    segments = []
    for tier in tiers:
        for record in eaf.get_annotation_data_for_tier(tier):
            (start_time, end_time, value) = record[:3]
            segments.append(AnnotatedSegment(tier, start_time,
                                             end_time, value))
    return segments

def segments_to_events(segments, label_func=lambda x: x.tier):
    """
    Given a list of `AnnotationSegment`s, return a sorted list of
    `Event` objects.
    """
    events = []
    for segment in segments:
        events.append(Event(timestamp = segment.start_time,
                            label = label_func(segment),
                            annotation = segment.value,
                            start = True))
        events.append(Event(timestamp = segment.end_time,
                            label = label_func(segment),
                            annotation = segment.value,
                            start = False))
    events.sort(key=lambda event: event.timestamp)
    return events

def process_events(events, labels = []):
    """Process a sorted list of `Event` objects."""
    # Initialize return values
    union_sum     = 0
    sections      = []
    section_sums  = defaultdict(int)

    # Temporary loop variables
    section_labels = []
    # Ignore any uncategorized space before the first event
    section_start = events[1].timestamp

    for event in events:
        # Any labels not included are ignored. Default is to consider
        # all labels.
        if labels and event.label not in labels:
            continue

        # We have reached the end of a section where a given set of
        # labels was active (either a new one started, or an active one
        # ended. We add the duration of the section to the appropriate
        # combination of labels' total.
        section_label = '+'.join(sorted(section_labels))
        section_duration = event.timestamp - section_start
        section_sums[section_label] += section_duration
        if section_duration > 0:
            sections.append((section_label, section_duration))
        if section_labels:
            union_sum += section_duration

        # Either a new label started, or an existing one ended. Either
        # way, we need to update the list of current labels.
        if event.change > 0:
            section_labels.append(event.label)
        else:
            section_labels.remove(event.label)

        # Now, if there are any active labels, set the timestamp to
        # record the next section.
        if section_labels:
            section_start = event.timestamp

    return union_sum, section_sums, sections

def process_category(category, events, output_records):
    for event in events:
        event.label = event.label.split(':')[0]
    (union_sum, section_sums, sections) = process_events(events)
    for label in labels:
        output_records[label].data[category] += section_sums[label]
        output_records['totals'].data[category] += section_sums[label]
    return


parser = argparse.ArgumentParser(description = """
Analyze and report the time segments annotated in EAF files.
""")
parser.add_argument('--xds', action='store_true',
                    help='summarize ADS & CDS amounts')
parser.add_argument('--totals', metavar='TOTALS_CSV', type=argparse.FileType('w'),
                    default='totals.csv',
                    help='file to write to')
parser.add_argument('--sep', metavar='CSV_SEPARATOR', default='\t',
                    help='separator to use in the output file')
parser.add_argument('--ignore', metavar='TIER', nargs='*',
                    default=['code_num', 'on_off', 'context', 'code'],
                    help='tiers to ignore')
parser.add_argument('eaf_files', metavar='EAF_FILE', nargs='+',
                    help='the name(s) of the EAF file(s) to process')
args = parser.parse_args()

args.totals.write(OutputRecord.header(args.sep) + '\n')

grand_totals = OutputRecord('Grand Totals', '')

for eaf_file in args.eaf_files:
    file_id = os.path.basename(eaf_file).replace('.eaf', '')
    warnings.filterwarnings('ignore')
    # pympi issues a warning "Parsing unknown version of ELAN spec..."
    eaf = pympi.Elan.Eaf(eaf_file)
    warnings.filterwarnings('default')
    tiers = filter(lambda tier: tier not in args.ignore,
                   eaf.get_tier_names())
    tiers = filter(lambda tier: '@' not in tier, tiers)
    segments = get_records(eaf, tiers)
    events = segments_to_events(segments)
    (union_sum, section_sums, sections) = process_events(events)
    labels = sorted(section_sums.keys())
    labels.remove('')
    output_records = dict()
    output_records['totals'] = OutputRecord(file_id, 'Totals')
    for label in labels:
        output_records[label] = OutputRecord(file_id, label)
        output_records[label].data['exclusive'] += section_sums[label]
        output_records['totals'].data['exclusive'] += section_sums[label]
    for tier in tiers:
        for label in labels:
            if tier in label:
                output_records[tier].data['total'] += section_sums[label]
                output_records['totals'].data['total'] += section_sums[label]

    if args.xds:
        ads_total = 0
        cds_total = 0
        both_total = 0
        tiers = filter(lambda tier: tier not in args.ignore,
                       eaf.get_tier_names())
        xds_tiers = filter(lambda tier: 'xds@' in tier, tiers)
        segments = get_records(eaf, xds_tiers)
        events = segments_to_events(
            segments, lambda x: x.tier.split('@')[-1] + ':' + x.value)

        cds_events = filter(lambda x: ':C' in x.label or ':T' in x.label, events)
        ads_events = filter(lambda x: ':A' in x.label, events)
        both_events = filter(lambda x: ':B' in x.label, events)

        process_category('cds', cds_events, output_records)
        process_category('ads', ads_events, output_records)
        process_category('both', both_events, output_records)

    labels = output_records.keys()
    labels.sort()
    for label in labels:
        args.totals.write(output_records[label].format(args.sep) + '\n')

    for category in output_records['totals'].data.keys():
        grand_totals.data[category] += output_records['totals'].data[category]

args.totals.write(grand_totals.format(args.sep) + '\n')
args.totals.close()

exit
