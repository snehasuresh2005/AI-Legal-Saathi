import os
import io
import docx
import pdfplumber
import streamlit as st
import google.generativeai as genai
from datetime import datetime

# ========================
# Config
# ========================
# Use st.secrets or os.getenv for API key
genai.configure(api_key=os.getenv("AIzaSyBNhYbRGScmFDkfB9GH-yn5VZA7OlMQfHE"))
LLM_MODEL = "gemini-1.5-flash"


def call_gemini(prompt: str, temperature: float = 0.2) -> str:
    """Send prompt to Gemini and return text response."""
    try:
        model_obj = genai.GenerativeModel(LLM_MODEL)
        response = model_obj.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=1500
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"(Error: {e})"


# ========================
# File extraction helpers
# ========================
def extract_pdf_text(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text.strip()


def extract_docx_text(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paras)


def extract_txt_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore")


def extract_text(file) -> str:
    fname = file.name.lower()
    file_bytes = file.read()
    if fname.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    elif fname.endswith(".docx"):
        return extract_docx_text(file_bytes)
    elif fname.endswith(".txt"):
        return extract_txt_text(file_bytes)
    else:
        return ""


# ========================
# Session State
# ========================
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None


# ========================
# Sidebar (ChatGPT-like)
# ========================
st.sidebar.title("📂 Chats")

# --- MODIFIED: Disable "New Chat" button if the current chat has no messages ---
# The button is disabled if a chat is open and it has no messages.
is_new_chat_disabled = (
    st.session_state.current_chat is not None and
    not st.session_state.chats[st.session_state.current_chat]["messages"]
)
if st.sidebar.button("➕ New Chat", disabled=is_new_chat_disabled, help="You can't start a new chat until you've sent a message in the current one."):
    chat_id = str(datetime.now().timestamp())
    st.session_state.chats[chat_id] = {"title": "New Chat", "messages": [], "docs": {}}
    st.session_state.current_chat = chat_id

# List previous chats
for chat_id, chat in st.session_state.chats.items():
    if st.sidebar.button(chat["title"], key=chat_id):
        st.session_state.current_chat = chat_id

st.sidebar.markdown("---")
temperature = st.sidebar.slider("✨ Creativity", 0.0, 1.0, 0.2)


# ========================
# Main Area
# ========================
if st.session_state.current_chat is None:
    # Landing Page
    st.markdown("""
    <div style="text-align:center; padding:60px;">
        <h1 style="color:#a855f7;">📜 AI Legal Document Simplifier</h1>
        <p style="font-size:1.2rem; color:#ccc;">
            Upload contracts, ask questions, and get clear answers in plain English.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload legal documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    if uploaded_files:
        # Start new chat with file
        chat_id = str(datetime.now().timestamp())
        texts = {f.name: extract_text(f) for f in uploaded_files}
        st.session_state.chats[chat_id] = {
            "title": uploaded_files[0].name,
            "messages": [("system", f"Documents uploaded: {', '.join(texts.keys())}")],
            "docs": texts
        }
        st.session_state.current_chat = chat_id
        st.rerun()

else:
    # Chat view
    chat = st.session_state.chats[st.session_state.current_chat]
    st.header(chat["title"])

    # --- NEW: Add an option to preview the document ---
    if chat.get("docs"):
        with st.expander("📄 Document Preview"):
            for doc_name, doc_text in chat["docs"].items():
                st.subheader(doc_name)
                # Use st.code to show text with fixed-width font
                st.code(doc_text, language="text")

    # Show conversation
    for role, msg in chat["messages"]:
        if role == "user":
            st.markdown(
                f"<div style='text-align:right; background:#222; padding:10px; border-radius:10px; margin:5px;'>{msg}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background:#111; padding:10px; border-radius:10px; margin:5px; color:#a855f7;'>{msg}</div>",
                unsafe_allow_html=True
            )
    
    # --- MODIFIED: Disable input and button if no document is uploaded ---
    docs_exist = bool(chat.get("docs"))
    
    # Input box + summarize button
    cols = st.columns([4, 1])

    with cols[0]:
        user_input = st.chat_input(
            "Ask a question about your document...",
            disabled=not docs_exist
        )
        if not docs_exist:
            st.warning("Please upload a document to enable the chat.")

    with cols[1]:
        summarize_btn = st.button(
            "📑 Summarize",
            disabled=not docs_exist,
            help="Upload a document to enable this button."
        )

    # Handle input
    if user_input:
        # Normal Q&A
        chat["messages"].append(("user", user_input))
        docs_text = "\n\n".join(chat.get("docs", {}).values())
        prompt = f"Document:\n{docs_text}\n\nQuestion: {user_input}\n\nAnswer in plain English."
        answer = call_gemini(prompt, temperature=temperature)
        chat["messages"].append(("assistant", answer))
        st.rerun()

    elif summarize_btn:
        # Summarize document when button clicked
        docs_text = "\n\n".join(chat.get("docs", {}).values())
        prompt = f"Summarize this legal document in simple English. Highlight obligations, deadlines, and risks.\n\n{docs_text}"
        summary = call_gemini(prompt, temperature=temperature)
        chat["messages"].append(("assistant", summary))
        st.rerun()