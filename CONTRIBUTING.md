# Contributing to Zero Trust Cisco ISE Lab

Thank you for your interest in contributing! This repository provides an end-to-end reference implementation for Zero Trust Network Access Control using Cisco ISE 3.2, Catalyst switches, and Python automation.

## How to Contribute

### 1. Reporting Issues
- Use the GitHub issue tracker to report bugs, documentation gaps, or syntax errors in switch configs.
- Provide full switch model, IOS-XE version, and ISE patch level where applicable.

### 2. Suggesting Enhancements
- Ideas for new test cases, Python audit scripts, Ansible automation, or posture rules are welcome.
- Please open an issue outlining the proposed change before submitting large pull requests.

### 3. Pull Request Guidelines
1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Verify all Python scripts adhere to PEP 8:
   ```bash
   flake8 scripts/ tests/
   black --check scripts/ tests/
   ```
3. Run the automated test suite:
   ```bash
   pytest
   ```
4. If modifying Cisco switch configurations:
   - Ensure all passwords and secrets use sanitized placeholders (e.g. `ChangeMe123!`).
   - Include corresponding test cases in `scripts/testing/test-plan.md`.
5. Submit your pull request with a detailed description of your changes.

## Code of Conduct
Please be respectful, collaborative, and constructive when communicating in issues and pull requests.
