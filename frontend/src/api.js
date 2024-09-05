import axios from 'axios';

// Function to send a message to the backend
export const sendMessageToBackend = async (message) => {
    try {
        const response = await axios.post('http://localhost:8000/send_message', { content: message });
        return response.data;
    } catch (error) {
        console.error("Error sending message to backend", error);
        return { response: "An error occurred while processing your request." };
    }
};
