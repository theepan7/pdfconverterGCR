/**
 * Mini PDF Tools – Shared Components
 * Defines <site-navbar> and <site-footer> custom elements.
 * Drop this file in your root and add ONE line to every page:
 *   <script src="/components.js"></script>
 *
 * Then replace every copy-pasted navbar/footer block with:
 *   <site-navbar></site-navbar>
 *   <site-footer></site-footer>
 */

/* ─────────────────────────────────────────────
   Shared CSS (navbar + footer styles)
   Injected once into the document <head>
───────────────────────────────────────────── */
const SHARED_STYLES = `
  /* ── Navbar ── */
  .navbar { background: linear-gradient(135deg, #475569, #4338ca); }
  .nav-link { color:rgba(255,255,255,0.82); transition:color 0.2s,background 0.2s; border-radius:0.375rem; padding:0.4rem 0.75rem; font-weight:500; font-size:0.95rem; text-decoration:none; }
  .nav-link:hover { color:#fff; background:rgba(255,255,255,0.12); }

  /* ── Dropdown fix: use padding + pseudo-element to bridge the gap ── */
  .dropdown { position:relative; }

  .dropdown-menu {
    display: none;
    position: absolute;
    top: 100%;                        /* sit flush against the button */
    left: 50%;
    transform: translateX(-50%);
    background: #fff;
    border-radius: 0.75rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
    min-width: 220px;
    z-index: 100;
    overflow: hidden;
    padding-top: 8px;                 /* visible gap becomes part of the menu */
  }

  /* Invisible bridge fills the gap so mouse doesn't leave hover area */
  .dropdown-menu::before {
    content: '';
    position: absolute;
    top: -8px;                        /* exactly covers the gap */
    left: 0;
    right: 0;
    height: 8px;
  }

  /* Keep menu open while hovering the button OR the menu itself */
  .dropdown:hover .dropdown-menu { display: block; }

  /* Small delay on hide so fast mouse movements don't close it instantly */
  .dropdown-menu { transition: opacity 0.1s; }
  .dropdown:not(:hover) .dropdown-menu { display: none; }

  .dropdown-inner {
    background: #fff;
    border-radius: 0.75rem;
    overflow: hidden;
  }

  .dropdown-section { padding:0.5rem 0; }
  .dropdown-section-label { font-size:0.68rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.08em; padding:0.4rem 1.1rem 0.2rem; }
  .dropdown-item { display:flex; align-items:center; gap:0.6rem; padding:0.6rem 1.1rem; color:#374151; font-size:0.875rem; font-weight:500; transition:background 0.15s; text-decoration:none; }
  .dropdown-item:hover { background:#f8fafc; }
  .dropdown-divider { border-top:1px solid #f1f5f9; margin:0.25rem 0; }

  /* ── Mobile nav ── */
  #mobile-menu { display:none; }
  #mobile-menu.open { display:block; }
  .mobile-tool-links { display:none; }
  .mobile-tool-links.open { display:block; }

  /* ── Footer ── */
  .site-footer { background:linear-gradient(135deg,#1e293b,#312e81); color:rgba(255,255,255,0.75); }
  .footer-link { color:rgba(255,255,255,0.65); transition:color 0.2s; font-size:0.875rem; text-decoration:none; }
  .footer-link:hover { color:#fff; }
  .footer-divider { border-color:rgba(255,255,255,0.12); }
  .social-icon { width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:rgba(255,255,255,0.8); transition:background 0.2s,color 0.2s; font-size:0.9rem; text-decoration:none; }
  .social-icon:hover { background:rgba(255,255,255,0.22); color:#fff; }
`;

function injectSharedStyles() {
  if (document.getElementById('mpt-shared-styles')) return;
  const style = document.createElement('style');
  style.id = 'mpt-shared-styles';
  style.textContent = SHARED_STYLES;
  document.head.appendChild(style);
}

