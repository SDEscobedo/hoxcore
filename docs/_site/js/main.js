/**
 * HoxCore Documentation - Main JavaScript
 * Handles interactive features, navigation, and UI enhancements
 */

(function() {
    'use strict';

    // ============================================
    // Mobile Navigation Toggle
    // ============================================
    function initMobileNav() {
        const navToggle = document.querySelector('.nav-toggle');
        const navMenu = document.querySelector('.nav-menu');

        if (navToggle && navMenu) {
            navToggle.addEventListener('click', function() {
                navMenu.classList.toggle('active');
                navToggle.classList.toggle('active');
                
                // Update ARIA attribute
                const isExpanded = navMenu.classList.contains('active');
                navToggle.setAttribute('aria-expanded', isExpanded);
            });

            // Close menu when clicking outside
            document.addEventListener('click', function(event) {
                const isClickInsideNav = navToggle.contains(event.target) || navMenu.contains(event.target);
                if (!isClickInsideNav && navMenu.classList.contains('active')) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                    navToggle.setAttribute('aria-expanded', 'false');
                }
            });

            // Close menu when pressing Escape
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape' && navMenu.classList.contains('active')) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                    navToggle.setAttribute('aria-expanded', 'false');
                }
            });
        }
    }

    // ============================================
    // Smooth Scrolling for Anchor Links
    // ============================================
    function initSmoothScroll() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                
                // Skip if it's just "#"
                if (href === '#') {
                    e.preventDefault();
                    return;
                }

                const target = document.querySelector(href);
                
                if (target) {
                    e.preventDefault();
                    
                    // Get header height for offset
                    const header = document.querySelector('.navbar');
                    const headerHeight = header ? header.offsetHeight : 0;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Update URL without jumping
                    history.pushState(null, null, href);

                    // Close mobile menu if open
                    const navMenu = document.querySelector('.nav-menu');
                    const navToggle = document.querySelector('.nav-toggle');
                    if (navMenu && navMenu.classList.contains('active')) {
                        navMenu.classList.remove('active');
                        navToggle.classList.remove('active');
                        navToggle.setAttribute('aria-expanded', 'false');
                    }
                }
            });
        });
    }

    // ============================================
    // Active Section Highlighting in Sidebar
    // ============================================
    function initActiveSection() {
        const sections = document.querySelectorAll('.doc-section[id]');
        const navLinks = document.querySelectorAll('.doc-nav a[href^="#"]');

        if (sections.length === 0 || navLinks.length === 0) {
            return;
        }

        function updateActiveLink() {
            const scrollPosition = window.scrollY + 100; // Offset for header

            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.offsetHeight;
                const sectionId = section.getAttribute('id');

                if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        }

        // Throttle scroll event
        let ticking = false;
        window.addEventListener('scroll', function() {
            if (!ticking) {
                window.requestAnimationFrame(function() {
                    updateActiveLink();
                    ticking = false;
                });
                ticking = true;
            }
        });

        // Initial check
        updateActiveLink();
    }

    // ============================================
    // Copy Code Button
    // ============================================
    function initCodeCopy() {
        const codeBlocks = document.querySelectorAll('pre code');

        codeBlocks.forEach(block => {
            const pre = block.parentElement;
            
            // Create copy button
            const button = document.createElement('button');
            button.className = 'copy-code-btn';
            button.textContent = 'Copy';
            button.setAttribute('aria-label', 'Copy code to clipboard');

            // Add button to pre element
            pre.style.position = 'relative';
            pre.appendChild(button);

            // Copy functionality
            button.addEventListener('click', async function() {
                const code = block.textContent;

                try {
                    await navigator.clipboard.writeText(code);
                    button.textContent = 'Copied!';
                    button.classList.add('copied');

                    setTimeout(() => {
                        button.textContent = 'Copy';
                        button.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy code:', err);
                    button.textContent = 'Failed';
                    
                    setTimeout(() => {
                        button.textContent = 'Copy';
                    }, 2000);
                }
            });
        });
    }

    // ============================================
    // Dark Mode Toggle
    // ============================================
    function initDarkMode() {
        const darkModeToggle = document.querySelector('.dark-mode-toggle');
        
        if (!darkModeToggle) {
            return;
        }

        // Check for saved preference or system preference
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
            document.documentElement.classList.add('dark-mode');
            darkModeToggle.setAttribute('aria-pressed', 'true');
        }

        // Toggle dark mode
        darkModeToggle.addEventListener('click', function() {
            document.documentElement.classList.toggle('dark-mode');
            const isDark = document.documentElement.classList.contains('dark-mode');
            
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            darkModeToggle.setAttribute('aria-pressed', isDark);
        });
    }

    // ============================================
    // Search Functionality
    // ============================================
    function initSearch() {
        const searchInput = document.querySelector('.search-input');
        const searchResults = document.querySelector('.search-results');

        if (!searchInput || !searchResults) {
            return;
        }

        let searchIndex = [];

        // Build search index from page content
        function buildSearchIndex() {
            const sections = document.querySelectorAll('.doc-section');
            
            sections.forEach(section => {
                const id = section.getAttribute('id');
                const title = section.querySelector('h2, h3')?.textContent || '';
                const content = section.textContent || '';

                searchIndex.push({
                    id: id,
                    title: title,
                    content: content.toLowerCase(),
                    element: section
                });
            });
        }

        // Perform search
        function performSearch(query) {
            if (!query || query.length < 2) {
                searchResults.innerHTML = '';
                searchResults.style.display = 'none';
                return;
            }

            const results = searchIndex.filter(item => 
                item.content.includes(query.toLowerCase())
            ).slice(0, 5); // Limit to 5 results

            if (results.length === 0) {
                searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
                searchResults.style.display = 'block';
                return;
            }

            const resultsHTML = results.map(result => `
                <a href="#${result.id}" class="search-result-item">
                    <strong>${result.title}</strong>
                </a>
            `).join('');

            searchResults.innerHTML = resultsHTML;
            searchResults.style.display = 'block';
        }

        // Debounce search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });

        // Close search results when clicking outside
        document.addEventListener('click', function(event) {
            if (!searchInput.contains(event.target) && !searchResults.contains(event.target)) {
                searchResults.style.display = 'none';
            }
        });

        // Build index on load
        buildSearchIndex();
    }

    // ============================================
    // Table of Contents Generator
    // ============================================
    function initTableOfContents() {
        const tocContainer = document.querySelector('.auto-toc');
        
        if (!tocContainer) {
            return;
        }

        const headings = document.querySelectorAll('.doc-content h2, .doc-content h3');
        
        if (headings.length === 0) {
            return;
        }

        const tocList = document.createElement('ul');
        tocList.className = 'toc-list';

        headings.forEach(heading => {
            const level = heading.tagName.toLowerCase();
            const text = heading.textContent;
            const id = heading.getAttribute('id') || text.toLowerCase().replace(/\s+/g, '-');
            
            // Ensure heading has an ID
            if (!heading.getAttribute('id')) {
                heading.setAttribute('id', id);
            }

            const listItem = document.createElement('li');
            listItem.className = `toc-item toc-${level}`;
            
            const link = document.createElement('a');
            link.href = `#${id}`;
            link.textContent = text;
            
            listItem.appendChild(link);
            tocList.appendChild(listItem);
        });

        tocContainer.appendChild(tocList);
    }

    // ============================================
    // Scroll to Top Button
    // ============================================
    function initScrollToTop() {
        const scrollBtn = document.querySelector('.scroll-to-top');
        
        if (!scrollBtn) {
            return;
        }

        // Show/hide button based on scroll position
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        });

        // Scroll to top on click
        scrollBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ============================================
    // External Links
    // ============================================
    function initExternalLinks() {
        const links = document.querySelectorAll('a[href^="http"]');
        
        links.forEach(link => {
            // Skip if it's an internal link
            if (link.hostname === window.location.hostname) {
                return;
            }

            // Add external link attributes
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
            
            // Add visual indicator
            if (!link.querySelector('.external-icon')) {
                const icon = document.createElement('span');
                icon.className = 'external-icon';
                icon.setAttribute('aria-hidden', 'true');
                icon.textContent = ' ↗';
                link.appendChild(icon);
            }
        });
    }

    // ============================================
    // Print Styles
    // ============================================
    function initPrintStyles() {
        // Add print button if needed
        const printBtn = document.querySelector('.print-btn');
        
        if (printBtn) {
            printBtn.addEventListener('click', function() {
                window.print();
            });
        }
    }

    // ============================================
    // Keyboard Navigation
    // ============================================
    function initKeyboardNav() {
        document.addEventListener('keydown', function(event) {
            // Skip if user is typing in an input
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            // Navigate with arrow keys
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                const prevLink = document.querySelector('.prev-page');
                const nextLink = document.querySelector('.next-page');

                if (event.key === 'ArrowLeft' && prevLink) {
                    prevLink.click();
                } else if (event.key === 'ArrowRight' && nextLink) {
                    nextLink.click();
                }
            }
        });
    }

    // ============================================
    // Accessibility Enhancements
    // ============================================
    function initAccessibility() {
        // Add skip to content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);

        // Add main content ID if not present
        const mainContent = document.querySelector('main');
        if (mainContent && !mainContent.id) {
            mainContent.id = 'main-content';
        }

        // Improve focus visibility
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Tab') {
                document.body.classList.add('keyboard-nav');
            }
        });

        document.addEventListener('mousedown', function() {
            document.body.classList.remove('keyboard-nav');
        });
    }

    // ============================================
    // Performance Monitoring
    // ============================================
    function initPerformanceMonitoring() {
        if ('performance' in window) {
            window.addEventListener('load', function() {
                const perfData = window.performance.timing;
                const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
                
                // Log performance data (can be sent to analytics)
                console.log('Page load time:', pageLoadTime + 'ms');
            });
        }
    }

    // ============================================
    // Initialize All Features
    // ============================================
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Initialize all features
        initMobileNav();
        initSmoothScroll();
        initActiveSection();
        initCodeCopy();
        initDarkMode();
        initSearch();
        initTableOfContents();
        initScrollToTop();
        initExternalLinks();
        initPrintStyles();
        initKeyboardNav();
        initAccessibility();
        initPerformanceMonitoring();

        // Add loaded class to body
        document.body.classList.add('loaded');
    }

    // Start initialization
    init();

})();