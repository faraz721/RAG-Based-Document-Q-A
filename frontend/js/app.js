(function () {
  "use strict";

  function initApp() {
    console.log("[RAG Q&A] JavaScript loaded and initializing...");

    var SESSION_KEY = "rag-qa-session-id";
    function getSessionId() {
      var id = localStorage.getItem(SESSION_KEY);
      if (!id || id.length < 8) {
        id = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(SESSION_KEY, id);
      }
      return id;
    }
    function apiHeaders(extra) {
      var h = { "X-Session-Id": getSessionId() };
      if (extra) {
        for (var k in extra) {
          if (Object.prototype.hasOwnProperty.call(extra, k)) h[k] = extra[k];
        }
      }
      return h;
    }

    function safeParseJson(res) {
      return res.text().then(function (text) {
        var trimmed = (text || "").trim();
        if (!trimmed) {
          throw new Error("Empty response from server. Please try again in a moment.");
        }
        if (trimmed.charAt(0) === "<") {
          throw new Error(
            "Server is waking up or busy. Please wait 20–30 seconds and refresh the page."
          );
        }
        try {
          return { res: res, data: JSON.parse(trimmed) };
        } catch (err) {
          throw new Error("Invalid server response. Please refresh the page.");
        }
      });
    }

    function apiFetch(url, options) {
      options = options || {};
      options.headers = apiHeaders(options.headers || {});
      return fetch(url, options).then(function (res) {
        return safeParseJson(res);
      });
    }

    // Theme
    var THEME_KEY = "rag-qa-theme";
    var html = document.documentElement;
    var savedTheme = localStorage.getItem(THEME_KEY) || "light";
    html.setAttribute("data-theme", savedTheme);

    var themeBtn = document.getElementById("themeBtn");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        var next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        localStorage.setItem(THEME_KEY, next);
      });
    }

    var API = {
      list: "/api/documents/list",
      upload: "/api/documents/upload",
      delete: "/api/documents/delete",
      ask: "/api/qa/ask",
    };

    var documents = [];
    var selectedDocId = null;
    var isProcessing = false;
    var pendingDeleteIds = [];

    var $ = function (sel) {
      return document.querySelector(sel);
    };

    var messagesEl = $("#messages");
    var emptyState = $("#emptyState");
    var emptyTitle = $("#emptyTitle");
    var emptyText = $("#emptyText");
    var questionInput = $("#questionInput");
    var sendBtn = $("#sendBtn");
    var inputHint = $("#inputHint");
    var currentDocBar = $("#currentDocBar");
    var currentDocLabel = $("#currentDocLabel");
    var docsList = $("#docsList");
    var docsEmpty = $("#docsEmpty");
    var fileInput = $("#fileInput");
    var uploadBtn = $("#uploadBtn");
    var uploadZone = $("#uploadZone");
    var deleteSelectedBtn = $("#deleteSelectedBtn");
    var toast = $("#toast");
    var docsDrawer = $("#docsDrawer");
    var docsOverlay = $("#docsOverlay");
    var aboutDrawer = $("#aboutDrawer");
    var aboutOverlay = $("#aboutOverlay");
    var deleteModal = $("#deleteModal");
    var aboutBtn = $("#aboutBtn");
    var openDocsBtn = $("#openDocsBtn");
    var closeDocsBtn = $("#closeDocsBtn");
    var closeAboutBtn = $("#closeAboutBtn");
    var cancelDeleteBtn = $("#cancelDeleteBtn");
    var confirmDeleteBtn = $("#confirmDeleteBtn");

    if (!aboutBtn || !openDocsBtn || !docsDrawer || !aboutDrawer) {
      console.error("[RAG Q&A] Critical DOM elements missing.");
      return;
    }

    function showToast(msg, type) {
      if (!toast) return;
      type = type || "";
      toast.textContent = msg;
      toast.className = "toast visible" + (type ? " " + type : "");
      toast.hidden = false;
      clearTimeout(showToast._t);
      showToast._t = setTimeout(function () {
        toast.classList.remove("visible");
        setTimeout(function () {
          toast.hidden = true;
        }, 300);
      }, 4000);
    }

    function openDrawer(drawer, overlay) {
      if (!drawer || !overlay) return;
      overlay.hidden = false;
      void overlay.offsetWidth;
      overlay.classList.add("visible");
      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
    }

    function closeDrawer(drawer, overlay) {
      if (!drawer || !overlay) return;
      drawer.classList.remove("open");
      overlay.classList.remove("visible");
      drawer.setAttribute("aria-hidden", "true");
      setTimeout(function () {
        overlay.hidden = true;
      }, 300);
    }

    function openDocs() {
      openDrawer(docsDrawer, docsOverlay);
    }
    function closeDocs() {
      closeDrawer(docsDrawer, docsOverlay);
    }
    function openAbout() {
      openDrawer(aboutDrawer, aboutOverlay);
    }
    function closeAbout() {
      closeDrawer(aboutDrawer, aboutOverlay);
    }

    function openDeleteModal(ids) {
      pendingDeleteIds = ids;
      var text =
        ids.length === 1
          ? "Are you sure you want to delete this document? This cannot be undone."
          : "Are you sure you want to delete " + ids.length + " documents? This cannot be undone.";
      var modalText = $("#deleteModalText");
      if (modalText) modalText.textContent = text;
      if (deleteModal) {
        deleteModal.hidden = false;
        void deleteModal.offsetWidth;
        deleteModal.classList.add("visible");
      }
    }

    function closeDeleteModal() {
      if (!deleteModal) return;
      deleteModal.classList.remove("visible");
      setTimeout(function () {
        deleteModal.hidden = true;
        pendingDeleteIds = [];
      }, 250);
    }

    function updateCurrentDocBar() {
      if (!currentDocBar || !currentDocLabel) return;
      if (!selectedDocId) {
        currentDocBar.classList.add("empty");
        currentDocLabel.textContent = "No document selected";
        if (inputHint) inputHint.textContent = "Select a document first";
        if (sendBtn) sendBtn.disabled = true;
        updateEmptyState();
        return;
      }
      var doc = null;
      for (var i = 0; i < documents.length; i++) {
        if (documents[i].id === selectedDocId) {
          doc = documents[i];
          break;
        }
      }
      if (!doc) {
        selectedDocId = null;
        updateCurrentDocBar();
        return;
      }
      currentDocBar.classList.remove("empty");
      currentDocLabel.textContent =
        "📄 Current document: " + (doc.original_name || doc.filename);
      if (inputHint) inputHint.textContent = "Press Enter to send";
      if (sendBtn)
        sendBtn.disabled =
          isProcessing || !(questionInput && questionInput.value.trim());
      updateEmptyState();
    }

    function updateEmptyState() {
      if (!emptyState) return;
      var hasMessages =
        messagesEl && messagesEl.querySelectorAll(".msg").length > 0;
      if (hasMessages) {
        emptyState.style.display = "none";
        return;
      }
      emptyState.style.display = "block";
      if (documents.length === 0) {
        if (emptyTitle) emptyTitle.textContent = "Upload a document to get started";
        if (emptyText)
          emptyText.textContent =
            "Upload a PDF, DOC, DOCX or TXT file, select it, then ask questions.";
      } else if (!selectedDocId) {
        if (emptyTitle)
          emptyTitle.textContent = "Select a document to start asking questions";
        if (emptyText)
          emptyText.textContent =
            "Open the documents panel (+) and choose one document for Q&A.";
      } else {
        if (emptyTitle) emptyTitle.textContent = "Ask a question";
        if (emptyText)
          emptyText.textContent =
            "Type a question about the selected document below.";
      }
    }

    function autoResizeTextarea() {
      if (!questionInput) return;
      questionInput.style.height = "auto";
      questionInput.style.height =
        Math.min(questionInput.scrollHeight, 120) + "px";
    }

    function scrollToBottom() {
      if (!messagesEl) return;
      requestAnimationFrame(function () {
        messagesEl.scrollTop = messagesEl.scrollHeight;
      });
    }

    function escapeHtml(str) {
      var div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    }

    function renderMarkdown(text) {
      if (!text) return "";
      var html = escapeHtml(text);
      html = html.replace(/```[\s\S]*?```/g, function (m) {
        var code = m.replace(/^```\w*\n?/, "").replace(/```$/, "");
        return "<pre><code>" + code + "</code></pre>";
      });
      html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
      html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
      html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
      html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
      html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
      html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
      html = html.replace(/((?:^[\-\*•] .+(?:\n|$))+)/gm, function (block) {
        var items = block
          .trim()
          .split("\n")
          .map(function (line) {
            return "<li>" + line.replace(/^[\-\*•] /, "") + "</li>";
          })
          .join("");
        return "<ul>" + items + "</ul>";
      });
      html = html.replace(/((?:^\d+\. .+(?:\n|$))+)/gm, function (block) {
        var items = block
          .trim()
          .split("\n")
          .map(function (line) {
            return "<li>" + line.replace(/^\d+\. /, "") + "</li>";
          })
          .join("");
        return "<ol>" + items + "</ol>";
      });
      var parts = html.split(/\n{2,}/);
      html = parts
        .map(function (p) {
          p = p.trim();
          if (!p) return "";
          if (
            p.indexOf("<h") === 0 ||
            p.indexOf("<ul") === 0 ||
            p.indexOf("<ol") === 0 ||
            p.indexOf("<pre") === 0
          )
            return p;
          return "<p>" + p.replace(/\n/g, "<br>") + "</p>";
        })
        .join("");
      return html;
    }

    function appendUserMessage(text) {
      if (!messagesEl) return;
      if (emptyState) emptyState.style.display = "none";
      var div = document.createElement("div");
      div.className = "msg user";
      div.innerHTML = '<div class="bubble"></div>';
      div.querySelector(".bubble").textContent = text;
      messagesEl.appendChild(div);
      scrollToBottom();
    }

    function appendAIMessage(htmlContent, sources) {
      if (!messagesEl) return;
      if (emptyState) emptyState.style.display = "none";
      var div = document.createElement("div");
      div.className = "msg ai";
      var sourcesHtml = "";
      if (sources && sources.length) {
        var parts = sources.map(function (s) {
          var t = "Source: " + (s.filename || "document");
          if (s.page) t += ", Page: " + s.page;
          return t;
        });
        var unique = [];
        parts.forEach(function (p) {
          if (unique.indexOf(p) === -1) unique.push(p);
        });
        sourcesHtml =
          '<div class="sources">' +
          unique
            .map(function (p) {
              return "<span>" + escapeHtml(p) + "</span>";
            })
            .join("") +
          "</div>";
      }
      div.innerHTML =
        '<div class="bubble">' + htmlContent + sourcesHtml + "</div>";
      messagesEl.appendChild(div);
      scrollToBottom();
    }

    function appendThinking() {
      if (!messagesEl) return;
      if (emptyState) emptyState.style.display = "none";
      var div = document.createElement("div");
      div.className = "msg ai";
      div.id = "thinkingMsg";
      div.innerHTML =
        '<div class="bubble thinking"><span>AI is thinking</span><span class="thinking-dots"><span></span><span></span><span></span></span></div>';
      messagesEl.appendChild(div);
      scrollToBottom();
    }

    function removeThinking() {
      var t = $("#thinkingMsg");
      if (t) t.remove();
    }

    function fetchDocuments(retry) {
      return apiFetch(API.list)
        .then(function (result) {
          if (!result.res.ok) {
            throw new Error(
              result.data.error || "Failed to load documents"
            );
          }
          documents = result.data.documents || [];
          renderDocsList();
          updateCurrentDocBar();
        })
        .catch(function (e) {
          console.warn("[RAG Q&A] list docs:", e.message);
          if (!retry) {
            // one automatic retry after cold-start delay
            setTimeout(function () {
              fetchDocuments(true);
            }, 2500);
            showToast(
              e.message || "Connecting to server… retrying shortly",
              "error"
            );
            return;
          }
          showToast(e.message || "Failed to load documents", "error");
        });
    }

    function renderDocsList() {
      if (!docsList) return;
      docsList.innerHTML = "";
      if (documents.length === 0) {
        if (docsEmpty) docsEmpty.hidden = false;
        if (deleteSelectedBtn) deleteSelectedBtn.hidden = true;
        return;
      }
      if (docsEmpty) docsEmpty.hidden = true;

      documents.forEach(function (doc) {
        var li = document.createElement("li");
        li.className =
          "doc-item" + (doc.id === selectedDocId ? " selected-qa" : "");
        if (doc.status === "processing") li.classList.add("processing");

        var name = doc.original_name || doc.filename || "Document";
        var meta =
          (doc.num_chunks ? doc.num_chunks + " chunks" : "") +
          (doc.extension
            ? " · " + doc.extension.toUpperCase().replace(".", "")
            : "");

        li.innerHTML =
          '<input type="radio" class="doc-radio" name="qaDoc" value="' +
          escapeHtml(doc.id) +
          '" ' +
          (doc.id === selectedDocId ? "checked" : "") +
          ' title="Select for Q&A" />' +
          '<input type="checkbox" class="doc-check" value="' +
          escapeHtml(doc.id) +
          '" title="Select for deletion" />' +
          '<div class="doc-info"><div class="doc-name" title="' +
          escapeHtml(name) +
          '">' +
          escapeHtml(name) +
          '</div><div class="doc-meta">' +
          escapeHtml(meta) +
          "</div></div>" +
          '<button type="button" class="doc-delete" data-id="' +
          escapeHtml(doc.id) +
          '" title="Delete" aria-label="Delete">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>';

        var radio = li.querySelector(".doc-radio");
        radio.addEventListener("change", function () {
          if (radio.checked) {
            selectedDocId = doc.id;
            updateCurrentDocBar();
            renderDocsList();
            showToast("Selected: " + name, "success");
          }
        });

        var check = li.querySelector(".doc-check");
        check.addEventListener("change", updateDeleteSelectedBtn);

        li.querySelector(".doc-delete").addEventListener("click", function (e) {
          e.stopPropagation();
          openDeleteModal([doc.id]);
        });

        docsList.appendChild(li);
      });
      updateDeleteSelectedBtn();
    }

    function updateDeleteSelectedBtn() {
      if (!docsList || !deleteSelectedBtn) return;
      var checked = docsList.querySelectorAll(".doc-check:checked");
      deleteSelectedBtn.hidden = checked.length === 0;
    }

    function clearChatMessages() {
      if (!messagesEl) return;
      messagesEl.querySelectorAll(".msg").forEach(function (m) {
        m.remove();
      });
      updateEmptyState();
    }

    function uploadFile(file) {
      if (!file) return;
      var allowed = [".pdf", ".doc", ".docx", ".txt"];
      var parts = file.name.split(".");
      var ext = "." + (parts.length > 1 ? parts.pop() : "").toLowerCase();
      if (allowed.indexOf(ext) === -1) {
        showToast("Unsupported file type. Use PDF, DOC, DOCX or TXT.", "error");
        return;
      }

      var form = new FormData();
      form.append("file", file);

      if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="spinner"></span> Processing...';
      }

      apiFetch(API.upload, { method: "POST", body: form })
        .then(function (result) {
          if (!result.res.ok) {
            throw new Error(result.data.error || "Upload failed");
          }
          showToast("Document uploaded and processed", "success");
          return fetchDocuments(true).then(function () {
            if (result.data.document && result.data.document.id) {
              if (!selectedDocId || documents.length === 1) {
                selectedDocId = result.data.document.id;
                updateCurrentDocBar();
                renderDocsList();
              }
            }
          });
        })
        .catch(function (e) {
          showToast(e.message || "Upload failed", "error");
        })
        .finally(function () {
          if (uploadBtn) {
            uploadBtn.disabled = false;
            uploadBtn.innerHTML =
              '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg> Upload document';
          }
          if (fileInput) fileInput.value = "";
        });
    }

    function deleteDocs(ids) {
      if (!ids.length) return;
      apiFetch(API.delete, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_ids: ids }),
      })
        .then(function (result) {
          if (!result.res.ok) {
            throw new Error(result.data.error || "Delete failed");
          }
          var data = result.data;
          if (ids.indexOf(selectedDocId) !== -1) {
            selectedDocId = null;
            clearChatMessages();
          }
          showToast(
            data.count === 1
              ? "Document deleted"
              : data.count + " documents deleted",
            "success"
          );
          return fetchDocuments(true);
        })
        .catch(function (e) {
          showToast(e.message || "Delete failed", "error");
        });
    }

    function sendQuestion() {
      if (!questionInput) return;
      var question = questionInput.value.trim();
      if (!question || isProcessing) return;

      if (!selectedDocId) {
        showToast("Please select a document first", "error");
        openDocs();
        return;
      }

      isProcessing = true;
      if (sendBtn) sendBtn.disabled = true;
      questionInput.value = "";
      autoResizeTextarea();

      appendUserMessage(question);
      appendThinking();

      apiFetch(API.ask, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: selectedDocId, question: question }),
      })
        .then(function (result) {
          removeThinking();
          if (!result.res.ok) {
            appendAIMessage(
              "<p>" +
                escapeHtml(result.data.error || "Something went wrong.") +
                "</p>"
            );
            return;
          }
          var html = renderMarkdown(
            result.data.answer || "No answer generated."
          );
          appendAIMessage(html, result.data.sources);
        })
        .catch(function (e) {
          removeThinking();
          appendAIMessage(
            "<p>" +
              escapeHtml(
                e.message ||
                  "Network error. Please check your connection and try again."
              ) +
              "</p>"
          );
        })
        .finally(function () {
          isProcessing = false;
          if (sendBtn) {
            sendBtn.disabled =
              !(questionInput && questionInput.value.trim()) || !selectedDocId;
          }
        });
    }

    aboutBtn.addEventListener("click", function (e) {
      e.preventDefault();
      openAbout();
    });
    openDocsBtn.addEventListener("click", function (e) {
      e.preventDefault();
      openDocs();
    });
    if (closeDocsBtn) closeDocsBtn.addEventListener("click", closeDocs);
    if (docsOverlay) docsOverlay.addEventListener("click", closeDocs);
    if (closeAboutBtn) closeAboutBtn.addEventListener("click", closeAbout);
    if (aboutOverlay) aboutOverlay.addEventListener("click", closeAbout);

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", function () {
        fileInput.click();
      });
      fileInput.addEventListener("change", function () {
        if (fileInput.files && fileInput.files[0])
          uploadFile(fileInput.files[0]);
      });
    }

    if (uploadZone) {
      uploadZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        uploadZone.classList.add("dragover");
      });
      uploadZone.addEventListener("dragleave", function () {
        uploadZone.classList.remove("dragover");
      });
      uploadZone.addEventListener("drop", function (e) {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0])
          uploadFile(e.dataTransfer.files[0]);
      });
    }

    if (deleteSelectedBtn) {
      deleteSelectedBtn.addEventListener("click", function () {
        var ids = Array.prototype.slice
          .call(docsList.querySelectorAll(".doc-check:checked"))
          .map(function (c) {
            return c.value;
          });
        if (ids.length) openDeleteModal(ids);
      });
    }

    if (cancelDeleteBtn)
      cancelDeleteBtn.addEventListener("click", closeDeleteModal);
    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener("click", function () {
        var ids = pendingDeleteIds.slice();
        closeDeleteModal();
        deleteDocs(ids);
      });
    }
    if (deleteModal) {
      deleteModal.addEventListener("click", function (e) {
        if (e.target === deleteModal) closeDeleteModal();
      });
    }

    if (sendBtn) sendBtn.addEventListener("click", sendQuestion);
    if (questionInput) {
      questionInput.addEventListener("input", function () {
        autoResizeTextarea();
        if (sendBtn)
          sendBtn.disabled =
            isProcessing || !questionInput.value.trim() || !selectedDocId;
      });
      questionInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendQuestion();
        }
      });
    }

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (deleteModal && !deleteModal.hidden) closeDeleteModal();
        else if (docsDrawer && docsDrawer.classList.contains("open"))
          closeDocs();
        else if (aboutDrawer && aboutDrawer.classList.contains("open"))
          closeAbout();
      }
    });

    fetchDocuments(false);
    updateCurrentDocBar();
    console.log("[RAG Q&A] Ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
  } else {
    initApp();
  }
})();
