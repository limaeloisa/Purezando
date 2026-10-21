(() => {
  const layout = document.querySelector("#admin-layout");
  const toggle = document.querySelector("#admin-sidebar-toggle");
  const sidebar = document.querySelector("#admin-sidebar");
  const backdrop = document.querySelector("#admin-backdrop");
  if (!layout || !toggle || !sidebar || !backdrop) return;

  function setOpen(open) {
    layout.classList.toggle("sidebar-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    backdrop.hidden = !open;
  }

  const navigationLinks = [...sidebar.querySelectorAll(".admin-nav-link")];
  const currentSection = document.querySelector("#admin-current-section");

  function updateCurrentSection() {
    const sectionId = window.location.hash.slice(1) || "dashboard";
    const activeLink = navigationLinks.find((link) => link.hash === `#${sectionId}`)
      || navigationLinks[0];

    navigationLinks.forEach((link) => {
      const active = link === activeLink;
      link.classList.toggle("active", active);
      if (active) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    if (currentSection && activeLink) {
      currentSection.textContent = activeLink.textContent.trim();
    }
  }

  toggle.addEventListener("click", () => {
    setOpen(!layout.classList.contains("sidebar-open"));
  });

  navigationLinks.forEach((link) => {
    link.addEventListener("click", () => {
      updateCurrentSection();
      setOpen(false);
    });
  });

  backdrop.addEventListener("click", () => setOpen(false));

  window.addEventListener("hashchange", updateCurrentSection);
  updateCurrentSection();

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
})();