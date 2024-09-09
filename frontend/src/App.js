import React, { useState, useEffect, useRef } from 'react';
import { sendMessageToBackend } from './api';
import './App.css';
import { FaUserAlt, FaRobot } from 'react-icons/fa';  // Import icons for user and assistant
import ReactMarkdown from 'react-markdown';  // Import ReactMarkdown for rendering markdown

function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const chatContainerRef = useRef(null);

    // Automatically scroll to the end of the chat when new messages are added
    useEffect(() => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
    }, [messages]);

    // Handle sending messages
    const handleSend = async () => {
        if (input.trim()) {
            const userMessage = { role: 'user', content: input };
            setMessages([...messages, userMessage]);

            const response = await sendMessageToBackend(input);
            const assistantMessage = { role: 'assistant', content: response.response };
            setMessages([...messages, userMessage, assistantMessage]);
            setInput('');
        }
    };

    // Handle Enter and Shift+Enter
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="App">
            <div className="chat-container" ref={chatContainerRef}>
                {messages.map((message, index) => (
                    <div key={index} className={`chat-message ${message.role}`}>
                        {message.role === 'user' ? (
                            <>
                                <FaUserAlt className="chat-icon" />
                                <p>{message.content}</p>
                            </>
                        ) : (
                            <>
                                <FaRobot className="chat-icon" />
                                <FormattedMessage content={message.content} />
                            </>
                        )}
                    </div>
                ))}
            </div>
            <div className="input-container">
                <textarea
                    rows="1"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question (Shift+Enter for new line)..."
                />
                <button onClick={handleSend}>Send</button>
            </div>
        </div>
    );
}

// Function to render markdown content, which will format the GPT-4 output neatly
const FormattedMessage = ({ content }) => {
    return (
        <div className="formatted-message">
            <ReactMarkdown
                components={{
                    a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default App;
