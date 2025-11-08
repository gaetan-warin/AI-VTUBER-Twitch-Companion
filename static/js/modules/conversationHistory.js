import { emit, socket } from './socket.js';

let currentUsername = 'Gaëtan'; // Default username

export function initializeConversationHistory() {
    setupHistoryEventListeners();
    setupSocketHandlers();
}

function setupHistoryEventListeners() {
    const $modal = $('#historyModal');
    const $closeBtn = $modal.find('.close');
    
    // Open modal when View History button is clicked
    $('#viewHistoryBtn').on('click', () => {
        $modal.show();
        refreshHistory();
    });
    
    // Close modal on X button
    $closeBtn.on('click', () => {
        $modal.hide();
    });
    
    // Close modal on outside click
    $(window).on('click', (event) => {
        if (event.target === $modal[0]) {
            $modal.hide();
        }
    });
    
    // Refresh history
    $('#refreshHistoryBtn').on('click', refreshHistory);
    
    // Clear history
    $('#clearHistoryBtn').on('click', clearHistory);
}

function setupSocketHandlers() {
    socket.on('conversation_history', handleConversationHistory);
    socket.on('conversation_history_cleared', handleHistoryCleared);
}

function refreshHistory() {
    $('#historyContent').html('<p class="no-history">Loading conversation history...</p>');
    emit('get_conversation_history', { username: currentUsername });
}

function clearHistory() {
    if (confirm('Are you sure you want to clear the conversation history?')) {
        emit('clear_conversation_history', { username: currentUsername });
    }
}

function handleConversationHistory(data) {
    if (data.status === 'success') {
        displayHistory(data.history);
    } else {
        $('#historyContent').html('<p class="no-history">Failed to load conversation history</p>');
        console.error('Failed to load conversation history');
    }
}

function handleHistoryCleared(data) {
    if (data.status === 'success') {
        $('#historyContent').html('<p class="no-history">No conversation history yet</p>');
    } else {
        alert('Failed to clear history: ' + data.message);
    }
}

function displayHistory(history) {
    const $content = $('#historyContent');
    
    if (!history || history.length === 0) {
        $content.html('<p class="no-history">No conversation history yet</p>');
        return;
    }
    
    $content.empty();
    
    history.forEach(entry => {
        const messageDiv = $('<div>')
            .addClass('history-message')
            .addClass(entry.role);
        
        const header = $('<div>')
            .addClass('history-message-header');
        
        const role = $('<span>')
            .addClass('history-message-role')
            .text(entry.role === 'user' ? `${entry.user}` : 'Sarah');
        
        const time = $('<span>')
            .addClass('history-message-time')
            .text(entry.timestamp);
        
        header.append(role, time);
        
        const content = $('<div>')
            .addClass('history-message-content')
            .text(entry.message);
        
        messageDiv.append(header, content);
        $content.append(messageDiv);
    });
    
    // Scroll to bottom
    $content.scrollTop($content[0].scrollHeight);
}

export function setCurrentUsername(username) {
    currentUsername = username;
}
