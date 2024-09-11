document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const followUpContainer = document.getElementById('follow-up-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');
    const leftPanel = document.querySelector('.left-panel');
    const rightPanel = document.querySelector('.right-panel');
    const resizer = document.getElementById('resizer');
    const splitScreen = document.querySelector('.split-screen');

    let isResizing = false;

    // Function to update chat with the user message and bot response
    function sendMessage() {
        const question = userInput.value.trim();
        if (question) {
            addMessage('user', question); // Show user message
            userInput.value = '';
            clearFollowUpQuestions();
            showSearchingIndicator();

            // Fetching the response from backend
            fetch('http://localhost:8000/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: question }),
            })
            .then(response => response.json())
            .then(data => {
                removeSearchingIndicator();
                addMessage('bot', data.response); // Show bot response
                if (data.sources) {
                    addSources(data.sources);
                }
                if (data.follow_up_questions) {
                    setTimeout(() => {
                        addFollowUpQuestions(data.follow_up_questions);
                    }, 1000);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                removeSearchingIndicator();
                addMessage('bot', 'Sorry, there was an error processing your request.');
            });
        }
    }

    // Add message to the chat container
    function addMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `${sender}-message message`;
        messageElement.textContent = message;
        chatContainer.appendChild(messageElement);
        scrollToBottom();
    }

    // Show searching indicator while waiting for bot's response
    function showSearchingIndicator() {
        const searchingElement = document.createElement('div');
        searchingElement.className = 'bot-message message searching';
        searchingElement.textContent = 'Searching...';
        searchingElement.id = 'searching-indicator';
        chatContainer.appendChild(searchingElement);
        scrollToBottom();
    }

    // Remove searching indicator
    function removeSearchingIndicator() {
        const searchingElement = document.getElementById('searching-indicator');
        if (searchingElement) {
            searchingElement.remove();
        }
    }

    function addSources(sources) {
        if (sources && sources.length > 0) {
            const sourcesElement = document.createElement('div');
            sourcesElement.className = 'sources';
            sourcesElement.innerHTML = 'Sources:<br>';
    
            sources.forEach(source => {
                const sourceLink = document.createElement('a');
                sourceLink.href = source.url;
                sourceLink.textContent = `${source.number}. ${source.title}`;
                sourceLink.target = "_blank";  // Opens in a new tab
                sourcesElement.appendChild(sourceLink);
                sourcesElement.appendChild(document.createElement('br'));
            });
            
            chatContainer.appendChild(sourcesElement);
            scrollToBottom();
        }
    }
    

    // Add follow-up questions as clickable buttons
    function addFollowUpQuestions(questions) {
        clearFollowUpQuestions();
        if (questions && questions.length > 0) {
            questions.forEach((question, index) => {
                const button = document.createElement('button');
                button.textContent = `${index + 1}. ${question}`;
                button.className = 'follow-up-button';
                button.addEventListener('click', () => {
                    userInput.value = question;
                    sendMessage();
                });
                followUpContainer.appendChild(button);
            });
        }
    }

    // Clear follow-up questions from the container
    function clearFollowUpQuestions() {
        followUpContainer.innerHTML = '';
    }

    // Scroll chat to bottom after new messages
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
