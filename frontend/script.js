const API_URL = "http://127.0.0.1:8001";

// =====================================
// DOM ELEMENTS
// =====================================

const dashboardSection = document.getElementById("dashboardSection");
const chatSection = document.getElementById("chatSection");

const dashboardBtn = document.getElementById("dashboardBtn");
const chatBtn = document.getElementById("chatBtn");
const chatBtnHero = document.getElementById("chatBtnHero");

const pdfInput = document.getElementById("pdfInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadStatus = document.getElementById("uploadStatus");

const documentList = document.getElementById("documentList");
const documentCount = document.getElementById("documentCount");
const refreshBtn = document.getElementById("refreshBtn");

const documentSelect = document.getElementById("documentSelect");

const questionInput = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const chatMessages = document.getElementById("chatMessages");

const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const themeText = document.getElementById("themeText");

// Remember the starting chat view (welcome message) so "New chat" can restore it
const initialChatHTML = chatMessages.innerHTML;


// =====================================
// 0. EXTRA STYLES (added from here, so no CSS file changes are needed)
// =====================================

(function injectStyles() {
    const style = document.createElement("style");

    style.textContent = `
        .source-item.clickable { cursor: pointer; transition: transform .15s ease, filter .15s ease; }
        .source-item.clickable:hover { filter: brightness(1.25); transform: translateY(-1px); }
        .source-item.clickable:focus-visible { outline: 2px solid #8b6cff; outline-offset: 2px; }

        .msg-actions { display: flex; gap: 8px; margin-top: 10px; }
        .msg-action-btn {
            background: transparent; color: inherit; cursor: pointer;
            border: 1px solid rgba(140, 120, 255, 0.35); border-radius: 8px;
            padding: 3px 10px; font-size: 12px; opacity: .75;
        }
        .msg-action-btn:hover { opacity: 1; background: rgba(140, 120, 255, 0.15); }

        .stop-btn {
            display: none; margin-left: 8px; cursor: pointer; font: inherit; font-size: 14px;
            padding: 10px 16px; border-radius: 12px; color: #f87171;
            background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.45);
        }
        .stop-btn.visible { display: inline-flex; align-items: center; }
        .stop-btn:hover { background: rgba(248, 113, 113, 0.22); }

        .chat-toolbar { display: flex; justify-content: flex-end; margin-bottom: 10px; }

        .summary-card {
            margin-top: 18px; padding: 16px 18px; border-radius: 14px;
            border: 1px solid rgba(140, 120, 255, 0.35); background: rgba(140, 120, 255, 0.08);
            text-align: left;
        }
        .summary-card h4 { margin: 0 0 6px; font-size: 14px; letter-spacing: .02em; }
        .summary-card p { margin: 0 0 12px; font-size: 14px; line-height: 1.5; opacity: .9; }
        .summary-hint { margin: 0 0 8px; font-size: 12px; opacity: .65; }
        .summary-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .summary-chip {
            cursor: pointer; font: inherit; font-size: 13px; color: inherit;
            padding: 7px 12px; border-radius: 999px;
            border: 1px solid rgba(140, 120, 255, 0.45); background: rgba(140, 120, 255, 0.12);
        }
        .summary-chip:hover { background: rgba(140, 120, 255, 0.28); }
    `;

    document.head.appendChild(style);
})();


// =====================================
// 1. NAVIGATION
// =====================================

function showDashboard() {
    dashboardSection.classList.remove("hidden");
    chatSection.classList.add("hidden");

    dashboardBtn.classList.add("active");
    chatBtn.classList.remove("active");
}

function showChat() {
    dashboardSection.classList.add("hidden");
    chatSection.classList.remove("hidden");

    chatBtn.classList.add("active");
    dashboardBtn.classList.remove("active");

    questionInput.focus();
}

dashboardBtn.addEventListener("click", showDashboard);
chatBtn.addEventListener("click", showChat);

if (chatBtnHero) {
    chatBtnHero.addEventListener("click", showChat);
}


// =====================================
// 2. DARK / LIGHT THEME
// =====================================

let currentTheme = localStorage.getItem("omnidoc-theme") || "dark";

function applyTheme(theme) {
    currentTheme = theme;

    document.documentElement.setAttribute("data-theme", theme);

    localStorage.setItem("omnidoc-theme", theme);

    updateThemeButton();
}

function updateThemeButton() {
    if (!themeToggle || !themeIcon || !themeText) return;

    if (currentTheme === "dark") {
        themeIcon.textContent = "☀";
        themeText.textContent = "Light mode";
        themeToggle.title = "Switch to light mode";
    } else {
        themeIcon.textContent = "☾";
        themeText.textContent = "Dark mode";
        themeToggle.title = "Switch to dark mode";
    }
}

applyTheme(currentTheme);

if (themeToggle) {
    themeToggle.addEventListener("click", () => {
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(newTheme);
    });
}


// =====================================
// 3. LOAD DOCUMENTS
// =====================================

async function loadDocuments() {
    documentList.innerHTML =
        '<p class="empty-message">Loading documents...</p>';

    refreshBtn.disabled = true;
    refreshBtn.textContent = "Loading...";

    try {
        const response = await fetch(`${API_URL}/documents`);

        if (!response.ok) {
            throw new Error("Could not load documents.");
        }

        const data = await response.json();

        documentCount.textContent = data.total_documents;

        documentList.innerHTML = "";

        const previousSelection = documentSelect.value;

        documentSelect.innerHTML =
            '<option value="">All documents</option>';

        if (!data.documents || data.documents.length === 0) {
            documentList.innerHTML =
                '<p class="empty-message">No documents uploaded yet.</p>';

            return;
        }

        data.documents.forEach(doc => {
            // Document card
            const card = document.createElement("div");
            card.className = "document-item";

            const info = document.createElement("div");
            info.className = "document-info";

            const icon = document.createElement("span");
            icon.className = "pdf-icon";
            icon.textContent = "📄";

            const details = document.createElement("div");

            const name = document.createElement("div");
            name.className = "document-name";
            name.textContent = doc.filename;

            const size = document.createElement("div");
            size.className = "document-size";
            size.textContent = `${doc.size_kb} KB`;

            details.append(name, size);
            info.append(icon, details);

            const deleteBtn = document.createElement("button");
            deleteBtn.className = "delete-btn";
            deleteBtn.textContent = "Delete";
            deleteBtn.type = "button";

            deleteBtn.addEventListener("click", () => {
                deleteDocument(doc.filename);
            });

            card.append(info, deleteBtn);
            documentList.appendChild(card);

            // Document dropdown
            const option = document.createElement("option");
            option.value = doc.filename;
            option.textContent = doc.filename;

            documentSelect.appendChild(option);
        });

        // Preserve previous selection if document still exists
        if (
            previousSelection &&
            data.documents.some(doc => doc.filename === previousSelection)
        ) {
            documentSelect.value = previousSelection;
        }

    } catch (error) {
        documentList.innerHTML =
            '<p class="empty-message">Could not connect to the backend. Check whether FastAPI is running.</p>';

        console.error("Document loading error:", error);

    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "↻ Refresh";
    }
}


// =====================================
// 4. PDF UPLOAD (returns instantly, indexing continues in the background)
// =====================================

let statusTimer = null;

function stopStatusPolling() {
    if (statusTimer) {
        clearInterval(statusTimer);
        statusTimer = null;
    }
}

// ----- summary card with suggested questions -----

function removeSummaryCard() {
    document.querySelectorAll(".summary-card").forEach(card => card.remove());
}

function showSummaryCard(filename, data) {
    removeSummaryCard();

    const card = document.createElement("div");
    card.className = "summary-card";

    const title = document.createElement("h4");
    title.textContent = `✨ About ${filename}`;

    const summary = document.createElement("p");
    summary.textContent = data.summary;

    card.append(title, summary);

    if (data.questions && data.questions.length > 0) {
        const hint = document.createElement("div");
        hint.className = "summary-hint";
        hint.textContent = "Try asking:";

        const chips = document.createElement("div");
        chips.className = "summary-chips";

        data.questions.forEach(question => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "summary-chip";
            chip.textContent = question;

            chip.addEventListener("click", () => {
                // Search only inside this document, then ask
                const hasOption = Array.from(documentSelect.options)
                    .some(option => option.value === filename);

                if (hasOption) {
                    documentSelect.value = filename;
                }

                showChat();
                questionInput.value = question;
                askQuestion();
            });

            chips.appendChild(chip);
        });

        card.append(hint, chips);
    }

    // Place the card just below the upload box
    const parent = uploadStatus.parentElement;
    const anchor =
        (parent && parent.closest("[class*='upload'], [class*='drop']")) ||
        parent ||
        uploadStatus;

    anchor.insertAdjacentElement("afterend", card);
}

