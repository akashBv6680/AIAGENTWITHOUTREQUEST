import streamlit as st
import requests
import json
import os

# -- Gemini API Config --
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)
MEMORY_FILE = "conversation_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def generate_gemini_response(user_prompt, conversation):
    contents = []
    system_instruction = (
        "You are a proactive, helpful AI agent built for a persistent chat experience in Streamlit. "
        "Summarize, suggest, or build on the user's last message when possible."
    )
    contents.append({
        "role": "user",
        "parts": [{"text": f"[SYSTEM INSTRUCTION]\n{system_instruction}"}],
    })
    for msg in conversation:
        role = msg.get("role")
        text = msg.get("content", "")
        g_role = "user" if role == "user" else "model"
        if text:
            contents.append({"role": g_role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.7},
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
    except Exception as e:
        return f"Request error: {e}"
    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"
    data = response.json()
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return "No response from model."
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        return "".join(texts).strip() or "No text in response."
    except Exception as e:
        return f"Parse error: {e}"

# -- Streamlit UI --
st.set_page_config(page_title="Gemini Static Chatbot Box", page_icon="💬")

if "conversation" not in st.session_state:
    st.session_state.conversation = load_memory()
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# -- Chat History as a Scrollable Box --
chat_height = 370 # px, tune as you wish
st.markdown(f"""
    <style>
    .chat-history {{height: {chat_height}px; overflow-y: auto; border:1px solid #ddd; border-radius:8px; padding:12px; background:#fafafa; margin-bottom:12px;}}
    .chat-message {{margin-bottom:8px;}}
    /* Remove footer padding for bottom-anchored input */
    .block-container {{ padding-bottom: 10px; }}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0'>Gemini Chatbot</h2>", unsafe_allow_html=True)
st.caption("Scroll inside the chat window if the conversation is long. The input box stays at the bottom like a standard chat app.")

with st.container():
    st.markdown("<div class='chat-history'>", unsafe_allow_html=True)
    for msg in st.session_state.conversation:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-message'><b>You:</b> {msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-message'><b>Agent:</b> {msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -- Static bottom input and buttons (not inside chat-history div!)
user_input = st.text_input("Type your message and press Enter...", key="user_input")
col1, col2 = st.columns([1,1])
send_clicked = col1.button("Send")
clear_clicked = col2.button("Clear Conversation")

if send_clicked and user_input.strip():
    st.session_state.conversation.append({"role": "user", "content": user_input.strip()})
    reply = generate_gemini_response(user_input.strip(), st.session_state.conversation)
    st.session_state.conversation.append({"role": "assistant", "content": reply})
    save_memory(st.session_state.conversation)
    st.session_state.user_input = ""
    st.experimental_rerun()  # ensures scroll/bottom anchor refresh

if clear_clicked:
    st.session_state.conversation = []
    if os.path.exists(MEMORY_FILE):
        try:
            os.remove(MEMORY_FILE)
        except Exception:
            pass
    st.experimental_rerun()
