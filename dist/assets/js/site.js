const header = document.querySelector('[data-header]');
const menuToggle = document.querySelector('[data-menu-toggle]');
const nav = document.querySelector('[data-nav]');

window.addEventListener('scroll', () => {
  header?.classList.toggle('is-scrolled', window.scrollY > 30);
}, { passive: true });

menuToggle?.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open');
  document.body.classList.toggle('menu-open', open);
  menuToggle.setAttribute('aria-expanded', String(open));
  menuToggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
});

nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  nav.classList.remove('is-open');
  document.body.classList.remove('menu-open');
  menuToggle?.setAttribute('aria-expanded', 'false');
}));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach((element) => revealObserver.observe(element));

const video = document.querySelector('[data-hero-video]');
const videoControl = document.querySelector('[data-video-control]');
const videoIcon = document.querySelector('[data-video-icon]');
const videoLabel = document.querySelector('[data-video-label]');

function setVideoState(isPlaying) {
  if (!videoControl) return;
  videoIcon.textContent = isPlaying ? 'Ⅱ' : '▶';
  videoLabel.textContent = isPlaying ? 'Pause film' : 'Play film';
  videoControl.setAttribute('aria-label', isPlaying ? 'Pause background video' : 'Play background video');
}

video?.addEventListener('play', () => setVideoState(true));
video?.addEventListener('pause', () => setVideoState(false));

videoControl?.addEventListener('click', async () => {
  if (video.paused) {
    try {
      await video.play();
    } catch (error) {
      if (error.name !== 'AbortError') console.error('Background video could not play.', error);
      setVideoState(false);
    }
  } else {
    video.pause();
  }
});

const enquiryDialog = document.querySelector('[data-enquiry-dialog]');
const enquiryForm = document.querySelector('[data-enquiry-form]');
const enquiryStatus = document.querySelector('[data-form-status]');
const enquirySubmit = document.querySelector('[data-submit-enquiry]');

document.querySelectorAll('[data-open-enquiry]').forEach((button) => {
  button.addEventListener('click', () => {
    if (typeof enquiryDialog?.showModal === 'function') {
      enquiryDialog.showModal();
      enquiryDialog.querySelector('input')?.focus();
    }
  });
});

document.querySelectorAll('[data-close-enquiry]').forEach((button) => {
  button.addEventListener('click', () => enquiryDialog?.close());
});

enquiryDialog?.addEventListener('click', (event) => {
  if (event.target === enquiryDialog) enquiryDialog.close();
});

enquiryForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!enquiryForm.reportValidity()) return;

  enquiryStatus.className = 'form-status';
  enquiryStatus.textContent = 'Submitting your enquiry…';
  enquirySubmit.disabled = true;
  enquirySubmit.setAttribute('aria-busy', 'true');

  const formData = new FormData(enquiryForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch('/api/inquiries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || 'The enquiry could not be recorded.');

    enquiryStatus.classList.add('is-success');
    enquiryStatus.textContent = `Thank you. Your enquiry has been recorded. Reference: ${result.reference}`;
    enquiryForm.reset();
  } catch (error) {
    enquiryStatus.classList.add('is-error');
    enquiryStatus.textContent = window.location.protocol === 'file:'
      ? 'The form interface is ready, but saving requires the local enquiry server or the deployed website.'
      : error.message;
  } finally {
    enquirySubmit.disabled = false;
    enquirySubmit.removeAttribute('aria-busy');
  }
});