/* ─────────────────────────────────────────────
   <site-navbar> component
───────────────────────────────────────────── */
class SiteNavbar extends HTMLElement {
  connectedCallback() {
    injectSharedStyles();
    this.innerHTML = `
      <nav class="navbar w-full shadow-lg sticky top-0 z-50" aria-label="Main navigation">
        <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">

          <!-- Logo -->
          <a href="/" class="flex items-center gap-2 text-white" style="text-decoration:none" aria-label="Mini PDF Tools Home">
            <div class="w-8 h-8 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
              <i class="fas fa-file-pdf text-white text-sm"></i>
            </div>
            <span class="font-bold text-lg tracking-tight">Mini PDF Tools</span>
          </a>

          <!-- Desktop nav -->
          <div class="hidden md:flex items-center gap-1">
            <a href="/" class="nav-link"><i class="fas fa-home mr-1 text-xs"></i> Home</a>

            <!-- Compress -->
            <div class="dropdown">
              <button class="nav-link flex items-center gap-1" style="background:transparent;border:none;cursor:pointer;" aria-haspopup="true">
                <i class="fas fa-compress-alt text-xs"></i>&nbsp;Compress&nbsp;<i class="fas fa-chevron-down text-xs opacity-70"></i>
              </button>
              <div class="dropdown-menu" style="min-width:200px" role="menu">
                <div class="dropdown-inner">
                  <div class="dropdown-section">
                    <div class="dropdown-section-label">Reduce File Size</div>
                    <a href="/compress-pdf" class="dropdown-item" role="menuitem"><i class="fas fa-compress-alt text-blue-500 w-4"></i> Compress PDF</a>
                  </div>
                </div>
              </div>
            </div>

            <!-- Organize -->
            <div class="dropdown">
              <button class="nav-link flex items-center gap-1" style="background:transparent;border:none;cursor:pointer;" aria-haspopup="true">
                <i class="fas fa-layer-group text-xs"></i>&nbsp;Organize&nbsp;<i class="fas fa-chevron-down text-xs opacity-70"></i>
              </button>
              <div class="dropdown-menu" style="min-width:200px" role="menu">
                <div class="dropdown-inner">
                  <div class="dropdown-section">
                    <div class="dropdown-section-label">Manage Pages</div>
                    <a href="/merge-pdf"        class="dropdown-item" role="menuitem"><i class="fas fa-object-group text-green-500 w-4"></i> Merge PDFs</a>
                    <a href="/split-pdf"        class="dropdown-item" role="menuitem"><i class="fas fa-cut text-red-500 w-4"></i> Split PDF</a>
                    <a href="/rotate-pdf"       class="dropdown-item" role="menuitem"><i class="fas fa-sync-alt text-orange-500 w-4"></i> Rotate PDF</a>
                    <a href="/delete-pdf-pages" class="dropdown-item" role="menuitem"><i class="fas fa-trash-alt text-yellow-600 w-4"></i> Delete Pages</a>
                  </div>
                </div>
              </div>
            </div>

            <!-- Convert -->
            <div class="dropdown">
              <button class="nav-link flex items-center gap-1" style="background:transparent;border:none;cursor:pointer;" aria-haspopup="true">
                <i class="fas fa-exchange-alt text-xs"></i>&nbsp;Convert&nbsp;<i class="fas fa-chevron-down text-xs opacity-70"></i>
              </button>
              <div class="dropdown-menu" style="min-width:200px" role="menu">
                <div class="dropdown-inner">
                  <div class="dropdown-section">
                    <div class="dropdown-section-label">Change Format</div>
                    <a href="/image-to-pdf" class="dropdown-item" role="menuitem"><i class="fas fa-image text-purple-500 w-4"></i> Image to PDF</a>
                    <a href="/pdf-to-jpg"   class="dropdown-item" role="menuitem"><i class="fas fa-file-image text-indigo-500 w-4"></i> PDF to JPG</a>
                  </div>
                </div>
              </div>
            </div>

            <!-- Annotate -->
            <div class="dropdown">
              <button class="nav-link flex items-center gap-1" style="background:transparent;border:none;cursor:pointer;" aria-haspopup="true">
                <i class="fas fa-highlighter text-xs"></i>&nbsp;Annotate&nbsp;<i class="fas fa-chevron-down text-xs opacity-70"></i>
              </button>
              <div class="dropdown-menu" style="min-width:200px" role="menu">
                <div class="dropdown-inner">
                  <div class="dropdown-section">
                    <div class="dropdown-section-label">Mark Up PDFs</div>
                    <a href="/annotate-pdf" class="dropdown-item" role="menuitem"><i class="fas fa-highlighter text-emerald-500 w-4"></i> Annotate PDF</a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Hamburger -->
          <button id="hamburger" class="md:hidden text-white p-2 rounded-lg hover:bg-white hover:bg-opacity-10 transition" onclick="window._mptToggleMobileMenu()" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-menu">
            <i class="fas fa-bars text-lg"></i>
          </button>
        </div>

        <!-- Mobile menu -->
        <div id="mobile-menu" class="md:hidden px-4 pb-4" style="background:#312e81" role="navigation" aria-label="Mobile navigation">
          <a href="/" class="block py-2 px-3 text-white text-sm font-medium rounded hover:bg-white hover:bg-opacity-10"><i class="fas fa-home mr-2"></i>Home</a>

          <!-- Mobile: Compress -->
          <button onclick="window._mptToggleSection('mobile-compress','chevron-compress')" class="w-full text-left py-2 px-3 text-white text-sm font-medium rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-between bg-transparent border-0 cursor-pointer" aria-expanded="false">
            <span><i class="fas fa-compress-alt mr-2"></i>Compress</span>
            <i class="fas fa-chevron-down text-xs" id="chevron-compress"></i>
          </button>
          <div id="mobile-compress" class="mobile-tool-links pl-4 border-l border-white border-opacity-20 ml-3">
            <a href="/compress-pdf" class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-compress-alt mr-2"></i>Compress PDF</a>
          </div>

          <!-- Mobile: Organize -->
          <button onclick="window._mptToggleSection('mobile-organize','chevron-organize')" class="w-full text-left py-2 px-3 text-white text-sm font-medium rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-between bg-transparent border-0 cursor-pointer" aria-expanded="false">
            <span><i class="fas fa-layer-group mr-2"></i>Organize</span>
            <i class="fas fa-chevron-down text-xs" id="chevron-organize"></i>
          </button>
          <div id="mobile-organize" class="mobile-tool-links pl-4 border-l border-white border-opacity-20 ml-3">
            <a href="/merge-pdf"        class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-object-group mr-2"></i>Merge PDFs</a>
            <a href="/split-pdf"        class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-cut mr-2"></i>Split PDF</a>
            <a href="/rotate-pdf"       class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-sync-alt mr-2"></i>Rotate PDF</a>
            <a href="/delete-pdf-pages" class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-trash-alt mr-2"></i>Delete Pages</a>
          </div>

          <!-- Mobile: Convert -->
          <button onclick="window._mptToggleSection('mobile-convert','chevron-convert')" class="w-full text-left py-2 px-3 text-white text-sm font-medium rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-between bg-transparent border-0 cursor-pointer" aria-expanded="false">
            <span><i class="fas fa-exchange-alt mr-2"></i>Convert</span>
            <i class="fas fa-chevron-down text-xs" id="chevron-convert"></i>
          </button>
          <div id="mobile-convert" class="mobile-tool-links pl-4 border-l border-white border-opacity-20 ml-3">
            <a href="/image-to-pdf" class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-image mr-2"></i>Image to PDF</a>
            <a href="/pdf-to-jpg"   class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-file-image mr-2"></i>PDF to JPG</a>
          </div>

          <!-- Mobile: Annotate -->
          <button onclick="window._mptToggleSection('mobile-annotate','chevron-annotate')" class="w-full text-left py-2 px-3 text-white text-sm font-medium rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-between bg-transparent border-0 cursor-pointer" aria-expanded="false">
            <span><i class="fas fa-highlighter mr-2"></i>Annotate</span>
            <i class="fas fa-chevron-down text-xs" id="chevron-annotate"></i>
          </button>
          <div id="mobile-annotate" class="mobile-tool-links pl-4 border-l border-white border-opacity-20 ml-3">
            <a href="/annotate-pdf" class="block py-2 px-3 text-white text-sm opacity-90 hover:opacity-100"><i class="fas fa-highlighter mr-2"></i>Annotate PDF</a>
          </div>
        </div>
      </nav>
    `;

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
      const menu = document.getElementById('mobile-menu');
      const hamburger = document.getElementById('hamburger');
      if (menu && hamburger && !menu.contains(e.target) && !hamburger.contains(e.target)) {
        menu.classList.remove('open');
      }
    });
  }
}

