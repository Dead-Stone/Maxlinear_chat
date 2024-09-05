import React, { useState } from 'react';
import { sendMessageToBackend } from './api';
import './App.css';

function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');

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

    return (
        <div className="App">
            <div className="chat-container">
                {messages.map((message, index) => (
                    <div key={index} className={`chat-message ${message.role}`}>
                        {message.role === 'assistant' ? (
                            <>
                                <FormattedMessage content={message.content} />
                                {console.log("inside the matrix")}
                            </>
                        ) : (
                            <p>{message.content}</p>
                        )}
                    </div>
                ))}
            </div>
            <div className="input-container">
                <input 
                    type="text" 
                    value={input} 
                    onChange={(e) => setInput(e.target.value)} 
                    placeholder="Ask a question..." 
                />
                <button onClick={handleSend}>Send</button>
            </div>
        </div>
    );
}

// Function to format and render the assistant's message content
const FormattedMessage = ({ content }) => {
    // Assuming the content is returned in a JSON format with title, summary, and link
    let formattedContent;
    try {
        const parsedContent = JSON.parse(content);
        formattedContent = (
            <div>
                <p><strong>{parsedContent.title}</strong></p>
                <p>{parsedContent.summary}</p>
                <p>For more details, visit: <a href={parsedContent.link} target="_blank" className="hover-link">[Link]</a></p>
            </div>
        );
    } catch (error) {
        // Fallback for plain text or unexpected content
        formattedContent = <p>{content}</p>;
    }

    return <div>{formattedContent}</div>;
};

export default App;
