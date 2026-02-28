# HoxCore Documentation

This directory contains the documentation website for HoxCore, deployed via GitHub Pages.

## Overview

The HoxCore documentation site provides comprehensive guides, references, and examples for using the HoxCore project registry and initialization system.

## Structure

```
docs/
├── index.html              # Homepage
├── getting-started.html    # Getting started guide
├── core-concepts.html      # Core concepts and architecture
├── cli-reference.html      # CLI command reference
├── templates.html          # Template system documentation
├── integrations.html       # Integration guides
├── ai-features.html        # AI and LLM integration features
├── css/
│   └── style.css          # Stylesheet
├── js/
│   └── main.js            # JavaScript functionality
├── _config.yml            # Jekyll configuration
└── README.md              # This file
```

## Local Development

To preview the documentation site locally:

### Using Python's built-in server:

```bash
cd docs
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

### Using Jekyll (if installed):

```bash
cd docs
bundle exec jekyll serve
```

Then open `http://localhost:4000` in your browser.

## Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch. The deployment is handled by the GitHub Actions workflow defined in `.github/workflows/deploy-docs.yml`.

### Manual Deployment

If you need to manually deploy:

1. Ensure all changes are committed
2. Push to the main branch
3. GitHub Actions will automatically build and deploy

## Content Guidelines

When contributing to the documentation:

1. **Clarity**: Write clear, concise explanations
2. **Examples**: Include practical examples for all features
3. **Consistency**: Follow the existing structure and style
4. **Accuracy**: Ensure all code examples are tested and working
5. **Completeness**: Cover all aspects of the feature being documented

## Technology Stack

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with responsive design
- **JavaScript**: Interactive features and navigation
- **Jekyll**: Static site generation (GitHub Pages compatible)
- **GitHub Pages**: Hosting and deployment

## Key Features

The documentation site includes:

- **Responsive Design**: Mobile-friendly layout
- **Search Functionality**: Quick access to documentation
- **Code Highlighting**: Syntax-highlighted examples
- **Interactive Navigation**: Easy browsing between sections
- **Dark Mode Support**: Comfortable reading in any environment

## Contributing

To contribute to the documentation:

1. Fork the repository
2. Create a feature branch
3. Make your changes in the `docs/` directory
4. Test locally
5. Submit a pull request

## Support

For questions or issues with the documentation:

- Open an issue on GitHub
- Check existing documentation for answers
- Refer to the CLI help: `hxc --help`

## License

The documentation is part of the HoxCore project and follows the same license terms.

---

**Note**: This documentation is separate from the CLI tool implementation and can be updated independently.
