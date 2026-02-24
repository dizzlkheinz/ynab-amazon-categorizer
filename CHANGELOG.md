# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
