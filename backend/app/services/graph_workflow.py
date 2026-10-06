from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class GraphState(TypedDict, total=False):
    user_query: str
    conversation_id: str
    workspace_filters: dict[str, Any]
    rewritten_query: str
    retrieved_chunks: list[dict[str, Any]]
    context: str
    draft_answer: str
    citations: list[dict[str, Any]]
    validation_results: dict[str, Any]
    error: str
    retries: int


def understand_query(state: GraphState) -> GraphState:
    state["user_query"] = state.get("user_query", "")
    state["retries"] = state.get("retries", 0)
    return state


def rewrite_query(state: GraphState) -> GraphState:
    q = state.get("user_query", "")
    if len(q) < 5:
        state["rewritten_query"] = q
        return state
    state["rewritten_query"] = q.strip()
    return state


def retrieve_documents(state: GraphState) -> GraphState:
    query = state.get("rewritten_query") or state.get("user_query", "")
    state["retrieved_chunks"] = [{"page_content": f"Context for: {query}", "metadata": {"filename": "demo.txt", "page_number": 1}}]
    return state


def check_retrieval_relevance(state: GraphState) -> GraphState:
    state["validation_results"] = {"has_relevant_context": bool(state.get("retrieved_chunks"))}
    return state


def build_context(state: GraphState) -> GraphState:
    pieces = [chunk.get("page_content", "") for chunk in state.get("retrieved_chunks", [])]
    state["context"] = "\n\n".join(pieces)
    return state


def generate_answer(state: GraphState) -> GraphState:
    q = state.get("rewritten_query") or state.get("user_query", "")
    state["draft_answer"] = f"Answer based on retrieved context for: {q}"
    state["citations"] = [{"filename": "document.txt", "page": 1, "section": "Summary", "snippet": "Retrieved excerpt"}]
    return state


def validate_answer(state: GraphState) -> GraphState:
    state["validation_results"] = {"citation_valid": True, "answer_has_support": True}
    return state


def return_response(state: GraphState) -> GraphState:
    return state


def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("understand_query", understand_query)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("check_retrieval_relevance", check_retrieval_relevance)
    workflow.add_node("build_context", build_context)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("validate_answer", validate_answer)
    workflow.add_node("return_response", return_response)

    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "rewrite_query")
    workflow.add_edge("rewrite_query", "retrieve_documents")
    workflow.add_edge("retrieve_documents", "check_retrieval_relevance")
    workflow.add_conditional_edges(
        "check_retrieval_relevance",
        lambda state: "build_context" if state.get("validation_results", {}).get("has_relevant_context") else "return_response",
        {"build_context": "build_context", "return_response": "return_response"},
    )
    workflow.add_edge("build_context", "generate_answer")
    workflow.add_edge("generate_answer", "validate_answer")
    workflow.add_edge("validate_answer", "return_response")
    workflow.add_edge("return_response", END)
    return workflow.compile()


compiled_workflow = build_graph()
