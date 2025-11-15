const chatbotToggle = document.getElementById('chatbotToggle');
const chatbotWindow = document.getElementById('chatbotWindow');
const chatbotClose = document.getElementById('chatbotClose');
const chatbotInput = document.getElementById('chatbotInput');
const chatbotSend = document.getElementById('chatbotSend');
const chatbotMessages = document.getElementById('chatbotMessages');

if (chatbotToggle) {
    chatbotToggle.addEventListener('click', () => {
        chatbotWindow.classList.toggle('active');
    });
}

if (chatbotClose) {
    chatbotClose.addEventListener('click', () => {
        chatbotWindow.classList.remove('active');
    });
}

if (chatbotSend) {
    chatbotSend.addEventListener('click', sendMessage);
}

if (chatbotInput) {
    chatbotInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

function sendMessage() {
    const message = chatbotInput.value.trim();
    if (!message) return;

    const userMessage = document.createElement('div');
    userMessage.className = 'chatbot-message user-message';
    userMessage.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="message-content">
            ${message}
        </div>
    `;
    chatbotMessages.appendChild(userMessage);

    chatbotInput.value = '';

    setTimeout(() => {
        const botMessage = document.createElement('div');
        botMessage.className = 'chatbot-message bot-message';

        const responses = [
            'I found 12 documents related to your query. Would you like me to show them?',
            'Based on your search history, I recommend checking out the Data Structures course materials.',
            'I can help you find documents for CS101. What specific topic are you looking for?',
            'Here are the top 3 resources for that topic. Would you like more details?',
            'I noticed you are interested in Machine Learning. I have some great resources for beginners.'
        ];

        const randomResponse = responses[Math.floor(Math.random() * responses.length)];

        botMessage.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                ${randomResponse}
            </div>
        `;
        chatbotMessages.appendChild(botMessage);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }, 1000);

    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}