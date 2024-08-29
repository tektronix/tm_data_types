# Waveform File Operations

## `write_file`

It is a generic function that takes two arguments:

- **path**: The file path to write to.
- **waveform**: The waveform data to write.

### Process Overview

1. **Lookup Table**: The method begins by using a lookup table to determine the behavior based on the waveform type.
2. **Formatting**: The waveform is formatted according to its type.
3. **Writing**: Finally, the formatted waveform is written to the specified file path.

### Special Cases

- **RawSample Type**: No transformations are applied when saving data in the `.wfm` format if the waveform is of the `RawSample` type. This is done to ensure that `.wfm` files are saved and loaded as quickly as possible.
- **Normalized Type**: If the waveform is of the `Normalized` type, a transformation is performed because `.wfm` files must contain digitized data, with spacing and offset stored separately.

## `write_files_in_parallel`

This method offers a parallelized approach to writing multiple waveform files.

### Parameters

- **file_paths**: A list of file paths where each waveform will be saved.
- **waveforms**: A list of waveforms to write, where each index corresponds to the matching file path.

### Process Overview

1. **Multiprocessing**: The lists of file paths and waveforms are partitioned and processed in parallel.
2. **Writing**: Each process uses the same method as `write_file` to save its assigned waveforms.

This method is particularly useful for saving multiple waveform files efficiently.

## `read_file`

This method is a generic function that takes one argument:

- **path**: The file path from which the waveform should be read.

### Process Overview

1. **Lookup Table**: Similar to `write_file`, a lookup table is used to determine the file extension.
2. **Type Detection**: The method reads small sections of the file to identify the waveform type.
3. **Reformatting**: The waveform is read and returned in the appropriate format, depending on how the data is structured.

### Special Cases

- All waveforms are returned in the `RawSample` format. The data is reformatted for compatibility with the oscilloscope, which involves mathematical transformations on the entire dataset. This can be time-consuming, so using the `.wfm` format is recommended for efficiency.

## `read_files_in_parallel`

This method allows for the parallel reading of multiple waveform files.

### Parameters

- **file_paths**: A list of file paths to read from.

### Process Overview

1. **Multiprocessing**: Similar to `write_files_in_parallel`, the file paths are partitioned and processed in parallel.
2. **Reading**: The waveforms are read using the same process as `read_file`, and a queue of waveforms is returned.
