(function () {
  function isRuPage() {
    return window.location.pathname.indexOf('/ru/') === 0;
  }

  function isKnowledgeHref(href) {
    if (!href) return false;
    return (
      href.indexOf('articles.html') !== -1 ||
      href.indexOf('faq.html') !== -1 ||
      href.indexOf('media.html') !== -1
    );
  }

  function removeFloatingContactButtons() {
    var selectors = ['.mobile-sticky-cta', '.whatsapp-float.fixed-whatsapp', '.whatsapp-float'];

    selectors.forEach(function (selector) {
      var nodes = document.querySelectorAll(selector);
      nodes.forEach(function (node) {
        node.remove();
      });
    });
  }

  function enhanceLegacyMobileMenu() {
    if (isRuPage()) return;

    var mobileMenu = document.getElementById('mobileMenu');
    var menuBtn = document.getElementById('menuBtn');

    if (!mobileMenu || !menuBtn) return;
    if (mobileMenu.classList.contains('mobile-drawer')) return;
    if (mobileMenu.querySelector('#mobileKnowledgeToggle')) return;

    mobileMenu.classList.add('mobile-menu-enhanced');
    menuBtn.classList.add('mobile-menu-toggle');

    var links = Array.prototype.slice.call(mobileMenu.querySelectorAll('a'));
    links.forEach(function (link) {
      link.classList.add('mobile-nav-link');
    });

    var knowledgeLinks = links.filter(function (link) {
      return isKnowledgeHref(link.getAttribute('href'));
    });

    if (!knowledgeLinks.length) return;

    var firstKnowledgeLink = knowledgeLinks[0];

    var knowledgeToggle = document.createElement('button');
    knowledgeToggle.id = 'mobileKnowledgeToggle';
    knowledgeToggle.type = 'button';
    knowledgeToggle.className = 'mobile-nav-link mobile-nav-accordion-toggle';
    knowledgeToggle.setAttribute('aria-expanded', 'false');
    knowledgeToggle.setAttribute('aria-controls', 'mobileKnowledgeMenu');
    knowledgeToggle.innerHTML =
      '<span class="mobile-nav-accordion-toggle__label">מרכז ידע</span><span class="mobile-nav-accordion-toggle__icon" aria-hidden="true">▾</span>';

    var knowledgeMenu = document.createElement('div');
    knowledgeMenu.id = 'mobileKnowledgeMenu';
    knowledgeMenu.className = 'mobile-subnav';
    knowledgeMenu.hidden = true;

    mobileMenu.insertBefore(knowledgeToggle, firstKnowledgeLink);
    mobileMenu.insertBefore(knowledgeMenu, firstKnowledgeLink);

    knowledgeLinks.forEach(function (link) {
      link.classList.remove('mobile-nav-link');
      link.classList.add('mobile-subnav-link');
      knowledgeMenu.appendChild(link);
    });

    knowledgeToggle.addEventListener('click', function () {
      var expanded = knowledgeToggle.getAttribute('aria-expanded') === 'true';
      knowledgeToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      knowledgeMenu.hidden = expanded;
    });
  }

  function createKnowledgeDropdown() {
    var dropdown = document.createElement('div');
    dropdown.className = 'nav-dropdown';

    var trigger = document.createElement('button');
    trigger.className = 'nav-dropdown__trigger';
    trigger.type = 'button';
    trigger.innerHTML = 'מרכז ידע <span aria-hidden="true">▾</span>';

    var menu = document.createElement('div');
    menu.className = 'nav-dropdown__menu';
    menu.setAttribute('role', 'menu');
    menu.setAttribute('aria-label', 'מרכז ידע');

    [
      { href: 'articles.html', label: 'מאמרים מקצועיים על פנסיה וביטוחים' },
      { href: 'faq.html', label: 'שאלות ותשובות' },
      { href: 'media.html', label: 'וידאו ומדיה' }
    ].forEach(function (item) {
      var link = document.createElement('a');
      link.href = item.href;
      link.className = 'nav-dropdown__item';
      link.setAttribute('role', 'menuitem');
      link.textContent = item.label;
      menu.appendChild(link);
    });

    dropdown.appendChild(trigger);
    dropdown.appendChild(menu);

    return dropdown;
  }

  function enhanceDesktopKnowledgeMenu() {
    if (isRuPage()) return;

    var desktopNav = document.querySelector('.site-nav, .site-header nav.hidden[class~="lg:flex"]');

    if (!desktopNav) return;
    if (desktopNav.querySelector('.nav-dropdown')) return;

    var desktopLinks = Array.prototype.slice.call(desktopNav.querySelectorAll('a[href]'));

    desktopLinks.forEach(function (link) {
      if (isKnowledgeHref(link.getAttribute('href'))) {
        link.parentNode.removeChild(link);
      }
    });

    var insertBeforeNode = desktopNav.querySelector('a[href^="tel:"]') || desktopNav.querySelector('button');
    var dropdown = createKnowledgeDropdown();

    if (insertBeforeNode) {
      desktopNav.insertBefore(dropdown, insertBeforeNode);
      return;
    }

    desktopNav.appendChild(dropdown);
  }



  function reduceContactCtaClutter() {
    var ctaNodes = Array.prototype.slice.call(document.querySelectorAll('[id^="openContact"]'));
    if (!ctaNodes.length) return;

    var keepIds = {
      openContactDesktop: true,
      openContactMobile: true
    };

    var secondaryKept = false;

    ctaNodes.forEach(function (node) {
      if (!node || !node.id) return;
      if (keepIds[node.id]) return;

      if (!secondaryKept) {
        secondaryKept = true;
        return;
      }

      node.remove();
    });
  }

  function init() {
    removeFloatingContactButtons();
    enhanceLegacyMobileMenu();
    enhanceDesktopKnowledgeMenu();
    reduceContactCtaClutter();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
