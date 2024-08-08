from openai import OpenAI
import streamlit as st
from dotenv import load_dotenv
import os
import shelve
from PyPDF2 import PdfReader
import io
from gtts import gTTS
import tempfile

load_dotenv()

st.title("Streamlit Chatbot Interface")

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ensure openai_model is initialized in session state
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini"  # Use gpt-4o-mini model

# Ensure document text is initialized in session state
if "document_text" not in st.session_state:
    st.session_state["document_text"] = ""

# Ensure speech input is initialized in session state
if "speech_input" not in st.session_state:
    st.session_state["speech_input"] = ""

# Load chat history from shelve file
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])

# Save chat history to shelve file
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# Function to convert text to speech in Hindi
def text_to_speech(text):
    tts = gTTS(text=text, lang='hi')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio_file:
        tts.save(temp_audio_file.name)
        return temp_audio_file.name

# Initialize or load chat history
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# Sidebar with a button to delete chat history
with st.sidebar:
    if st.button("Delete Chat History"):
        st.session_state.messages = []
        save_chat_history([])

    st.write("Upload a document:")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf"])
    if uploaded_file:
        st.session_state["document_text"] = extract_text_from_pdf(uploaded_file)
        st.write("Document uploaded and processed.")

# Function to get response from OpenAI
def get_openai_response(messages):
    full_response = ""
    for response in client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=messages,
        stream=True,
    ):
        full_response += response.choices[0].delta.content or ""
    return full_response

# Display chat messages
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# JavaScript for Speech-to-Text
st.components.v1.html("""
<!DOCTYPE html>
<html>
<head>
    <title>Voice Chat</title>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const startButton = document.createElement('button');
            startButton.innerText = 'Start Voice Input';
            startButton.style.margin = '10px';
            startButton.id = 'start-recording';
            document.body.appendChild(startButton);
            
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'hi-IN'; // Hindi language
            
            startButton.onclick = () => {
                recognition.start();
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                const inputField = document.getElementById('voice-input');
                inputField.value = transcript;
                inputField.dispatchEvent(new Event('input', { bubbles: true }));
            };
        });
    </script>
</head>
<body>
    <input type="hidden" id="voice-input" />
</body>
</html>
""", height=150)

# Handle speech-to-text input
prompt = st.text_input("Or use voice input:", key="voice_input")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    if st.session_state["document_text"]:
        prompt_with_context = f"{st.session_state['document_text']}\n\nUser question: {prompt}"
        response = get_openai_response([{"role": "user", "content": prompt_with_context}])
    else:
        response = get_openai_response(st.session_state["messages"])

    # Convert response to speech
    audio_file = text_to_speech(response)
    
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        message_placeholder.markdown(response + "|")
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.audio(audio_file, format='audio/mp3')

# Save chat history after each interaction
save_chat_history(st.session_state.messages)
