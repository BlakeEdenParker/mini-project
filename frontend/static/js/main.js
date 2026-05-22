document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const message = form.getAttribute("data-confirm") || "계속 진행할까요?";
    if (!window.confirm(message)) {
      event.preventDefault();
    }
  });
});

