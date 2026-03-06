# Contributing to HoxCore

Thank you for your interest in contributing to HoxCore! To maintain our automated deployment standards and ensure registry integrity, please follow this guide.

## 1. Branching Strategy & CI/CD Workflow
HoxCore uses a structured branching model to manage automated releases:

* **`develop` Branch**: This is the primary integration branch. 
    * **Target all Pull Requests here.**
    * Pushing to this branch triggers `publish-develop.yml`, which runs the test suite and deploys a development build (e.g., `0.1.2.devN`) to [**TestPyPI**](https://test.pypi.org/project/hoxcore/).
* **`master` Branch**: This is the stable production branch.
    * Merging into `master` triggers `publish.yml`, which automatically increments the version, creates a GitHub Release/Tag, and publishes the official package to [**PyPI**](https://pypi.org/project/hoxcore/), and updates the version labels in the documentation site.
* **GitHub Pages**: Changes to the `docs/` folder on the `master` branch trigger `deploy-docs.yml` to update the project documentation site.

## 2. Local Development Setup
To set up your environment for development:

1. **Clone the repository**:

```bash
   git clone https://github.com/SDEscobedo/hoxcore
   cd hoxcore
   git checkout develop
```

2. **Create a virtual environment**:

```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
```
3. **Install in development mode**:
   pip install -e ".[dev]"

## 3. Testing
We use `pytest` for validation. Before submitting a PR, ensure all tests pass locally:

```bash
pytest
```

## The CI pipeline will also run these tests on Python 3.11 as a requirement for deployment.

## 4. Pull Request Process
Create a feature branch from develop (e.g., feature/your-feature-name).

Ensure your code follows the project's style (run black and isort).

Open your Pull Request against the develop branch.

Once the PR is merged, you can verify your changes by installing the dev-build from TestPyPI.

## 5. Adding New Commands
To add a new CLI command to hxc:

Create a new file in src/hxc/commands/.

Define a class inheriting from BaseCommand.

Use the @register_command decorator.

Implement register_subparser and execute methods.

## 6. Security & Conduct
Security: If you find a vulnerability, please do not open a public issue. Instead refer to our [security policy](SECURITY.md).

Conduct: Be respectful. We follow standard Contributor Covenant expectations.
