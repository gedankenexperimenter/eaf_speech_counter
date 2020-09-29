#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# For more information, please refer to <https://unlicense.org>

from __future__ import print_function

import argparse
import csv
import logging
import os
import sys
import warnings

from collections import defaultdict

import pympi  # Import for EAF file parsing

__version__ = '0.1.0'
__status__  = 'Development'
__author__  = 'Michael Richters'
__email__   = 'gedankenexperimenter@gmail.com'
__license__ = 'UNLICENSE'

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

    def fmt(self):
        return '{:10d} {:+d} {} -- {}'.format(
            self.timestamp, self.change, self.label, self.annotation
        )

# ------------------------------------------------------------------------------
class Segment:
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
# Helper functions
# ------------------------------------------------------------------------------
def get_segments(eaf, tiers):
    """
    Extract a list of annotated segments for a set of tiers from an
    EAF file object.
    """
    segments = []
    for tier in tiers:
        for record in eaf.get_annotation_data_for_tier(tier):
            (start_time, end_time, value) = record[:3]
            segments.append(Segment(tier, start_time, end_time, value))
    return segments

# ------------------------------------------------------------------------------
def get_events(segments, label_func=lambda x: x.tier):
    """
    Given a list of `AnnotationSegment`s, return a sorted list of
    `Event` objects.
    """
    events = []
    for segment in segments:
        # Start of segment
        events.append(Event(timestamp  = segment.start_time,
                            label      = label_func(segment),
                            annotation = segment.value,
                            start      = True))
        # End of segment
        events.append(Event(timestamp  = segment.end_time,
                            label      = label_func(segment),
                            annotation = segment.value,
                            start      = False))
    # Sort events chronologically
    events.sort(key=lambda event: event.timestamp)
    return events

# ------------------------------------------------------------------------------
def process_events(events, labels = []):
    """Process a sorted list of `Event` objects."""

    # Initialize return values
    union_sum      = 0
    sections       = []
    section_sums   = defaultdict(int)
    section_counts = defaultdict(int)

    # Temporary loop variables
    section_labels = []
    # Ignore any uncategorized space before the first event
    section_start = events[0].timestamp

    for event in events:
        # Any labels not included are ignored. Default is to consider
        # all labels.
        if labels and event.label not in labels:
            continue

        if (args.verbose > 2):
            logging.debug('Event: %s', event.fmt())
        # We have reached the end of a section where a given set of
        # labels was active (either a new one started, or an active one
        # ended. We add the duration of the section to the appropriate
        # combination of labels' total.
        section_label = '+'.join(sorted(section_labels))
        section_duration = event.timestamp - section_start
        section_sums[section_label] += section_duration
        section_counts[section_label] += 1
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

    return union_sum, section_sums

# ------------------------------------------------------------------------------
def process_category(category, events, labels, output_records):
    if len(events) == 0: return
    for event in events:
        event.label = event.label.split(':')[0]
    (_, section_sums) = process_events(events)
    for label in labels:
        output_records[label].data[category] += section_sums[label]
        output_records['totals'].data[category] += section_sums[label]
    return

# ==============================================================================
# Command-line parser
# ------------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    formatter_class = argparse.RawDescriptionHelpFormatter,
    description = "Analyze and report the annotated time segments for tiers in EAF files.",
    epilog =
    "Examples:\n" +
    "    {} -o foo.csv raw_FOO/*.eaf\n".format(__file__) +
    "    {} --ignore-tiers EE1 UC1 -- raw_FOO/*.eaf\n\n".format(__file__) +
    "[When using --ignore-tiers, separate tier names from EAF file names with '--'.]"
)

parser.add_argument('-o', '--output',
                    metavar = '<csv_file>',
                    type    = argparse.FileType('w'),
                    default = 'eaf-counts.csv',
                    help    = "Write output to <csv_file> (default: '%(default)s')")

parser.add_argument('-d', '--delimiter',
                    choices = ['tab', 'comma', 'ascii'],
                    default = 'tab',
                    help    = "Use <delimiter> as CSV output field separator (default: '%(default)s')")

parser.add_argument('--ignore-tiers',
                    dest    = 'ignore',
                    metavar = '<tier>',
                    nargs   = '+',
                    default = [],
                    help    = "List of one or more additional EAF tiers to ignore (space separated list)")

parser.add_argument('--no-xds',
                    dest    = 'xds',
                    action  = 'store_false',
                    help    = "Don't summarize ADS & CDS amounts")

parser.add_argument('--no-overlap',
                    dest    = 'overlap',
                    action  = 'store_false',
                    help    = "Don't include tier overlap details in output")

parser.add_argument('-v', '--verbose',
                    action  = 'count',
                    default = 0,
                    help    = "Write status messages to STDERR while processing")

parser.add_argument('eaf_files',
                    metavar = '<eaf_file>',
                    nargs   = '+',
                    help    = "The name(s) of the EAF file(s) to process")

args = parser.parse_args()

# ==============================================================================
# Finalize options, initialize output
# ------------------------------------------------------------------------------
log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
log_level = log_levels[min(args.verbose, len(log_levels) - 1)]

logging.basicConfig(level  = log_level,
                    format = '%(levelname)s %(message)s')

ignored_tiers = ['code_num', 'on_off', 'context', 'code']
ignored_tiers.extend(args.ignore)
logging.info('Ignoring tiers: {}'.format(ignored_tiers))

