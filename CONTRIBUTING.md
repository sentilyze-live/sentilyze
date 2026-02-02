# Contributing to Sentilyze

Thank you for your interest in contributing to Sentilyze! We welcome contributions from the community and are pleased to have you join us.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and what behavior you expected**
- **Include code samples and screenshots if relevant**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repository
2. Create a new branch from `main` (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Workflow

### Setting Up Your Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/sentilyze.git
cd sentilyze

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Start local services
./scripts/deploy-local.sh up
```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**:
   ```bash
   # Run unit tests
   pytest tests/unit
   
   # Run integration tests
   pytest tests/integration
   
   # Run all tests with coverage
   pytest --cov=sentilyze tests/
   ```

4. **Update documentation** if needed

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

### Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding or correcting tests
- **chore**: Changes to build process or auxiliary tools

Examples:
```
feat: add batch sentiment analysis endpoint
fix: correct sentiment score calculation for neutral texts
docs: update API documentation with new parameters
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these additions:

- **Line length**: Maximum 100 characters
- **Imports**: Use absolute imports, organize with isort
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

Example:
```python
def analyze_sentiment(
    text: str,
    language: str = "en",
    include_entities: bool = False
) -> SentimentResult:
    """Analyze sentiment of the provided text.
    
    Args:
        text: The text to analyze.
        language: ISO 639-1 language code (default: "en").
        include_entities: Whether to include entity extraction.
    
    Returns:
        SentimentResult containing score, magnitude, and label.
    
    Raises:
        ValueError: If text is empty or language is not supported.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Implementation here
    pass
```

### Code Formatting

We use the following tools to ensure code quality:

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Lint with flake8
flake8 .

# Type check with mypy
mypy .
```

### Testing Guidelines

- **Write tests for all new code**
- **Maintain test coverage above 80%**
- **Use pytest for all tests**
- **Mock external services in unit tests**

```python
# Example test
def test_analyze_sentiment_positive():
    result = analyze_sentiment("This is amazing!")
    assert result.label == "positive"
    assert result.score > 0.5
```

## Project Structure

```
sentilyze/
├── services/              # Application services
│   ├── api/              # REST API
│   │   ├── routes/       # API routes
│   │   ├── models/       # Data models
│   │   └── handlers/     # Request handlers
│   ├── worker/           # Background workers
│   └── scheduler/        # Job scheduler
├── services/shared/      # Shared libraries
│   └── sentilyze_core/   # Core utilities
├── tests/                # Test suites
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test fixtures
├── scripts/             # Deployment scripts
├── tools/               # Utility scripts
└── docs/                # Documentation
```

## Adding New Features

### Adding a New API Endpoint

1. Define the route in `services/api/routes/`
2. Implement the handler in `services/api/handlers/`
3. Add request/response models in `services/api/models/`
4. Write tests in `tests/unit/api/`
5. Update API documentation

### Adding a Database Migration

```bash
# Create a new migration file
python tools/migrate-db.py --environment local create add_feature_x

# Edit the generated file in migrations/

# Test the migration
python tools/migrate-db.py --environment local migrate
```

### Adding Environment Variables

1. Add to configuration in `services/shared/sentilyze_core/config/`
2. Document in `QUICKSTART.md`
3. Add to deployment scripts if needed
4. Update `.env.example` if applicable

## Review Process

All submissions require review. We use GitHub pull requests for this purpose:

1. **Automated checks** must pass (tests, linting, etc.)
2. **Code review** by at least one maintainer
3. **Approval** from a maintainer
4. **Merge** to main branch

## Documentation

- Update `README.md` if you change major functionality
- Update `QUICKSTART.md` for user-facing changes
- Add docstrings to all public functions and classes
- Update API documentation in `/docs/api`

## Performance Considerations

- Profile your changes if they affect performance
- Consider caching for expensive operations
- Optimize database queries
- Use async operations where appropriate

## Security

- Never commit secrets or credentials
- Use Secret Manager for sensitive data
- Follow security best practices
- Report security issues privately

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Create an issue with the bug template
- **Feature requests**: Create an issue with the feature template

## Attribution

Contributors will be acknowledged in our `CONTRIBUTORS.md` file and release notes.

Thank you for contributing to Sentilyze!
