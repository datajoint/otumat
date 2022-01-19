# Changelog

Observes [Semantic Versioning](https://semver.org/spec/v2.0.0.html) standard and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) convention.
## [0.3.1] - 2022-01-19
### Fixed
- Error when running `watch` without including the `watch_args` argument. (#6) PR #7

### Added
- Required and optional argument groups for `argparse`. PR #7
- Interval argument for `watch`. PR #7
- Defaults for `watch_interval` and `watch_args`. PR #7
- Cross-platform support for running scripts with `watch`. PR #7

### Changed
- Update test case for new `WatchAgent` initializer. PR #7
- Update README to include section for `watch` PR #7

### Removed
- Argument flag for `watch_args` PR #7

## [0.3.0] - 2022-01-14
### Added
- `watch` utility. (#5) PR #4
- Unit testing with `pytest`. (#5) PR #4

### Changed
- Replace Alpine image with Debian. PR #4

[0.3.1]: https://github.com/datajoint/otumat/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/datajoint/otumat/compare/v0.1.0...v0.3.0