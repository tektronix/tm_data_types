# Basic Usage

A collection of examples showing the basics of how to use `tm_data_types` in a
project.

## Write Data

`tm_data_types` can be used for writing data to a file using [`write_file()`][tm_data_types.write_file].

```python
# fmt: off
--8<-- "examples/write_file.py"
```

## Type Conversion and Normalization of Data

`tm_data_types` can be used for type conversion and normalization of analog waveform data.

```python
# fmt: off
--8<-- "examples/type_conversion_example.py"
```

## Write Analog Waveform to CSV file

`tm_data_types` can be used to write an analog waveform to a CSV file using the [`WaveformFileCSVAnalog`][tm_data_types.WaveformFileCSVAnalog] class.

```python
# fmt: off
--8<-- "examples/write_csv_example.py"
```