// Returns true once there is nothing more to wait for (shown, failed, or not coming)
async function checkSummary(filename) {
    const response = await fetch(
        `${API_URL}/summary/${encodeURIComponent(filename)}`
    );

    if (!response.ok) return true;

    const data = await response.json();

    if (data.ready) {
        showSummaryCard(filename, data);
        return true;
    }

    return Boolean(data.finished);
}

function pollStatus(filename) {
    stopStatusPolling();

    let summaryDone = false;

    statusTimer = setInterval(async () => {
        try {
            const response = await fetch(
                `${API_URL}/status/${encodeURIComponent(filename)}`
            );

            if (!response.ok) return;

            const info = await response.json();

            if (!summaryDone) {
                summaryDone = await checkSummary(filename);
            }

            let finished = false;

            if (info.stage === "done") {
                let message = `✅ ${filename} is fully indexed and ready.`;

                if (info.warnings && info.warnings.length > 0) {
                    message += ` (${info.warnings.join(", ")})`;
                }

                uploadStatus.textContent = message;
                finished = true;

            } else if (info.stage === "error") {
                uploadStatus.textContent = `❌ ${info.error || "Indexing failed."}`;
                finished = true;

            } else if (
                info.stage === "tables" ||
                info.stage === "summary" ||
                info.stage === "images"
            ) {
                uploadStatus.textContent =
                    `${info.label} Text is ready, so you can already start asking questions.`;

            } else {
                uploadStatus.textContent = info.label;
            }

            if (finished && summaryDone) {
                stopStatusPolling();
            }

        } catch (error) {
            // Backend is busy; try again on the next tick
        }
    }, 2000);
}

