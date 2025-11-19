import streamlit as st
import requests
import json
import os

# Gemini API Key from Streamlit secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Gemini 2.5 Flash endpoint
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# Local file for persistent conversation
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
    # Construct context for Gemini model
    contents = []

    system_instruction = (
        "You are a helpful AI agent in a Streamlit app. "
        "You store and use previous conversations for context-aware replies."
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

# ---------------------
# UI STARTS HERE
# ---------------------

st.set_page_config(page_title="Gemini 2.5 Flash Agent", page_icon="🤖")
st.title("Gemini 2.5 Flash – Persistent AI Agent")

# Initialize session state vars
if "conversation" not in st.session_state:
    st.session_state.conversation = load_memory()
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "user_input_widget" not in st.session_state:
    st.session_state.user_input_widget = ""

st.caption("This agent loads your previous conversation and uses persistent memory from a JSON file.")

# Display previous conversation
if st.session_state.conversation:
    st.subheader("Previous conversation")
    for msg in st.session_state.conversation:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            st.markdown(f"**You:** {content}")
        else:
            st.markdown(f"**Agent:** {content}")
else:
    st.info("No previous conversation found. Starting with a greeting.")
    greeting = (
        "Hi, welcome! I'll remember our conversation using persistent memory. What would you like to talk about today?"
    )
    st.markdown(f"**Agent:** {greeting}")
    st.session_state.conversation.append({"role": "assistant", "content": greeting})
    save_memory(st.session_state.conversation)

st.divider()

# Callback to copy text and clear widget input
def submit_message():
    st.session_state.user_input = st.session_state.user_input_widget
    st.session_state.user_input_widget = ""

st.text_input(
    "Your message",
    key="user_input_widget",
    on_change=submit_message,
)

col1, col2 = st.columns(2)
with col1:
    send_clicked = st.button("Send")
with col2:
    clear_clicked = st.button("Clear memory (file + session)")

if clear_clicked:
    st.session_state.conversation = []
    if os.path.exists(MEMORY_FILE):
        try:
            os.remove(MEMORY_FILE)
        except Exception:
            pass
    st.success("Memory cleared. Reload the page to start fresh.")
    st.stop()

# Send logic: process new input either on Button click or new input
if (send_clicked or st.session_state.user_input) and st.session_state.user_input.strip():
    user_msg = st.session_state.user_input.strip()
    st.session_state.conversation.append({"role": "user", "content": user_msg})

    with st.spinner("Agent is thinking..."):
        reply = generate_gemini_response(user_msg, st.session_state.conversation)

    st.session_state.conversation.append({"role": "assistant", "content": reply})
    save_memory(st.session_state.conversation)
    st.markdown(f"**Agent:** {reply}")

    # Reset input to avoid accidental repeat
    st.session_state.user_input = ""
