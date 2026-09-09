// resuMe landing — reveal on scroll. No deps, no telemetry (privacy promise).
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

  // Demo (lazy por preload="none"): comeca a tocar quando entra na viewport.
  var demo = document.querySelector('#demo video');
  if (demo && 'IntersectionObserver' in window) {
    var dio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          demo.preload = 'metadata';
          demo.play().catch(function () {});
          dio.unobserve(e.target);
        }
      });
    }, { threshold: 0.3 });
    dio.observe(demo);
  }

  // V2: video de fundo — respeitar reduced-motion + parallax leve (so desktop).
  var bg = document.querySelector('.hero-bg');
  var bgVideo = bg ? bg.querySelector('video') : null;
  if (bgVideo && reduce) {
    bgVideo.pause();
    bgVideo.removeAttribute('autoplay');
    bgVideo.removeAttribute('src');
    bgVideo.load(); // libera banda; o poster assume
  } else if (bgVideo && !window.matchMedia('(pointer: coarse)').matches) {
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var y = Math.min(window.scrollY, window.innerHeight);
        bg.style.transform = 'translateY(' + (y * 0.25) + 'px)';
        ticking = false;
      });
    }, { passive: true });
  }
})();
