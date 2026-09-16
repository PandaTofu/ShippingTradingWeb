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
