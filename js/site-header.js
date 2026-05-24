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
    var ctaLabel = isRuPage ? 'Записаться на персональную проверку' : 'לתיאום בדיקה אישית';

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
    injectSkipLink();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
