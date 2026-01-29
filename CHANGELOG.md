# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com), and this
project adheres to [Semantic Versioning](https://semver.org).

Valid subsections within a version are:

- Added
- Changed
- Deprecated
- Removed
- Fixed
- Security

---

## Unreleased

Things to be included in the next release go here.

### Fixed

- Updated `check_style()` logic to properly detect Digital and IQ waveform file types in addition to Analog waveforms.

### Changed

- Dropped support for Python 3.9

---

## v0.3.0 (2025-10-28)

### Merged Pull Requests

- wfm type detection ([#125](https://github.com/tektronix/tm_data_types/pull/125))
- python-deps(deps): bump the python-dependencies group with 6 updates ([#103](https://github.com/tektronix/tm_data_types/pull/103))
- gh-actions(deps): bump tektronix/python-package-ci-cd ([#104](https://github.com/tektronix/tm_data_types/pull/104))
- chore: Update Mermaid library source to use CDN ([#117](https://github.com/tektronix/tm_data_types/pull/117))
- python-deps(deps): bump the python-dependencies group with 2 updates ([#116](https://github.com/tektronix/tm_data_types/pull/116))
- python-deps(deps): bump the python-dependencies group with 5 updates ([#112](https://github.com/tektronix/tm_data_types/pull/112))
- docs: Correct formatting in glossary and update setuptools version in pre-commit config ([#111](https://github.com/tektronix/tm_data_types/pull/111))
- gh-actions(deps): bump actions/checkout ([#107](https://github.com/tektronix/tm_data_types/pull/107))
- python-deps(deps): bump the python-dependencies group with 8 updates ([#105](https://github.com/tektronix/tm_data_types/pull/105))
- Removed unused models ([#101](https://github.com/tektronix/tm_data_types/pull/101))

### Fixed

- Fixed WFM file type detection to correctly identify digital and IQ waveforms instead of always defaulting to analog waveforms
- Improved metadata system error messages to provide helpful guidance when accessing custom metadata fields

### Added

- Added `set_custom_metadata()` convenience method to `WaveformMetaInfo` classes for easier custom metadata management
- Added comprehensive docstrings to all metadata classes with practical examples and usage guidance
- Added helpful warnings in `remap()` method for unknown metadata fields

### Changed

- Enhanced error messages for custom metadata access to guide users on proper usage
- Improved documentation for `extended_metadata` field with file format compatibility notes

---

## v0.2.0 (2025-07-10)

### Merged Pull Requests

- Allow optional/unknown metadata keys in .wfm files ([#100](https://github.com/tektronix/tm_data_types/pull/100))
- Drop support for Python 3.8, add support for Python 3.13, and update dependencies. ([#97](https://github.com/tektronix/tm_data_types/pull/97))
- python-deps(deps-dev): update pyright requirement from 1.1.390 to 1.1.391 in the python-dependencies group ([#70](https://github.com/tektronix/tm_data_types/pull/70))
- gh-actions(deps): bump tektronix/python-package-ci-cd ([#44](https://github.com/tektronix/tm_data_types/pull/44))
- python-deps(deps-dev): update pyright requirement from 1.1.389 to 1.1.390 in the python-dependencies group ([#69](https://github.com/tektronix/tm_data_types/pull/69))
- python-deps(deps-dev): update twine requirement from ^5.0.0 to ^6.0.1 in the python-dependencies group ([#67](https://github.com/tektronix/tm_data_types/pull/67))
- Enable insiders documentation features ([#65](https://github.com/tektronix/tm_data_types/pull/65))
- python-deps(deps-dev): update pyright requirement from 1.1.388 to 1.1.389 in the python-dependencies group ([#64](https://github.com/tektronix/tm_data_types/pull/64))
- python-deps(deps-dev): bump the python-dependencies group with 2 updates ([#63](https://github.com/tektronix/tm_data_types/pull/63))
- docs: Update link to badge ([#62](https://github.com/tektronix/tm_data_types/pull/62))
- refactor: No longer allow printouts in this package ([#61](https://github.com/tektronix/tm_data_types/pull/61))
- chore: Update pyright dependency and use more reliable method of installing local nodejs for it ([#59](https://github.com/tektronix/tm_data_types/pull/59))
- python-deps(deps-dev): update pyright requirement from 1.1.383 to 1.1.386 in the python-dependencies group across 1 directory ([#58](https://github.com/tektronix/tm_data_types/pull/58))
- ci: Skip updating the mdformat repo during the dependency updater workflow ([#57](https://github.com/tektronix/tm_data_types/pull/57))
- docs: Update documentation templates and macros ([#55](https://github.com/tektronix/tm_data_types/pull/55))
- python-deps(deps-dev): update pyright requirement from 1.1.382.post1 to 1.1.383 in the python-dependencies group ([#52](https://github.com/tektronix/tm_data_types/pull/52))
- python-deps(deps-dev): update pyright requirement from 1.1.381 to 1.1.382.post1 in the python-dependencies group ([#49](https://github.com/tektronix/tm_data_types/pull/49))
- python-deps(deps-dev): update pyright requirement from 1.1.380 to 1.1.381 in the python-dependencies group ([#46](https://github.com/tektronix/tm_data_types/pull/46))
- test: Ignore googletagmanager links during doctests ([#47](https://github.com/tektronix/tm_data_types/pull/47))
- test: enabled doctests in test-docs.yml ([#45](https://github.com/tektronix/tm_data_types/pull/45))

### Removed

- Python 3.8 support has been removed from the package. The minimum supported version is now Python 3.9.
- Removed unused instrument series models (MSO64, MSO54, MSO24, etc.) from InstrumentSeries enum.

### Added

- Added support for Python 3.13.
- Allow optional/unknown metadata keys in .wfm files.
    - _**<span style="color:red">WARNING</span>**_: This update is known to break digital and IQ waveform handling. This will be fixed in an upcoming release.

---

## v0.1.1 (2024-09-11)

### Merged Pull Requests

- Update documentation and add missing dependencies ([#42](https://github.com/tektronix/tm_data_types/pull/42))

### Fixed

- Added missing dependencies to `pyproject.toml`.

### Changed

- Updated all documentation links to use the proper URL.

---

## v0.1.0 (2024-09-11)

### Merged Pull Requests

- docs: Ignore the generated files when building docs ([#39](https://github.com/tektronix/tm_data_types/pull/39))
- fix: Update code to remove an unreachable statement by simplifying a while loop ([#38](https://github.com/tektronix/tm_data_types/pull/38))
- python-deps(deps-dev): bump the python-dependencies group across 1 directory with 3 updates ([#37](https://github.com/tektronix/tm_data_types/pull/37))
- Update test_wfm to pass and fix linting issues ([#34](https://github.com/tektronix/tm_data_types/pull/34))
- chore: Update contributor_setup.py to encase executables and paths in quotes to avoid splitting paths ([#13](https://github.com/tektronix/tm_data_types/pull/13))
- docs: Add footnote in main Readme ([#8](https://github.com/tektronix/tm_data_types/pull/8))
- docs: Updated Readme and docstrings ([#7](https://github.com/tektronix/tm_data_types/pull/7))
- ci: Add pre-commit hook to better lint GitHub workflows ([#6](https://github.com/tektronix/tm_data_types/pull/6))
- ci: Switch to using reusable workflows from tektronix/python-package-ci-cd ([#4](https://github.com/tektronix/tm_data_types/pull/4))
- Added examples and contribution scripts ([#1](https://github.com/tektronix/tm_data_types/pull/1))
- python-deps(deps-dev): bump the python-dependencies group with 3 updates ([#2](https://github.com/tektronix/tm_data_types/pull/2))

### Added

- First release of `tm_data_types`!
