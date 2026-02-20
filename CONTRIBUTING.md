# Contributing to Nexxi

Thank you for your interest in contributing to Nexxi! 🎉

## Development Setup

```bash
git clone https://github.com/your-org/nexxi.git
cd nexxi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your values
```

## Code Standards

- **Style**: `black` + `ruff` — run `black app/ tests/` before committing
- **Types**: All functions must have type hints — run `mypy app/`
- **Docs**: All public functions must have docstrings
- **Tests**: New features must include unit tests

## Pull Request Checklist

- [ ] Tests pass: `pytest tests/unit/ -v`
- [ ] No lint errors: `ruff check app/` and `black --check app/`
- [ ] No type errors: `mypy app/ --ignore-missing-imports`
- [ ] No hardcoded credentials
- [ ] Docstrings on all new public functions

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add streaming endpoint
fix: correct sliding window off-by-one
docs: update API reference
test: add jailbreak detection tests
chore: bump langchain to 0.2.1
```

## Reporting Issues

Open a GitHub Issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Python version and OS
- **Never include real API keys or tokens in issues**
