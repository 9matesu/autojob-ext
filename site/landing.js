// resuMe landing — reveal snap-in + reduced-motion. No deps, no telemetry.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var els = document.querySelectorAll('.reveal');
  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.15 });
    els.forEach(function (el) { io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add('in'); });
  }

  // Video de fundo: com reduced-motion, pausa e troca pelo poster (economiza banda tambem).
  var bg = document.querySelector('.hero-bg');
  var bgVideo = bg ? bg.querySelector('video') : null;
  if (bgVideo && reduce) {
    bgVideo.pause();
    bgVideo.removeAttribute('autoplay');
    bgVideo.removeAttribute('src');
    bgVideo.load(); // poster assume
  }
})();
