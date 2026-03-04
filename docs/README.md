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
├── 404.html                # Custom 404 error page
├── robots.txt              # Search engine directives
├── sitemap.xml             # Sitemap for SEO
├── css/
│   └── style.css          # Stylesheet
├── js/
│   └── main.js            # JavaScript functionality
└── README.md              # This file
```

## Local Development

To preview the documentation site locally:

```bash
cd docs
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

> Use a local server rather than opening HTML files directly — browsers block CDN scripts (syntax highlighting) on `file://` URLs due to CORS restrictions.

If port 8000 is already in use, pick any other port:

```bash
python -m http.server 8080
```

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
- **CSS3**: Custom properties, responsive design, dark mode
- **JavaScript**: Theme toggle, mobile nav, code copy buttons, scroll-to-top
- **highlight.js**: Syntax highlighting (loaded from CDN)
- **GitHub Pages**: Hosting and deployment

No build step required — the site is plain static HTML.

## Key Features

- **Responsive design**: Mobile-friendly layout
- **Dark mode**: System-aware, toggle persisted via localStorage
- **Syntax highlighting**: Via highlight.js (GitHub Dark theme)
- **Code copy buttons**: One-click copy on all code blocks
- **Accessible**: Skip links, ARIA labels, keyboard navigation, focus indicators
- **SEO**: Canonical URLs, Open Graph tags, sitemap, robots.txt

## Contributing

To contribute to the documentation:

1. Fork the repository
2. Create a feature branch
3. Make your changes in the `docs/` directory
4. Test locally with `python -m http.server 8000`
5. Submit a pull request

## Support

For questions or issues with the documentation:

- Open an issue on GitHub
- Check existing documentation for answers
- Refer to the CLI help: `hxc --help`

## License

The documentation is part of the HoxCore project and follows the same license terms.