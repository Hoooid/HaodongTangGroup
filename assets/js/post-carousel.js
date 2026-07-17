(() => {
  const carousels = document.querySelectorAll("[data-np-post-carousel]");

  carousels.forEach((carousel) => {
    const viewport = carousel.querySelector("[data-np-carousel-viewport]");
    const slides = Array.from(carousel.querySelectorAll("[data-np-carousel-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-np-carousel-dot]"));
    const previous = carousel.querySelector("[data-np-carousel-previous]");
    const next = carousel.querySelector("[data-np-carousel-next]");
    const toggle = carousel.querySelector("[data-np-carousel-toggle]");
    const currentLabel = carousel.querySelector("[data-np-carousel-current]");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const interval = Number(carousel.dataset.autoplay) || 6500;

    if (!viewport || slides.length === 0) return;

    let current = 0;
    let timer = null;
    let userPaused = false;
    let hovering = false;
    let focused = false;
    let visible = true;
    let scrollFrame = null;

    const updateState = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const isCurrent = slideIndex === current;
        slide.setAttribute("aria-hidden", String(!isCurrent));
        const link = slide.querySelector("a");
        if (link) link.tabIndex = isCurrent ? 0 : -1;
      });
      dots.forEach((dot, dotIndex) => {
        dot.setAttribute("aria-current", String(dotIndex === current));
      });
      if (currentLabel) currentLabel.textContent = String(current + 1).padStart(2, "0");
    };

    const shouldAutoplay = () =>
      slides.length > 1 &&
      !userPaused &&
      !hovering &&
      !focused &&
      visible &&
      !reduceMotion.matches &&
      document.visibilityState === "visible";

    const stopTimer = () => {
      window.clearInterval(timer);
      timer = null;
    };

    const startTimer = () => {
      stopTimer();
      if (!shouldAutoplay()) return;
      timer = window.setInterval(() => {
        goTo(current + 1);
      }, interval);
    };

    const goTo = (index, behavior = "smooth") => {
      const target = (index + slides.length) % slides.length;
      viewport.scrollTo({
        left: target * viewport.clientWidth,
        behavior: reduceMotion.matches ? "auto" : behavior,
      });
      updateState(target);
      startTimer();
    };

    viewport.addEventListener(
      "scroll",
      () => {
        if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
        scrollFrame = window.requestAnimationFrame(() => {
          const index = Math.round(viewport.scrollLeft / Math.max(viewport.clientWidth, 1));
          updateState(index);
        });
      },
      { passive: true },
    );

    previous?.addEventListener("click", () => goTo(current - 1));
    next?.addEventListener("click", () => goTo(current + 1));
    dots.forEach((dot, index) => dot.addEventListener("click", () => goTo(index)));

    toggle?.addEventListener("click", () => {
      userPaused = !userPaused;
      const label = userPaused ? carousel.dataset.playLabel : carousel.dataset.pauseLabel;
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("title", label);
      const icon = toggle.querySelector("i");
      icon?.classList.toggle("fa-play", userPaused);
      icon?.classList.toggle("fa-pause", !userPaused);
      startTimer();
    });

    carousel.addEventListener("mouseenter", () => {
      hovering = true;
      stopTimer();
    });
    carousel.addEventListener("mouseleave", () => {
      hovering = false;
      startTimer();
    });
    carousel.addEventListener("focusin", () => {
      focused = true;
      stopTimer();
    });
    carousel.addEventListener("focusout", () => {
      window.requestAnimationFrame(() => {
        focused = carousel.contains(document.activeElement);
        startTimer();
      });
    });
    document.addEventListener("visibilitychange", startTimer);
    reduceMotion.addEventListener?.("change", startTimer);

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          visible = entry.isIntersecting;
          startTimer();
        },
        { threshold: 0.25 },
      );
      observer.observe(carousel);
    }

    window.addEventListener("resize", () => goTo(current, "auto"), { passive: true });
    updateState(0);
    startTimer();
  });
})();
