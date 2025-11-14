# chatbot.py
"""
Gradio chat UI that answers ONLY from the Bucknell course catalog stored in Chroma.
- Uses the SAME Chroma collection name as ingestion (bucknell_catalogue)
- Uses MMR retrieval for more diverse hits
- Passes chunk headers with [filename, p.X] so the model can cite pages
- Streams responses for a nice UX
"""

import os
from dotenv import load_dotenv
import gradio as gr

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# Paths & names 
DATA_PATH = "data"
CHROMA_PATH = "chroma_db"
COLLECTION = "bucknell_catalogue"  # <-- MUST MATCH ingest_database.py

#  Embeddings & LLM 
# Requires OPENAI_API_KEY
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

# Keep temperature modest; catalog is factual.
llm = ChatOpenAI(temperature=0.3, model="gpt-4o-mini")

#  Vector store & retriever 
vector_store = Chroma(
    collection_name=COLLECTION,
    embedding_function=embeddings_model,
    persist_directory=CHROMA_PATH,
)

# MMR surfaces diverse but relevant chunks; higher fetch_k to broaden the pool
retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 8, "fetch_k": 50, "lambda_mult": 0.4},
)

def _short_source(path: str) -> str:
    """Turn a long file path into a friendly filename for citations."""
    if not path:
        return "Source"
    name = os.path.basename(path)
    return name.replace("_", " ")

def _prepare_knowledge(docs):
    """
    Build a labeled context string so the model can cite pages.
    Each chunk gets a header like:
    [2025-2026 course catalog.pdf, p. 367]
    <chunk text>
    """
    parts = []
    for d in docs:
        meta = d.metadata or {}
        src = _short_source(meta.get("source", "Catalogue"))
        # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
        page = (meta.get("page", 0) or 0) + 1
        header = f"[{src}, p. {page}]"
        parts.append(f"{header}\n{d.page_content.strip()}\n")
    return "\n".join(parts)

def stream_response(message, history):
    """
    Called for each user turn. Retrieves chunks, builds a strict RAG prompt,
    and streams back the LLM response.
    `history` is provided by Gradio; we don’t need it for retrieval itself.
    """
    # 1) Retrieve context
    docs = retriever.invoke(message)
    if not docs:
        # If nothing retrieved, be transparent and helpful
        yield ("I couldn’t retrieve relevant catalog sections. "
               "Please try rephrasing (e.g., include a course code like CSCI 204) "
               "or check that the PDF is ingested.")
        return

    knowledge = _prepare_knowledge(docs)

    # 2) Build the prompt (single string is fine for streaming)
    rag_prompt = f"""
You are the Bucknell University Academic Catalogue Virtual Assistant.
Answer ONLY using the content below in *Knowledge*. Do NOT use outside knowledge.
If the answer is not explicitly supported, say you don’t know and suggest contacting an academic advisor.

Rules you MUST follow:
- Be professional, warm, and student-centered.
- Use short bullets for lists (requirements, steps, recommended courses).
- Include page citations by copying the bracket tags from the relevant chunks
  (e.g., [2025-2026 course catalog.pdf, p. 367]).
- Never hallucinate course counts, requirements, or policies.

Course Recommendation Guidance (when applicable):
- Prioritize courses aligned with the student’s major/concentration/interests.
- Verify prerequisites before recommending.
- Recommend a balanced load (major/core + gen ed + electives).
- Consider student’s year (100-level for first-years, then 200/300 etc.).
- Don’t suggest courses already completed or their prerequisites; suggest the next level instead.
- List suggested courses in ascending order (100–500).

QUESTION:
{message}

KNOWLEDGE (catalog snippets with page tags):
{knowledge}
"""

    # 3) Stream back the model output
    partial = ""
    for token in llm.stream(rag_prompt):
        partial += token.content
        yield partial

#  Gradio UI 
# The deprecation warning you saw is harmless, but we can ignore it for now.
chatbot = gr.ChatInterface(
    fn=stream_response,
    textbox=gr.Textbox(
        placeholder="Ask about majors, prerequisites, or course planning…",
        container=False,
        autoscroll=True,
        scale=7,
    ),
)

if __name__ == "__main__":
    # share=True gives you a temporary public URL for quick demos
    chatbot.launch(share=True)
