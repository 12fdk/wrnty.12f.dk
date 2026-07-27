/* wrnty — header state, mobile nav, scroll reveals.
   No dependencies. Smooth scrolling is handled in CSS (scroll-behavior). */

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Reveal elements as they enter the viewport.
function setupScrollReveals() {
  const items = document.querySelectorAll('.fade-in');
  if (!items.length) return;

  if (reduceMotion || !('IntersectionObserver' in window)) {
    items.forEach(el => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  items.forEach(el => observer.observe(el));
}

// Border + stronger blur once the page is scrolled off the top.
function setupHeaderState() {
  const header = document.getElementById('site-header');
  if (!header) return;

  const update = () => header.classList.toggle('is-stuck', window.scrollY > 8);
  update();
  window.addEventListener('scroll', update, { passive: true });
}

// Hamburger menu below 768px.
function setupMobileNav() {
  const toggle = document.getElementById('nav-toggle');
  const nav = document.getElementById('nav');
  if (!toggle || !nav) return;

  const close = () => {
    nav.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  };

  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });

  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', close));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('is-open')) {
      close();
      toggle.focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupScrollReveals();
  setupHeaderState();
  setupMobileNav();
});
