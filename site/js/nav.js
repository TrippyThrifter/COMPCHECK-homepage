(function () {
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");

  if (!toggle || !nav) {
    return;
  }

  var label = toggle.querySelector(".nav-toggle-label");

  function setOpen(open, returnFocus) {
    var wasOpen = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    nav.classList.toggle("is-open", open);
    if (label) {
      label.textContent = open ? "Close" : "Menu";
    }
    if (!open && wasOpen && returnFocus) {
      toggle.focus();
    }
  }

  toggle.addEventListener("click", function () {
    var open = toggle.getAttribute("aria-expanded") === "true";
    setOpen(!open, false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setOpen(false, true);
    }
  });

  document.addEventListener("click", function (event) {
    if (toggle.getAttribute("aria-expanded") !== "true") {
      return;
    }
    var target = event.target;
    if (!target || typeof target.nodeType !== "number") {
      return;
    }
    var element = target.nodeType === 1 ? target : target.parentElement;
    if (!element) {
      return;
    }
    if (nav.contains(element) || toggle.contains(element)) {
      return;
    }
    setOpen(false, false);
  });

  nav.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || typeof target.nodeType !== "number") {
      return;
    }
    var element = target.nodeType === 1 ? target : target.parentElement;
    if (element && element.closest("a")) {
      setOpen(false, false);
    }
  });

  var desktop = window.matchMedia("(min-width: 760px)");

  function closeIfDesktop() {
    if (desktop.matches) {
      setOpen(false, false);
    }
  }

  if (typeof desktop.addEventListener === "function") {
    desktop.addEventListener("change", closeIfDesktop);
  } else if (typeof desktop.addListener === "function") {
    desktop.addListener(closeIfDesktop);
  }
})();
