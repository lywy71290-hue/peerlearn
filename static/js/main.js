/* ═══════════════════════════════════════════════════════════════════════════
   PeerLearn — Main JavaScript
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ─── Navbar scroll effect ──────────────────────────────────────────── */
  const nav = document.getElementById('mainNav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.style.background = window.scrollY > 20
        ? 'rgba(15,23,42,.98)'
        : 'rgba(15,23,42,.92)';
    });
  }

  /* ─── Auto-dismiss alerts ───────────────────────────────────────────── */
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 5000);
  });

  /* ─── Upload drag-and-drop ──────────────────────────────────────────── */
  const uploadZone = document.getElementById('uploadZone');
  const fileInput  = document.getElementById('video_file');

  if (uploadZone && fileInput) {
    uploadZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(e =>
      uploadZone.addEventListener(e, ev => { ev.preventDefault(); uploadZone.classList.add('dragover'); })
    );
    ['dragleave', 'drop'].forEach(e =>
      uploadZone.addEventListener(e, ev => { ev.preventDefault(); uploadZone.classList.remove('dragover'); })
    );
    uploadZone.addEventListener('drop', ev => {
      const files = ev.dataTransfer.files;
      if (files.length) {
        fileInput.files = files;
        updateUploadZoneLabel(files[0].name);
      }
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) updateUploadZoneLabel(fileInput.files[0].name);
    });

    function updateUploadZoneLabel(name) {
      const label = uploadZone.querySelector('p');
      if (label) label.textContent = `Selected: ${name}`;
      uploadZone.style.borderColor = 'var(--success)';
    }
  }

  /* ─── Upload form progress ──────────────────────────────────────────── */
  const uploadForm = document.getElementById('uploadForm');
  const spinner    = document.getElementById('spinnerOverlay');

  if (uploadForm && spinner) {
    uploadForm.addEventListener('submit', () => {
      spinner.classList.add('active');
    });
  }

  /* ─── Star rating (interactive) ────────────────────────────────────── */
  const starContainer = document.getElementById('starRatingInput');
  if (starContainer) {
    const videoId = starContainer.dataset.videoId;
    const stars   = starContainer.querySelectorAll('.star-btn');

    stars.forEach((star, idx) => {
      star.addEventListener('mouseenter', () => highlightStars(idx + 1));
      star.addEventListener('mouseleave', () => highlightStars(getCurrentRating()));
      star.addEventListener('click', () => submitRating(idx + 1));
    });

    function highlightStars(n) {
      stars.forEach((s, i) => s.classList.toggle('active', i < n));
    }
    function getCurrentRating() {
      return parseInt(starContainer.dataset.currentRating || '0');
    }
    function submitRating(score) {
      fetch(`/videos/${videoId}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) return;
          starContainer.dataset.currentRating = score;
          highlightStars(score);
          const avgEl = document.getElementById('avgRating');
          const cntEl = document.getElementById('ratingCount');
          if (avgEl) avgEl.textContent = data.avg_rating;
          if (cntEl) cntEl.textContent = `(${data.rating_count} ratings)`;
          showToast('Rating submitted!', 'success');
        });
    }
  }

  /* ─── Comment form (AJAX) ───────────────────────────────────────────── */
  const commentForm = document.getElementById('commentForm');
  if (commentForm) {
    const videoId = commentForm.dataset.videoId;
    commentForm.addEventListener('submit', e => {
      e.preventDefault();
      const textarea = commentForm.querySelector('textarea');
      const content  = textarea.value.trim();
      if (!content) return;

      fetch(`/videos/${videoId}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) { showToast(data.error, 'danger'); return; }
          textarea.value = '';
          prependComment(data);
          showToast('Comment posted!', 'success');
        });
    });

    function prependComment(c) {
      const list = document.getElementById('commentsList');
      if (!list) return;
      const initial = c.username[0].toUpperCase();
      const html = `
        <div class="comment-card fade-in-up">
          <div class="d-flex gap-3 align-items-start">
            <div class="comment-avatar">${initial}</div>
            <div class="flex-grow-1">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="fw-600 text-white">${escapeHtml(c.username)}</span>
                <span class="text-muted small">${c.created_at}</span>
              </div>
              <p class="mb-0 text-secondary">${escapeHtml(c.content)}</p>
            </div>
          </div>
        </div>`;
      list.insertAdjacentHTML('afterbegin', html);
      const emptyState = document.getElementById('noComments');
      if (emptyState) emptyState.remove();
    }
  }

  /* ─── Toast helper ──────────────────────────────────────────────────── */
  function showToast(msg, type = 'success') {
    const container = document.getElementById('toastContainer') || createToastContainer();
    const id = 'toast_' + Date.now();
    const icons = { success: 'check-circle-fill', danger: 'exclamation-circle-fill', info: 'info-circle-fill' };
    const html = `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
        <div class="d-flex">
          <div class="toast-body"><i class="bi bi-${icons[type] || 'info-circle-fill'} me-2"></i>${msg}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>`;
    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }

  function createToastContainer() {
    const div = document.createElement('div');
    div.id = 'toastContainer';
    div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    div.style.zIndex = '9999';
    document.body.appendChild(div);
    return div;
  }

  /* ─── Utility ───────────────────────────────────────────────────────── */
  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ─── Filter form auto-submit ───────────────────────────────────────── */
  const filterForm = document.getElementById('filterForm');
  if (filterForm) {
    filterForm.querySelectorAll('select').forEach(sel => {
      sel.addEventListener('change', () => filterForm.submit());
    });
  }

  /* ─── Smooth scroll to comments ─────────────────────────────────────── */
  document.querySelectorAll('[data-scroll-to]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.scrollTo);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

});
