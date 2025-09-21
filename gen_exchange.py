import os
import io
import json
import re
import streamlit as st
import google.generativeai as genai
from typing import Dict

import pdfplumber
import docx

# ========================
# 🔑 Configure Gemini
# ========================
genai.configure(api_key=os.getenv("AIzaSyAkkcZb_iR9Ffe6z_xgPbfLaP5-T2P6puA"))
LLM_MODEL = "gemini-1.5-flash"

def call_gemini(prompt: str, model: str = LLM_MODEL, temperature: float = 0.2) -> str:
    """Send a prompt to Gemini and return text response."""
    try:
        model_obj = genai.GenerativeModel(model)
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
# 📄 Document Extraction
# ========================
def extract_pdf_text(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
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
# 🌐 Streamlit UI
# ========================
st.set_page_config(page_title="AI Legal Simplifier", layout="wide")
st.title("📜 AI Legal Document Simplifier")
st.write("Upload a legal document, ask questions, or get AI-powered summaries and insights.")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    temperature = st.slider("AI Creativity / Temperature", 0.0, 1.0, 0.2)
    dark_mode = st.checkbox("Dark Mode", value=False)

# ========================
# File Upload (Main Area)
# ========================
uploaded_files = st.file_uploader(
    "📂 Upload one or more documents (PDF, DOCX, TXT)",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

if uploaded_files:
    all_texts: Dict[str, str] = {}
    for file in uploaded_files:
        text = extract_text(file)
        all_texts[file.name] = text

    tabs = st.tabs(["📄 Document Preview", "❓ Ask a Question", "📝 Summaries & Highlights", "✅ Action Items / Tips"])

    # ---------------- Document Preview ----------------
    with tabs[0]:
        for name, text in all_texts.items():
            st.subheader(f"Document: {name}")
            st.text_area("Extracted Text", text[:3000] + "...", height=200)

    # ---------------- Ask a Question ----------------
    with tabs[1]:
        doc_names = list(all_texts.keys())
        selected_doc = st.selectbox("Select a document", doc_names)
        user_question = st.text_input("Ask a question about this document:")

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Get Answer"):
                if user_question.strip():
                    prompt = f"""
                    You are a legal assistant. Read the following document and answer the user's question clearly in simple English.

                    Document:
                    {all_texts[selected_doc]}

                    Question:
                    {user_question}
                    """
                    answer = call_gemini(prompt, temperature=temperature)
                    st.subheader("💡 Answer")
                    st.write(answer)
                else:
                    st.warning("Please type a question to get an answer.")

        with col2:
            if st.button("Generate Suggested Questions"):
                prompt = f"Based on this document, generate 5 important questions a user might ask."
                sq = call_gemini(prompt, temperature=0.3)
                st.subheader("Suggested Questions")
                st.write(sq)

    # ---------------- Summaries & Highlights ----------------
    with tabs[2]:
        for name, text in all_texts.items():
            st.subheader(f"Document: {name}")
            prompt = f"""
            Summarize this legal document in plain English.
            Then provide a 3–4 line ultra-short summary.
            List obligations, deadlines, and risks as bullet points.
            Document:
            {text}
            """
            summary = call_gemini(prompt, temperature=temperature)
            st.text_area("Summary & Highlights", summary, height=250)

    # ---------------- Action Items / Tips ----------------
    with tabs[3]:
        for name, text in all_texts.items():
            st.subheader(f"Document: {name}")
            prompt = f"""
            Based on this legal document, generate a list of actionable tips or steps
            that a user should follow, in order of priority.
            Document:
            {text}
            """
            tips = call_gemini(prompt, temperature=temperature)
            st.text_area("Actionable Tips", tips, height=200)

            # Download option
            st.download_button(
                "Download Tips",
                data=tips,
                file_name=f"{name}_tips.txt",
                mime="text/plain"
            )
else:
    st.info("👆 Please upload a PDF, DOCX, or TXT document to begin.")

