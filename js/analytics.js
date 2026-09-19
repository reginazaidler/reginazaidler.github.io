(function () {
  'use strict';

  var GA_ID = 'G-EM8SYH542C';
  var startedAt = Date.now();
  var maxScroll = 0;
  var sentScroll = {};
  var formStarted = new WeakSet();
  var youtubePlayers = new WeakMap();

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };

  function analyticsAllowed() {
    try {
      var consent = JSON.parse(localStorage.getItem('vainzof_cookie_consent_v1') || 'null');
      return !!(consent && consent.analytics === true);
    } catch (e) { return false; }
  }

  if (!analyticsAllowed()) {
    window.addEventListener('vainzof:consent', function (event) {
      if (event.detail && event.detail.analytics) location.reload();
    }, { once: true });
    return;
  }

  function hasGaConfig() {
    return window.dataLayer.some(function (item) {
      return item && item[0] === 'config' && item[1] === GA_ID;
    });
  }

  if (!document.querySelector('script[src*="googletagmanager.com/gtag/js"]')) {
    var gaScript = document.createElement('script');
    gaScript.async = true;
    gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA_ID);
    document.head.appendChild(gaScript);
  }

  if (!hasGaConfig()) {
    window.gtag('js', new Date());
    window.gtag('config', GA_ID, {
      anonymize_ip: true,
      allow_google_signals: false,
      send_page_view: true
    });
  }

  function sendEvent(name, params) {
    var payload = params || {};
    payload.page_path = window.location.pathname;
    payload.page_title = document.title;
    window.gtag('event', name, payload);
  }

  function cleanText(element) {
    if (!element) return '';
    return (element.getAttribute('aria-label') || element.textContent || '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 100);
  }

  function classifyLink(anchor) {
    var href = anchor.getAttribute('href') || '';
    if (/^(https?:\/\/)?(wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)/i.test(href) || /whatsapp/i.test(href)) return 'whatsapp_click';
    if (/^tel:/i.test(href)) return 'phone_click';
    if (/^mailto:/i.test(href)) return 'email_click';

    try {
      var url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return 'outbound_click';
      if (url.pathname !== window.location.pathname) return 'internal_navigation';
    } catch (error) {
      return '';
    }
    return '';
  }

  document.addEventListener('click', function (event) {
    var videoCard = event.target.closest('[data-video-src]');
    if (videoCard) {
      var source = videoCard.getAttribute('data-video-src') || '';
      if (source && source.indexOf('enablejsapi=1') === -1) {
        source += (source.indexOf('?') === -1 ? '?' : '&') + 'enablejsapi=1&origin=' + encodeURIComponent(window.location.origin);
        videoCard.setAttribute('data-video-src', source);
      }
      sendEvent('video_open', {
        video_title: videoCard.getAttribute('data-video-title') || cleanText(videoCard)
      });
    }

    var anchor = event.target.closest('a[href]');
    if (!anchor) return;
    var eventName = classifyLink(anchor);
    if (!eventName) return;

    sendEvent(eventName, {
      link_url: anchor.href,
      link_text: cleanText(anchor),
      link_location: anchor.closest('header') ? 'header' : anchor.closest('footer') ? 'footer' : 'content'
    });
  }, true);

  document.addEventListener('focusin', function (event) {
    var form = event.target.closest('form');
    if (!form || formStarted.has(form)) return;
    formStarted.add(form);
    sendEvent('form_start', {
      form_id: form.id || form.getAttribute('name') || 'unnamed_form'
    });
  });

  document.addEventListener('submit', function (event) {
    var form = event.target;
    sendEvent('generate_lead', {
      form_id: form.id || form.getAttribute('name') || 'unnamed_form'
    });
  });

  function updateScrollDepth() {
    var available = document.documentElement.scrollHeight - window.innerHeight;
    var depth = available <= 0 ? 100 : Math.round((window.scrollY / available) * 100);
    maxScroll = Math.max(maxScroll, Math.min(100, depth));
    [25, 50, 75, 90, 100].forEach(function (threshold) {
      if (maxScroll >= threshold && !sentScroll[threshold]) {
        sentScroll[threshold] = true;
        sendEvent('scroll_depth', { percent_scrolled: threshold });
      }
    });
  }

  var scrollTimer;
  window.addEventListener('scroll', function () {
    window.clearTimeout(scrollTimer);
    scrollTimer = window.setTimeout(updateScrollDepth, 150);
  }, { passive: true });

  function normalizeYoutubeIframe(iframe, index) {
    if (!iframe.src || iframe.src.indexOf('youtube.com/embed/') === -1) return;
    if (iframe.dataset.analyticsTracked === 'true') return;
    iframe.dataset.analyticsTracked = 'true';
    var url = new URL(iframe.src);
    url.searchParams.set('enablejsapi', '1');
    url.searchParams.set('origin', window.location.origin);
    if (iframe.src !== url.toString()) iframe.src = url.toString();
    iframe.dataset.analyticsPlayerId = 'youtube-' + index;
    youtubePlayers.set(iframe.contentWindow, {
      iframe: iframe,
      title: iframe.title || 'YouTube video',
      played: false,
      progress: {}
    });
    iframe.addEventListener('load', function () {
      iframe.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: iframe.dataset.analyticsPlayerId }), '*');
    });
  }

  function scanYoutubeIframes() {
    document.querySelectorAll('iframe[src*="youtube.com/embed/"]').forEach(normalizeYoutubeIframe);
  }

  window.addEventListener('message', function (event) {
    var player = youtubePlayers.get(event.source);
    if (!player) return;
    var data = event.data;
    if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch (error) { return; }
    }
    if (!data || data.event !== 'infoDelivery' || !data.info) return;

    var state = data.info.playerState;
    if (state === 1 && !player.played) {
      player.played = true;
      sendEvent('video_start', { video_title: player.title, video_provider: 'youtube' });
    }
    if (state === 0) {
      sendEvent('video_complete', { video_title: player.title, video_provider: 'youtube' });
    }

    var duration = Number(data.info.duration);
    var current = Number(data.info.currentTime);
    if (!duration || !current) return;
    var percent = Math.floor((current / duration) * 100);
    [25, 50, 75].forEach(function (threshold) {
      if (percent >= threshold && !player.progress[threshold]) {
        player.progress[threshold] = true;
        sendEvent('video_progress', {
          video_title: player.title,
          video_provider: 'youtube',
          video_percent: threshold
        });
      }
    });
  });

  var observer = new MutationObserver(scanYoutubeIframes);

  function loadOptionalClarity() {
    var meta = document.querySelector('meta[name="clarity-project-id"]');
    var clarityId = meta && meta.content.trim();
    if (!clarityId) return;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', clarityId);
  }

  function initialize() {
    updateScrollDepth();
    scanYoutubeIframes();
    observer.observe(document.body, { childList: true, subtree: true });
    loadOptionalClarity();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

  window.addEventListener('pagehide', function () {
    updateScrollDepth();
    sendEvent('page_exit', {
      engagement_time_seconds: Math.max(1, Math.round((Date.now() - startedAt) / 1000)),
      max_scroll_percent: maxScroll,
      transport_type: 'beacon'
    });
  });
})();
