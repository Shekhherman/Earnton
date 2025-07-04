# Contributing to TON Reward Bot

Thank you for considering contributing to the TON Reward Bot project! Here's how you can help:

## Reporting Bugs

1. Search existing issues to avoid duplicates
2. Create a new issue with:
   - Clear title
   - Detailed description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

## Suggesting Enhancements

1. Search existing issues to avoid duplicates
2. Create a new issue with:
   - Clear title
   - Detailed description
   - Use case
   - Screenshots if applicable

## Setting Up Development Environment

1. Clone the repository:
```bash
git clone [your-repo-url]
cd ton-reward-bot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Development Guidelines

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Follow PEP 8 style guidelines
3. Write tests for new features
4. Update documentation
5. Commit your changes:
```bash
git add .
git commit -m "feat: your feature description"
```

6. Push to the branch:
```bash
git push origin feature/your-feature-name
```

7. Create a Pull Request

## Code Style

- Use black for code formatting
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions and classes
- Use descriptive variable names

## Testing

1. Run tests:
```bash
pytest
```

2. Run linters:
```bash
flake8
black .
isort .
```

## Security

If you find a security vulnerability, please:
1. Do NOT open a public issue
2. Email the maintainers directly
3. Include:
   - Description of the vulnerability
   - Impact
   - Steps to reproduce
   - Your contact information
