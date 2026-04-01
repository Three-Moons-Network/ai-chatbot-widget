/**
 * AI Chatbot Widget
 *
 * Embeddable chat widget for customer support.
 * Include in your page via:
 *
 *   window.ChatWidgetConfig = {
 *     apiEndpoint: "https://api-id.execute-api.region.amazonaws.com",
 *     sessionId: "user-123"
 *   };
 *   <script src="https://your-domain.com/widget/widget.js"></script>
 */

(function () {
  "use strict";

  const config = window.ChatWidgetConfig || {};

  // Validation
  if (!config.apiEndpoint) {
    console.error(
      "ChatWidgetConfig.apiEndpoint is required for AI Chatbot Widget"
    );
    return;
  }
  if (!config.sessionId) {
    console.error("ChatWidgetConfig.sessionId is required for AI Chatbot Widget");
    return;
  }

  // Configuration with defaults
  const settings = {
    apiEndpoint: config.apiEndpoint,
    sessionId: config.sessionId,
    title: config.title || "Chat Support",
    greeting: config.greeting || "Hi there! How can I help?",
    position: config.position || "bottom-right",
    width: config.width || 380,
    height: config.height || 500,
  };

  // Generate unique widget ID
  const widgetId = "chat-widget-" + Math.random().toString(36).substr(2, 9);

  // DOM elements
  let widgetContainer = null;
  let chatWindow = null;
  let messagesContainer = null;
  let inputField = null;
  let sendButton = null;

  /**
   * Initialize the widget
   */
  function init() {
    createWidgetUI();
    attachEventListeners();
    loadConversationHistory();

    // Show greeting if new session
    setTimeout(() => {
      if (messagesContainer.children.length === 0) {
        addMessage("assistant", settings.greeting);
      }
    }, 100);
  }

  /**
   * Create the widget UI
   */
  function createWidgetUI() {
    // Container
    widgetContainer = document.createElement("div");
    widgetContainer.id = widgetId;
    widgetContainer.style.cssText = getContainerStyles();

    // Chat window
    chatWindow = document.createElement("div");
    chatWindow.className = "chat-widget-window";
    chatWindow.style.cssText = getChatWindowStyles();

    // Header
    const header = document.createElement("div");
    header.className = "chat-widget-header";
    header.style.cssText = getHeaderStyles();
    header.innerHTML = `
      <div style="flex: 1;">
        <div style="font-weight: 600; font-size: 14px; margin: 0;">${settings.title}</div>
        <div style="font-size: 12px; opacity: 0.8; margin: 2px 0 0 0;">Usually replies instantly</div>
      </div>
      <button id="${widgetId}-close" class="chat-widget-close-btn" style="${getCloseButtonStyles()}">×</button>
    `;

    // Messages container
    messagesContainer = document.createElement("div");
    messagesContainer.className = "chat-widget-messages";
    messagesContainer.style.cssText = getMessagesContainerStyles();

    // Input area
    const inputArea = document.createElement("div");
    inputArea.style.cssText = `
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid #e0e0e0;
      background: white;
    `;

    inputField = document.createElement("input");
    inputField.type = "text";
    inputField.placeholder = "Type your message...";
    inputField.style.cssText = getInputFieldStyles();

    sendButton = document.createElement("button");
    sendButton.textContent = "Send";
    sendButton.style.cssText = getSendButtonStyles();

    inputArea.appendChild(inputField);
    inputArea.appendChild(sendButton);

    // Assemble
    chatWindow.appendChild(header);
    chatWindow.appendChild(messagesContainer);
    chatWindow.appendChild(inputArea);
    widgetContainer.appendChild(chatWindow);
    document.body.appendChild(widgetContainer);

    // Close button handler
    document.getElementById(widgetId + "-close").addEventListener("click", () => {
      chatWindow.style.display =
        chatWindow.style.display === "none" ? "flex" : "none";
    });
  }

  /**
   * Attach event listeners
   */
  function attachEventListeners() {
    sendButton.addEventListener("click", sendMessage);
    inputField.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  /**
   * Send a message to the API
   */
  async function sendMessage() {
    const message = inputField.value.trim();
    if (!message) return;

    // Add user message to UI
    addMessage("user", message);
    inputField.value = "";
    inputField.focus();

    // Send to API
    try {
      sendButton.disabled = true;
      sendButton.textContent = "...";

      const response = await fetch(`${settings.apiEndpoint}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: settings.sessionId,
          message: message,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        addMessage(
          "assistant",
          `Error: ${errorData.error || "Failed to get response"}`
        );
        return;
      }

      const data = await response.json();
      addMessage("assistant", data.assistant_message);
    } catch (error) {
      console.error("Chat error:", error);
      addMessage(
        "assistant",
        "Sorry, I'm having trouble connecting. Please try again."
      );
    } finally {
      sendButton.disabled = false;
      sendButton.textContent = "Send";
    }
  }

  /**
   * Add a message to the messages container
   */
  function addMessage(role, content) {
    const messageEl = document.createElement("div");
    messageEl.className = `chat-widget-message chat-widget-message-${role}`;
    messageEl.style.cssText = getMessageStyles(role);

    const bubble = document.createElement("div");
    bubble.className = `chat-widget-bubble chat-widget-bubble-${role}`;
    bubble.style.cssText = getBubbleStyles(role);
    bubble.textContent = content;

    messageEl.appendChild(bubble);
    messagesContainer.appendChild(messageEl);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /**
   * Load conversation history from API
   */
  async function loadConversationHistory() {
    try {
      const response = await fetch(
        `${settings.apiEndpoint}/chat/${settings.sessionId}`
      );

      if (!response.ok) return;

      const data = await response.json();
      if (data.messages && data.messages.length > 0) {
        data.messages.forEach((msg) => {
          addMessage(msg.role, msg.content);
        });
      }
    } catch (error) {
      console.error("Failed to load conversation history:", error);
    }
  }

  // =====================================================================
  // Styles
  // =====================================================================

  function getContainerStyles() {
    const positionMap = {
      "bottom-right": "right: 20px; bottom: 20px;",
      "bottom-left": "left: 20px; bottom: 20px;",
      "top-right": "right: 20px; top: 20px;",
      "top-left": "left: 20px; top: 20px;",
    };

    return `
      position: fixed;
      ${positionMap[settings.position] || positionMap["bottom-right"]}
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 14px;
    `;
  }

  function getChatWindowStyles() {
    return `
      display: flex;
      flex-direction: column;
      width: ${settings.width}px;
      height: ${settings.height}px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      overflow: hidden;
      animation: chatWidgetSlideIn 0.3s ease-out;
    `;
  }

  function getHeaderStyles() {
    return `
      display: flex;
      align-items: center;
      padding: 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-bottom: 1px solid #e0e0e0;
    `;
  }

  function getCloseButtonStyles() {
    return `
      background: none;
      border: none;
      font-size: 24px;
      color: white;
      cursor: pointer;
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s;
    `;
  }

  function getMessagesContainerStyles() {
    return `
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      background: #f5f5f5;
      display: flex;
      flex-direction: column;
      gap: 8px;
    `;
  }

  function getInputFieldStyles() {
    return `
      flex: 1;
      padding: 10px 12px;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    `;
  }

  function getSendButtonStyles() {
    return `
      padding: 10px 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.2s;
    `;
  }

  function getMessageStyles(role) {
    return `
      display: flex;
      justify-content: ${role === "user" ? "flex-end" : "flex-start"};
      margin-bottom: 4px;
    `;
  }

  function getBubbleStyles(role) {
    if (role === "user") {
      return `
        max-width: 80%;
        padding: 10px 14px;
        background: #667eea;
        color: white;
        border-radius: 12px;
        word-wrap: break-word;
        line-height: 1.4;
      `;
    } else {
      return `
        max-width: 80%;
        padding: 10px 14px;
        background: white;
        color: #333;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        word-wrap: break-word;
        line-height: 1.4;
      `;
    }
  }

  // Add animations
  if (!document.querySelector("#chat-widget-styles")) {
    const style = document.createElement("style");
    style.id = "chat-widget-styles";
    style.textContent = `
      @keyframes chatWidgetSlideIn {
        from {
          opacity: 0;
          transform: translateY(20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      #chat-widget-close-btn:hover {
        opacity: 0.8;
      }

      .chat-widget-messages::-webkit-scrollbar {
        width: 6px;
      }

      .chat-widget-messages::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
      }

      .chat-widget-messages::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 3px;
      }

      .chat-widget-messages::-webkit-scrollbar-thumb:hover {
        background: #555;
      }
    `;
    document.head.appendChild(style);
  }

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
