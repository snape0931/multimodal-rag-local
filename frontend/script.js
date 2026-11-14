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

const accentPicker = document.getElementById("accentPicker");

const chatLayout = document.getElementById("chatLayout");
const splitBtn = document.getElementById("splitBtn");
const pdfPane = document.getElementById("pdfPane");
const pdfFrame = document.getElementById("pdfFrame");
const pdfEmpty = document.getElementById("pdfEmpty");
const pdfPaneTitle = document.getElementById("pdfPaneTitle");
const pdfOpenTab = document.getElementById("pdfOpenTab");
const pdfClose = document.getElementById("pdfClose");

const uploadCard = document.querySelector(".upload-card");
const pageFlip = document.getElementById("pageFlip");

const paletteBackdrop = document.getElementById("paletteBackdrop");
const paletteInput = document.getElementById("paletteInput");
const paletteList = document.getElementById("paletteList");
const paletteBtn = document.getElementById("paletteBtn");

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
        .source-item.clickable:focus-visible { outline: 2px solid var(--purple); outline-offset: 2px; }

        .msg-actions { display: flex; gap: 8px; margin-top: 10px; }
        .msg-action-btn {
            background: transparent; color: inherit; cursor: pointer;
            border: 1px solid hsl(var(--accent-hue) 100% 74% / 0.35); border-radius: 8px;
            padding: 3px 10px; font-size: 12px; opacity: .75;
        }
        .msg-action-btn:hover { opacity: 1; background: hsl(var(--accent-hue) 100% 74% / 0.15); }

        .stop-btn {
            display: none; margin-left: 8px; cursor: pointer; font: inherit; font-size: 14px;
            padding: 10px 16px; border-radius: 12px; color: #f87171;
            background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.45);
        }
        .stop-btn.visible { display: inline-flex; align-items: center; }
        .stop-btn:hover { background: rgba(248, 113, 113, 0.22); }

        .summary-card {
            margin-top: 18px; padding: 16px 18px; border-radius: 14px;
            border: 1px solid hsl(var(--accent-hue) 100% 74% / 0.35); background: hsl(var(--accent-hue) 100% 74% / 0.08);
            text-align: left;
        }
        .summary-card h4 { margin: 0 0 6px; font-size: 14px; letter-spacing: .02em; }
        .summary-card p { margin: 0 0 12px; font-size: 14px; line-height: 1.5; opacity: .9; }
        .summary-hint { margin: 0 0 8px; font-size: 12px; opacity: .65; }
        .summary-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .summary-chip {
            cursor: pointer; font: inherit; font-size: 13px; color: inherit;
            padding: 7px 12px; border-radius: 999px;
            border: 1px solid hsl(var(--accent-hue) 100% 74% / 0.45); background: hsl(var(--accent-hue) 100% 74% / 0.12);
        }
        .summary-chip:hover { background: hsl(var(--accent-hue) 100% 74% / 0.28); }
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
// 2b. ACCENT COLOURS (purple / teal / sunset)
// =====================================

const ACCENTS = ["purple", "teal", "sunset"];

let currentAccent = localStorage.getItem("omnidoc-accent") || "purple";

function applyAccent(name) {
    if (!ACCENTS.includes(name)) name = "purple";

    currentAccent = name;

    document.documentElement.setAttribute("data-accent", name);
    localStorage.setItem("omnidoc-accent", name);

    if (accentPicker) {
        accentPicker.querySelectorAll("button").forEach(button => {
            button.classList.toggle("active", button.dataset.accent === name);
        });
    }
}

applyAccent(currentAccent);

if (accentPicker) {
    accentPicker.addEventListener("click", event => {
        const button = event.target.closest("button[data-accent]");

        if (button) applyAccent(button.dataset.accent);
    });
}


// =====================================
// 3. LOAD DOCUMENTS
// =====================================

// Shimmering placeholder cards while the list loads
function showDocumentSkeleton(count = 4) {
    documentList.innerHTML = "";

    for (let i = 0; i < count; i++) {
        const card = document.createElement("div");
        card.className = "document-item skeleton-card";

        const icon = document.createElement("div");
        icon.className = "skeleton skeleton-icon";

        const lines = document.createElement("div");
        lines.className = "skeleton-lines";

        const long = document.createElement("div");
        long.className = "skeleton skeleton-line";

        const short = document.createElement("div");
        short.className = "skeleton skeleton-line short";

        lines.append(long, short);
        card.append(icon, lines);
        documentList.appendChild(card);
    }
}

