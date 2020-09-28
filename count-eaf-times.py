#!/usr/bin/env python
from __future__ import print_function

import argparse
import csv
import glob
import os
import sys
import warnings

from collections import defaultdict

import pympi  # Import for EAF file read

# ==============================================================================
# Class definitions
# ------------------------------------------------------------------------------
class Event:
    """Represents either the beginning or the end of an annotated segment"""
    def __init__(self, timestamp, label, start=True, annotation=''):
        self.label      = label
        self.annotation = annotation
        self.timestamp  = timestamp
        if start:
            self.change =  1
        else:
            self.change = -1

# ------------------------------------------------------------------------------
class AnnotatedSegment:
    """Represents an annotated segment from an EAF file"""
    def __init__(self, tier, start_time, end_time, value):
        self.tier       = tier
        self.start_time = int(start_time)
        self.end_time   = int(end_time)
        self.value      = value

# ------------------------------------------------------------------------------
class OutputRecord:
    """Represents a row of the data table to be written to the output file"""
    data_labels = ['exclusive', 'total', 'cds', 'ads', 'both']
    header = ['File', 'Tier(s)', 'Exclusive', 'Total', 'CDS', 'ADS', 'BOTH']

    def __init__(self, file_id, label):
        self.file_id = file_id
        self.label = label
        self.data = defaultdict(int)
        return

    def fmt(self):
        values = [self.file_id, self.label]
        def _blank_zero(entry):
            value = self.data[entry]
            return '' if value == 0 else value
        data_values = map(_blank_zero, self.data_labels)
        values.extend(data_values)
        return values


# ==============================================================================

# ------------------------------------------------------------------------------
def get_segments(eaf, tiers):
    segments = []
    for tier in tiers:
        for record in eaf.get_annotation_data_for_tier(tier):
            (start_time, end_time, value) = record[:3]
            segments.append(AnnotatedSegment(tier, start_time,
                                             end_time, value))
    return segments

# ------------------------------------------------------------------------------
def get_events(segments, label_func=lambda x: x.tier):
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

# ------------------------------------------------------------------------------
def process_events(events, labels = []):
    """Process a sorted list of `Event` objects."""
    # Initialize return values
    union_sum     = 0
    sections      = []
    section_sums  = defaultdict(int)

    # Temporary loop variables
    section_labels = []
    # Ignore any uncategorized space before the first event
    section_start = events[0].timestamp

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

# ------------------------------------------------------------------------------
def process_category(category, events, labels, output_records):
    if len(events) == 0: return
    for event in events:
        event.label = event.label.split(':')[0]
    (union_sum, section_sums, sections) = process_events(events)
    for label in labels:
        output_records[label].data[category] += section_sums[label]
        output_records['totals'].data[category] += section_sums[label]
    return


# ==============================================================================
# CLI
# ------------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    formatter_class = argparse.RawDescriptionHelpFormatter,
    description = "Analyze and report the annotated time segments for tiers in EAF files.",
    epilog =
    "Examples: {} -o foo.csv raw_FOO/*.eaf\n".format(__file__) +
    "          {} --ignore-tiers EE1 UC1 -- raw_FOO/*.eaf\n\n".format(__file__) +
    "[Note: If using --ignore-tiers, separate tier names from EAF file names with '--'.]"
)

parser.add_argument('-o', '--output',
                    metavar = '<csv_file>',
                    type    = argparse.FileType('w'),
                    default = 'eaf-counts.csv',
                    help    = "Write output to <csv_file> (default: 'eaf-counts.csv')")

parser.add_argument('-d', '--delimiter',
                    metavar = '<delimiter>',
                    default = '\t',
                    help    = "Use <delimiter> as CSV field separator in output (default: TAB)")

parser.add_argument('--ignore-tiers',
                    dest    = 'ignore',
                    metavar = '<tier>',
                    nargs   = '*',
                    default = [],
                    help    = "List of additional EAF tiers to ignore (space separated list)")

parser.add_argument('--no-xds',
                    dest    = 'xds',
                    action  = 'store_false',
                    help    = "Don't summarize ADS & CDS amounts")

parser.add_argument('--no-overlap',
                    dest    = 'overlap',
                    action  = 'store_false',
                    help    = "Don't include tier overlap details in output")

parser.add_argument('eaf_files',
                    metavar = '<eaf_file>',
                    nargs   = '+',
                    help    = "The name(s) of the EAF file(s) to process")

args = parser.parse_args()

# ------------------------------------------------------------------------------
ignored_tiers = ['code_num', 'on_off', 'context', 'code']
ignored_tiers.extend(args.ignore)

output = csv.writer(args.output, delimiter=args.delimiter,
                    escapechar='\\', quoting=csv.QUOTE_MINIMAL) 
output.writerow(OutputRecord.header)

grand_totals = OutputRecord('Grand Totals', '')

# ------------------------------------------------------------------------------
for eaf_file in args.eaf_files:
    print(eaf_file)
    file_id = os.path.basename(eaf_file).replace('.eaf', '')
    warnings.filterwarnings('ignore')
    # pympi issues a warning "Parsing unknown version of ELAN spec..."
    eaf = pympi.Elan.Eaf(eaf_file)
    warnings.filterwarnings('default')
    tiers = filter(lambda tier: tier not in ignored_tiers,
                   eaf.get_tier_names())
    tiers = filter(lambda tier: '@' not in tier, tiers)
    segments = get_segments(eaf, tiers)
    events = get_events(segments)
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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if args.xds:
        tiers = filter(lambda t: t not in ignored_tiers, eaf.get_tier_names())
        xds_tiers = filter(lambda t: 'xds@' in t, tiers)
        segments = get_segments(eaf, xds_tiers)
        events = get_events(
            segments, lambda x: x.tier.split('@')[-1] + ':' + x.value)

        cds_events = filter(lambda x: ':C' in x.label or ':T' in x.label, events)
        ads_events = filter(lambda x: ':A' in x.label, events)
        both_events = filter(lambda x: ':B' in x.label, events)

        process_category('cds', cds_events, labels, output_records)
        process_category('ads', ads_events, labels, output_records)
        process_category('both', both_events, labels, output_records)

    labels = sorted(output_records.keys())
    for label in filter(lambda x: x in tiers, labels):
        output.writerow(output_records[label].fmt())

    if args.overlap:
        for label in filter(lambda x: x not in tiers, labels):
            output.writerow(output_records[label].fmt())

    for category in output_records['totals'].data.keys():
        grand_totals.data[category] += output_records['totals'].data[category]

    output.writerow(output_records['totals'].fmt())

# ------------------------------------------------------------------------------
output.writerow(grand_totals.fmt())
args.output.close()

exit
