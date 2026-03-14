/* ── Portfolio Main JS ── */
(function() {
  'use strict';

  // ── Navbar scroll ──
  const navbar = document.getElementById('navbar');
  const navLinks = document.querySelectorAll('.nav-link[data-section]');
  const sections = document.querySelectorAll('section[id]');

  const onScroll = () => {
    // Scrolled class
    if (window.scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }

    // Active nav link
    let current = '';
    sections.forEach(sec => {
      const top = sec.offsetTop - 100;
      if (window.scrollY >= top) current = sec.id;
    });

    navLinks.forEach(link => {
      link.classList.toggle('active', link.dataset.section === current);
    });

    // Back to top
    const btn = document.getElementById('back-to-top');
    if (btn) btn.classList.toggle('visible', window.scrollY > 400);

    // Animate in elements
    document.querySelectorAll('.animate-in:not(.visible)').forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight - 60) el.classList.add('visible');
    });

    // Skill bars
    document.querySelectorAll('.skill-bar-fill[data-width]').forEach(bar => {
      const rect = bar.getBoundingClientRect();
      if (rect.top < window.innerHeight + 40 && bar.style.width === '') {
        bar.style.width = bar.dataset.width + '%';
      }
    });
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll(); // initial

  // ── Mobile nav ──
  const toggle = document.getElementById('nav-toggle');
  const navLinksContainer = document.getElementById('nav-links');

  if (toggle && navLinksContainer) {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('open');
      navLinksContainer.classList.toggle('open');
    });

    navLinksContainer.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        toggle.classList.remove('open');
        navLinksContainer.classList.remove('open');
      });
    });
  }

  // ── Skills tabs ──
  document.querySelectorAll('.skills-tab').forEach(tab => {
    tab.addEventListener('click', function() {
      document.querySelectorAll('.skills-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.skills-panel').forEach(p => p.classList.remove('active'));
      this.classList.add('active');
      const panel = document.getElementById(this.dataset.tab);
      if (panel) {
        panel.classList.add('active');
        // Animate bars in this panel
        setTimeout(() => {
          panel.querySelectorAll('.skill-bar-fill[data-width]').forEach(bar => {
            bar.style.width = bar.dataset.width + '%';
          });
        }, 50);
      }
    });
  });

  // ── Contact form ──
  const form = document.getElementById('contact-form');
  const status = document.getElementById('form-status');

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type=submit]');
      const originalText = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
      btn.disabled = true;

      try {
        const fd = new FormData(form);
        const res = await fetch('/send_message', { method: 'POST', body: fd });
        const data = await res.json();

        if (data.ok) {
          form.reset();
          showToast('✅ ' + (document.documentElement.lang === 'uz'
            ? 'Xabar yuborildi!'
            : document.documentElement.lang === 'ru'
            ? 'Сообщение отправлено!'
            : 'Message sent!'), 'success');
          if (status) {
            status.className = 'form-status success';
            status.textContent = '✅ ' + (document.documentElement.lang === 'uz'
              ? 'Xabar muvaffaqiyatli yuborildi!'
              : document.documentElement.lang === 'ru'
              ? 'Сообщение успешно отправлено!'
              : 'Message sent successfully!');
          }
        } else {
          throw new Error(data.error || 'Error');
        }
      } catch (err) {
        showToast('❌ Error. Try again.', 'error');
        if (status) {
          status.className = 'form-status error';
          status.textContent = '❌ ' + (document.documentElement.lang === 'uz'
            ? 'Xatolik yuz berdi. Qayta urinib ko\'ring.'
            : document.documentElement.lang === 'ru'
            ? 'Ошибка. Попробуйте снова.'
            : 'Error. Please try again.');
        }
      } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
        if (status) {
          setTimeout(() => { status.className = 'form-status'; }, 5000);
        }
      }
    });
  }

  // ── Back to top ──
  const backBtn = document.getElementById('back-to-top');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Toast ──
  function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  // ── Smooth anchor scrolling ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

})();