uploadBtn.addEventListener("click", () => {
    pdfInput.click();
});

pdfInput.addEventListener("change", async () => {
    const file = pdfInput.files[0];

    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        uploadStatus.textContent = "Please select a PDF file.";
        pdfInput.value = "";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadBtn.disabled = true;
    uploadBtn.textContent = "Uploading...";
    uploadStatus.textContent = "Uploading PDF...";
    removeSummaryCard();

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Upload failed.");
        }

        uploadStatus.textContent =
            "Uploaded! Indexing has started in the background...";

        await loadDocuments();

        pollStatus(data.filename);

    } catch (error) {
        uploadStatus.textContent = error.message;
        console.error("Upload error:", error);

    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = "<span>↑</span> Choose PDF";
        pdfInput.value = "";
    }
});


// =====================================
// 5. DELETE DOCUMENT
// =====================================

async function deleteDocument(filename) {
    const confirmed = confirm(
        `Are you sure you want to delete "${filename}"?`
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API_URL}/documents/${encodeURIComponent(filename)}`,
            {
                method: "DELETE"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Deletion failed.");
        }

        alert(data.message || "Document deleted successfully.");

        removeSummaryCard();

        await loadDocuments();

    } catch (error) {
        alert(error.message);
        console.error("Delete error:", error);
    }
}


// =====================================
// 6. DISPLAY CHAT MESSAGES
// =====================================

function addMessage(role, content) {
    const message = document.createElement("div");

    // Use ai class for assistant messages to match existing CSS
    const cssRole = role === "assistant" ? "ai" : role;

    message.className = `message ${cssRole}`;

    const label = document.createElement("div");
    label.className = "message-label";

    label.textContent = role === "user" ? "You" : "OmniDoc AI";

    const text = document.createElement("div");
    text.className = "message-content";

    // textContent prevents HTML injection from model responses
    text.textContent = content;

    message.append(label, text);
    chatMessages.appendChild(message);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;
}

async function copyText(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        // Fallback for browsers that block the clipboard API
        try {
            const box = document.createElement("textarea");
            box.value = text;
            box.style.position = "fixed";
            box.style.opacity = "0";
            document.body.appendChild(box);
            box.select();
            const ok = document.execCommand("copy");
            box.remove();
            return ok;
        } catch (e) {
            return false;
        }
    }
}

// Adds a "Copy" button under an assistant answer
function addCopyButton(messageEl, getText) {
    const row = document.createElement("div");
    row.className = "msg-actions";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "msg-action-btn";
    copyBtn.textContent = "📋 Copy";

    copyBtn.addEventListener("click", async () => {
        const ok = await copyText(getText());

        copyBtn.textContent = ok ? "✅ Copied" : "Copy failed";

        setTimeout(() => {
            copyBtn.textContent = "📋 Copy";
        }, 1500);
    });

    row.appendChild(copyBtn);
    messageEl.appendChild(row);
}


// =====================================
// 7. DISPLAY SOURCE REFERENCES (click to open the PDF at that page)
// =====================================

function pdfUrl(source) {
    if (!source || !source.source || source.source === "Unknown") return null;

    const base = `${API_URL}/pdfs/${encodeURIComponent(source.source)}`;
    const page = Number(source.page);

    return Number.isInteger(page) && page > 0 ? `${base}#page=${page}` : base;
}

