/* HoxCore Docs — main.js */
(function () {
  'use strict';

  /* ── Helpers ─────────────────────────────────── */
  function qs(sel, ctx)  { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  /* ── Theme (dark / light) ────────────────────── */
  function initTheme() {
    const btn = qs('.theme-toggle');
    const root = document.documentElement;

    // Restore saved preference or fall back to OS
    const saved = localStorage.getItem('hxc-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (saved === 'dark' || (!saved && prefersDark)) root.classList.add('dark');

    if (!btn) return;
    btn.addEventListener('click', () => {
      const isDark = root.classList.toggle('dark');
      localStorage.setItem('hxc-theme', isDark ? 'dark' : 'light');
      btn.setAttribute('aria-pressed', String(isDark));
    });
    btn.setAttribute('aria-pressed', String(root.classList.contains('dark')));
  }

  /* ── Mobile nav ──────────────────────────────── */
  function initMobileNav() {
    const toggle = qs('.nav-toggle');
    const menu   = qs('.nav-menu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });

    // Close on outside click
    document.addEventListener('click', e => {
      if (!toggle.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    // Close on Escape
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── Smooth scroll for in-page anchors ───────── */
  function initSmoothScroll() {
    const navbarH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--navbar-h')) || 64;
    document.addEventListener('click', e => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute('href').slice(1);
      const target = id ? document.getElementById(id) : null;
      if (!target) return;
      e.preventDefault();
      const top = target.getBoundingClientRect().top + window.scrollY - navbarH - 16;
      window.scrollTo({ top, behavior: 'smooth' });
      history.pushState(null, '', '#' + id);
    });
  }

  /* ── Active sidebar link on scroll ──────────── */
  function initActiveSidebar() {
    const links    = qsa('.sidebar-nav a[href^="#"]');
    const sections = links
      .map(a => document.getElementById(a.getAttribute('href').slice(1)))
      .filter(Boolean);

    if (!sections.length) return;

    const navbarH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--navbar-h')) || 64;
    let ticking = false;

    function update() {
      const scrollY = window.scrollY + navbarH + 24;
      let current = sections[0];
      for (const s of sections) {
        if (s.offsetTop <= scrollY) current = s;
      }
      links.forEach(a => {
        const active = a.getAttribute('href') === '#' + current.id;
        a.classList.toggle('active', active);
      });
    }

    window.addEventListener('scroll', () => {
      if (!ticking) { requestAnimationFrame(() => { update(); ticking = false; }); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ── Code copy buttons ───────────────────────── */
  function initCopyButtons() {
    const COPY_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
    const CHECK_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;

    qsa('pre').forEach(pre => {
      const code = pre.querySelector('code');
      if (!code) return;

      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.setAttribute('aria-label', 'Copy code');
      btn.innerHTML = COPY_ICON + '<span>Copy</span>';

      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(code.innerText);
          btn.classList.add('copied');
          btn.innerHTML = CHECK_ICON + '<span>Copied!</span>';
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = COPY_ICON + '<span>Copy</span>';
          }, 2000);
        } catch {
          btn.querySelector('span').textContent = 'Error';
          setTimeout(() => { btn.querySelector('span').textContent = 'Copy'; }, 1500);
        }
      });

      pre.appendChild(btn);
    });
  }

  /* ── Hero install copy button ────────────────── */
  function initHeroInstallCopy() {
    const btn = qs('.hero-install-copy');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const text = qs('.hero-install .cmd')?.textContent || 'pip install hoxcore';
      navigator.clipboard.writeText(text).catch(() => {});
      const icon = btn.querySelector('svg');
      if (icon) {
        icon.style.color = '#059669';
        setTimeout(() => { icon.style.color = ''; }, 1500);
      }
    });
  }

  /* ── Scroll to top button ─────────────────────── */
  function initScrollTop() {
    const btn = qs('.scroll-top');
    if (!btn) return;

    window.addEventListener('scroll', () => {
      btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  /* ── Sidebar mobile toggle ───────────────────── */
  function initSidebarToggle() {
    const toggle  = qs('.sidebar-toggle');
    const sidebar = qs('.doc-sidebar');
    if (!toggle || !sidebar) return;
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  /* ── External links ─────────────────────────── */
  function initExternalLinks() {
    qsa('a[href^="http"]').forEach(a => {
      if (a.hostname === location.hostname) return;
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener noreferrer');
    });
  }

  /* ── Current year in footer ──────────────────── */
  function initFooterYear() {
    qsa('.footer-year').forEach(el => { el.textContent = new Date().getFullYear(); });
  }

  /* ── Init ────────────────────────────────────── */
  function init() {
    initTheme();
    initMobileNav();
    initSmoothScroll();
    initActiveSidebar();
    initCopyButtons();
    initHeroInstallCopy();
    initScrollTop();
    initSidebarToggle();
    initExternalLinks();
    initFooterYear();
    initVersion();
    document.body.classList.add('js-loaded');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();  // ← this fires immediately if DOM is already parsed
  }
  
})();