![Scio Logo](https://d347awuzx0kdse.cloudfront.net/vicomaus/content-image/Tek_Logo_RGB.png){width="50px"}

# tm_data_types

## Purpose

Python Instrument IO can be used to:

- **Convert** CSV, WFM, and BIN format into the waveform object format,
- **Generate** analog waveforms with NRZ or PAM4 signal processes,
- **Add or edit** waveform metadata,
- **Write** a valid waveform object to a file.

This interface assists the client and development team in parsing the format from Tek instrument and construct a
python object with features. The API is funneled into a single Python file, \[InstrumentIO\]{.title-ref}, which contains
all the functions required to read, write, and generate various instrument data.

For additional documentation, visit our Wiki page.

- Supported files for reader interface function include: '.wfm', '.bin', '.csv', '.awg_wfm'
- Supported files for writer interface function include: '.wfm', '.csv', '.awg_wfm'

## Quick Start

Requirements: [Python 3.0 or above](https://www.python.org/download/releases/3.0/)

Installed Library: \[datatime\]{.title-ref}, \[struct\]{.title-ref},
\[numpy\]{.title-ref}, \[scipy\]{.title-ref}, \[pandas\]{.title-ref} (Test waveform plot with \[matplotlib\]{.title-ref})

```bash
pip install tm_data_types
```

## Waveform Object Attributes

- `._vertical_data` → An array of binary values.
- `._size` → The size of the vertical data. Read-only, must be an integer.
- `._spacing` → The horizontal interval between two consecutive vertical data points. Must be an integer or float.
- `._trigger_index` →
- `.vertical_data` → vertical data
- `.horizontal_data` → horizontal data
- `.time_interval` → time intervals across vertical data
- `.trigger_position` → trigger position

## Examples

- `read_file_channels(file_path)` → return lists of channels for csv file only
- `read_file(file_path, channel (opt.))` → return waveform object
- `write_file(waveform obj, file_path, instrument_type (opt.))` → write file with extension format
- `initialize_waveform(size (opt.), sample_rate (opt.))` → return simple waveform with size and sample rate.
- `create_unique_filepath(file_path, file_template)` → return unique file path for converted/created file
- `random_bits(size)` → returns a random array of values 1 or 0 of user-inputted size.
- `random_symbols(size)` → returns a random array of values between 0 and 3 of user-inputted size.
- `nrz(bit_array, symbol_rate=1.0e9, sample_per_ui=10.12345, amplitude=1., offset=0.0, impairment=0.2, noise=0.01, repeats=1)`
    → return NRZ waveform object based on user-inputted bit array. Array could be derived from InstrumentIO's \[random_bits\]{.title-ref} function, or from some other random number generator specified by the user (i.e. PBRS).
- `pam4(symbol_arr, data_rate=1.0e9, sample_per_ui=10.12345, amplitude=1.0, offset=0.0, impairment=0.2, noise=0.01, repeats=1)`
    → return PAM4 waveform object based on user-inputted symbol array. Array could be derived from InstrumentIO's \[random_symbols\]{.title-ref} function, or from some other random number generator specified by the user (i.e. PBRS).
- `square(frequency=1000, repeat=5, amplitude=1, rec_length=1000)` → return square waveform object.
- `sawtooth(frequency=1000, repeat=5, amplitude=1, rec_length=1000)` → return sawtooth waveform object.
- `triangle(frequency=1000, repeat=5, amplitude=1, rec_length=1000)` → return triangle waveform object.

## Maintainers

.. TODO: update email -  tmdevicessupport@tektronix.com - For technical support and questions.

- <opensource@tektronix.com> - For open-source policy and license questions.
- Keith Rule <keith.d.rule@tektronix.com>

For more information about this repository, you can leave a question/comment on the [repository's Discussion board](https://github.com/tektronix/PythonInstrumentIO/discussions).

## Contributing

Interested in contributing? Check out the [contributing guidelines](https://github.com/tektronix/tm_data_types/blob/main/CONTRIBUTING.md). Please
note that this project is released with a [Code of Conduct](https://github.com/tektronix/tm_data_types/blob/main/CODE_OF_CONDUCT.md). By
contributing to this project, you agree to abide by its terms.

## License

`tm_data_types` was created by Tektronix. It is licensed under the terms of
the [Apache License 2.0](https://github.com/tektronix/tm_data_types/blob/main/LICENSE.md).

## Security

The signatures of the files uploaded to [PyPI](https://pypi.org/project/tm_data_types/) and each
[GitHub Release](https://github.com/tektronix/tm_data_types/releases) can be verified using
the [GitHub CLI `attestation verify` command](https://cli.github.com/manual/gh_attestation_verify).
The artifact attestations can also be directly downloaded from the
[GitHub repo attestations page](https://github.com/tektronix/tm_data_types/attestations) if desired.

```shell
gh attestation verify --owner tektronix <file>
```

## Credits

`tm_data_types` was created with
[cookiecutter](https://cookiecutter.readthedocs.io/en/latest/README.html)
and the `py-pkgs-cookiecutter`
[template](https://py-pkgs-cookiecutter.readthedocs.io/en/latest/).
