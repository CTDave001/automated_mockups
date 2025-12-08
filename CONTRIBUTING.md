# Contributing to Automated Mockup Generator

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/automated_mockups.git
   cd automated_mockups
   ```
3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

Run these before committing:

```bash
# Format code
black mockup_generator/

# Lint code
ruff check mockup_generator/ --fix

# Type check
mypy mockup_generator/ --ignore-missing-imports
```

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=mockup_generator --cov-report=html
```

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and add tests if applicable

3. Run the test suite and linters

4. Commit your changes with a clear message:
   ```bash
   git commit -m "Add feature: brief description"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a Pull Request

## Pull Request Guidelines

- **Keep PRs focused** - One feature or fix per PR
- **Write clear descriptions** - Explain what changed and why
- **Add tests** - For new features or bug fixes
- **Update documentation** - If your change affects usage
- **Follow existing patterns** - Match the project's coding style

## Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- Operating system
- Package version (`pip show mockup-generator`)
- Steps to reproduce
- Expected vs actual behavior
- Error messages (if any)

## Feature Requests

Feature requests are welcome! Please:

- Check existing issues first
- Clearly describe the use case
- Explain why it would be valuable

## Questions?

Feel free to open an issue for questions about contributing.
