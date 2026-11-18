import Lenis from "lenis";

function initMotionSystem() {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const disableSmooth = document.documentElement.hasAttribute("data-no-smooth-scroll");

  let lenis: Lenis | null = null;

  if (!prefersReducedMotion && !disableSmooth) {
    lenis = new Lenis({
      duration: 1.05,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 1,
      touchMultiplier: 1.5
    });
    (window as any).__lenis = lenis;
  }

  // Scroll reveal
  const revealElements = document.querySelectorAll<HTMLElement>("[data-reveal]");
  if (revealElements.length > 0) {
    if (prefersReducedMotion) {
      revealElements.forEach((el) => el.classList.add("is-visible"));
    } else {
      const revealObserver = new IntersectionObserver(
        (entries, obs) => {
          let batchIdx = 0;
          for (const entry of entries) {
            if (entry.isIntersecting) {
              const el = entry.target as HTMLElement;
              if (batchIdx > 0) {
                el.style.transitionDelay = `${Math.min(batchIdx * 55, 220)}ms`;
              }
              requestAnimationFrame(() => {
                el.classList.add("is-visible");
              });
              obs.unobserve(el);
              batchIdx += 1;
            }
          }
        },
        { rootMargin: "0px 0px -6% 0px", threshold: 0.05 }
      );
      revealElements.forEach((el) => revealObserver.observe(el));
    }
  }

  // Parallax
  const parallaxElements = Array.from(document.querySelectorAll<HTMLElement>("[data-parallax]"));
  const activeParallax = new Set<HTMLElement>();

  if (!prefersReducedMotion && parallaxElements.length > 0) {
    const parallaxObserver = new IntersectionObserver(
      (entries) => {
        let added = false;
        for (const entry of entries) {
          const el = entry.target as HTMLElement;
          if (entry.isIntersecting) {
            activeParallax.add(el);
            added = true;
          } else {
            activeParallax.delete(el);
          }
        }
        if (added) updateParallax();
      },
      { rootMargin: "100px 0px 100px 0px" }
    );

    parallaxElements.forEach((el) => parallaxObserver.observe(el));
  }

  let lastScrollY = -1;

  function updateParallax() {
    if (activeParallax.size === 0) return;
    const vh = window.innerHeight;

    activeParallax.forEach((el) => {
      const speed = parseFloat(el.dataset.parallax || "0.15");
      const container = el.closest(".parallax-window") || el.parentElement || el;
      const rect = container.getBoundingClientRect();
      const centerOffset = rect.top + rect.height * 0.5 - vh * 0.5;
      const translateY = Math.round(centerOffset * -speed * 10) / 10;
      el.style.transform = `translate3d(0, ${translateY}px, 0) scale(1.12)`;
    });
  }

  function raf(time: number) {
    if (lenis) {
      lenis.raf(time);
    }
    const currentScroll = window.scrollY;
    if (currentScroll !== lastScrollY) {
      lastScrollY = currentScroll;
      updateParallax();
    }
    requestAnimationFrame(raf);
  }

  updateParallax();
  requestAnimationFrame(raf);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMotionSystem);
} else {
  initMotionSystem();
}