function addSources(sources) {
    if (!sources || sources.length === 0) return;

    const container = document.createElement("div");
    container.className = "message ai source-message";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "REFERENCES";

    const sourceList = document.createElement("div");
    sourceList.className = "source-list";

    sources.forEach((source, index) => {
        const item = document.createElement("div");
        item.className = "source-item";

        const url = pdfUrl(source);

        if (url) {
            item.classList.add("clickable");
            item.tabIndex = 0;
            item.setAttribute("role", "link");
            item.title = `Open ${source.source} at page ${source.page}`;

            const openPdf = () => window.open(url, "_blank", "noopener");

            item.addEventListener("click", openPdf);

            item.addEventListener("keydown", event => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openPdf();
                }
            });
        }

        const number = document.createElement("span");
        number.className = "source-number";
        number.textContent = `[${index + 1}]`;

        const details = document.createElement("span");
        details.className = "source-details";

        details.textContent =
            `${source.source || "Document"} · Page ${source.page ?? "N/A"} · ${source.type || "Content"}` +
            (url ? " ↗" : "");

        item.append(number, details);
        sourceList.appendChild(item);
    });

    container.append(label, sourceList);
    chatMessages.appendChild(container);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// =====================================
// 8. AI LOADING INDICATOR
// =====================================

function showLoadingMessage() {
    const message = document.createElement("div");
    message.className = "message ai loading-message";
    message.id = "aiLoadingMessage";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "OmniDoc AI";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = "Let me check your documents... 🔍";

    message.append(label, content);
    chatMessages.appendChild(message);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoadingMessage() {
    const loading = document.getElementById("aiLoadingMessage");

    if (loading) {
        loading.remove();
    }
}


// =====================================
// 9. ASK AI (streams the answer, remembers the last few turns, can be stopped)
// =====================================

// Last few question/answer pairs, so follow-ups like "give formula for this rate" work
const chatHistory = [];
const MAX_HISTORY_MESSAGES = 4;

let currentAbort = null;   // lets the Stop button cancel the request
let chatEpoch = 0;         // increases on "New chat" so old requests stop touching the page

// Stop button (next to Ask AI)
const stopBtn = document.createElement("button");
stopBtn.type = "button";
stopBtn.className = "stop-btn";
stopBtn.textContent = "■ Stop";
askBtn.insertAdjacentElement("afterend", stopBtn);

stopBtn.addEventListener("click", () => {
    if (currentAbort) {
        currentAbort.abort();
    }
});

// New chat button (above the messages)
const chatToolbar = document.createElement("div");
chatToolbar.className = "chat-toolbar";

const newChatBtn = document.createElement("button");
newChatBtn.type = "button";
newChatBtn.className = "msg-action-btn";
newChatBtn.textContent = "＋ New chat";

chatToolbar.appendChild(newChatBtn);
chatMessages.insertAdjacentElement("beforebegin", chatToolbar);

newChatBtn.addEventListener("click", () => {
    chatEpoch += 1;

    if (currentAbort) {
        currentAbort.abort();
    }

    chatHistory.length = 0;
    chatMessages.innerHTML = initialChatHTML;
    questionInput.value = "";
    questionInput.focus();
});

// Turns leftover LaTeX like $f_s = 2B$ into plain readable text
function cleanMath(text) {
    return text
        .replace(/\\\[|\\\]|\\\(|\\\)/g, "")
        .replace(/\$\$?/g, "")
        .replace(/\\text\{([^}]*)\}/g, "$1")
        .replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, "($1)/($2)")
        .replace(/_\{([^}]*)\}/g, "_$1")
        .replace(/\^\{([^}]*)\}/g, "^$1")
        .replace(/\\times/g, "×")
        .replace(/\\cdot/g, "·")
        .replace(/\\le(q)?\b/g, "≤")
        .replace(/\\ge(q)?\b/g, "≥")
        .replace(/\\approx/g, "≈")
        .replace(/\\pi\b/g, "π")
        .replace(/\\infty/g, "∞")
        .replace(/\\,/g, " ");
}