/* ─────────────────────────────────────────────
   <site-footer> component
───────────────────────────────────────────── */
class SiteFooter extends HTMLElement {
  connectedCallback() {
    injectSharedStyles();
    this.innerHTML = `
      <footer class="site-footer w-full mt-auto" id="contact">
        <div class="max-w-6xl mx-auto px-6 py-10">
          <div class="flex flex-col md:flex-row justify-between gap-8 mb-8">

            <!-- Brand -->
            <div class="flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                  <i class="fas fa-file-pdf text-white text-sm"></i>
                </div>
                <span class="text-white font-bold text-lg">Mini PDF Tools</span>
              </div>
              <p class="text-sm max-w-xs" style="color:rgba(255,255,255,0.6)">Free, fast, and secure PDF tools. No signup required. Your files are never stored on our servers.</p>
              <div class="flex gap-2 mt-1">
                <a href="#" class="social-icon" aria-label="Twitter"><i class="fab fa-twitter"></i></a>
                <a href="#" class="social-icon" aria-label="Facebook"><i class="fab fa-facebook-f"></i></a>
                <a href="#" class="social-icon" aria-label="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
              </div>
            </div>

            <!-- Organise -->
            <div>
              <p class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">Organise</p>
              <ul class="flex flex-col gap-2" style="list-style:none;padding:0;margin:0">
                <li><a href="/merge-pdf"        class="footer-link"><i class="fas fa-object-group mr-2 text-xs"></i>Merge PDFs</a></li>
                <li><a href="/split-pdf"         class="footer-link"><i class="fas fa-cut mr-2 text-xs"></i>Split PDF</a></li>
                <li><a href="/rotate-pdf"        class="footer-link"><i class="fas fa-sync-alt mr-2 text-xs"></i>Rotate PDF</a></li>
                <li><a href="/delete-pdf-pages"  class="footer-link"><i class="fas fa-trash-alt mr-2 text-xs"></i>Delete Pages</a></li>
              </ul>
            </div>

            <!-- Optimise & Convert -->
            <div>
              <p class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">Optimise &amp; Convert</p>
              <ul class="flex flex-col gap-2" style="list-style:none;padding:0;margin:0">
                <li><a href="/compress-pdf"  class="footer-link"><i class="fas fa-compress-alt mr-2 text-xs"></i>Compress PDF</a></li>
                <li><a href="/image-to-pdf"  class="footer-link"><i class="fas fa-image mr-2 text-xs"></i>Image to PDF</a></li>
                <li><a href="/pdf-to-jpg"    class="footer-link"><i class="fas fa-file-image mr-2 text-xs"></i>PDF to JPG</a></li>
                <li><a href="/annotate-pdf"  class="footer-link"><i class="fas fa-highlighter mr-2 text-xs"></i>Annotate PDF</a></li>
              </ul>
            </div>

            <!-- Company -->
            <div>
              <p class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">Company</p>
              <ul class="flex flex-col gap-2" style="list-style:none;padding:0;margin:0">
                <li><a href="/about"                          class="footer-link"><i class="fas fa-info-circle mr-2 text-xs"></i>About</a></li>
                <li><a href="/contactform"                    class="footer-link"><i class="fas fa-envelope mr-2 text-xs"></i>Contact</a></li>
                <li><a href="mailto:support@minipdftools.com" class="footer-link"><i class="fas fa-at mr-2 text-xs"></i>support@minipdftools.com</a></li>
                <li><a href="/privacy"                        class="footer-link"><i class="fas fa-shield-alt mr-2 text-xs"></i>Privacy Policy</a></li>
              </ul>
            </div>

          </div>
          <hr class="footer-divider mb-6" />
          <div class="flex flex-col md:flex-row justify-between items-center gap-2 text-xs" style="color:rgba(255,255,255,0.45)">
            <p>Your document privacy is our top priority. Files are never stored on our servers.</p>
            <p>&copy; 2026 Mini PDF Tools. All rights reserved.</p>
          </div>
        </div>
      </footer>
    `;
  }
}

/* ─────────────────────────────────────────────
   Global helpers (mobile menu toggles)
   Exposed on window so onclick="" attributes work
───────────────────────────────────────────── */
window._mptToggleMobileMenu = function () {
  const menu = document.getElementById('mobile-menu');
  const hamburger = document.getElementById('hamburger');
  if (!menu) return;
  menu.classList.toggle('open');
  if (hamburger) hamburger.setAttribute('aria-expanded', menu.classList.contains('open'));
};

window._mptToggleSection = function (sectionId, chevronId) {
  const section = document.getElementById(sectionId);
  const chevron = document.getElementById(chevronId);
  if (!section) return;
  section.classList.toggle('open');
  if (chevron) {
    chevron.classList.toggle('fa-chevron-down');
    chevron.classList.toggle('fa-chevron-up');
  }
};

/* ─────────────────────────────────────────────
   Register custom elements
───────────────────────────────────────────── */
customElements.define('site-navbar', SiteNavbar);
customElements.define('site-footer', SiteFooter);
