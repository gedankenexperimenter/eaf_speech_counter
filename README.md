# Summarize EAF Files

## Overview

The script `summarize-eaf.py` reads [ELAN](https://archive.mpi.nl/tla/elan)
files in [EUDICO Annotation
Format](https://www.mpi.nl/tools/elan/EAF_Annotation_Format_3.0_and_ELAN.pdf)
and calculates the total times of the sets of (possibly overlapping) annotated
segments therein. It uses the [`pympi-ling`](https://github.com/dopefishh/pympi)
library to parse the input files, and writes its output to table in CSV format
in a specified output file.

In particular, it is intended for use in analyzing speech recordings for the
study of the language environments of infants and children.

## Computation Method

First, `summarize-eaf.py` reads all of the base tier names from the EAF file,
filtering out tiers specified as "ignored" on the command line (using the
`--ignore-tiers` option), along with any tiers that have no sub-tiers, including
a built-in list (`code_num`, `on_off`, `context`, and `code`). Then it extracts
all of the annotated segments for each of the non-ignored base tiers, and builds
a list of start and end timestamps from that.

Once that list of "events" is sorted in chronological order, it scans through
them, keeping track of which segments are active at each point in time, and
producing a list of the sum of the active time (in milliseconds) that each
unique combination of tiers was active, as well as the total time each tier was
active (regardless of overlap with other tiers).

Then it goes through a similar process, computing the total times annotated and
child-directed speech (CDS), adult-directed speech (ADS), and speech segments
directed at both. This is done by selecting the tiers named `xds@<BASE>`, where
`<BASE>` is the name of a base tier.

## Output Table

The output tables look like this:

| File | Tier(s)      | Exclusive | Total   | CDS    | ADS    | BOTH  |
|------|--------------|-----------|---------|--------|--------|-------|
| 1234 | CHI          | 143099    | 195471  |        |        |       |
| 1234 | FA1          | 206302    | 249630  | 148523 | 47897  | 32494 |
| 1234 | MA1          | 202093    | 240012  | 162588 | 59462  | 2474  |
| 1234 | CHI+FA1      | 28308     |         |        |        |       |
| 1234 | CHI+FA1+MA1  | 1166      |         |        |        |       |
| 1234 | CHI+MA1      | 22898     |         |        |        |       |
| 1234 | FA1+MA1      | 13855     |         | 559    | 2319   | 2291  |
| 1234 | Totals       | 617721    | 685113  | 311670 | 109678 | 37259 |
| 5678 | CHI          | 242516    | 311834  |        |        |       |
| 5678 | FA1          | 477640    | 565899  | 549321 | 3528   |       |
| 5678 | FA2          | 23787     | 45555   | 337    | 6852   |       |
| 5678 | MA1          | 3708      | 5808    | 4481   |        |       |
| 5678 | CHI+FA1      | 66504     |         |        |        |       |
| 5678 | CHI+FA1+FA2  | 700       |         |        |        |       |
| 5678 | CHI+FA2      | 1340      |         |        |        |       |
| 5678 | CHI+MA1      | 773       |         |        |        |       |
| 5678 | FA1+FA2      | 19728     |         | 436    |        |       |
| 5678 | FA1+MA1      | 1327      |         | 1327   |        |       |
| 5678 | Totals       | 838023    | 929096  | 555902 | 10380  |       |
| *    | Grand Totals | 1455744   | 1614209 | 867572 | 120058 | 37259 |

Each row is identified by the filename (without the `.eaf` extension) and the
unique combination of simultaneously active tiers. For rows representing
overlapping speech, the base tier names are concatenated with `+` signs.

The `Exclusive` column contains the sum total time (in milliseconds) during
which that particular set of tiers was the only one active. If we combine all of
these `Exclusive` values for a given file, we should get the amount for that
file in the `Totals` row for the file. This equals the total time marked as
annotated speech for the non-ignored tiers in the file.

The `Total` column contains the total time that an individual base tier was
active, whether or not it was overlapping with any other tiers for some of that
time. Therefore, the `Total` amount for a tier should be greater than or equal
to the `Exclusive` amount for that tier. This amount is only reported for base
tiers on their own, not for overlapping combinations of base tiers.

The last three columns contain similar totals, but for child-directed,
adult-directed, and both-directed speech. All of these are likewise summed in
the `Totals` row for each file.

Finally, if multiple EAF files are processed in a batch, a `Grand Totals` row
contains the sum of the `Totals` rows for each file.

## Options

There are several command-line options for controlling the behaviour of the
`summarize-eaf.py` script. Notably:

- Setting the output file name with `--output`
- Setting the output delimiter character with `--delimiter`
- Suppressing the `CDS`/`ADS`/`BOTH` computation with `--no-xds`
- Suppressing the `Totals` and `Grand Totals` rows with `--no-totals`
- Suppressing the output of overlapping tier combinations with `--no-overlap`
- Ignoring specified tiers with `--ignore-tiers`
- Using specified tiers as an input mask with `--masking-tiers`

Some of these options are self-explanatory, but a few require a bit more
explanation.

### Suppressing `Totals`

Since the `Totals` (and `Grand Totals`) row(s) are simple sums of rows above
them, it could be convenient for some analyses to omit them by using the option
`--no-totals`.

### Suppressing overlap details

If invoked with `--no-overlap`, `summarize-eaf.py` won't write rows for
overlapping tier combinations to the output file, but those amounts will still
be included in the `Totals` (and `Grand Totals`) row(s). If you don't care about
the details of which tiers overlapped and for how long, this can produce a
substantially smaller output table.

Note: If you use both `--no-overlap` and `--no-totals`, you will not have access
to enough information to compute the omitted `Totals` row(s) correctly.

### Suppressing `CDS`, _et al_

The option `--no-xds` will cause `summarize-eaf.py` to omit the data for the
final three columns. The columns (and their headers) will still be included in
the output, but the data won't be compiled and the cells will all be empty. The
script only runs very slightly faster with this option, so it's really only
useful for removing unwanted noise from the output table.

### Ignoring tiers

Tiers can be added to the "ignored tiers" list by specifying them after the
`--ignore-tiers` option. This is useful if you want to segregate one tier from
the others, and report totals from the other tiers as if the ignored tiers were
not present. Most likely, this would be used to filter out electronic devices
(i.e. the `EE1` tier).

### Using a tier as a mask

The `--masking-tiers` option turns the specified tier into an "input mask" for
the tiers being processed. The EAF files are processed as if there were no
active tiers wherever a masking tier is active. Put another way, any overlap of
other tiers with a masking tier is not counted in the totals.

This allows an analysis where subjects (i.e. `CHI`) are assumed to not be
listening whenever they are speaking.

## Setup

### Dependencies

To run the script, you'll need Python installed (tested on versions 2.7.18 and
3.8.5), and the pympi-ling package, which can be installed using pip:

```console
$ pip install pympi-ling
```

Version 1.69 of pympi-ling works, but if your EAF files are version 3.0 or
higher, you'll see error messages on standard output:

```
Parsing unknown version of ELAN spec... This could result in errors...
```

The master branch of [pympi-ling](https://github.com/dopefishh/pympi) on GitHub
has an improved warning system, which allows us to suppress this warning (since
our EAF v3.0 files are compatible), but both versions will work.

### Running the script

First, clone the repository:

```console
$ git clone https://github.com/aclew/eaf_speech_counter
```

Supposing you have a folder named `data` containing a set of EAF files, run the
script like this:

```console
$ eaf_speech_counter/summarize-eaf.py -o output.csv data/*.eaf
```

The output table will be written to `output.csv`, including a totals row for
each file, grand totals for the set of files, and CDS/ADS data.

#### Ignoring tiers

Tiers can be added to the ignore list by using the `--ignore-tiers` option (or
simply `-i` for short):

```console
$ summarize-eaf.py -o output.csv -i EE1 -- data/*.eaf
```

Note that the `--` separating option parameters from the name(s) of the target
EAF file(s) is required; otherwise the filenames will be treated as the names of
tiers to be ignored.

Multiple tiers can be ignored, as well:

```console
$ summarize-eaf.py -o output.csv -i EE1 UC1 MA3 -- data/*.eaf
```

#### Omitting `Totals`

The totals rows and grand totals row will be omitted with the `--no-totals`
option:

```console
$ summarize-eaf.py -o output.csv --no-totals data/*.eaf
```

#### Omitting overlap details

The rows showing overlap details can be omitted with `--no-overlap`:

```console
$ summarize-eaf.py -o output.csv --no-overlap data/*.eaf
```

#### Masking tiers

To use a tier as a mask, use the option `--masking-tiers` (or `-m`):

```console
$ summarize-eaf.py -o output.csv -m CHI -- data/*.eaf
```

#### Debugging

To turn on debug output, use `--verbose` or `-v`. There are three levels,
depending on how many time you use the option:

```console
# INFO level
$ summarize-eaf.py -o output.csv -i EE1 -v data/*.eaf
```

```console
# DEBUG level
$ summarize-eaf.py -o output.csv -i EE1 -vv data/*.eaf
```

```console
# VERBOSE level
$ summarize-eaf.py -o output.csv -i EE1 -vvv data/*.eaf
```

The highest level of output is _extremely_ verbose; it writes a line for every
event in sequence.
