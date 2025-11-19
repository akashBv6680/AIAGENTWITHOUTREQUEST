import streamlit as st
import requests
import json
import os

# =========================
# Gemini API configuration
# =========================
# Put your key in .streamlit/secrets.toml as:
# GEMINI_API_KEY = "your_key_here"
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Official Gemini 2.5 Flash text endpoint
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# Local file to persist chat memory
MEMORY_FILE = "conversation_memory.json"


# =========================
# Persistent memory helpers
# =========================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Expecting list of {"role": "...", "content": "..."}
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


# =========================
# Gemini call
# =========================
def generate_gemini_response(user_prompt, conversation):
    """
    conversation: list of {"role": "user"|"assistant", "content": "text"}
    This converts to Gemini 'contents' format and calls generateContent.
    """
    # Build contents for Gemini
    contents = []

    # Optional system instruction
    system_instruction = (
        "You are a helpful AI agent embedded inside a Streamlit app. "
        "You remember previous conversation turns and proactively use them "
        "to provide context-aware replies. Keep responses concise and friendly."
    )

    contents.append(
        {
            "role": "user",
            "parts": [{"text": f"[SYSTEM INSTRUCTION]\n{system_instruction}"}],
        }
    )

    # Add history
    for msg in conversation:
        role = msg.get("role")
        text = msg.get("content", "")
        if not text:
            continue
        # Map to Gemini roles
        if role == "user":
            g_role = "user"
        else:
            g_role = "model"
        contents.append({"role": g_role, "parts": [{"text": text}]})

    # Add current user message
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
        },
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
    except Exception as e:
        return f"Request error: {e}"

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    data = response.json()

    # Parse text from candidates
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return "No response from model."
        parts = candidates[0].get("content", {}).get("parts", [])
        # Concatenate all text parts
        texts = [p.get("text", "") for p in parts if "text" in p]
        final_text = "".join(texts).strip()
        return final_text or "No text in response."
    except Exception as e:
        return f"Parse error: {e}"


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Gemini 2.5 Flash Agent", page_icon="🤖")
st.title("Gemini 2.5 Flash – Persistent Memory Agent")

# Initialize memory in session_state
if "conversation" not in st.session_state:
    st.session_state.conversation = load_memory()

st.caption(
    "This agent automatically loads your previous conversation and uses persistent memory "
    "from a local JSON file."
)

# Show previous conversation (auto-trigger behavior)
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
    st.info("No previous conversation found. Agent will start with a greeting.")
    greeting = (
        "Hi, welcome back! I’ll remember our conversation using persistent memory. "
        "What would you like to talk about today?"
    )
    st.markdown(f"**Agent:** {greeting}")
    st.session_state.conversation.append({"role": "assistant", "content": greeting})
    save_memory(st.session_state.conversation)

st.divider()

# User input
user_input = st.text_input("Your message", key="user_input")

col1, col2 = st.columns(2)
with col1:
    send_clicked = st.button("Send")
with col2:
    clear_clicked = st.button("Clear memory (file + session)")

# Clear memory logic
if clear_clicked:
    st.session_state.conversation = []
    if os.path.exists(MEMORY_FILE):
        try:
            os.remove(MEMORY_FILE)
        except Exception:
            pass
    st.success("Memory cleared. Reload the page to start fresh.")
    st.stop()

# Send message logic
if send_clicked and user_input.strip():
    user_msg = user_input.strip()

    # Add user message
    st.session_state.conversation.append({"role": "user", "content": user_msg})

    # Get response from Gemini
    with st.spinner("Agent is thinking..."):
        reply = generate_gemini_response(user_msg, st.session_state.conversation)

    # Add agent response
    st.session_state.conversation.append({"role": "assistant", "content": reply})

    # Persist to file
    save_memory(st.session_state.conversation)

    # Display latest response
    st.markdown(f"**Agent:** {reply}")

    # Clear input box
    st.session_state.user_input = ""