output_delimiter = '\t'
if args.delimiter == 'comma':
    output_delimiter = ','
elif args.delimiter == 'ascii':
    output_delimiter = '\x1f'

# Set up output csv writer
output = csv.writer(args.output,
                    delimiter      = output_delimiter,
                    quoting        = csv.QUOTE_MINIMAL,
                    lineterminator = '\n')
# Write headers
output.writerow(OutputRecord.header)
logging.debug('Writing output header')

grand_totals = OutputRecord('Grand Totals', '')

# ==============================================================================
# Start processing EAF files
# ------------------------------------------------------------------------------
for eaf_file in args.eaf_files:
    logging.info('Processing {}'.format(eaf_file))
    file_id = os.path.basename(eaf_file).replace('.eaf', '')

    # Initialize the EAF file parser
    warnings.filterwarnings('ignore')
    # pympi issues a warning "Parsing unknown version of ELAN spec..."
    eaf = pympi.Elan.Eaf(eaf_file)
    warnings.filterwarnings('default')

    # Get tier names from EAF file
    all_tiers = eaf.get_tier_names()
    # Filter out tiers with no sub-tiers
    tiers = filter(lambda t: '@' in t, all_tiers)
    # From those, extract the set of unique base tiers
    tiers = sorted(set(map(lambda t: t.split('@')[-1], tiers)))
    # Filter out ignored tiers
    tiers = filter(lambda t: t not in ignored_tiers, tiers)
    logging.debug('Ignoring tiers: {}'.format(
        filter(lambda t: t not in tiers, all_tiers)
    ))

    # Extract annotated segments from EAF
    segments = get_segments(eaf, tiers)
    logging.debug('Found {:,} segments'.format(len(segments)))

    # Convert segments (with start & end times) to events (with either
    # a start or end timestamp, but not both)
    events = get_events(segments)

    # Calculate sums and overlap for each combination of tiers
    (union_sum, section_sums) = process_events(events)
    logging.debug('Union sum: {:,} ms'.format(union_sum))
    logging.debug('Found {:,} section types'.format(len(section_sums)))

    # Get list of tier combinations (e.g. `CHI+FA2`)
    labels = sorted(section_sums.keys())
    # Ignore gaps between annotated sections
    labels.remove('')
    logging.debug('Empty sections sum: {:,} ms'.format(section_sums['']))

    # Create dictionary for storing output records, and add the record
    # for storing the totals for the whole EAF
    output_records = dict()
    output_records['totals'] = OutputRecord(file_id, 'Totals')

    # Iterate through the tier combinations found above, and add the
    # total time that combination was the only one active
    for label in labels:
        output_records[label] = OutputRecord(file_id, label)
        output_records[label].data['exclusive'] += section_sums[label]
        output_records['totals'].data['exclusive'] += section_sums[label]

    # For top-level tiers only, report a value in the `total` field
    for tier in tiers:
        for label in labels:
            if tier in label:
                output_records[tier].data['total'] += section_sums[label]
                output_records['totals'].data['total'] += section_sums[label]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # If we're reporting ADS & CDS data:
    if args.xds:
        # Get the list of tiers, including sub-tiers, but excluding
        # the ignored ones
        tiers = filter(lambda t: t not in ignored_tiers, eaf.get_tier_names())
        # Narrow that list to only the tiers with ADS & CDS annotations
        xds_tiers = filter(lambda t: 'xds@' in t, tiers)
        logging.debug('XDS tiers found: {}'.format(xds_tiers))

        # Extract annotated segment data for the XDS tiers
        segments = get_segments(eaf, xds_tiers)
        logging.debug('Found {:,} XDS segments'.format(len(segments)))

        # Convert segments to events list, setting the event labels to
        # the base tier name with the annotation code appended (for
        # example: `xds@FA1` with a `C` code becomes `FA1:C`)
        events = get_events(
            segments, lambda x: x.tier.split('@')[-1] + ':' + x.value)

        # Create filtered lists corresponding to ADS, CDS, and BOTH annotations
        cds_events = filter(lambda x: ':C' in x.label or ':T' in x.label, events)
        ads_events = filter(lambda x: ':A' in x.label, events)
        both_events = filter(lambda x: ':B' in x.label, events)
        logging.debug('Events found: CDS: {}, ADS: {}, BOTH: {}'.format(
            len(cds_events), len(ads_events), len(both_events)
        ))

        # Process the categories, adding the extracted data to the
        # corresponding output records
        process_category('cds', cds_events, labels, output_records)
        process_category('ads', ads_events, labels, output_records)
        process_category('both', both_events, labels, output_records)

    # Get the list of labels for all output records
    labels = sorted(output_records.keys())
    labels.remove('totals')

    # Report on top-level tiers on their own first
    for label in filter(lambda x: x in tiers, labels):
        output.writerow(output_records[label].fmt())

    # If it has been requested, report overlap details for each
    # combination of tiers in the EAF file
    if args.overlap:
        for label in filter(lambda x: x not in tiers, labels):
            output.writerow(output_records[label].fmt())

    # Write the totals for the current EAF file
    output.writerow(output_records['totals'].fmt())

    # Update the Grand Totals data for the set of EAF files being processed
    for category in output_records['totals'].data.keys():
        grand_totals.data[category] += output_records['totals'].data[category]

# ------------------------------------------------------------------------------
# Finally, write the Grand Totals row
output.writerow(grand_totals.fmt())
args.output.close()

exit
