(function () {
  function isDrawerMenu(menu) {
    return !!menu && menu.classList.contains('mobile-drawer');
  }

  function setMenuState(menuBtn, mobileMenu, shouldOpen) {
    if (!menuBtn || !mobileMenu) return;

    if (isDrawerMenu(mobileMenu)) {
      mobileMenu.classList.toggle('is-open', shouldOpen);
    } else {
      mobileMenu.classList.toggle('hidden', !shouldOpen);
    }

    menuBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    document.body.classList.toggle('overflow-hidden', shouldOpen && isDrawerMenu(mobileMenu));
  }

  function isMenuOpen(menuBtn, mobileMenu) {
    if (!menuBtn || !mobileMenu) return false;
    if (isDrawerMenu(mobileMenu)) {
      return mobileMenu.classList.contains('is-open');
    }
    return !mobileMenu.classList.contains('hidden');
  }

  function initMobileMenu() {
    var menuBtn = document.getElementById('menuBtn');
    var mobileMenu = document.getElementById('mobileMenu');
    if (!menuBtn || !mobileMenu) return;

    if (!menuBtn.hasAttribute('aria-controls')) {
      menuBtn.setAttribute('aria-controls', 'mobileMenu');
    }
    if (!menuBtn.hasAttribute('aria-expanded')) {
      menuBtn.setAttribute('aria-expanded', 'false');
    }

    menuBtn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      var nextState = !isMenuOpen(menuBtn, mobileMenu);
      setMenuState(menuBtn, mobileMenu, nextState);
    }, true);

    mobileMenu.addEventListener('click', function (event) {
      var actionTarget = event.target.closest('a, button.mobile-contact-cta');
      if (!actionTarget) return;
      setMenuState(menuBtn, mobileMenu, false);
    });

    document.addEventListener('click', function (event) {
      if (!isMenuOpen(menuBtn, mobileMenu)) return;
      if (mobileMenu.contains(event.target) || menuBtn.contains(event.target)) return;
      setMenuState(menuBtn, mobileMenu, false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isMenuOpen(menuBtn, mobileMenu)) {
        setMenuState(menuBtn, mobileMenu, false);
      }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1024) {
        setMenuState(menuBtn, mobileMenu, false);
      }
    });
  }

  function initDesktopKnowledgeMenu() {
    var dropdown = document.querySelector('.nav-dropdown');
    if (!dropdown) return;

    var trigger = dropdown.querySelector('.nav-dropdown__trigger');
    var menu = dropdown.querySelector('.nav-dropdown__menu');
    if (!trigger || !menu) return;

    if (!menu.id) {
      menu.id = 'desktopKnowledgeMenu';
    }

    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', menu.id);
    trigger.setAttribute('aria-haspopup', 'true');

    function setOpenState(shouldOpen) {
      dropdown.classList.toggle('is-open', shouldOpen);
      trigger.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    }

    trigger.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      var isOpen = dropdown.classList.contains('is-open');
      setOpenState(!isOpen);
    });

    document.addEventListener('click', function (event) {
      if (!dropdown.contains(event.target)) {
        setOpenState(false);
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        setOpenState(false);
      }
    });
  }

  function removeSavingsCalculatorLinks() {
    document.querySelectorAll('a[href*="calculator.html"]').forEach(function (link) {
      var parentItem = link.closest('li');
      if (parentItem && parentItem.textContent.trim() === link.textContent.trim()) {
        parentItem.remove();
      } else {
        link.remove();
      }
    });
  }



  function ensureMobileContactActions() {
    var mobileMenu = document.getElementById('mobileMenu');
    if (!mobileMenu) return;

    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var phoneNumber = '0524520222';
    var phoneLabel = isRuPage ? 'Позвонить: 052-4520222' : 'התקשר עכשיו';
    var ctaLabel = isRuPage ? 'Связаться' : 'צור קשר';

    var callLink = mobileMenu.querySelector('a[href^="tel:"]');
    if (!callLink) {
      callLink = document.createElement('a');
      callLink.href = 'tel:' + phoneNumber;
      callLink.className = 'block font-bold text-slate-600 border-b pb-2';
      callLink.textContent = phoneLabel;
      mobileMenu.appendChild(callLink);
    }

    var contactBtn = mobileMenu.querySelector('.mobile-contact-cta');
    if (!contactBtn) {
      contactBtn = document.createElement('button');
      contactBtn.type = 'button';
      contactBtn.id = 'openContactMobile';
      contactBtn.className = 'mobile-contact-cta';
      contactBtn.textContent = ctaLabel;
      mobileMenu.appendChild(contactBtn);
    }
  }

  function initLanguageSwitcher() {
    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var desktopNav = document.querySelector('.site-nav');
    if (desktopNav && !desktopNav.querySelector('.language-switch')) {
      var desktopSwitch = document.createElement('a');
      desktopSwitch.href = isRuPage ? '/index.html' : '/ru/index.html';
      desktopSwitch.className = 'language-switch';
      desktopSwitch.setAttribute('lang', isRuPage ? 'he' : 'ru');
      desktopSwitch.setAttribute('hreflang', isRuPage ? 'he' : 'ru');
      desktopSwitch.textContent = isRuPage ? 'HE' : 'RU';
      desktopSwitch.setAttribute('aria-label', isRuPage ? 'Переключиться на иврит' : 'Переключиться на русский');
      var desktopCta = desktopNav.querySelector('.site-cta');
      if (desktopCta) {
        desktopNav.insertBefore(desktopSwitch, desktopCta);
      } else {
        desktopNav.appendChild(desktopSwitch);
      }
    }

    var mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu && !mobileMenu.querySelector('.mobile-language-switch')) {
      var mobileSwitch = document.createElement('a');
      mobileSwitch.href = isRuPage ? '/index.html' : '/ru/index.html';
      mobileSwitch.className = 'block font-bold text-slate-600 border-b pb-2 mobile-language-switch';
      mobileSwitch.setAttribute('lang', isRuPage ? 'he' : 'ru');
      mobileSwitch.setAttribute('hreflang', isRuPage ? 'he' : 'ru');
      mobileSwitch.textContent = isRuPage ? 'עברית' : 'Русский';
      mobileSwitch.setAttribute('aria-label', isRuPage ? 'Перейти на версию на иврите' : 'Перейти на русскую версию');

      var callLink = mobileMenu.querySelector('a[href^="tel:"]');
      if (callLink) {
        mobileMenu.insertBefore(mobileSwitch, callLink);
      } else {
        mobileMenu.appendChild(mobileSwitch);
      }
    }
  }


  function injectSkipLink() {
    var main = document.querySelector('main');
    if (!main) return;
    if (!main.id) main.id = 'main-content';
    if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1');
    var existing = document.querySelector('.skip-link, .sr-focusable');
    if (existing) {
      existing.href = '#' + main.id;
      return;
    }
    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var skip = document.createElement('a');
    skip.href = '#' + main.id;
    skip.className = 'skip-link';
    skip.textContent = isRuPage ? 'Перейти к основному содержанию' : 'דלג לתוכן הראשי';
    document.body.insertBefore(skip, document.body.firstChild);

  }

  function init() {
    injectSkipLink();
    removeSavingsCalculatorLinks();
    initMobileMenu();
    initDesktopKnowledgeMenu();
    ensureMobileContactActions();
    initLanguageSwitcher();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

(function () {
  if (window.__quietContactExperienceBound) return;
  window.__quietContactExperienceBound = true;

  function initQuietContactExperience() {
    if (window.location.pathname.indexOf('/ru/') === 0) return;

    document.querySelectorAll('header a[href^="tel:"]').forEach(function (link) {
      link.remove();
    });

    document.querySelectorAll('header .site-cta').forEach(function (button, index) {
      if (index > 0) {
        button.remove();
        return;
      }
      button.textContent = 'יצירת קשר';
    });

    var mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu) {
      mobileMenu.querySelectorAll('a[href^="tel:"]').forEach(function (link) {
        link.remove();
      });
      var mobileContact = mobileMenu.querySelector('.mobile-contact-cta');
      if (mobileContact) mobileContact.textContent = 'יצירת קשר';
    }

    var isHomePage = /\/(?:index\.html)?$/.test(window.location.pathname);
    if (isHomePage) {
      var heroActions = document.querySelector('.home-hero .hero-actions');
      if (heroActions) {
        var actions = Array.prototype.slice.call(heroActions.querySelectorAll('a, button'));
        actions.forEach(function (action, index) {
          if (index > 0) action.remove();
        });
        if (actions[0]) actions[0].textContent = 'יצירת קשר';
      }
      var heroHighlight = document.querySelector('.home-hero__highlight');
      if (heroHighlight) heroHighlight.remove();
    }

    document.querySelectorAll('.media-whatsapp-float, .mobile-sticky-cta, .desktop-sticky-cta').forEach(function (node) {
      node.remove();
    });

    if (!document.querySelector('.whatsapp-float')) {
      var whatsapp = document.createElement('a');
      whatsapp.href = 'https://wa.me/972524520222';
      whatsapp.className = 'whatsapp-float';
      whatsapp.target = '_blank';
      whatsapp.rel = 'noopener noreferrer';
      whatsapp.setAttribute('aria-label', 'שליחת הודעה ב-WhatsApp');
      whatsapp.setAttribute('title', 'WhatsApp');
      whatsapp.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347M12.05 21.785a9.87 9.87 0 0 1-5.034-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.886 9.884M20.463 3.488A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>';
      document.body.appendChild(whatsapp);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initQuietContactExperience);
  } else {
    initQuietContactExperience();
  }
})();

