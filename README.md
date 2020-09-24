# Get Total time with Overlaps

The script `'TotalTimeGrouped.py'` takes EAF files from a folder as input and outputs a csv file containing
1. Total annotation time
2. Individual overlapping time between tiers
3. Total Overlapping time

We are only considering the main tiers (no sub tiers) and all the times mentioned are in milliseconds. If the Grand Total is less than 10 minutes it shows another message `Resampling Required`

The script can be run as follows:

```
> python TotalTimeGrouped.py [input_dir] [output_file_name.csv]
```
Here `input_dir` is the directory that contains the target EAF files and `output_file_name.csv` is the name of the output file. The csv output will look like:

```
```
FileName | TierName | CHI | FA1 | UC1 | TotalOverlap | Total |
| ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
File1 | CHI | 0 | 0 | 3190 | 3190 | 26086 |
File1 | FA1 | 0 | 0 | 1246 | 1246 | 9695 |
File1 | UC1 | 3190 | 0 | 0 | 0 | 83303 |
 |  |  |  |  | |  Grand Total | 119084  |
```
```

Here `TierName` represents the main tiers  which are being considered from the `File1.eaf` file.  The other columns represent the other tiers along with their Total Overlap in milliseconds. 

9/24/20: The script 'TotalTimeGrouped1.py' is the same as the original counter however it includes a section to tabulate the ADS, CDS, and Both speech tags in milliseconds.


