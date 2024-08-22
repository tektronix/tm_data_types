write_file is a generic method which takes two arguments, the path to write to and the waveform
to write. The method begins by utilizing a lookup table 
along with the waveform type to determine what type of behavior it will utilize to write.
Following this, the waveform is formatted and written to the path specified.

Alternatively, write_files_in_parallel can be used instead. This method accepts two separate list for
lists for file paths and waveforms, where each value in one list index will correspond to the other.
Multiprocessing is leveraged by partitioning each list and sending them into their own
distinct process for saving. The write process is identical to the standard write_file.

This writing process is involved, and is distinctly different between each format and waveform type
No transformations are done when saving to the .wfm format if the data is of the RawSample type.
This done as the express purpose of this library is to save and load .wfm files as fast as possible. 
However if the data type is Normalized, a transformed is performed, as .wfm files are required to contain
digitized data with the spacing and offset being separate.

read_file is a generic method which takes one argument, the path in which a waveform file exists that
should be read. The same lookup table for file extensions is used from write_file, however an additional
step is used, which is looking through small sections of the files data to determine what the waveform type is.
Following this, a waveform is provided from the read file, the type of which is dependant on how the data is
formatted.

read_files_in_parallel handles the same way functionally as write_files_in_parallel, the main difference between
the two being what arguments are passed in and the queue of waveforms returned.

Reading will reformat the waveform data to match what is required for the oscilloscope to display.
Waveform files will all return the waveform in the RawSample format. This process takes some time 
as the conversion utilizes mathematical transformations
on the entire dataset, so the best way to utilize this library is to utilize the .wfm extension.