const HXC_VERSION = '0.1.8';

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.nav-version').forEach(el => { el.textContent = 'v' + HXC_VERSION; });
  document.querySelectorAll('.footer-version').forEach(el => { el.textContent = 'v' + HXC_VERSION; });
  document.querySelectorAll('.hero-version').forEach(el => { el.textContent = 'v' + HXC_VERSION; });
});