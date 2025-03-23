const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const newChatBtn = document.getElementById('new-chat-btn');
const chatHistory = document.querySelector('.chat-history');
const fileUpload = document.getElementById('file-upload');

// Initialize variables
let chats = [];
let currentChatId = null;
let selectedFiles = [];

// Save chats to localStorage
function saveChats() {
    const chatData = {
        chats: chats,
        currentChatId: currentChatId
    };
    localStorage.setItem('chatData', JSON.stringify(chatData));
}

// Load chats from localStorage
function loadChats() {
    const savedData = localStorage.getItem('chatData');
    if (savedData) {
        const data = JSON.parse(savedData);
        chats = data.chats;
        currentChatId = data.currentChatId;
        
        // Update UI
        updateChatHistory();
        if (currentChatId) {
            displayChat(currentChatId);
        }
    }
}

// Display a specific chat
function displayChat(chatId) {
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;

    currentChatId = chatId;
    chatMessages.innerHTML = '';

    // Display all messages in the chat
    chat.messages.forEach(msg => {
        chatMessages.appendChild(createMessageElement(msg.content, msg.isUser));
    });

    // Update active state in sidebar
    updateChatHistory();
}

// Create new chat
function initializeNewChat() {
    chatMessages.innerHTML = `
        <div class="welcome-container">
            <h1 class="welcome-title">What can I help with?</h1>
        </div>
    `;
    
    const chatId = Date.now();
    const newChat = {
        id: chatId,
        title: 'New Chat',
        messages: []
    };
    
    chats.push(newChat);
    currentChatId = chatId;
    
    // Update UI
    updateChatHistory();
    
    // Save to localStorage
    saveChats();
    
    return chatId;
}

// Send message function
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Create new chat if none exists
    if (!currentChatId) {
        initializeNewChat();
    }

    const currentChat = chats.find(c => c.id === currentChatId);
    
    // Add user message
    currentChat.messages.push({ content: message, isUser: true });
    chatMessages.appendChild(createMessageElement(message, true));
    
    // Update chat title if it's the first message
    if (currentChat.messages.length === 1) {
        currentChat.title = message.slice(0, 30) + (message.length > 30 ? '...' : '');
        updateChatHistory();
    }

    // Save to localStorage
    saveChats();

    // Clear input
    userInput.value = '';

    try {
        // Show loading message
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'ai-message');
        loadingDiv.textContent = 'Thinking...';
        chatMessages.appendChild(loadingDiv);

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: message,
                chatId: currentChatId 
            })
        });

        const data = await response.json();
        
        // Remove loading message
        chatMessages.removeChild(loadingDiv);

        // Add AI response
        if (data.error) {
            const errorMessage = 'Error: ' + data.error;
            currentChat.messages.push({ content: errorMessage, isUser: false });
            chatMessages.appendChild(createMessageElement(errorMessage, false));
        } else {
            currentChat.messages.push({ content: data.response, isUser: false });
            chatMessages.appendChild(createMessageElement(data.response, false));
        }

        // Save to localStorage
        saveChats();

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        console.error('Error:', error);
    }
}

// Update chat history in sidebar
function updateChatHistory() {
    const chatHistory = document.querySelector('.chat-history');
    chatHistory.innerHTML = '';
    
    chats.forEach(chat => {
        chatHistory.appendChild(createChatHistoryItem(chat));
    });
}

// Update the createChatHistoryItem function
function createChatHistoryItem(chat) {
    const div = document.createElement('div');
    div.classList.add('chat-item');
    if (chat.id === currentChatId) {
        div.classList.add('active');
    }
    
    div.innerHTML = `
        <div class="chat-item-content" onclick="displayChat(${chat.id})">
            <i class="fas fa-message"></i>
            <span class="chat-item-title">${chat.title}</span>
        </div>
        <div class="chat-item-actions">
            <button class="more-options" onclick="event.stopPropagation(); showContextMenu(${chat.id})">
                <i class="fas fa-ellipsis-vertical"></i>
            </button>
            <div class="context-menu" id="context-menu-${chat.id}">
                <div class="context-menu-item" onclick="event.stopPropagation(); renameChat(${chat.id})">
                    <i class="fas fa-pen"></i> Rename
                </div>
                <div class="context-menu-item delete" onclick="event.stopPropagation(); deleteChat(${chat.id})">
                    <i class="fas fa-trash"></i> Delete
                </div>
            </div>
        </div>
    `;
    return div;
}

