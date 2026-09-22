(function () {
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("site-menu");
  if (!toggle || !menu) {
    return;
  }

  var label = toggle.querySelector(".nav-toggle-text");
  var desktop = window.matchMedia("(min-width: 960px)");

  function setOpen(open) {
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    menu.classList.toggle("is-open", open);
    if (label) {
      label.textContent = open ? "Close" : "Menu";
    }
  }

  toggle.addEventListener("click", function () {
    var open = toggle.getAttribute("aria-expanded") === "true";
    setOpen(!open);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener("click", function (event) {
    if (toggle.getAttribute("aria-expanded") !== "true") {
      return;
    }
    if (!menu.contains(event.target) && !toggle.contains(event.target)) {
      setOpen(false);
    }
  });

  menu.addEventListener("click", function (event) {
    if (event.target.closest("a")) {
      setOpen(false);
    }
  });

  function closeOnDesktop() {
    if (desktop.matches) {
      setOpen(false);
    }
  }

  if (typeof desktop.addEventListener === "function") {
    desktop.addEventListener("change", closeOnDesktop);
  } else if (typeof desktop.addListener === "function") {
    desktop.addListener(closeOnDesktop);
  }
})();
