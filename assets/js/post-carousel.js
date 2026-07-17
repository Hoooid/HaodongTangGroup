(() => {
  const carousels = document.querySelectorAll("[data-np-post-carousel]");

  carousels.forEach((carousel) => {
    const viewport = carousel.querySelector("[data-np-carousel-viewport]");
    const track = carousel.querySelector(".np-post-carousel-track");
    const slides = Array.from(carousel.querySelectorAll("[data-np-carousel-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-np-carousel-dot]"));
    const previous = carousel.querySelector("[data-np-carousel-previous]");
    const next = carousel.querySelector("[data-np-carousel-next]");
    const toggle = carousel.querySelector("[data-np-carousel-toggle]");
    const currentLabel = carousel.querySelector("[data-np-carousel-current]");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const interval = Number(carousel.dataset.autoplay) || 6500;

    if (!viewport || !track || slides.length === 0) return;

    let loopClone = track.querySelector("[data-np-carousel-clone]");
    if (slides.length > 1 && !loopClone) {
      loopClone = slides[0].cloneNode(true);
      loopClone.removeAttribute("id");
      loopClone.removeAttribute("data-np-carousel-slide");
      loopClone.setAttribute("data-np-carousel-clone", "first");
      loopClone.setAttribute("aria-hidden", "true");
      const cloneLink = loopClone.querySelector("a");
      if (cloneLink) cloneLink.tabIndex = -1;
      track.append(loopClone);
    }

    let current = 0;
    let timer = null;
    let userPaused = false;
    let hovering = false;
    let focused = false;
    let visible = true;
    let wrapping = false;
    let scrollFrame = null;
    let wrapResetTimer = null;

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
      !wrapping &&
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

    const jumpTo = (left) => {
      const previousBehavior = viewport.style.scrollBehavior;
      viewport.style.scrollBehavior = "auto";
      viewport.scrollLeft = left;
      viewport.style.scrollBehavior = previousBehavior;
    };

    const resetForwardLoop = () => {
      window.clearTimeout(wrapResetTimer);
      wrapResetTimer = null;
      jumpTo(0);
      wrapping = false;
      updateState(0);
      startTimer();
    };

    const goTo = (index, behavior = "smooth") => {
      if (wrapping) return;

      const forwardWrap =
        Boolean(loopClone) &&
        current === slides.length - 1 &&
        index >= slides.length;
      const target = forwardWrap
        ? slides.length
        : (index + slides.length) % slides.length;

      wrapping = forwardWrap;
      const targetLeft = target * viewport.clientWidth;
      if (reduceMotion.matches || behavior === "auto") {
        jumpTo(targetLeft);
      } else {
        viewport.scrollTo({ left: targetLeft, behavior });
      }
      updateState(forwardWrap ? 0 : target);

      if (forwardWrap && reduceMotion.matches) {
        resetForwardLoop();
        return;
      }

      startTimer();
    };

    viewport.addEventListener(
      "scroll",
      () => {
        if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
        scrollFrame = window.requestAnimationFrame(() => {
          const rawIndex = Math.round(viewport.scrollLeft / Math.max(viewport.clientWidth, 1));

          if (loopClone && rawIndex >= slides.length) {
            wrapping = true;
            stopTimer();
            updateState(0);
            window.clearTimeout(wrapResetTimer);
            wrapResetTimer = window.setTimeout(resetForwardLoop, 140);
            return;
          }

          if (!wrapping) updateState(rawIndex);
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

    window.addEventListener(
      "resize",
      () => {
        window.clearTimeout(wrapResetTimer);
        wrapping = false;
        goTo(current, "auto");
      },
      { passive: true },
    );
    updateState(0);
    startTimer();
  });
})();