// Delete chat
function deleteChat(chatId) {
    if (confirm('Are you sure you want to delete this chat?')) {
        const index = chats.findIndex(c => c.id === chatId);
        if (index > -1) {
            chats.splice(index, 1);
            
            if (chatId === currentChatId) {
                if (chats.length > 0) {
                    displayChat(chats[0].id);
                } else {
                    initializeNewChat();
                }
            }
            
            updateChatHistory();
            saveChats();
        }
    }
}

// Load chats when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadChats();
    if (chats.length === 0) {
        initializeNewChat();
    }
});

// Add event listener for new chat button
document.getElementById('new-chat-btn').addEventListener('click', () => {
    initializeNewChat();
});

// Auto-resize textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// Handle send button click
sendButton.addEventListener('click', sendMessage);

// Handle enter key (with shift+enter for new line)
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function createMessageElement(content, isUser = false, messageId = Date.now()) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user-message' : 'ai-message');
    messageDiv.dataset.messageId = messageId;

    const iconDiv = document.createElement('div');
    iconDiv.classList.add('message-icon');
    iconDiv.innerHTML = isUser ? 
        '<i class="fas fa-user"></i>' : 
        '<i class="fas fa-robot"></i>';

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.textContent = content;

    const actionsDiv = document.createElement('div');
    actionsDiv.classList.add('message-actions');
    
    // Only show action buttons for AI messages
    if (!isUser) {
        actionsDiv.innerHTML = `
            <button class="action-btn like-btn" onclick="handleAction('like', this)">
                <i class="fas fa-thumbs-up"></i>
            </button>
            <button class="action-btn dislike-btn" onclick="handleAction('dislike', this)">
                <i class="fas fa-thumbs-down"></i>
            </button>
            <button class="action-btn copy-btn" onclick="handleAction('copy', this)">
                <i class="fas fa-copy"></i>
            </button>
            <button class="action-btn model-switch-btn disabled" title="Switch AI Model (Coming Soon)">
                <i class="fas fa-sync-alt"></i>
            </button>
        `;
    }

    messageDiv.appendChild(iconDiv);
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(actionsDiv);

    return messageDiv;
}

// Add this helper function for copying text
function copyToClipboard(text) {
    // Try using the clipboard API first
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            textArea.remove();
            return Promise.resolve();
        } catch (error) {
            textArea.remove();
            return Promise.reject(error);
        }
    }
}

// Handle message actions
async function handleAction(action, button) {
    const messageDiv = button.closest('.message');
    const messageContent = messageDiv.querySelector('.message-content').textContent;
    const timestamp = new Date().toISOString();

    switch (action) {
        case 'like':
            // Remove dislike if exists
            messageDiv.querySelector('.dislike-btn')?.classList.remove('active');
            button.classList.toggle('active');
            await logAction('like', messageContent);
            break;

        case 'dislike':
            // Remove like if exists
            messageDiv.querySelector('.like-btn')?.classList.remove('active');
            button.classList.toggle('active');
            await logAction('dislike', messageContent);
            break;

        case 'copy':
            try {
                await copyToClipboard(messageContent);
                // Show success feedback
                const originalIcon = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i>';
                button.style.color = '#19c37d';
                
                setTimeout(() => {
                    button.innerHTML = originalIcon;
                    button.style.color = '';
                }, 2000);
                
                await logAction('copy', messageContent);
            } catch (err) {
                console.error('Failed to copy:', err);
                const originalIcon = button.innerHTML;
                button.innerHTML = '<i class="fas fa-times"></i>';
                button.style.color = '#ff4444';
                
                setTimeout(() => {
                    button.innerHTML = originalIcon;
                    button.style.color = '';
                }, 2000);
            }
            break;
    }
}

// Log actions to backend
async function logAction(action, content) {
    try {
        const response = await fetch('/log_action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                content: content,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            console.error('Failed to log action');
        }
    } catch (error) {
        console.error('Error logging action:', error);
    }
}