(function () {
  if (window.__mobileContactActionBound) return;
  window.__mobileContactActionBound = true;

  document.addEventListener('click', function (event) {
    var contactButton = event.target.closest('button.mobile-contact-cta');
    if (!contactButton) return;

    event.preventDefault();
    event.stopImmediatePropagation();
window.location.assign('https://wa.me/972524520222');
  }, true);
})();
(function () {
  function isDrawerMenu(menu) {
    return !!menu && menu.classList.contains('mobile-drawer');
  }

  function setMenuState(menuBtn, mobileMenu, shouldOpen) {
    if (!menuBtn || !mobileMenu) return;

    if (isDrawerMenu(mobileMenu)) {
      mobileMenu.classList.toggle('is-open', shouldOpen);
    } else {
      mobileMenu.classList.toggle('hidden', !shouldOpen);
    }

    menuBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    document.body.classList.toggle('overflow-hidden', shouldOpen && isDrawerMenu(mobileMenu));
  }

  function isMenuOpen(menuBtn, mobileMenu) {
    if (!menuBtn || !mobileMenu) return false;
    if (isDrawerMenu(mobileMenu)) {
      return mobileMenu.classList.contains('is-open');
    }
    return !mobileMenu.classList.contains('hidden');
  }

  function initMobileMenu() {
    var menuBtn = document.getElementById('menuBtn');
    var mobileMenu = document.getElementById('mobileMenu');
    if (!menuBtn || !mobileMenu) return;

    if (!menuBtn.hasAttribute('aria-controls')) {
      menuBtn.setAttribute('aria-controls', 'mobileMenu');
    }
    if (!menuBtn.hasAttribute('aria-expanded')) {
      menuBtn.setAttribute('aria-expanded', 'false');
    }

    menuBtn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      var nextState = !isMenuOpen(menuBtn, mobileMenu);
      setMenuState(menuBtn, mobileMenu, nextState);
    }, true);

    mobileMenu.addEventListener('click', function (event) {
      var actionTarget = event.target.closest('a, button.mobile-contact-cta');
      if (!actionTarget) return;
      setMenuState(menuBtn, mobileMenu, false);
    });

    document.addEventListener('click', function (event) {
      if (!isMenuOpen(menuBtn, mobileMenu)) return;
      if (mobileMenu.contains(event.target) || menuBtn.contains(event.target)) return;
      setMenuState(menuBtn, mobileMenu, false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isMenuOpen(menuBtn, mobileMenu)) {
        setMenuState(menuBtn, mobileMenu, false);
      }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1024) {
        setMenuState(menuBtn, mobileMenu, false);
      }
    });
  }

  function initDesktopKnowledgeMenu() {
    var dropdown = document.querySelector('.nav-dropdown');
    if (!dropdown) return;

    var trigger = dropdown.querySelector('.nav-dropdown__trigger');
    var menu = dropdown.querySelector('.nav-dropdown__menu');
    if (!trigger || !menu) return;

    if (!menu.id) {
      menu.id = 'desktopKnowledgeMenu';
    }

    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', menu.id);
    trigger.setAttribute('aria-haspopup', 'true');

    function setOpenState(shouldOpen) {
      dropdown.classList.toggle('is-open', shouldOpen);
      trigger.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    }

    trigger.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      var isOpen = dropdown.classList.contains('is-open');
      setOpenState(!isOpen);
    });

    document.addEventListener('click', function (event) {
      if (!dropdown.contains(event.target)) {
        setOpenState(false);
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        setOpenState(false);
      }
    });
  }



  function ensureMobileContactActions() {
    var mobileMenu = document.getElementById('mobileMenu');
    if (!mobileMenu) return;

    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var phoneNumber = '0524520222';
    var phoneLabel = isRuPage ? 'Позвонить: 052-4520222' : 'התקשר עכשיו';
    var ctaLabel = isRuPage ? 'Связаться' : 'צור קשר';

    var callLink = mobileMenu.querySelector('a[href^="tel:"]');
    if (!callLink) {
      callLink = document.createElement('a');
      callLink.href = 'tel:' + phoneNumber;
      callLink.className = 'block font-bold text-slate-600 border-b pb-2';
      callLink.textContent = phoneLabel;
      mobileMenu.appendChild(callLink);
    }

    var contactBtn = mobileMenu.querySelector('.mobile-contact-cta');
    if (!contactBtn) {
      contactBtn = document.createElement('button');
      contactBtn.type = 'button';
      contactBtn.id = 'openContactMobile';
      contactBtn.className = 'mobile-contact-cta';
      contactBtn.textContent = ctaLabel;
      mobileMenu.appendChild(contactBtn);
    }
  }

  function initLanguageSwitcher() {
    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var desktopNav = document.querySelector('.site-nav');
    if (desktopNav && !desktopNav.querySelector('.language-switch')) {
      var desktopSwitch = document.createElement('a');
      desktopSwitch.href = isRuPage ? '/index.html' : '/ru/index.html';
      desktopSwitch.className = 'language-switch';
      desktopSwitch.setAttribute('lang', isRuPage ? 'he' : 'ru');
      desktopSwitch.setAttribute('hreflang', isRuPage ? 'he' : 'ru');
      desktopSwitch.textContent = isRuPage ? 'HE' : 'RU';
      desktopSwitch.setAttribute('aria-label', isRuPage ? 'Переключиться на иврит' : 'Переключиться на русский');
      var desktopCta = desktopNav.querySelector('.site-cta');
      if (desktopCta) {
        desktopNav.insertBefore(desktopSwitch, desktopCta);
      } else {
        desktopNav.appendChild(desktopSwitch);
      }
    }

    var mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu && !mobileMenu.querySelector('.mobile-language-switch')) {
      var mobileSwitch = document.createElement('a');
      mobileSwitch.href = isRuPage ? '/index.html' : '/ru/index.html';
      mobileSwitch.className = 'block font-bold text-slate-600 border-b pb-2 mobile-language-switch';
      mobileSwitch.setAttribute('lang', isRuPage ? 'he' : 'ru');
      mobileSwitch.setAttribute('hreflang', isRuPage ? 'he' : 'ru');
      mobileSwitch.textContent = isRuPage ? 'עברית' : 'Русский';
      mobileSwitch.setAttribute('aria-label', isRuPage ? 'Перейти на версию на иврите' : 'Перейти на русскую версию');

      var callLink = mobileMenu.querySelector('a[href^="tel:"]');
      if (callLink) {
        mobileMenu.insertBefore(mobileSwitch, callLink);
      } else {
        mobileMenu.appendChild(mobileSwitch);
      }
    }
  }


  function injectSkipLink() {
    if (document.querySelector('.skip-link')) return;
    var isRuPage = window.location.pathname.indexOf('/ru/') === 0;
    var skip = document.createElement('a');
    skip.href = '#main-content';
    skip.className = 'skip-link';
    skip.textContent = isRuPage ? 'Перейти к основному содержанию' : 'דלג לתוכן הראשי';
    document.body.insertBefore(skip, document.body.firstChild);

    var main = document.querySelector('main');
    if (main && !main.id) {
      main.id = 'main-content';
    }
  }

  function init() {
    initMobileMenu();
    initDesktopKnowledgeMenu();
    ensureMobileContactActions();
    initLanguageSwitcher();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
