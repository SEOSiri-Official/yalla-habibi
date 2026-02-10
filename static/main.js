let currentLang = 'ar-SA'; // Default to Saudi Arabic

function setLanguage(langCode) {
    currentLang = langCode; // 'ar-SA', 'bn-BD', or 'en-US'
    console.log("Assistant is now listening in: " + langCode);
    // Restart recognition with new lang
    recognition.stop();
    recognition.lang = currentLang;
    recognition.start();
}

// Inside your SpeechRecognition result handler:
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    
    // Send to your FastAPI backend
    fetch(`/api/chat?user_input=${transcript}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById("response").innerText = data.reply;
            // Highlight the persona being used
            document.getElementById("status").innerText = "Mode: " + data.persona;
        });
};