// Add this function to handle file selection
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    selectedFiles = [...selectedFiles, ...files];
    
    // Create file preview container if it doesn't exist
    let filePreview = document.querySelector('.file-preview');
    if (!filePreview) {
        filePreview = document.createElement('div');
        filePreview.className = 'file-preview';
        document.querySelector('.input-box').insertBefore(filePreview, document.querySelector('textarea'));
    }
    
    // Clear existing preview
    filePreview.innerHTML = '';
    
    // Add preview for each file
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-preview-item';
        fileItem.innerHTML = `
            <i class="fas fa-file"></i>
            <span>${file.name}</span>
            <button onclick="removeFile(${index})">
                <i class="fas fa-times"></i>
            </button>
        `;
        filePreview.appendChild(fileItem);
    });
    
    filePreview.classList.add('active');
}

// Add this function to remove files
function removeFile(index) {
    selectedFiles.splice(index, 1);
    if (selectedFiles.length === 0) {
        document.querySelector('.file-preview').classList.remove('active');
    } else {
        handleFileSelect({ target: { files: selectedFiles } });
    }
}

// Add event listener for file upload
fileUpload.addEventListener('change', handleFileSelect);

// Add modal HTML to the page
document.body.insertAdjacentHTML('beforeend', `
    <div class="modal" id="rename-modal">
        <div class="modal-content">
            <div class="modal-header">Rename Chat</div>
            <input type="text" class="modal-input" id="rename-input" placeholder="Enter new name">
            <div class="modal-buttons">
                <button class="modal-button cancel" onclick="hideRenameModal()">Cancel</button>
                <button class="modal-button confirm" onclick="confirmRename()">Rename</button>
            </div>
        </div>
    </div>
`);

// Context menu functions
let activeContextMenu = null;
let chatToRename = null;

function showContextMenu(chatId) {
    // Hide any other open menus
    document.querySelectorAll('.context-menu').forEach(menu => {
        menu.classList.remove('active');
    });
    
    // Show this menu
    const menu = document.getElementById(`context-menu-${chatId}`);
    if (menu) {
        menu.classList.add('active');
    }
}

// Add click handler to close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.chat-item-actions')) {
        document.querySelectorAll('.context-menu').forEach(menu => {
            menu.classList.remove('active');
        });
    }
});

function shareChat(chatId) {
    const chat = chats.find(c => c.id === chatId);
    const chatContent = chat.messages.map(m => 
        `${m.isUser ? 'User' : 'Assistant'}: ${m.content}`
    ).join('\n\n');
    
    navigator.clipboard.writeText(chatContent).then(() => {
        alert('Chat content copied to clipboard!');
    });
}

function showRenameModal(chatId) {
    chatToRename = chatId;
    const chat = chats.find(c => c.id === chatId);
    const modal = document.getElementById('rename-modal');
    const input = document.getElementById('rename-input');
    input.value = chat.title;
    modal.style.display = 'block';
}

function hideRenameModal() {
    const modal = document.getElementById('rename-modal');
    modal.style.display = 'none';
    chatToRename = null;
}

function confirmRename() {
    const input = document.getElementById('rename-input');
    const newTitle = input.value.trim();
    
    if (newTitle && chatToRename) {
        const chat = chats.find(c => c.id === chatToRename);
        chat.title = newTitle;
        updateChatHistory();
        saveChats();
        hideRenameModal();
    }
}

// Add this function to help with debugging
function debugStorage() {
    console.log('Current chats:', chats);
    console.log('Current chat ID:', currentChatId);
    console.log('localStorage:', localStorage.getItem('chatData'));
}

// Add this function to handle rename
function renameChat(chatId) {
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;

    // Create rename modal if it doesn't exist
    let modal = document.getElementById('rename-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'rename-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">Rename chat</div>
                <input type="text" id="rename-input" class="modal-input" placeholder="Enter new name">
                <div class="modal-buttons">
                    <button class="modal-button cancel" onclick="hideRenameModal()">Cancel</button>
                    <button class="modal-button confirm" onclick="confirmRename(${chatId})">Rename</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Show modal and set current value
    const input = document.getElementById('rename-input');
    input.value = chat.title;
    modal.style.display = 'block';
    input.focus();
    input.select();

    // Add enter key support
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmRename(chatId);
        } else if (e.key === 'Escape') {
            hideRenameModal();
        }
    };
}

// Add these helper functions for the rename modal
function hideRenameModal() {
    const modal = document.getElementById('rename-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function confirmRename(chatId) {
    const input = document.getElementById('rename-input');
    const newTitle = input.value.trim();
    
    if (newTitle) {
        const chat = chats.find(c => c.id === chatId);
        if (chat) {
            chat.title = newTitle;
            updateChatHistory();
            saveChats();
        }
    }
    
    hideRenameModal();
} 