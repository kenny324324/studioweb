/* Kenny Studio — AdSense 安全載入器。
 * 頁面以 <div data-ad-unit="area"></div> 標記版位；只有當
 * assets/ads-config.js 中對應 slot 有真實值時才建立 <ins> 並載入
 * AdSense library。缺值時移除版位節點，不保留空白框、不載入外部 script。
 */
(function () {
  'use strict';
  var cfg = window.KENNY_ADS;
  var units = document.querySelectorAll('[data-ad-unit]');
  if (!units.length) return;

  var hasAny = false;
  units.forEach(function (el) {
    var key = el.getAttribute('data-ad-unit');
    var slot = cfg && cfg.slots ? cfg.slots[key] : '';
    if (!cfg || !cfg.client || !slot) {
      el.remove();
      return;
    }
    hasAny = true;
    var ins = document.createElement('ins');
    ins.className = 'adsbygoogle';
    ins.style.display = 'block';
    ins.setAttribute('data-ad-client', cfg.client);
    ins.setAttribute('data-ad-slot', slot);
    ins.setAttribute('data-ad-format', el.getAttribute('data-ad-format') || 'auto');
    ins.setAttribute('data-full-width-responsive', 'true');
    el.appendChild(ins);
    (window.adsbygoogle = window.adsbygoogle || []).push({});
  });

  if (hasAny && !document.querySelector('script[src*="adsbygoogle.js"]')) {
    var s = document.createElement('script');
    s.async = true;
    s.crossOrigin = 'anonymous';
    s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + cfg.client;
    document.head.appendChild(s);
  }
})();
