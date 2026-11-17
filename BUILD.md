# Build Instructions for Antigravity CLI

This document describes how to build, test, and maintain the Antigravity CLI project.

## Overview

Antigravity CLI is a fork of [verialabs/ctf-agent](https://github.com/verialabs/ctf-agent) that maintains the original solver architecture while establishing a new, independent CLI interface.

## Prerequisites

- Python 3.14+
- Docker
- `uv` (Fast Python package manager)
- For Codex coordinator: `codex` CLI
- For Claude coordinator: `claude` CLI (bundled with claude-agent-sdk)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/verialabs/ctf-agent.git ctf-agent-src
cd ctf-agent-src
cp -r backend antigravity-cli/backend
cp -r sandbox antigravity-cli/sandbox
cp pull_challenges.py antigravity-cli/
cp .env.example antigravity-cli/
cd antigravity-cli
```

### 2. Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate (Windows: .venv/Scripts/activate)
# For macOS/Linux: source .venv/bin/activate

# Install dependencies with uv
uv sync

# Install the package in editable mode
uv pip install -e .
```

### 3. Build the Package

```bash
# Build wheel
uv build --wheel

# Build source distribution
uv build --sdist

# Or use the build helper script
python build.py wheel
```

### 4. Build Docker Sandbox

```bash
# Build the sandbox image
docker build -f sandbox/Dockerfile.sandbox -t ctf-sandbox .

# Or use build helper
python build.py sandbox
```

## Development Commands

The `build.py` script provides several useful commands:

```bash
# Install dependencies and package
python build.py install

# Run tests
python build.py test

# Build wheel
python build.py wheel

# Build source distribution
python build.py sdist

# Build Docker sandbox
python build.py sandbox

# Clean build artifacts
cpython build.py clean
```

## Running the CLI

### Basic Usage

```bash
# Show help
antigravity --help

# Full coordinator (continuous until Ctrl+C)
antigravity --ctfd-url https://ctf.example.com --ctfd-token ctfd_...

# Solve a single challenge directory
antigravity --challenge ./challenges/example

# Dry run (don't submit flags)
antigravity --no-submit
```

### Coordinator Backends

```bash
# Claude SDK coordinator (default)
antigravity --coordinator claude ...

# Codex coordinator (GPT-5.4 via JSON-RPC)
antigravity --coordinator codex ...
```

## Testing

Run the test suite:

```bash
uv run pytest -v
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your API keys and CTFd token
```

Environment variables (overrides .env):

- `CTFD_URL` - CTFd instance URL
- `CTFD_TOKEN` - CTFd API token
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Gemini API key

### Command Line Options

All settings can also be passed as CLI flags, which override environment variables.

See `antigravity --help` for the complete list of options.

## Project Structure

```
antigravity-cli/
├── backend/                    # Solver backend (copied from verialabs/ctf-agent)
│   ├── agents/                # Coordinator and solver implementations
│   ├── tools/                 # SDK-agnostic tool wrappers
│   ├── config.py              # Pydantic settings
│   ├── cli.py                 # Click CLI entry point
│   └── ...
├── sandbox/                    # Docker sandbox environment
│   ├── Dockerfile.sandbox     # Sandbox image
│   └── sandbox-tools.txt     # Tools reference
├── .env.example              # Environment template
├── .gitignore               # File ignore patterns
├── LICENSE                  # MIT license
├── README.md                # Project documentation
├── pyproject.toml          # Package configuration
├── build.py                # Build helper script
└── CHANGES_SUMMARY.md      # Changes summary
```

## Package Information

- **Name**: antigravity
- **Version**: 1.0.0
- **Description**: Antigravity CLI — autonomous CTF solver swarm (fork of verialabs/ctf-agent)
- **Entry Points**: `antigravity` (aliases: `nag`)

## License

MIT License - See `LICENSE` file for details.

## Acknowledgements

- Based on verialabs/ctf-agent — the tool that solved all 52/52 challenges and won 1st place at BSidesSF 2026 CTF
- Built by forking the original project to create a standalone CLI tool

## Local Development Notes

### To-Do List

1. Test with a real CTFd instance
2. Validate flag submission workflow
3. Document any changes from original verialabs/ctf-agent
4. Add more comprehensive testing

### Quick Testing

Create a simple test challenge to verify basic functionality:

```bash
mkdir -p test-challenges/hello-world/distfiles
echo "Test challenge" > test-challenges/hello-world/metadata.yml
```

## Future Work

1. Add comprehensive CI/CD pipeline
2. Document solver architecture and algorithms
3. Add performance benchmarks
4. Create demo videos or tutorials

## Troubleshooting

### Common Issues

**Python 3.14+ Requirement**

If you encounter Python version issues, ensure you have Python 3.14+:

```bash
python3 --version  # Should show Python 3.14.x
```

**uv Installation**

If `uv` is not available:

```bash
# macOS/river
curl -LsSf https://astral.sh/uv/install.sh | sh

# Other platforms: https://github.com/astral-sh/uv
```

**Docker Sandbox Build**

If the sandbox image fails to build, check your Docker installation:

```bash
docker --version  # Should show Docker version
```

**Package Installation**

If package installation fails:

```bash
# Try with system Python (not recommended)
uv pip install --system --editable .venv
```

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Run `uv sync` periodically
2. **Run Tests**: Regular test runs with `uv run pytest`
3. **Update Documentation**: Keep README, examples, and documentation current

### Version Management

- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update `pyproject.toml` when releasing new versions
- Test with all dependencies before releasing

## Contact

For questions, issues, or contributions:

- Repository: This project (antigravity-cli)
- Based on: verialabs/ctf-agent

## Support

This project is based on proven technology that has successfully solved all 52/52 challenges in a professional CTF competition. While maintaining the original solver capabilities, this fork provides a clean, standalone CLI interface for developers and users interested in autonomous CTF solving.