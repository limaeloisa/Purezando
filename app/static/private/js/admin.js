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

  toggle.addEventListener("click", () => {
    setOpen(!layout.classList.contains("sidebar-open"));
  });

  sidebar.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setOpen(false));
  });

  backdrop.addEventListener("click", () => setOpen(false));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
})();