<div markdown="1" class="custom-badge-table">

|                   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Testing**       | [![Code testing status](https://github.com/tektronix/tm_data_types/actions/workflows/test-code.yml/badge.svg?branch=main)](https://github.com/tektronix/tm_data_types/actions/workflows/test-code.yml) [![Docs testing status](https://github.com/tektronix/tm_data_types/actions/workflows/test-docs.yml/badge.svg?branch=main)](https://github.com/tektronix/tm_data_types/actions/workflows/test-docs.yml) [![Coverage status](https://codecov.io/gh/tektronix/tm_data_types/branch/main/graph/badge.svg)](https://codecov.io/gh/tektronix/tm_data_types)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Code Quality**  | [![CodeQL status](https://github.com/tektronix/tm_data_types/actions/workflows/codeql-analysis.yml/badge.svg?branch=main)](https://github.com/tektronix/tm_data_types/actions/workflows/codeql-analysis.yml) [![CodeFactor grade](https://www.codefactor.io/repository/github/tektronix/tm_data_types/badge)](https://www.codefactor.io/repository/github/tektronix/tm_data_types) [![pre-commit status](https://results.pre-commit.ci/badge/github/tektronix/tm_data_types/main.svg)](https://results.pre-commit.ci/latest/github/tektronix/tm_data_types/main)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Package**       | [![PyPI: Package status](https://img.shields.io/pypi/status/tm_data_types?logo=pypi)](https://pypi.org/project/tm_data_types/) [![PyPI: Latest release version](https://img.shields.io/pypi/v/tm_data_types?logo=pypi)](https://pypi.org/project/tm_data_types/) [![PyPI: Supported Python versions](https://img.shields.io/pypi/pyversions/tm_data_types?logo=python)](https://pypi.org/project/tm_data_types/) [![PyPI: Downloads](https://pepy.tech/badge/tm_data_types)](https://pepy.tech/project/tm_data_types) [![License: Apache 2.0](https://img.shields.io/pypi/l/tm_data_types)](https://github.com/tektronix/tm_data_types/blob/main/LICENSE.md) [![Package build status](https://github.com/tektronix/tm_data_types/actions/workflows/package-build.yml/badge.svg?branch=main)](https://github.com/tektronix/tm_data_types/actions/workflows/package-build.yml) [![PyPI upload status](https://github.com/tektronix/tm_data_types/actions/workflows/package-release.yml/badge.svg?branch=main)](https://github.com/tektronix/tm_data_types/actions/workflows/package-release.yml) |
| **Documentation** | [![ReadtheDocs Status](https://img.shields.io/readthedocs/tm_data_types/stable?logo=readthedocs)](https://tm-data-types.readthedocs.io)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Code Style**    | [![Test style: pytest](https://img.shields.io/badge/test%20style-pytest-blue)](https://github.com/pytest-dev/pytest) [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-black)](https://docs.astral.sh/ruff/formatter/) [![Docstring style: google](https://img.shields.io/badge/docstring%20style-google-tan)](https://google.github.io/styleguide/pyguide.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Linting**       | [![pre-commit enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit) [![Docstring formatter: docformatter](https://img.shields.io/badge/docstring%20formatter-docformatter-tan)](https://github.com/PyCQA/docformatter)[![Linter: pylint](https://img.shields.io/badge/linter-pylint-purple)](https://github.com/pylint-dev/pylint)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

</div>

---

# tm_data_types: Test & Measurement Data Types

`tm_data_types` provides tools to convert, edit, and write waveform data from Test & Measurement devices.
It simplifies handling waveform formats like CSV, WFM, and BIN in Python.

`tm_data_types` can be used to:

- **Convert** CSV, WFM, and BIN format into a waveform object,
- **Add or edit** waveform metadata,
- **Write** a valid waveform object to a file.

## Supported File Formats

<div markdown="1" class="custom-table-center-cells support-table">

| Interface | File formats       |
| --------- | ------------------ |
| Reader    | **.csv, .wfm[^1]** |
| Writer    | **.csv, .wfm[^1]** |

</div>

## Installation

```shell
pip install tm_data_types
```

## Basic Usage

### Write File

```python
from tm_data_types import AnalogWaveform, write_file

waveform = AnalogWaveform()
file_path = "waveform_1.wfm"
write_file(file_path, waveform)
```

### Read File

```python
from tm_data_types import read_file

file_path = "waveform_1.wfm"
waveform = read_file(file_path)
```

## Documentation

See the full documentation at <https://tm-data-types.readthedocs.io>

## Maintainers

Before reaching out to any maintainers directly, please first check if
your issue or question is already covered by any [open
issues](https://github.com/tektronix/tm_data_types/issues). If the issue or
question you have is not already covered, please [file a new
issue](https://github.com/tektronix/tm_data_types/issues/new/choose) or
start a
[discussion](https://github.com/tektronix/tm_data_types/discussions) and
the maintainers will review and respond there.

- <opensource@tektronix.com> - For open-source policy and license
    questions.

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

[^1]: Currently, `tm_data_types` only supports the [Tektronix proprietary `.wfm`](https://download.tek.com/manual/Waveform-File-Format-Manual-077022011.pdf) format. Support for other formats is planned for future releases.