async function askQuestion() {
    const question = questionInput.value.trim();

    if (!question || askBtn.disabled) return;

    const selectedDocument = documentSelect.value || null;

    // Remove welcome message
    const welcome = chatMessages.querySelector(".welcome-message");

    if (welcome) {
        welcome.remove();
    }

    addMessage("user", question);

    questionInput.value = "";
    askBtn.disabled = true;
    askBtn.textContent = "Thinking...";
    stopBtn.classList.add("visible");

    showLoadingMessage();

    const epoch = chatEpoch;
    currentAbort = new AbortController();

    let answerMessage = null;   // the reply that is being streamed
    let answerBox = null;       // its text element
    let answerText = "";

    function handleEvent(event) {
        if (epoch !== chatEpoch) return;   // chat was reset meanwhile

        if (event.type === "token") {
            if (!answerBox) {
                removeLoadingMessage();
                answerMessage = addMessage("assistant", "");
                answerBox = answerMessage.querySelector(".message-content");
            }

            answerText += event.text;
            answerBox.textContent = cleanMath(answerText);
            chatMessages.scrollTop = chatMessages.scrollHeight;

        } else if (event.type === "not_found") {
            removeLoadingMessage();
            addMessage("assistant", event.text);

        } else if (event.type === "sources") {
            addSources(event.sources);

        } else if (event.type === "error") {
            removeLoadingMessage();
            addMessage("assistant", `Error: ${event.text}`);
        }
    }

    try {
        const response = await fetch(`${API_URL}/ask_stream`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            signal: currentAbort.signal,

            body: JSON.stringify({
                question: question,
                document: selectedDocument,
                history: chatHistory.slice(-MAX_HISTORY_MESSAGES)
            })
        });

        if (!response.ok) {
            let detail = "Question failed.";

            try {
                const data = await response.json();
                detail = data.detail || detail;
            } catch (e) {
                // response had no JSON body
            }

            throw new Error(detail);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n");
            buffer = lines.pop();   // keep the unfinished line

            for (const line of lines) {
                if (line.trim()) {
                    handleEvent(JSON.parse(line));
                }
            }
        }

        if (buffer.trim()) {
            handleEvent(JSON.parse(buffer));
        }

        if (epoch === chatEpoch) {
            removeLoadingMessage();

            if (answerMessage && answerText.trim()) {
                addCopyButton(answerMessage, () => cleanMath(answerText));

                // Remember this exchange, but only when it was actually answered
                chatHistory.push({ role: "user", content: question });
                chatHistory.push({
                    role: "assistant",
                    content: cleanMath(answerText)
                });
            }
        }

    } catch (error) {
        if (epoch === chatEpoch) {
            removeLoadingMessage();

            if (error.name === "AbortError") {
                // The user pressed Stop: keep what was written so far
                if (answerBox) {
                    answerBox.textContent = cleanMath(answerText) + "\n\n⏹️ (stopped)";
                    addCopyButton(answerMessage, () => cleanMath(answerText));
                } else {
                    addMessage("assistant", "⏹️ Stopped.");
                }

            } else {
                addMessage("assistant", `Error: ${error.message}`);
                console.error("AI question error:", error);
            }
        }

    } finally {
        currentAbort = null;
        stopBtn.classList.remove("visible");
        askBtn.disabled = false;
        askBtn.innerHTML = 'Ask AI <span>↑</span>';
        questionInput.focus();
    }
}

askBtn.addEventListener("click", askQuestion);


// =====================================
// 10. ENTER TO SEND
// =====================================

questionInput.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
    }
});


// =====================================
// 11. CLICKABLE SUGGESTIONS
// =====================================

chatMessages.addEventListener("click", event => {
    const suggestion = event.target.closest(".suggestion-pills span");

    if (!suggestion) return;

    questionInput.value = suggestion.textContent.trim();
    questionInput.focus();
});


// =====================================
// 12. REFRESH DOCUMENTS
// =====================================

refreshBtn.addEventListener("click", loadDocuments);


// =====================================
// 13. INITIALIZE APPLICATION
// =====================================

loadDocuments();

console.log("OmniDoc AI frontend initialized successfully.");