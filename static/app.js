const form = document.querySelector("#shorten-form");
const input = document.querySelector("#url-input");
const customCodeInput = document.querySelector("#custom-code-input");
const submitButton = document.querySelector("#shorten-button");
const message = document.querySelector("#form-message");
const resultPanel = document.querySelector("#result-panel");
const resultLink = document.querySelector("#result-link");
const resultOriginal = document.querySelector("#result-original");
const copyButton = document.querySelector("#copy-button");
const copyLabel = document.querySelector("#copy-label");
const historyBody = document.querySelector("#history-body");
const emptyState = document.querySelector("#empty-state");
const historyTotal = document.querySelector("#history-total");
const linkCount = document.querySelector("#link-count");

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("is-error", isError);
}

function safeHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function shortUrlFor(item) {
  return item.short_url.startsWith("http") ? item.short_url : new URL(item.short_url, window.location.origin).href;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

async function copyText(value, button, label) {
  try {
    await navigator.clipboard.writeText(value);
    if (label) {
      label.textContent = "Copied";
      window.setTimeout(() => { label.textContent = "Copy link"; }, 1600);
    } else {
      button.textContent = "✓";
      window.setTimeout(() => { button.textContent = "▢"; }, 1600);
    }
  } catch {
    if (label) label.textContent = "Copy failed";
  }
}

function renderHistory(items) {
  historyBody.replaceChildren();
  emptyState.hidden = items.length > 0;
  historyTotal.textContent = `(${items.length})`;
  linkCount.textContent = `${String(items.length).padStart(2, "0")} LINKS`;

  for (const item of items) {
    const row = document.createElement("tr");
    const shortCell = document.createElement("td");
    const shortAnchor = document.createElement("a");
    shortAnchor.href = shortUrlFor(item);
    shortAnchor.target = "_blank";
    shortAnchor.rel = "noopener noreferrer";
    shortAnchor.textContent = new URL(shortAnchor.href).host + new URL(shortAnchor.href).pathname;
    shortCell.append(shortAnchor);

    const originalCell = document.createElement("td");
    const originalUrl = safeHttpUrl(item.original_url);
    originalCell.textContent = originalUrl ?? item.original_url;
    originalCell.title = item.original_url;

    const clicksCell = document.createElement("td");
    clicksCell.className = "history-clicks";
    clicksCell.textContent = String(item.click_count ?? 0);

    const dateCell = document.createElement("td");
    dateCell.textContent = formatDate(item.created_at);

    const actionCell = document.createElement("td");
    const rowCopy = document.createElement("button");
    rowCopy.className = "table-copy";
    rowCopy.type = "button";
    rowCopy.textContent = "▢";
    rowCopy.setAttribute("aria-label", "Copy short link");
    rowCopy.title = "Copy short link";
    rowCopy.addEventListener("click", () => copyText(shortAnchor.href, rowCopy));
    actionCell.append(rowCopy);

    row.append(shortCell, originalCell, clicksCell, dateCell, actionCell);
    historyBody.append(row);
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/urls");
    if (!response.ok) throw new Error("Could not load link history.");
    renderHistory(await response.json());
  } catch {
    showMessage("Could not load saved links. Check that the server is running.", true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const normalizedUrl = safeHttpUrl(input.value.trim());
  if (!normalizedUrl) {
    showMessage("Enter a complete URL beginning with http:// or https://.", true);
    input.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.querySelector("span:first-child").textContent = "Shortening…";
  showMessage("Making your link…");
  try {
    const customCode = customCodeInput.value.trim();
    const payload = { url: normalizedUrl };
    if (customCode) payload.custom_code = customCode;
    const response = await fetch("/api/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "That URL could not be shortened.");

    resultLink.href = data.short_url;
    resultLink.textContent = data.short_url.replace(/^https?:\/\//, "");
    resultOriginal.textContent = data.original_url;
    resultPanel.hidden = false;
    showMessage("Your link is ready.");
    await loadHistory();
  } catch (error) {
    showMessage(error.message || "Something went wrong. Please try again.", true);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span:first-child").textContent = "Shorten link";
  }
});

copyButton.addEventListener("click", () => copyText(resultLink.href, copyButton, copyLabel));
document.querySelector("#refresh-button").addEventListener("click", loadHistory);
loadHistory();