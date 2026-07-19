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
})();
