const form = document.getElementById("shorten-form");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");
const shortLink = document.getElementById("short-link");
const statsLink = document.getElementById("stats-link");
const copyButton = document.getElementById("copy");

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  result.hidden = true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  const body = { url: form.url.value.trim() };
  if (form.alias.value.trim()) body.alias = form.alias.value.trim();
  if (form.expires.value) body.expires_in_days = Number(form.expires.value);

  let response;
  try {
    response = await fetch("/api/links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    showError("Could not reach the server. Check your connection and try again.");
    return;
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    showError(data.error || "Something went wrong. Try again.");
    return;
  }

  shortLink.textContent = data.short_url;
  shortLink.href = data.short_url;
  statsLink.href = data.stats_url;
  copyButton.textContent = "Copy";
  result.hidden = false;
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(shortLink.textContent);
    copyButton.textContent = "Copied";
  } catch {
    copyButton.textContent = "Press Ctrl+C";
  }
});
