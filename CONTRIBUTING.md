# Contributing

## Getting Started

Get your environment set up per the [README](README.md).

## Workflow

- **Create a branch** (e.g., `feature/new-icons`, `fix/login-bug`, `docs/api-guide`)
- **Make your changes** and write tests
- **Validate locally**

```bash
make lint        # Format + lint backend and frontend
make test        # Run pytest + vitest
```

- **Commit** — pre-commit hooks run formatting, linting, and secret detection automatically
- **Push and open a Pull Request** against `main`
- **Wait for CI** — GitHub Actions runs tests, linting, and type checking
- **Merge** when CI passes (self-merge is fine)
