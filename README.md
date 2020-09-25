# Get Total Time with Overlaps

## Overview

The script `TotalTimeGrouped1.py` takes two parameters: a folder
containing EAF files to be processed, and the name of an output
file. It uses the [`pympi-ling`](https://github.com/dopefishh/pympi)
library to parse the input files, and writes its output in CSV format.

Each EAF input file's data is written as a separate table in the
output file, with one row per top-level tier, showing times in
milliseconds of overlap with each other tier, each in its own
column. After that, each row also contains columns for the total time
annotated as CDS, ADS, and both, followed by a column containing the
total overlap time for that row's tier, then a column showing the
adjusted total time for that tier's annotated segments (total time
minus overlap time). After that, there's one row that shows the
(overlap-adjusted) grand total time for that file.

After all files are processed, totals for the whole set of EAF files
processed are included in a separate table.


## Details

The output tables warrant a bit more explanation. Each file's output
table will look something like this (example numbers not derived from
real data):

| Filename | TierName | CHI   | EE1 | FA1   | MA1   | ADS     | CDS    | BOTH        | TotalOverlap | Total    |
|----------|----------|-------|-----|-------|-------|---------|--------|-------------|--------------|----------|
| 1234     | CHI      | 0     | 0   | 22222 | 3333  | 0       | 0      | 0           | 25555        | 612434   |
| 1234     | EE1      | 54321 | 0   | 41414 | 8967  | 1195452 | 50335  | 0           | 104702       | 1153668  |
| 1234     | FA1      | 0     | 0   | 0     | 65536 | 151808  | 425062 | 30362       | 65536        | 541695   |
| 1234     | MA1      | 0     | 0   | 0     | 0     | 128502  | 102801 | 20560       | 0            | 257003   |
|          |          |       |     |       |       |         |        | Grand Total | 1411132      | Resample |

Note: all time values are in milliseconds.

The first column shows the filename without the `.eaf` extension. Then
comes the name of the tier whose totals are shown, followed by columns
for that tier's overlap with each of the included tiers, in this case
`CHI`, `EE1`, `FA1`, and `MA1`. Note that the overlap between two
tiers does not appear in the rows for both tiers. This is an effect of
the mechanism used to avoid double-counting overlaps so that the
correct grand total can be calculated.

The next three columns correspond to the the total time annotated as
ADS, CDS, and both ADS and CDS simultaneous. The third column's values
are not included in the first two, so a segment annotated as "both" is
not part of either the ADS or CDS number. Also note that no overlap
correction is applied to these columns.

The final two columns are `TotalOverlap` and `Total`. Since we're
avoiding double-counting time periods where segments belonging to two
different tiers overlap (see above), this number is not necessarily
the total amount of time that the given tier's segments overlap other
tiers' segments. In the example above, the `MA1` row shows a total
overlap value of `0`, but if we look at the `MA1` column, we can see
that it did have overlaps with the other tiers (`3333`, `8967`, and
`65536`), but it wasn't necessary to subtract those amounts from the
final `Grand Adjusted Total` value.

### Handling of the `EE1` tier

The `EE1` tier is segregated from the other tiers, and is not included
in the `Grand Total`. This is because of differences in notation
between corpora, and the different nature of the speech it
represents. In order to do this, but still report its total numbers in
its row, the counter includes all of its overlap data in its own
row. The other tiers have their data reported as if the `EE1` tier did
not exist. This is why, in the example above, the `54321`ms overlap
time between `CHI` and `EE1` is attributed to `EE1` instead of `CHI`.

### Grand Totals

After writing a table of values for each file, a smaller table is
written to the output file with a set of grand totals for the corpus,
like this:

| Grand Total | Grand Adjusted Total | ADS    | CDS     | BOTH |
|-------------|----------------------|--------|---------|------|
| 4544909     | 4047123              | 957014 | 1848422 | 5926 |

The `Grand Total` value comprises the union of the annotated segments
for all tiers (except `EE1`), not the sum of the total annotated time
for each tier. In other words, when two segments, one lasting 7s and
the other lasting 8s overlap by 2s, they collectively contribute 13s
to the grand total annotated time, not 15s.

The `Grand Adjusted Total` value is equal to the `Grand Total` minus
the total amount of overlap time for all tiers (except `EE1`).

The other grand totals (`ADS`, `CDS`, and `BOTH`) are not adjusted for
overlap, so if two `ADS` segments overlap, the overlap will not be
subtracted. It is technically possible, but very unlikely, for any of
these numbers to be greater than the `Grand Total` value.


## Setup

To run the script, you'll need at least one EAF file, Python version
2.7, and the [`pympi`](https://github.com/dopefishh/pympi) library. As
of 2020-09-25, the released version installable via `pip` doesn't work
well enough, so I recommend installing the version from GitHub.

The script should be invoked as follows:

```sh
$ python TotalTimeGrouped1.py [input_dir] [output_file.csv]
```

---

2020-09-25: The original version, `TotalTimeGrouped.py` reported fewer
columns, and still has very minor bugs. Please use the newer
`TotalTimeGrouped1.py` instead.
