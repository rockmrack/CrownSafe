# Contributing to BabyShield Backend

Thank you for your interest in contributing to BabyShield! 🎉

We welcome contributions from the community and are grateful for your help in improving this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry (dependency management)
- Docker (optional, for local development)

### Setup Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/babyshield-backend.git
   cd babyshield-backend
   ```

2. **Install dependencies**
   ```bash
   poetry install
   poetry shell
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Run the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Verify setup**
   ```bash
   pytest
   ```

## Development Workflow

### Branching Strategy

We follow a simplified Git workflow:

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring

### Creating a Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) and use automated tools to enforce code quality:

- **Formatter**: Black (line length: 100)
- **Linter**: Ruff
- **Type Checker**: MyPy

### Code Formatting

Before committing, format your code:

```bash
# Format code
black .

# Check linting
ruff check .

# Type checking
mypy .
```

### Code Quality Rules

- Write clear, self-documenting code
- Add docstrings to all public functions/classes
- Keep functions small and focused (max ~50 lines)
- Use type hints for function parameters and return values
- Avoid deeply nested code (max 3-4 levels)

### Example Function

```python
from typing import Optional

def create_user(
    username: str,
    email: str,
    age: Optional[int] = None
) -> dict[str, any]:
    """
    Create a new user account.

    Args:
        username: Unique username for the account
        email: User's email address
        age: Optional user age

    Returns:
        Dictionary containing user data

    Raises:
        ValueError: If username or email is invalid
    """
    # Implementation
    pass
```

## Commit Guidelines

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(auth): add JWT token refresh endpoint

Implements automatic token refresh to improve UX
and reduce authentication friction.

Closes #123
```

```
fix(api): resolve 500 error on empty request body

Added validation to handle edge case when request
body is empty or malformed.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. ✅ Ensure all tests pass: `pytest`
2. ✅ Run code formatters: `black .`
3. ✅ Check linting: `ruff check .`
4. ✅ Verify type hints: `mypy .`
5. ✅ Update documentation if needed
6. ✅ Add tests for new features

### PR Checklist

When creating a pull request, ensure:

- [ ] Code follows our style guide
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventional commits
- [ ] PR description clearly explains changes
- [ ] Linked to related issue(s)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #(issue number)

## Testing
Describe testing performed

## Screenshots (if applicable)
Add screenshots for UI changes
```

### Review Process

1. Automated checks must pass (CI/CD pipeline)
2. At least one code review approval required
3. All review comments must be addressed
4. PR will be merged by maintainers

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory
- Mirror the application structure
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_create_user_success():
    # Arrange
    user_data = {"username": "test", "email": "test@example.com"}

    # Act
    result = create_user(**user_data)

    # Assert
    assert result["username"] == "test"
    assert "id" in result
```

## Reporting Issues

### Bug Reports

When reporting bugs, include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Numbered steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, dependencies
- **Screenshots**: If applicable

### Feature Requests

When requesting features, include:

- **Problem**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Alternatives**: Other solutions considered
- **Additional Context**: Any other relevant information

## Questions?

- 📧 General Email: dev@babyshield.dev
- 🛡️ Security Email: security@babyshield.dev
- 💬 Discussions: [GitHub Discussions](https://github.com/BabyShield/babyshield-backend/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/BabyShield/babyshield-backend/issues)

Thank you for contributing to BabyShield! 🚀
