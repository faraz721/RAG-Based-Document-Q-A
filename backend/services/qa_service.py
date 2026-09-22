from typing import List, Dict, Any

from groq import Groq

from utils.config import GROQ_API_KEY, GROQ_MODEL, TOP_K
from utils.session import valid_session_id, touch_session, cleanup_expired_sessions
from rag.embeddings import embed_query
from rag.vector_store import get_store


SYSTEM_PROMPT = """You are a helpful document Q&A assistant. You answer questions using ONLY the provided document context.

Rules:
1. Use the provided context as the primary and only source of factual information.
2. Do NOT invent or fabricate facts that are not supported by the context.
3. If the answer cannot be found in the context, clearly say: "The information was not found in the selected document."
4. Keep answers relevant to the user's question.
5. Structure your response based on the type of question:
   - General explanation → use ## Summary, ## Explanation, ## Key Points
   - Steps / process → use ## Steps with ### Step 1, ### Step 2, etc.
   - Comparison → use a clear comparison structure or markdown table if suitable
   - Advantages → ## Advantages with bullet points
   - Disadvantages → ## Disadvantages with bullet points
   - Simple explanation → give a simple explanation, important points, and an example if useful
6. Use markdown headings and bullet points for clarity.
7. When page numbers are available in the context, you may mention them (e.g. Source: filename, Page: N).
8. Be concise but complete. Do not add unnecessary fluff.
"""


def build_context(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return ""
    parts = []
    for i, c in enumerate(chunks, 1):
        page = c.get("page")
        filename = c.get("filename", "document")
        header = f"[Excerpt {i}"
        if page:
            header += f" | Page {page}"
        header += f" | {filename}]"
        parts.append(f"{header}\n{c.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def answer_question(doc_id: str, question: str, session_id: str) -> Dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Please enter a question.")

    if not valid_session_id(session_id):
        raise ValueError("Invalid or missing session. Please refresh the page.")

    if not GROQ_API_KEY:
        raise ValueError(
            "Groq API key is not configured. Please set GROQ_API_KEY in the .env file."
        )

    cleanup_expired_sessions(get_store())
    touch_session(session_id)

    store = get_store()
    if not store.document_exists(doc_id, session_id=session_id):
        raise ValueError("Selected document not found. It may have been deleted or expired.")

    doc = store.get_document(doc_id, session_id=session_id)
    original_name = doc.get("original_name") or doc.get("filename") or "document"

    try:
        query_emb = embed_query(question)
        chunks = store.search(doc_id, query_emb, top_k=TOP_K, session_id=session_id)
    except Exception as e:
        raise ValueError(f"Search failed: {str(e)}")

    if not chunks:
        return {
            "answer": "The information was not found in the selected document. No relevant excerpts could be retrieved for your question.",
            "sources": [],
            "document": original_name,
        }

    context = build_context(chunks)
    user_message = f"""Document: {original_name}

Context from the selected document:
{context}

---
User question: {question}

Answer the question using only the context above. Structure the answer appropriately for the type of question."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        answer = completion.choices[0].message.content or ""
    except TypeError as e:
        if "proxies" in str(e):
            raise ValueError(
                'Library conflict (httpx/groq). Run: pip install "httpx>=0.25.0,<0.28.0" then restart.'
            )
        raise ValueError(f"Failed to generate answer: {str(e)}")
    except Exception as e:
        err = str(e).lower()
        if "proxies" in err:
            raise ValueError(
                'Library conflict (httpx/groq). Run: pip install "httpx>=0.25.0,<0.28.0" then restart.'
            )
        if "api key" in err or "authentication" in err or "401" in err:
            raise ValueError(
                "Invalid or missing Groq API key. Please check GROQ_API_KEY in your .env file."
            )
        if "model" in err and ("not found" in err or "invalid" in err):
            raise ValueError(
                f"Model '{GROQ_MODEL}' is not available. Please set a supported GROQ_MODEL in .env."
            )
        raise ValueError(f"Failed to generate answer: {str(e)}")

    sources = []
    for c in chunks:
        src = {"filename": c.get("filename") or original_name}
        if c.get("page"):
            src["page"] = c["page"]
        if src not in sources:
            sources.append(src)

    return {
        "answer": answer.strip(),
        "sources": sources,
        "document": original_name,
    }
