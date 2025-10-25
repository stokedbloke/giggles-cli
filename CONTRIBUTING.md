# Contributing to Giggles

Thank you for your interest in contributing to Giggles! 🎭

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

- **Clear title and description** of the bug
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Screenshots or logs** if applicable

### Suggesting Features

Feature suggestions are welcome! Please include:

- **Clear description** of the proposed feature
- **Use case** and why it would be valuable
- **Potential implementation** approach (optional)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes** with clear, descriptive commit messages
4. **Test your changes** thoroughly
5. **Push to your fork**:
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request** on GitHub

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/giggles-cli.git
   cd giggles-cli
   ```

2. Set up the development environment:
   ```bash
   cd laughter-detector
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file (see `env.example`)

4. Run the application:
   ```bash
   python3 -m uvicorn src.main:app --reload
   ```

## Code Style

- **Python**: Follow PEP 8 style guide
- **JavaScript**: Use ES6+ features
- **Commits**: Use clear, descriptive commit messages
- **Comments**: Add comments for complex logic
- **Naming**: Use descriptive variable and function names

## Testing

Before submitting a PR:

- ✅ Test all new features
- ✅ Test existing functionality still works
- ✅ Check for linting errors
- ✅ Ensure no sensitive data is committed

## Commit Message Convention

Use clear, descriptive commit messages:

```
<type>: <description>

<optional body>

Examples:
fix: Resolve audio playback issue in day view
feat: Add laughter class filter functionality
docs: Update README with deployment instructions
refactor: Simplify authentication flow
```

## Code Review Process

1. All PRs require review before merging
2. Address review feedback promptly
3. Keep PRs focused and reasonably sized
4. Respond to comments and questions

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

Thank you for contributing! 🎉
