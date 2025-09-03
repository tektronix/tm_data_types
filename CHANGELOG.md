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
