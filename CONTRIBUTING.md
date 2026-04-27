# Contributing

Contributions are welcome. Here's how to get started.

## Development setup

```bash
git clone https://github.com/<your-fork>/aws-lambda-chromium-playwright-python.git
cd aws-lambda-chromium-playwright-python
make build    # builds the Docker image
make test     # runs smoke tests (requires internet)
```

## Making changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Test locally with `make test`
4. Commit with a clear message describing what changed and why
5. Open a pull request

## Code style

- Python: no linter enforced, but keep it readable and consistent with existing code
- Dockerfile: one logical operation per `RUN`, ordered by change frequency
- Documentation: update README.md if your change affects usage

## What to contribute

- Bug fixes
- New example scripts in `examples/`
- Documentation improvements
- Performance optimizations (with benchmark data)
- Integration patterns for ARCHITECTURE.md

## What to avoid

- Adding dependencies to `requirements.txt` unless essential
- Changing the handler's event schema (breaking change)
- Increasing the Docker image size without justification