async function loadDocuments() {
    showDocumentSkeleton();

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
                deleteDocument(doc.filename, doc.status);
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
let polledFile = null;   // the PDF whose indexing progress is being shown

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
    polledFile = filename;

    let summaryDone = false;
    let celebrated = false;

    setProcessing(true);

    statusTimer = setInterval(async () => {
        try {
            const response = await fetch(
                `${API_URL}/status/${encodeURIComponent(filename)}`
            );

            if (response.status === 404) {
                // The PDF was deleted while it was being indexed
                stopStatusPolling();
                setProcessing(false);
                uploadStatus.textContent = "";
                return;
            }

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
                setProcessing(false);

                if (!celebrated) {
                    celebrated = true;
                    launchConfetti();
                }

            } else if (info.stage === "error") {
                uploadStatus.textContent = `❌ ${info.error || "Indexing failed."}`;
                finished = true;
                setProcessing(false);

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

async function uploadFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        uploadStatus.textContent = "Please select a PDF file.";
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
    }
}

pdfInput.addEventListener("change", async () => {
    const file = pdfInput.files[0];

    await uploadFile(file);

    pdfInput.value = "";
});


// =====================================
// 5. DELETE DOCUMENT
// =====================================

async function deleteDocument(filename, status) {
    const stillIndexing = Boolean(status) && !["done", "error"].includes(status);

    const confirmed = confirm(
        stillIndexing
            ? `"${filename}" is still being indexed.\n\nDeleting it will stop the indexing and remove the document. Continue?`
            : `Are you sure you want to delete "${filename}"?`
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

        if (polledFile === filename) {
            stopStatusPolling();
            setProcessing(false);
            uploadStatus.textContent = "";
        }

        removeSummaryCard();

        if (currentPdf.name === filename) clearPdfPane();

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

            const openPdf = () => {
                if (splitOn) {
                    showPdfPage(source.source, Number(source.page) || 1);
                } else {
                    window.open(url, "_blank", "noopener");
                }
            };

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

function showLoadingMessage(mode) {
    const message = document.createElement("div");
    message.className = "message ai loading-message";
    message.id = "aiLoadingMessage";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "OmniDoc AI";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent =
        mode === "chat" ? "Thinking... 💭" : "Let me check your documents... 🔍";

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

// New chat button (placed in the existing toolbar, next to the SOURCE selector)
const newChatBtn = document.createElement("button");
newChatBtn.type = "button";
newChatBtn.className = "msg-action-btn";
newChatBtn.textContent = "＋ New chat";

document.querySelector(".chat-controls").appendChild(newChatBtn);

newChatBtn.addEventListener("click", () => {
    chatEpoch += 1;

    if (currentAbort) {
        currentAbort.abort();
    }

    chatHistory.length = 0;
    chatMessages.innerHTML = welcomeHTML(currentMode);
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

    const requestMode = currentMode;
    const show = text => (requestMode === "chat" ? cleanChat(text) : cleanMath(text));

    showLoadingMessage(requestMode);

    const epoch = chatEpoch;
    currentAbort = new AbortController();

    let answerMessage = null;   // the reply that is being streamed
    let answerBox = null;       // its text element
    let answerText = "";
    let answerSources = [];

    function handleEvent(event) {
        if (epoch !== chatEpoch) return;   // chat was reset meanwhile

        if (event.type === "token") {
            if (!answerBox) {
                removeLoadingMessage();
                answerMessage = addMessage("assistant", "");
                answerBox = answerMessage.querySelector(".message-content");
            }

            answerText += event.text;
            answerBox.textContent = show(answerText);
            chatMessages.scrollTop = chatMessages.scrollHeight;

        } else if (event.type === "not_found") {
            removeLoadingMessage();
            addMessage("assistant", event.text);

        } else if (event.type === "sources") {
            answerSources = event.sources || [];
            addSources(answerSources);

            // In split view, bring the best source page into view
            const best = answerSources.find(
                s => Number.isInteger(Number(s.page)) && Number(s.page) > 0
            );

            if (splitOn && best) {
                showPdfPage(best.source, Number(best.page));
            }

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
                mode: requestMode,
                document: requestMode === "chat" ? null : selectedDocument,
                history: chatHistory.slice(
                    -(requestMode === "chat" ? CHAT_HISTORY_MESSAGES : MAX_HISTORY_MESSAGES)
                )
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
                if (requestMode === "chat") {
                    renderChatMarkdown(answerBox, show(answerText));
                } else {
                    linkCitations(answerBox, show(answerText), answerSources);
                }
                addCopyButton(answerMessage, () => show(answerText));

                // Remember this exchange, but only when it was actually answered
                chatHistory.push({ role: "user", content: question });
                chatHistory.push({
                    role: "assistant",
                    content: show(answerText)
                });
            }
        }

    } catch (error) {
        if (epoch === chatEpoch) {
            removeLoadingMessage();

            if (error.name === "AbortError") {
                // The user pressed Stop: keep what was written so far
                if (answerBox) {
                    answerBox.textContent = show(answerText) + "\n\n⏹️ (stopped)";
                    addCopyButton(answerMessage, () => show(answerText));
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
    askQuestion();   // send straight away
});


// =====================================
// 12. REFRESH DOCUMENTS
// =====================================

refreshBtn.addEventListener("click", loadDocuments);


// =====================================
// 13b. ASSISTANT MODE: PDF Analyzer <-> Chatbot
// =====================================

const modeSwitch = document.getElementById("modeSwitch");
const chatEyebrow = document.getElementById("chatEyebrow");
const chatSubtitle = document.getElementById("chatSubtitle");
const modeNote = document.getElementById("modeNote");
const toolbarLabelText = document.getElementById("toolbarLabelText");

const CHAT_HISTORY_MESSAGES = 10;

const MODE_TEXT = {
    pdf: {
        eyebrow: "INTELLIGENT DOCUMENT SEARCH",
        subtitle: "Your documents hold the answers. Let's find them.",
        note: "PDF Analyzer answers only from the PDFs you upload.",
        toolbar: "DOCUMENT CONTEXT",
        placeholder: "Ask a question about your documents..."
    },
    chat: {
        eyebrow: "GENERAL ASSISTANT",
        subtitle: "Ask me anything: study doubts, coding, maths, writing.",
        note: "Chatbot mode doesn't use your PDFs. Switch to PDF Analyzer to ask about them.",
        toolbar: "GENERAL CHAT",
        placeholder: "Ask me anything..."
    }
};

const CHAT_WELCOME_HTML = `
    <div class="welcome-message">
        <div class="welcome-ai-icon">💬</div>
        <div class="welcome-eyebrow">OMNIDOC CHATBOT</div>
        <h3>Ask me anything</h3>
        <p>Study doubts, coding help, maths, writing, ideas. No PDF needed.</p>
        <div class="suggestion-pills">
            <span>Explain recursion with an example</span>
            <span>Difference between RAM and ROM</span>
            <span>Help me plan a study timetable</span>
        </div>
    </div>
`;

// Each mode keeps its own conversation, so switching never mixes them up
const modeState = {
    pdf: { history: [], nodes: null },
    chat: { history: [], nodes: null }
};

let currentMode = "pdf";

function welcomeHTML(mode) {
    return mode === "chat" ? CHAT_WELCOME_HTML : initialChatHTML;
}

function updateModeUI() {
    const text = MODE_TEXT[currentMode];

    chatSection.classList.toggle("mode-chat", currentMode === "chat");

    modeSwitch.querySelectorAll("button[data-mode]").forEach(button => {
        const active = button.dataset.mode === currentMode;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
    });

    chatEyebrow.textContent = text.eyebrow;
    chatSubtitle.textContent = text.subtitle;
    modeNote.textContent = text.note;
    toolbarLabelText.textContent = text.toolbar;
    questionInput.placeholder = text.placeholder;
}

function setMode(mode) {
    if (!MODE_TEXT[mode] || mode === currentMode) return;

    // Wait for a running answer instead of mixing two conversations
    if (askBtn.disabled) return;

    // Park the current conversation (moving the nodes keeps their buttons working)
    const saved = modeState[currentMode];
    saved.history = chatHistory.slice();

    const parked = document.createDocumentFragment();

    while (chatMessages.firstChild) {
        parked.appendChild(chatMessages.firstChild);
    }

    saved.nodes = parked;

    // Bring back the other one
    currentMode = mode;

    const next = modeState[mode];

    chatHistory.length = 0;
    chatHistory.push(...next.history);

    if (next.nodes && next.nodes.childNodes.length > 0) {
        chatMessages.appendChild(next.nodes);
    } else {
        chatMessages.innerHTML = welcomeHTML(mode);
    }

    next.nodes = null;

    if (mode === "chat" && splitOn) setSplit(false);

    localStorage.setItem("omnidoc-mode", mode);

    updateModeUI();
    chatMessages.scrollTop = chatMessages.scrollHeight;
    questionInput.focus();
}

modeSwitch.addEventListener("click", event => {
    const button = event.target.closest("button[data-mode]");

    if (button) setMode(button.dataset.mode);
});

// Like cleanMath, but leaves code alone so $, _{ } and \ inside code survive
function cleanChat(text) {
    return text
        .split(/(```[\s\S]*?(?:```|$)|`[^`\n]*`)/g)
        .map((part, index) => (index % 2 === 1 ? part : cleanMath(part)))
        .join("");
}

function appendInline(parent, text) {
    text.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).forEach((piece, index) => {
        if (!piece) return;

        if (index % 2 === 1) {
            if (piece.startsWith("`")) {
                const code = document.createElement("code");
                code.textContent = piece.slice(1, -1);
                parent.appendChild(code);
            } else {
                const strong = document.createElement("strong");
                strong.textContent = piece.slice(2, -2);
                parent.appendChild(strong);
            }
        } else {
            parent.appendChild(document.createTextNode(piece));
        }
    });
}

function buildCodeBlock(language, code) {
    const block = document.createElement("div");
    block.className = "code-block";

    const head = document.createElement("div");
    head.className = "code-head";

    const label = document.createElement("span");
    label.textContent = language || "code";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "code-copy";
    copyBtn.textContent = "Copy";

    copyBtn.addEventListener("click", async () => {
        await copyText(code);
        copyBtn.textContent = "Copied ✓";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
    });

    head.append(label, copyBtn);

    const pre = document.createElement("pre");
    const codeEl = document.createElement("code");
    codeEl.textContent = code;
    pre.appendChild(codeEl);

    block.append(head, pre);

    return block;
}

// Shows code blocks, `inline code` and **bold** without using innerHTML
function renderChatMarkdown(box, text) {
    box.textContent = "";

    const FENCE = /```([\w+#.-]*)[^\S\n]*\n?([\s\S]*?)(?:```|$)/g;
    let lastIndex = 0;
    let match;

    while ((match = FENCE.exec(text)) !== null) {
        const before = text.slice(lastIndex, match.index).replace(/^\n/, "").replace(/\n$/, "");

        if (before) appendInline(box, before);

        box.appendChild(buildCodeBlock(match[1], match[2].replace(/\n$/, "")));

        lastIndex = FENCE.lastIndex;
    }

    const rest = text.slice(lastIndex).replace(/^\n/, "");

    if (rest) appendInline(box, rest);
}


// =====================================
// 14. SPLIT-SCREEN READING MODE (chat left, PDF right)
// =====================================

let splitOn = false;
const currentPdf = { name: null, page: 1, version: 0 };

function setSplit(on) {
    splitOn = on;

    chatLayout.classList.toggle("split", on);
    splitBtn.classList.toggle("active", on);
    splitBtn.textContent = on ? "📖 Split view: on" : "📖 Split view";

    // Nothing open yet: show the selected document
    if (on && !currentPdf.name && documentSelect.value) {
        showPdfPage(documentSelect.value, 1);
    }
}

function showPdfPage(name, page = 1) {
    if (!name) return;

    if (!splitOn) setSplit(true);

    currentPdf.name = name;
    currentPdf.page = page;
    currentPdf.version += 1;

    // The ?v= makes the browser reload the viewer so it jumps to the new page
    pdfFrame.src =
        `${API_URL}/pdfs/${encodeURIComponent(name)}?v=${currentPdf.version}#page=${page}`;

    pdfFrame.hidden = false;
    pdfEmpty.hidden = true;
    pdfPaneTitle.textContent = `${name} · page ${page}`;

    // Little glow so the eye finds the pane
    pdfPane.classList.remove("flash");
    void pdfPane.offsetWidth;
    pdfPane.classList.add("flash");

    if (window.innerWidth <= 1100) {
        pdfPane.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function clearPdfPane() {
    currentPdf.name = null;
    pdfFrame.src = "about:blank";
    pdfFrame.hidden = true;
    pdfEmpty.hidden = false;
    pdfPaneTitle.textContent = "No document open";
}

splitBtn.addEventListener("click", () => setSplit(!splitOn));
pdfClose.addEventListener("click", () => setSplit(false));

pdfOpenTab.addEventListener("click", () => {
    if (!currentPdf.name) return;

    window.open(
        `${API_URL}/pdfs/${encodeURIComponent(currentPdf.name)}#page=${currentPdf.page}`,
        "_blank",
        "noopener"
    );
});

documentSelect.addEventListener("change", () => {
    if (splitOn && documentSelect.value) {
        showPdfPage(documentSelect.value, 1);
    }
});

// Turns "(file.pdf, p. 5)" or "(p. 5)" in an answer into clickable chips
const CITATION_RE =
    /\(\s*(?:([^(),]+?\.pdf)\s*,\s*)?(?:pp?|pages?)\.?\s*(\d{1,4})\s*\)/gi;

function linkCitations(box, text, sources) {
    if (!box) return;

    const knownDocs = Array.from(documentSelect.options)
        .map(option => option.value)
        .filter(Boolean);

    const fallbackDoc =
        documentSelect.value ||
        (sources && sources[0] && sources[0].source) ||
        (knownDocs.length === 1 ? knownDocs[0] : null);

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let found = false;
    let match;

    CITATION_RE.lastIndex = 0;

    while ((match = CITATION_RE.exec(text)) !== null) {
        const named = match[1] ? match[1].trim() : null;
        const docName = named && knownDocs.includes(named) ? named : fallbackDoc;

        if (!docName) continue;

        const page = Number(match[2]);

        found = true;

        fragment.append(document.createTextNode(text.slice(lastIndex, match.index)));

        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "cite-chip";
        chip.textContent = `p. ${page}`;
        chip.title = `Open ${docName} at page ${page}`;
        chip.addEventListener("click", () => showPdfPage(docName, page));

        fragment.append(chip);

        lastIndex = match.index + match[0].length;
    }

    if (!found) return;

    fragment.append(document.createTextNode(text.slice(lastIndex)));

    box.textContent = "";
    box.append(fragment);
}


// =====================================
// 15. COMMAND PALETTE (Ctrl+K)
// =====================================

let paletteItems = [];
let paletteActive = 0;
let paletteReturnFocus = null;

function askFromPalette(question, forcePdf = false) {
    showChat();

    if (forcePdf) setMode("pdf");

    questionInput.value = question;
    askQuestion();
}

function buildCommands() {
    const commands = [
        { icon: "▦", title: "Go to Documents", hint: "Navigate", run: showDashboard },
        { icon: "✧", title: "Go to Ask AI", hint: "Navigate", run: showChat },
        { icon: "📄", title: "Switch to PDF Analyzer mode", hint: "Mode", run: () => { showChat(); setMode("pdf"); } },
        { icon: "💬", title: "Switch to Chatbot mode", hint: "Mode", run: () => { showChat(); setMode("chat"); } },
        { icon: "＋", title: "New chat", hint: "Chat", run: () => { showChat(); newChatBtn.click(); } },
        { icon: "↑", title: "Upload a PDF", hint: "Documents", run: () => { showDashboard(); pdfInput.click(); } },
        { icon: "↻", title: "Refresh documents", hint: "Documents", run: loadDocuments },
        { icon: "📖", title: "Toggle split view (PDF next to chat)", hint: "View", run: () => { showChat(); setSplit(!splitOn); } },
        { icon: "☾", title: "Switch light / dark mode", hint: "Theme", run: () => themeToggle.click() },
        { icon: "🎨", title: "Accent colour: Purple", hint: "Theme", run: () => applyAccent("purple") },
        { icon: "🎨", title: "Accent colour: Teal", hint: "Theme", run: () => applyAccent("teal") },
        { icon: "🎨", title: "Accent colour: Sunset", hint: "Theme", run: () => applyAccent("sunset") },
        { icon: "✨", title: "Summarize this document", hint: "Ask", run: () => askFromPalette("Summarize this document", true) },
        { icon: "💡", title: "Find important concepts", hint: "Ask", run: () => askFromPalette("Find important concepts", true) },
        { icon: "🖼️", title: "Explain a diagram", hint: "Ask", run: () => askFromPalette("Explain a diagram", true) },
    ];

    // One entry per uploaded PDF
    Array.from(documentSelect.options)
        .filter(option => option.value)
        .forEach(option => {
            commands.push({
                icon: "📄",
                title: `Open ${option.value}`,
                hint: "PDF",
                run: () => {
                    showChat();
                    setMode("pdf");
                    documentSelect.value = option.value;
                    showPdfPage(option.value, 1);
                }
            });

            commands.push({
                icon: "🔎",
                title: `Ask only in ${option.value}`,
                hint: "Source",
                run: () => {
                    showChat();
                    setMode("pdf");
                    documentSelect.value = option.value;
                    questionInput.focus();
                }
            });
        });

    return commands;
}

function filterCommands(query) {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);

    const matches = buildCommands().filter(command => {
        const haystack = `${command.title} ${command.hint}`.toLowerCase();
        return words.every(word => haystack.includes(word));
    });

    // Anything typed can also be sent to the AI as a question
    if (query.trim()) {
        matches.push({
            icon: "✦",
            title: `Ask AI: “${query.trim()}”`,
            hint: "Ask",
            run: () => askFromPalette(query.trim())
        });
    }

    return matches;
}

function updatePaletteActive(scroll) {
    Array.from(paletteList.children).forEach((item, index) => {
        item.classList.toggle("active", index === paletteActive);

        if (scroll && index === paletteActive) {
            item.scrollIntoView({ block: "nearest" });
        }
    });
}

function renderPalette() {
    paletteList.innerHTML = "";

    if (paletteItems.length === 0) {
        const empty = document.createElement("li");
        empty.className = "palette-empty";
        empty.textContent = "No matching commands";
        paletteList.appendChild(empty);
        return;
    }

    paletteItems.forEach((command, index) => {
        const item = document.createElement("li");
        item.className = "palette-item" + (index === paletteActive ? " active" : "");
        item.setAttribute("role", "option");

        const icon = document.createElement("span");
        icon.className = "palette-icon";
        icon.textContent = command.icon;

        const title = document.createElement("span");
        title.className = "palette-title";
        title.textContent = command.title;

        const hint = document.createElement("span");
        hint.className = "palette-hint";
        hint.textContent = command.hint || "";

        item.append(icon, title, hint);

        item.addEventListener("mouseenter", () => {
            paletteActive = index;
            updatePaletteActive(false);
        });

        item.addEventListener("click", () => runPaletteCommand(command));

        paletteList.appendChild(item);
    });
}

function refreshPalette() {
    paletteItems = filterCommands(paletteInput.value);
    paletteActive = 0;
    renderPalette();
}

function openPalette() {
    paletteReturnFocus = document.activeElement;
    paletteBackdrop.hidden = false;
    paletteInput.value = "";
    refreshPalette();
    paletteInput.focus();
}

function closePalette(restoreFocus = true) {
    paletteBackdrop.hidden = true;

    if (restoreFocus && paletteReturnFocus && paletteReturnFocus.focus) {
        paletteReturnFocus.focus();
    }
}

function runPaletteCommand(command) {
    closePalette(false);
    command.run();
}

paletteInput.addEventListener("input", refreshPalette);

paletteInput.addEventListener("keydown", event => {
    if (event.key === "ArrowDown" && paletteItems.length) {
        event.preventDefault();
        paletteActive = (paletteActive + 1) % paletteItems.length;
        updatePaletteActive(true);

    } else if (event.key === "ArrowUp" && paletteItems.length) {
        event.preventDefault();
        paletteActive = (paletteActive - 1 + paletteItems.length) % paletteItems.length;
        updatePaletteActive(true);

    } else if (event.key === "Enter") {
        event.preventDefault();

        const command = paletteItems[paletteActive];

        if (command) runPaletteCommand(command);

    } else if (event.key === "Escape") {
        event.preventDefault();
        closePalette();
    }
});

paletteBackdrop.addEventListener("mousedown", event => {
    if (event.target === paletteBackdrop) closePalette();
});

paletteBtn.addEventListener("click", openPalette);

document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();

        if (paletteBackdrop.hidden) {
            openPalette();
        } else {
            closePalette();
        }
    }
});


// =====================================
// 16. DRAG & DROP UPLOAD, PAGE-FLIP, CONFETTI
// =====================================

let dragDepth = 0;

function dragHasFiles(event) {
    return Boolean(
        event.dataTransfer &&
        Array.from(event.dataTransfer.types || []).includes("Files")
    );
}

uploadCard.addEventListener("dragenter", event => {
    if (!dragHasFiles(event)) return;

    event.preventDefault();
    dragDepth += 1;
    uploadCard.classList.add("drag-over");
});

uploadCard.addEventListener("dragover", event => {
    if (!dragHasFiles(event)) return;

    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
});

uploadCard.addEventListener("dragleave", event => {
    if (!dragHasFiles(event)) return;

    dragDepth = Math.max(0, dragDepth - 1);

    if (dragDepth === 0) uploadCard.classList.remove("drag-over");
});

uploadCard.addEventListener("drop", event => {
    if (!dragHasFiles(event)) return;

    event.preventDefault();
    dragDepth = 0;
    uploadCard.classList.remove("drag-over");

    const pdf = Array.from(event.dataTransfer.files)
        .find(file => file.name.toLowerCase().endsWith(".pdf"));

    if (!pdf) {
        uploadStatus.textContent = "Please drop a PDF file.";
        return;
    }

    uploadFile(pdf);
});

// A file dropped outside the card must not make the browser open it
["dragover", "drop"].forEach(type => {
    window.addEventListener(type, event => {
        if (dragHasFiles(event)) event.preventDefault();
    });
});

// Page-flip animation while a PDF is being indexed
function setProcessing(active) {
    if (pageFlip) pageFlip.hidden = !active;
}

function launchConfetti() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const canvas = document.createElement("canvas");
    canvas.className = "confetti-canvas";
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);

    const ctx = canvas.getContext("2d");

    const hue = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--accent-hue")
    ) || 262;

    const colors = [
        `hsl(${hue} 90% 68%)`,
        `hsl(${hue + 25} 90% 70%)`,
        `hsl(${hue - 25} 85% 65%)`,
        "#ffd166",
        "#4ed6a0",
        "#ffffff"
    ];

    // Burst from the middle of the upload card (kept inside the screen)
    const box = uploadCard.getBoundingClientRect();
    const originX = Math.min(Math.max(box.left + box.width / 2, 0), canvas.width);
    const originY = Math.min(Math.max(box.top + box.height / 2, 0), canvas.height);

    const pieces = Array.from({ length: 150 }, () => ({
        x: originX + (Math.random() - 0.5) * 120,
        y: originY,
        vx: (Math.random() - 0.5) * 16,
        vy: -Math.random() * 13 - 4,
        size: 5 + Math.random() * 6,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 0.4
    }));

    const DURATION = 2800;
    const startedAt = performance.now();

    function frame(now) {
        const elapsed = now - startedAt;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        pieces.forEach(piece => {
            piece.vy += 0.35;
            piece.vx *= 0.99;
            piece.x += piece.vx;
            piece.y += piece.vy;
            piece.rotation += piece.spin;

            ctx.save();
            ctx.translate(piece.x, piece.y);
            ctx.rotate(piece.rotation);
            ctx.globalAlpha = Math.max(0, 1 - elapsed / DURATION);
            ctx.fillStyle = piece.color;
            ctx.fillRect(-piece.size / 2, -piece.size / 4, piece.size, piece.size / 2);
            ctx.restore();
        });

        if (elapsed < DURATION) {
            requestAnimationFrame(frame);
        } else {
            canvas.remove();
        }
    }

    requestAnimationFrame(frame);
}


// =====================================
// 13. INITIALIZE APPLICATION
// =====================================

loadDocuments();

// Restore the last used mode
if (localStorage.getItem("omnidoc-mode") === "chat") {
    setMode("chat");
} else {
    updateModeUI();
}

console.log("OmniDoc AI frontend initialized successfully.");