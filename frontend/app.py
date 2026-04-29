"""DocuSense AI — Streamlit frontend."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import requests
import streamlit as st

API = os.environ.get("DOCUSENSE_API", "http://localhost:8001/api")
TIMEOUT = 180

st.set_page_config(
    page_title="DocuSense AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------- Style ---------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Source+Sans+3:wght@300;400;600&display=swap');

:root {
  --bg: #0e141b;
  --panel: #141d28;
  --panel-2: #1a2532;
  --ink: #e6edf3;
  --muted: #8b96a3;
  --accent: #f7b955;
  --accent-2: #5ec3a5;
  --line: #233040;
  --danger: #e26b6b;
}

html, body, [data-testid="stAppViewContainer"], .main {
  background: var(--bg) !important;
  color: var(--ink) !important;
  font-family: 'Source Sans 3', sans-serif;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1118 0%, #101822 100%) !important;
  border-right: 1px solid var(--line);
}

h1, h2, h3, h4, .docusense-brand {
  font-family: 'JetBrains Mono', monospace !important;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.docusense-brand {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1rem;
}
.docusense-brand .dot {
  width: 10px; height: 10px; border-radius: 2px;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent);
}
.docusense-tag { color: var(--muted); font-size: 0.85rem; font-family: 'Source Sans 3'; font-weight: 300; }

.section-title {
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 0.18em;
  margin: 0.5rem 0 0.75rem;
}

.doc-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
  margin-bottom: 0.5rem;
}
.doc-card.active { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
.doc-card .name { font-weight: 600; color: var(--ink); font-size: 0.92rem; }
.doc-card .meta { color: var(--muted); font-size: 0.78rem; font-family: 'JetBrains Mono'; }

.chat-bubble-user, .chat-bubble-ai {
  padding: 1rem 1.2rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  border: 1px solid var(--line);
  line-height: 1.6;
}
.chat-bubble-user { background: var(--panel-2); border-left: 3px solid var(--accent-2); }
.chat-bubble-ai { background: var(--panel); border-left: 3px solid var(--accent); }
.chat-role { font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.4rem; }

.citation {
  background: #0b1118;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent-2);
  padding: 0.6rem 0.8rem;
  border-radius: 3px;
  margin: 0.4rem 0;
  font-size: 0.85rem;
  color: var(--muted);
  font-family: 'JetBrains Mono';
}
.citation b { color: var(--accent); font-weight: 600; }

.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  font-family: 'JetBrains Mono'; text-transform: uppercase; letter-spacing: 0.12em;
  font-size: 0.78rem; color: var(--muted); padding: 0.6rem 1.2rem;
  background: transparent; border: 0; border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }

.stButton > button, .stDownloadButton > button {
  background: var(--accent); color: #1a1208; font-family: 'JetBrains Mono';
  font-weight: 700; letter-spacing: 0.04em; border: 0; border-radius: 3px;
  padding: 0.55rem 1.1rem; text-transform: uppercase; font-size: 0.78rem;
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(247,185,85,0.25); }

.stTextArea textarea, .stTextInput input, .stChatInput textarea {
  background: var(--panel) !important; color: var(--ink) !important;
  border: 1px solid var(--line) !important; border-radius: 3px !important;
  font-family: 'Source Sans 3' !important;
}

[data-testid="stFileUploader"] {
  background: var(--panel); border: 1px dashed var(--line); border-radius: 4px; padding: 0.5rem;
}

.stSelectbox > div > div, .stMultiSelect > div > div {
  background: var(--panel) !important; border: 1px solid var(--line) !important; color: var(--ink) !important;
}
.empty-state {
  text-align: center; padding: 4rem 1rem; color: var(--muted);
  border: 1px dashed var(--line); border-radius: 4px;
}
.empty-state .big { font-family: 'JetBrains Mono'; font-size: 2.4rem; color: var(--accent); letter-spacing: 0.05em; }

.kpi-row { display: flex; gap: 0.75rem; margin: 0.75rem 0 1.25rem; }
.kpi { flex: 1; background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--accent); padding: 0.75rem 1rem; border-radius: 3px; }
.kpi .v { font-family: 'JetBrains Mono'; font-size: 1.4rem; color: var(--ink); font-weight: 700; }
.kpi .l { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; }
hr { border: 0; border-top: 1px solid var(--line); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------- API Helpers ---------------------------


def api_get(path: str) -> Any:
    r = requests.get(f"{API}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json_body: Dict | None = None, files=None) -> Any:
    r = requests.post(f"{API}{path}", json=json_body, files=files, timeout=TIMEOUT)
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(f"{r.status_code}: {detail}")
    return r.json()


def api_delete(path: str) -> Any:
    r = requests.delete(f"{API}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# --------------------------- State ---------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict] = []
if "selected_doc_ids" not in st.session_state:
    st.session_state.selected_doc_ids: List[str] = []
if "last_summary" not in st.session_state:
    st.session_state.last_summary: Dict[str, str] = {}
if "last_insights" not in st.session_state:
    st.session_state.last_insights: Dict[str, Any] = {}
if "last_compare" not in st.session_state:
    st.session_state.last_compare: Dict[str, Any] = {}
if "last_contradictions" not in st.session_state:
    st.session_state.last_contradictions: Dict[str, Any] = {}


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


# --------------------------- Sidebar: library & upload ---------------------------
with st.sidebar:
    st.markdown(
        '<div class="docusense-brand"><span class="dot"></span>DocuSense AI</div>'
        '<div class="docusense-tag">Intelligent Research & Synthesis Engine</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Upload</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "PDF, TXT or MD",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="file_uploader",
    )
    if uploaded:
        for f in uploaded:
            key = f"_uploaded::{f.name}::{f.size}"
            if key in st.session_state:
                continue
            with st.spinner(f"Ingesting {f.name}…"):
                try:
                    api_post(
                        "/upload",
                        files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")},
                    )
                    st.session_state[key] = True
                    st.toast(f"Ingested · {f.name}", icon="✓")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

    try:
        documents = api_get("/documents")
    except Exception as exc:
        st.error(f"Backend unreachable: {exc}")
        documents = []

    st.markdown('<div class="section-title">Library</div>', unsafe_allow_html=True)
    if not documents:
        st.markdown('<div style="color:var(--muted);font-size:0.85rem">No documents yet.</div>', unsafe_allow_html=True)
    else:
        all_ids = [d["id"] for d in documents]
        labels = {d["id"]: d["name"] for d in documents}
        valid_default = [i for i in st.session_state.selected_doc_ids if i in all_ids]
        if not valid_default:
            valid_default = all_ids
        st.session_state.selected_doc_ids = st.multiselect(
            "Documents in scope",
            options=all_ids,
            default=valid_default,
            format_func=lambda i: labels.get(i, i),
            key="scope_select",
        )
        for d in documents:
            active = d["id"] in st.session_state.selected_doc_ids
            cls = "doc-card active" if active else "doc-card"
            st.markdown(
                f'<div class="{cls}"><div class="name">{d["name"]}</div>'
                f'<div class="meta">{d["num_pages"]} pages · {d["num_chunks"]} chunks · {fmt_size(d["size_bytes"])}</div></div>',
                unsafe_allow_html=True,
            )
            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("Remove", key=f"del-{d['id']}", use_container_width=True):
                    try:
                        api_delete(f"/documents/{d['id']}")
                        st.toast(f"Removed {d['name']}", icon="–")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Delete failed: {exc}")

# --------------------------- Header ---------------------------
left, right = st.columns([3, 1])
with left:
    st.markdown(
        '<h1 style="margin-bottom:0.2rem">Intelligent Research<br/><span style="color:var(--accent)">& Synthesis</span></h1>'
        '<div style="color:var(--muted);font-family:Source Sans 3;font-weight:300;font-size:1.05rem;max-width:42rem;margin-bottom:1rem">'
        'Upload research papers, contracts, reports — chat with them, surface insights, and pit two documents against each other to see exactly where they disagree.'
        '</div>',
        unsafe_allow_html=True,
    )
with right:
    n_docs = len(documents) if documents else 0
    n_pages = sum(d.get("num_pages", 0) for d in (documents or []))
    n_chunks = sum(d.get("num_chunks", 0) for d in (documents or []))
    st.markdown(
        f'<div class="kpi-row">'
        f'<div class="kpi"><div class="v">{n_docs}</div><div class="l">Docs</div></div>'
        f'<div class="kpi"><div class="v">{n_pages}</div><div class="l">Pages</div></div>'
        f'<div class="kpi"><div class="v">{n_chunks}</div><div class="l">Chunks</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# --------------------------- Tabs ---------------------------
tab_chat, tab_summary, tab_insights, tab_compare, tab_contra = st.tabs(
    ["Chat", "Summary", "Insights", "Compare", "Contradictions"]
)

# ----- Chat -----
with tab_chat:
    if not documents:
        st.markdown(
            '<div class="empty-state"><div class="big">▢</div>'
            '<p>Upload a PDF in the sidebar to start a conversation.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        scope = st.session_state.selected_doc_ids or [d["id"] for d in documents]
        scope_names = ", ".join(documents and [d["name"] for d in documents if d["id"] in scope]) or "All"
        st.markdown(f'<div class="section-title">In scope · {scope_names}</div>', unsafe_allow_html=True)

        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-bubble-user"><div class="chat-role">You</div>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-bubble-ai"><div class="chat-role">DocuSense</div>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("citations"):
                    with st.expander(f"Sources ({len(msg['citations'])})"):
                        for i, c in enumerate(msg["citations"], start=1):
                            st.markdown(
                                f'<div class="citation"><b>[Source {i}]</b> {c["doc_name"]} · p.{c["page"]} · '
                                f'score {c.get("score") or 0:.2f}<br/><br/>{c["text"][:1200]}{"…" if len(c["text"])>1200 else ""}</div>',
                                unsafe_allow_html=True,
                            )

        prompt = st.chat_input("Ask anything about your documents…")
        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.spinner("Thinking…"):
                try:
                    res = api_post(
                        "/query",
                        json_body={"question": prompt, "doc_ids": scope, "top_k": 6},
                    )
                    st.session_state.chat_history.append(
                        {"role": "ai", "content": res["answer"], "citations": res.get("citations", [])}
                    )
                except Exception as exc:
                    st.session_state.chat_history.append(
                        {"role": "ai", "content": f"Error: {exc}", "citations": []}
                    )
            st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

# ----- Summary -----
with tab_summary:
    if not documents:
        st.info("Upload a document to generate a summary.")
    else:
        labels = {d["id"]: d["name"] for d in documents}
        sel = st.selectbox("Document", options=list(labels), format_func=lambda i: labels[i], key="summary_sel")
        if st.button("Generate summary", key="gen_summary"):
            with st.spinner("Summarising…"):
                try:
                    res = api_post("/summary", json_body={"doc_id": sel})
                    st.session_state.last_summary[sel] = res["summary"]
                except Exception as exc:
                    st.error(f"{exc}")
        if sel in st.session_state.last_summary:
            st.markdown(st.session_state.last_summary[sel])

# ----- Insights -----
with tab_insights:
    if not documents:
        st.info("Upload a document to extract insights.")
    else:
        labels = {d["id"]: d["name"] for d in documents}
        sel = st.selectbox("Document", options=list(labels), format_func=lambda i: labels[i], key="insights_sel")
        if st.button("Extract insights", key="gen_insights"):
            with st.spinner("Extracting…"):
                try:
                    res = api_post("/insights", json_body={"doc_id": sel})
                    st.session_state.last_insights[sel] = res["raw"]
                except Exception as exc:
                    st.error(f"{exc}")
        raw = st.session_state.last_insights.get(sel)
        if raw:
            m = re.search(r"\{.*\}", raw, re.S)
            data = None
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = None
            if data and "insights" in data:
                col_left, col_right = st.columns([2, 1])
                with col_left:
                    st.markdown('<div class="section-title">Key Insights</div>', unsafe_allow_html=True)
                    for ins in data.get("insights", []):
                        st.markdown(
                            f'<div class="chat-bubble-ai"><div class="chat-role">p.{ins.get("page","?")} · {ins.get("title","")}</div>'
                            f'{ins.get("detail","")}</div>',
                            unsafe_allow_html=True,
                        )
                with col_right:
                    ents = data.get("entities", {})
                    st.markdown('<div class="section-title">Entities</div>', unsafe_allow_html=True)
                    for k, vals in ents.items():
                        if vals:
                            st.markdown(f'**{k.title()}**')
                            st.markdown(", ".join(vals))
            else:
                st.markdown(raw)

# ----- Compare -----
with tab_compare:
    if len(documents) < 2:
        st.info("Upload at least two documents to compare.")
    else:
        labels = {d["id"]: d["name"] for d in documents}
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("Document A", options=list(labels), format_func=lambda i: labels[i], key="cmp_a")
        with c2:
            opts_b = [i for i in labels if i != a]
            b = st.selectbox("Document B", options=opts_b, format_func=lambda i: labels[i], key="cmp_b")
        if st.button("Run comparison", key="gen_compare"):
            with st.spinner("Comparing…"):
                try:
                    res = api_post("/compare", json_body={"doc_id_a": a, "doc_id_b": b})
                    st.session_state.last_compare[(a, b)] = res
                except Exception as exc:
                    st.error(f"{exc}")
        cached = st.session_state.last_compare.get((a, b))
        if cached:
            st.markdown(cached["comparison"])

# ----- Contradictions -----
with tab_contra:
    if len(documents) < 2:
        st.info("Upload at least two documents to find contradictions.")
    else:
        labels = {d["id"]: d["name"] for d in documents}
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("Document A", options=list(labels), format_func=lambda i: labels[i], key="ct_a")
        with c2:
            opts_b = [i for i in labels if i != a]
            b = st.selectbox("Document B", options=opts_b, format_func=lambda i: labels[i], key="ct_b")
        if st.button("Find contradictions", key="gen_contra"):
            with st.spinner("Cross-checking…"):
                try:
                    res = api_post("/contradictions", json_body={"doc_id_a": a, "doc_id_b": b})
                    st.session_state.last_contradictions[(a, b)] = res
                except Exception as exc:
                    st.error(f"{exc}")
        cached = st.session_state.last_contradictions.get((a, b))
        if cached:
            st.markdown(cached["contradictions"])

st.markdown(
    '<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--muted);font-family:JetBrains Mono;font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase">DocuSense AI · powered by Gemini 3 Flash · all-MiniLM-L6-v2 · ChromaDB</div>',
    unsafe_allow_html=True,
)
