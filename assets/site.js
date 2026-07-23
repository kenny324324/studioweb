/* Kenny Studio shared behaviour — screenshot rail 控制（漸進增強，無相依套件）。
   規範：不自動播放；支援 touch / pointer / keyboard 與單次點擊按鈕。 */
(function () {
  'use strict';

  function initRail(rail) {
    var track = rail.querySelector('.rail-track');
    if (!track) return;
    var slides = track.querySelectorAll('.rail-slide');
    if (!slides.length) return;

    var prev = rail.querySelector('[data-rail-prev]');
    var next = rail.querySelector('[data-rail-next]');
    var status = rail.querySelector('[data-rail-status]');
    var total = slides.length;

    function slideStep() {
      var gap = 16;
      return slides[0].getBoundingClientRect().width + gap;
    }

    function currentIndex() {
      return Math.min(total - 1, Math.max(0, Math.round(track.scrollLeft / slideStep())));
    }

    function updateStatus() {
      if (status) status.textContent = (currentIndex() + 1) + ' / ' + total;
    }

    function scrollBySlides(n) {
      track.scrollBy({ left: n * slideStep(), behavior: 'smooth' });
    }

    if (prev) prev.addEventListener('click', function () { scrollBySlides(-1); });
    if (next) next.addEventListener('click', function () { scrollBySlides(1); });

    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); scrollBySlides(1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); scrollBySlides(-1); }
    });

    var ticking = false;
    track.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { updateStatus(); ticking = false; });
    }, { passive: true });

    updateStatus();
  }

  document.querySelectorAll('.rail').forEach(initRail);

  /* 一次性區塊進場：第一次進入視窗時淡入上移，之後移除標記、不重播。
     reduced motion 或不支援 IntersectionObserver 時完全不啟用。 */
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches &&
      'IntersectionObserver' in window) {
    var targets = document.querySelectorAll(
      '.section-head, .product-card, .feature, .trust-item, .final-cta'
    );
    var byParent = new Map();
    targets.forEach(function (el) {
      var i = byParent.get(el.parentElement) || 0;
      byParent.set(el.parentElement, i + 1);
      el.style.setProperty('--reveal-delay', Math.min(i * 40, 120) + 'ms');
      el.setAttribute('data-reveal', '');
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        io.unobserve(el);
        el.classList.add('is-revealed');
        setTimeout(function () {
          el.removeAttribute('data-reveal');
          el.classList.remove('is-revealed');
          el.style.removeProperty('--reveal-delay');
        }, 600);
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -5% 0px' });
    targets.forEach(function (el) { io.observe(el); });
  }

  /* 首頁導覽底線跟隨:捲到 #apps 區塊時,aria-current 從 Home 移到 Apps；
     捲回上方時還原。其他頁面沒有 #apps,整段不啟用。 */
  var appsSection = document.getElementById('apps');
  var navLinks = document.querySelectorAll('.site-nav a');
  if (appsSection && navLinks.length) {
    var appsLink = null;
    var homeLink = null;
    navLinks.forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (href.indexOf('#apps') !== -1) appsLink = a;
      else if (a.getAttribute('aria-current') === 'page') homeLink = a;
    });
    if (appsLink && homeLink) {
      var navTicking = false;
      var updateNav = function () {
        var rect = appsSection.getBoundingClientRect();
        var mark = window.innerHeight * 0.4;
        var inApps = rect.top <= mark && rect.bottom > mark;
        if (inApps) {
          appsLink.setAttribute('aria-current', 'page');
          homeLink.removeAttribute('aria-current');
        } else {
          homeLink.setAttribute('aria-current', 'page');
          appsLink.removeAttribute('aria-current');
        }
      };
      var onScroll = function () {
        if (navTicking) return;
        navTicking = true;
        requestAnimationFrame(function () { updateNav(); navTicking = false; });
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onScroll, { passive: true });
      updateNav();
    }
  }

  /* 返回上一頁:有同源瀏覽紀錄時走 history.back(),
     直接空降（無紀錄或從站外來）則照 href 回首頁。 */
  document.querySelectorAll('a[data-back]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var sameOrigin = false;
      try {
        sameOrigin = !!document.referrer &&
          new URL(document.referrer).origin === window.location.origin;
      } catch (err) { /* referrer 不可解析就走 fallback */ }
      if (window.history.length > 1 && sameOrigin) {
        e.preventDefault();
        window.history.back();
      }
    });
  });
})();
