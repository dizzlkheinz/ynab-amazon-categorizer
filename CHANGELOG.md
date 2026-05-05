# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.2.3] - 2026-05-05

### Fixed

- Footer and nav boilerplate from the Amazon orders page (copyright lines, address blocks, credit card promos, accessibility hints) is no longer extracted as order items

## [2.2.2] - 2026-04-23

### Fixed

- Pin `ty==0.0.14` in dev dependencies so CI uses the same type-checker version as the lock file

## [2.2.1] - 2026-04-23

### Fixed

- Cancelled orders no longer cause their items to bleed into the preceding valid order
- Quantity badge numbers (e.g. trailing ` 2`, ` 4`) are stripped from item names when the bare form also appears, without corrupting size numbers like `Size 10`
- `"Now arriving today X:XX p.m."` delivery status lines are no longer extracted as item names

## [2.2.0] - 2026-02-23

### Fixed

- Comprehensive audit fixes across all modules
- Preserve Amazon order link in memo truncation when prefix space is too small

## [2.1.8] - 2026-02-05

### Fixed

- Ruff formatting compliance for CI

## [2.1.7] - 2026-02-04

### Changed

- Extracted testable functions from `cli.py` for better modularity
- Added retry logic to YNAB API client (3 retries with backoff on 429/5xx)
- Added stdlib logging throughout the codebase

### Added

- Comprehensive test suite for extracted CLI functions
