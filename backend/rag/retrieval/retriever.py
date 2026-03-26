"""RAG retrieval logic."""
import re
import asyncio
from typing import List, Optional
from langchain_chroma import Chroma
from core.settings import settings


class Retriever:
    """Wraps Chroma vector store retrieval with enrichment logic."""

    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store
        self.retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.rag.RETRIEVER_K,
                "fetch_k": settings.rag.RETRIEVER_FETCH_K,
                "lambda_mult": settings.rag.RETRIEVER_LAMBDA_MULT,
            }
        )

    def _extract_course_codes(self, docs: List) -> List[str]:
        code_re = re.compile(r'\b[A-Z]{2,4}\s?\d{3}[A-Z]?\b')
        codes = set()
        for doc in docs:
            text = (doc.page_content or "")
            for m in code_re.finditer(text):
                code = m.group(0).upper()
                code = re.sub(r'\s+', ' ', code).strip()
                codes.add(code)
        return sorted(codes)

    def _is_sequence_question(self, question: str) -> bool:
        q = question.lower()
        direct_markers = ("sequence", "four-year", "four year", "plan", "recommended sequence", "curriculum", "roadmap")
        if any(key in q for key in direct_markers):
            return True
        year_markers = ("first year", "sophomore", "junior", "senior")
        schedule_markers = ("schedule", "semester", "fall", "spring", "what should i take")
        return any(y in q for y in year_markers) and any(s in q for s in schedule_markers)

    def _is_management_major_query(self, text: str) -> bool:
        q = text.lower()
        management_markers = (
            "freeman", "management college", "college of management", "bsba",
            "business analytics", "anop", "accounting", "finance", "acfm",
            "mors", "mgmt", "management and organizations",
            "markets, innovation & design", "mide", "markets innovation and design",
        )
        return any(marker in q for marker in management_markers)

    def _enrich_with_course_entries(self, docs: List, question: str) -> List:
        if not docs or not self._is_sequence_question(question):
            return docs
        codes = self._extract_course_codes(docs)
        if not codes:
            return docs
        max_codes = 14
        extra_docs = []
        for code in codes[:max_codes]:
            variants = [code, code.replace(" ", "")]
            found = []
            for variant in variants:
                filt = {"$and": [{"doc_type": "catalog"}, {"course_code": variant}]}
                found = self.vector_store.similarity_search(code, k=1, filter=filt)
                if found:
                    break
            if not found:
                found = self.vector_store.similarity_search(code, k=2, filter={"doc_type": "catalog"})
            if found:
                extra_docs.extend(found)
        if extra_docs:
            return self._merge_docs(docs, extra_docs)
        return docs

    def _augment_management_plan_docs(self, docs: List, question: str, search_query: str) -> List:
        if not docs or not self._is_sequence_question(question):
            return docs
        if not self._is_management_major_query(f"{search_query} {question}"):
            return docs
        augmentation_queries = [
            "Freeman College Core Requirements",
            "Freeman College of Management General Education Curriculum",
            "BSBA degree requirements",
            "FOUNDATIONAL LITERACY REQUIREMENTS",
            "MANAGERIAL LITERACY REQUIREMENTS",
            "Analytics & Operations Management Suggested Plan of Study Freeman Core Courses",
        ]
        extra_docs = []
        for query in augmentation_queries:
            found = self.vector_store.similarity_search(query, k=2, filter={"doc_type": "catalog"})
            if found:
                extra_docs.extend(found)
        if extra_docs:
            return self._merge_docs(docs, extra_docs)
        return docs

    def _merge_docs(self, base_docs: List, extra_docs: List) -> List:
        merged = list(base_docs)
        seen = set()
        for d in merged:
            meta = d.metadata or {}
            seen.add((meta.get("source", ""), meta.get("page", 0)))
        for d in extra_docs:
            meta = d.metadata or {}
            key = (meta.get("source", ""), meta.get("page", 0))
            if key not in seen:
                seen.add(key)
                merged.append(d)
        return merged

    def retrieve(self, query: str, doc_type_filter: Optional[str] = None) -> List:
        if doc_type_filter:
            return self.vector_store.similarity_search(
                query, k=settings.rag.RETRIEVER_K, filter={"doc_type": doc_type_filter}
            )
        return self.retriever.invoke(query)

    async def retrieve_async(self, query: str, doc_type_filter: Optional[str] = None) -> List:
        try:
            if doc_type_filter:
                return await asyncio.to_thread(
                    self.vector_store.similarity_search, query,
                    k=settings.rag.RETRIEVER_K, filter={"doc_type": doc_type_filter}
                )
            return await asyncio.to_thread(self.retriever.invoke, query)
        except Exception as e:
            print(f"[WARNING] Async retrieval failed for '{query}': {e}")
            return []

    def retrieve_for_subqueries(self, sub_questions: List[str], doc_type_filter: Optional[str] = None) -> List:
        num_subqueries = len(sub_questions)
        if num_subqueries == 0:
            return []
        min_per_query = settings.rag.MIN_DOCS_PER_SUBQUERY
        total_min = min_per_query * num_subqueries
        if total_min > settings.rag.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, settings.rag.MAX_MULTI_STEP_DOCS // num_subqueries)
        docs_per_question = []
        for sub_q in sub_questions:
            try:
                docs_per_question.append(self.retrieve(sub_q, doc_type_filter))
            except Exception as e:
                print(f"[WARNING] Retrieval failed for sub-query '{sub_q}': {e}")
                docs_per_question.append([])
        return self._merge_subquery_docs(docs_per_question, min_per_query, num_subqueries)

    async def retrieve_for_subqueries_async(self, sub_questions: List[str], doc_type_filter: Optional[str] = None) -> List:
        num_subqueries = len(sub_questions)
        if num_subqueries == 0:
            return []
        tasks = [self.retrieve_async(sq, doc_type_filter) for sq in sub_questions]
        docs_per_question = await asyncio.gather(*tasks)
        min_per_query = settings.rag.MIN_DOCS_PER_SUBQUERY
        total_min = min_per_query * num_subqueries
        if total_min > settings.rag.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, settings.rag.MAX_MULTI_STEP_DOCS // num_subqueries)
        return self._merge_subquery_docs(docs_per_question, min_per_query, num_subqueries)

    def _merge_subquery_docs(self, docs_per_question, min_per_query: int, num_subqueries: int) -> List:
        all_docs = []
        seen_keys = set()
        docs_count_per_query = [0] * num_subqueries
        for idx, docs in enumerate(docs_per_question):
            for doc in docs[:min_per_query]:
                meta = doc.metadata or {}
                key = (meta.get("source", ""), meta.get("page", 0))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_docs.append(doc)
                    docs_count_per_query[idx] += 1
                    if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                        return all_docs
        max_per_question = max(len(docs) for docs in docs_per_question) if docs_per_question else 0
        for i in range(min_per_query, max_per_question):
            for idx, docs in enumerate(docs_per_question):
                if i < len(docs):
                    doc = docs[i]
                    meta = doc.metadata or {}
                    key = (meta.get("source", ""), meta.get("page", 0))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_docs.append(doc)
                        docs_count_per_query[idx] += 1
                        if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                            return all_docs
        return all_docs
