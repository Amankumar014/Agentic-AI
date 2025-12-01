"""
LangGraph-based RAG Chatbot for Lalla Care
Implements RAG retrieval with conditional edges for out-of-scope questions.
"""
from __future__ import annotations

import os
import sqlite3
import logging
from pathlib import Path
from typing import Annotated, Any, Dict, Optional, TypedDict, List, Literal
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from huggingface_hub import InferenceClient

from src.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
RAG_DOCUMENTS_DIR = PROJECT_ROOT / "rag_document"
LALLA_CARE_PDF = RAG_DOCUMENTS_DIR / "LALLA CARE.pdf"
CHATBOT_DB = PROJECT_ROOT / "chatbot_langgraph.db"

# ==============================================================================
# GLOBAL INSTANCES
# ==============================================================================

_llm: Optional[InferenceClient] = None
_embeddings: Optional[HuggingFaceEmbeddings] = None
_retriever: Optional[Any] = None
_checkpointer: Optional[SqliteSaver] = None
_chatbot_graph: Optional[Any] = None


def get_llm() -> InferenceClient:
    """Get or initialize HuggingFace LLM for chatbot."""
    global _llm
    if _llm is None:
        logger.info("🔧 Initializing HuggingFace LLM for chatbot...")
        settings = get_settings()
        
        # Use HuggingFace token
        hf_token = settings.HF_TOKEN
        
        if not hf_token:
            raise ValueError(
                "HuggingFace token not configured in .env file. "
                "Please set HF_TOKEN"
            )
        
        _llm = InferenceClient(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            token=hf_token
        )
        logger.info("✅ HuggingFace LLM initialized for chatbot (model: meta-llama/Meta-Llama-3-8B-Instruct)")
    return _llm


def get_embeddings() -> HuggingFaceEmbeddings:
    """Get or initialize HuggingFace embeddings."""
    global _embeddings
    if _embeddings is None:
        logger.info("🔧 Loading HuggingFace embeddings model...")
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        logger.info("✅ HuggingFace embeddings model loaded")
    return _embeddings


def get_retriever() -> Any:
    """Get or build the FAISS retriever for Lalla Care document (cached)."""
    global _retriever
    
    # Return cached retriever if available
    if _retriever is not None:
        return _retriever
    
    logger.info("🔧 Initializing FAISS retriever...")
    
    # Check if index already exists
    index_path = RAG_DOCUMENTS_DIR / "faiss_index_langgraph"
    
    if index_path.exists() and (index_path / "index.faiss").exists():
        logger.info("📂 Loading existing FAISS index...")
        try:
            vector_store = FAISS.load_local(
                str(index_path),
                get_embeddings(),
                allow_dangerous_deserialization=True
            )
            _retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4}
            )
            logger.info("✅ FAISS retriever loaded from disk")
            return _retriever
        except Exception as e:
            logger.warning(f"⚠️  Failed to load existing index: {e}. Rebuilding...")
    
    # Build new index
    logger.info("🔨 Building new FAISS index from Lalla Care PDF...")
    
    if not LALLA_CARE_PDF.exists():
        raise FileNotFoundError(f"PDF not found: {LALLA_CARE_PDF}")
    
    # Load PDF
    loader = PyPDFLoader(str(LALLA_CARE_PDF))
    docs = loader.load()
    
    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    
    logger.info(f"📄 Loaded {len(docs)} pages, created {len(chunks)} chunks")
    
    # Create vector store
    vector_store = FAISS.from_documents(chunks, get_embeddings())
    
    # Save for future use
    index_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_path))
    logger.info(f"💾 Saved FAISS index to {index_path}")
    
    # Create retriever and cache it
    _retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    
    logger.info("✅ FAISS retriever built and cached")
    return _retriever


def get_checkpointer() -> SqliteSaver:
    """Get or initialize SQLite checkpointer for conversation history."""
    global _checkpointer
    if _checkpointer is None:
        logger.info(f"🔧 Initializing SQLite checkpointer at {CHATBOT_DB}")
        conn = sqlite3.connect(str(CHATBOT_DB), check_same_thread=False)
        _checkpointer = SqliteSaver(conn=conn)
        logger.info(f"✅ SQLite checkpointer initialized")
    return _checkpointer


# ==============================================================================
# STATE DEFINITION
# ==============================================================================

class ChatState(TypedDict):
    """State for the chatbot conversation."""
    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    context: Optional[str]
    routing_decision: Optional[str]  # "rag" or "general"


# ==============================================================================
# ROUTING LOGIC
# ==============================================================================

def route_question(state: ChatState) -> Literal["retrieve_docs", "general_llm"]:
    """
    Conditional edge: Determine if the question is about Lalla Care (use RAG)
    or general/out-of-scope (use general LLM).
    
    Args:
        state: Current conversation state
        
    Returns:
        "retrieve_docs" for RAG retrieval or "general_llm" for direct LLM
    """
    question = state["question"].lower()
    
    # Keywords that indicate Lalla Care related questions
    lalla_care_keywords = [
        "lalla", "baby monitor", "camera", "sensor", "alert",
        "setup", "install", "connect", "app", "mobile",
        "feature", "detection", "crying", "movement", "temperature",
        "notification", "how to", "what is", "does it", "can it",
        "guide", "manual", "instruction", "help"
    ]
    
    # Check if any keyword is in the question
    for keyword in lalla_care_keywords:
        if keyword in question:
            logger.info(f"🔀 Routing to RAG (keyword: '{keyword}')")
            return "retrieve_docs"
    
    # Default to general LLM for out-of-scope questions
    logger.info("🔀 Routing to general LLM (out of scope)")
    return "general_llm"


# ==============================================================================
# NODES
# ==============================================================================

def classify_question_node(state: ChatState) -> Dict[str, Any]:
    """
    Entry node: Extract the user question and prepare for routing.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with question extracted
    """
    messages = state["messages"]
    
    # Get the last user message
    last_message = messages[-1] if messages else None
    
    if isinstance(last_message, HumanMessage):
        question = last_message.content
    else:
        question = str(last_message.content) if last_message else ""
    
    logger.info(f"📝 Question extracted: {question[:100]}...")
    
    return {
        "question": question,
        "context": None,
        "routing_decision": None
    }


def retrieve_docs_node(state: ChatState) -> Dict[str, Any]:
    """
    RAG node: Retrieve relevant documents from Lalla Care PDF.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with retrieved context
    """
    question = state["question"]
    
    logger.info(f"🔍 Retrieving documents for: {question[:100]}...")
    
    try:
        retriever = get_retriever()
        docs = retriever.invoke(question)
        
        # Format context
        context_parts = []
        for i, doc in enumerate(docs, 1):
            page = doc.metadata.get("page", "?")
            context_parts.append(f"[Page {page}] {doc.page_content}")
        
        context = "\n\n".join(context_parts)
        
        logger.info(f"✅ Retrieved {len(docs)} documents")
        
        return {
            "context": context,
            "routing_decision": "rag"
        }
    
    except Exception as e:
        logger.error(f"❌ Error retrieving documents: {e}")
        return {
            "context": None,
            "routing_decision": "rag"
        }


def rag_answer_node(state: ChatState) -> Dict[str, Any]:
    """
    RAG answer node: Generate answer using retrieved context.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with AI answer added to messages
    """
    question = state["question"]
    context = state.get("context", "")
    
    logger.info("🤖 Generating RAG-based answer...")
    
    system_prompt = """You are Lalla Care's helpful assistant. Your role is to answer questions about the Lalla Care baby monitoring system.

IMPORTANT RULES:
1. Answer ONLY using the provided context from the user guide
2. Do NOT hallucinate or make up information
3. Explain everything in simple, friendly, non-technical language
4. If the answer is not in the context, say: "I don't have that information in the guide."
5. Be helpful, concise, and parent-friendly
6. Focus on practical guidance and clear instructions

Context from the guide:
{context}

User Question: {question}"""
    
    prompt = system_prompt.format(context=context or "No context available", question=question)
    
    try:
        llm = get_llm()
        
        # HuggingFace InferenceClient expects a single message string
        full_prompt = f"You are a helpful assistant for Lalla Care baby monitoring system.\n\n{prompt}"
        
        response = llm.chat_completion(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        logger.info(f"✅ RAG answer generated ({len(answer)} chars)")
        
        return {
            "messages": [AIMessage(content=answer)]
        }
    
    except Exception as e:
        logger.error(f"❌ Error generating RAG answer: {e}")
        error_message = "I'm sorry, I'm having trouble accessing the information right now. Please try again later."
        return {
            "messages": [AIMessage(content=error_message)]
        }


def general_llm_node(state: ChatState) -> Dict[str, Any]:
    """
    General LLM node: Handle out-of-scope questions with general knowledge.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with AI answer added to messages
    """
    question = state["question"]
    
    logger.info("🤖 Generating general LLM answer...")
    
    system_prompt = """You are a helpful AI assistant. The user has asked a question that is not directly related to the Lalla Care baby monitoring system documentation.

Please provide a helpful, friendly response. If the question is completely unrelated to baby monitoring or parenting, politely mention that you're primarily designed to help with Lalla Care system questions, but you'll do your best to help.

User Question: {question}"""
    
    prompt = system_prompt.format(question=question)
    
    try:
        llm = get_llm()
        
        # HuggingFace InferenceClient expects a single message string
        full_prompt = f"You are a helpful AI assistant.\n\n{prompt}"
        
        response = llm.chat_completion(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        logger.info(f"✅ General answer generated ({len(answer)} chars)")
        
        return {
            "messages": [AIMessage(content=answer)],
            "routing_decision": "general"
        }
    
    except Exception as e:
        logger.error(f"❌ Error generating general answer: {e}")
        error_message = "I'm sorry, I'm having trouble generating a response right now. Please try again later."
        return {
            "messages": [AIMessage(content=error_message)],
            "routing_decision": "general"
        }


# ==============================================================================
# GRAPH CONSTRUCTION
# ==============================================================================

def build_chatbot_graph():
    """Build the LangGraph workflow for the chatbot."""
    
    logger.info("🔨 Building chatbot graph...")
    
    # Create graph
    graph = StateGraph(ChatState)
    
    # Add nodes
    graph.add_node("classify_question", classify_question_node)
    graph.add_node("retrieve_docs", retrieve_docs_node)
    graph.add_node("rag_answer", rag_answer_node)
    graph.add_node("general_llm", general_llm_node)
    
    # Add edges
    graph.add_edge(START, "classify_question")
    
    # Conditional edge from classify to either retrieve_docs or general_llm
    graph.add_conditional_edges(
        "classify_question",
        route_question,
        {
            "retrieve_docs": "retrieve_docs",
            "general_llm": "general_llm"
        }
    )
    
    # RAG path: retrieve_docs -> rag_answer -> END
    graph.add_edge("retrieve_docs", "rag_answer")
    graph.add_edge("rag_answer", END)
    
    # General path: general_llm -> END
    graph.add_edge("general_llm", END)
    
    # Compile with checkpointer
    checkpointer = get_checkpointer()
    chatbot = graph.compile(checkpointer=checkpointer)
    
    logger.info("✅ Chatbot graph built and compiled")
    
    return chatbot


def get_chatbot():
    """Get or build the chatbot graph (cached)."""
    global _chatbot_graph
    if _chatbot_graph is None:
        logger.info("🔧 Initializing chatbot graph for the first time...")
        _chatbot_graph = build_chatbot_graph()
    return _chatbot_graph


def initialize_chatbot_at_startup():
    """
    Eagerly initialize all chatbot components at startup.
    
    This function should be called once during application startup to:
    - Load HuggingFace embeddings model
    - Initialize HuggingFace LLM
    - Build/load FAISS retriever
    - Initialize SQLite checkpointer
    - Build and compile LangGraph workflow
    
    After this initialization, all subsequent API calls will use the cached components.
    """
    logger.info("\n" + "=" * 70)
    logger.info("🚀 INITIALIZING LANGGRAPH RAG CHATBOT AT STARTUP")
    logger.info("=" * 70)
    
    try:
        # 1. Initialize embeddings (heavy - loads transformer model)
        logger.info("\n[1/5] 📥 Loading HuggingFace embeddings model...")
        embeddings = get_embeddings()
        logger.info("✅ Embeddings model loaded and cached")
        
        # 2. Initialize LLM
        logger.info("\n[2/5] 🧠 Initializing HuggingFace LLM...")
        llm = get_llm()
        logger.info("✅ HuggingFace LLM initialized and cached")
        
        # 3. Build/load retriever (heavy - builds FAISS index if needed)
        logger.info("\n[3/5] 🔍 Building/loading FAISS retriever...")
        retriever = get_retriever()
        logger.info("✅ FAISS retriever ready and cached")
        
        # 4. Initialize checkpointer
        logger.info("\n[4/5] 💾 Initializing SQLite checkpointer...")
        checkpointer = get_checkpointer()
        logger.info("✅ SQLite checkpointer initialized and cached")
        
        # 5. Build chatbot graph
        logger.info("\n[5/5] 🔨 Building and compiling LangGraph workflow...")
        chatbot = get_chatbot()
        logger.info("✅ LangGraph workflow compiled and cached")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ CHATBOT INITIALIZATION COMPLETE - ALL COMPONENTS CACHED")
        logger.info("=" * 70)
        logger.info("Next requests will be fast (no initialization needed)\n")
        
        return {
            "status": "success",
            "initialized": {
                "embeddings": True,
                "llm": True,
                "retriever": True,
                "checkpointer": True,
                "chatbot_graph": True
            }
        }
    
    except Exception as e:
        logger.error(f"\n❌ FAILED TO INITIALIZE CHATBOT: {e}")
        import traceback
        traceback.print_exc()
        raise


# ==============================================================================
# PUBLIC API
# ==============================================================================

async def ask_chatbot_langgraph(
    question: str,
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ask the LangGraph RAG chatbot a question.
    
    Args:
        question: User's question
        thread_id: Optional thread ID for conversation history
        
    Returns:
        Dictionary with answer and metadata
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"💬 LANGGRAPH CHATBOT QUERY: {question}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Use default thread if not provided
        if thread_id is None:
            thread_id = "default"
        
        # Get chatbot
        chatbot = get_chatbot()
        
        # Prepare config
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Prepare input
        input_state = {
            "messages": [HumanMessage(content=question)]
        }
        
        # Run the graph
        result = chatbot.invoke(input_state, config=config)
        
        # Extract answer
        messages = result.get("messages", [])
        answer = ""
        
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                answer = msg.content
                break
        
        routing = result.get("routing_decision", "unknown")
        context = result.get("context")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        response = {
            "answer": answer,
            "question": question,
            "routing": routing,
            "thread_id": thread_id,
            "has_context": context is not None,
            "processing_time_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Answer generated in {elapsed:.2f}s (routing: {routing})")
        logger.info("=" * 60 + "\n")
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Error in chatbot pipeline: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "answer": "I'm sorry, I encountered an error while processing your question. Please try again.",
            "question": question,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def rebuild_index_langgraph() -> Dict[str, Any]:
    """
    Rebuild the FAISS index for the LangGraph chatbot.
    
    Returns:
        Dictionary with rebuild statistics
    """
    global _retriever
    
    logger.info("\n" + "=" * 60)
    logger.info("🔄 REBUILDING LANGGRAPH RAG INDEX")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Clear cached retriever
        _retriever = None
        
        # Delete existing index
        index_path = RAG_DOCUMENTS_DIR / "faiss_index_langgraph"
        if index_path.exists():
            import shutil
            shutil.rmtree(index_path)
            logger.info("🗑️  Removed existing index")
        
        # Rebuild by calling get_retriever (will build new index)
        retriever = get_retriever()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        stats = {
            "status": "success",
            "build_time_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("=" * 60)
        logger.info(f"✅ INDEX REBUILD COMPLETE in {elapsed:.2f}s")
        logger.info("=" * 60 + "\n")
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Failed to rebuild index: {e}")
        raise


def get_all_threads() -> List[str]:
    """
    Retrieve all conversation thread IDs.
    
    Returns:
        List of thread IDs
    """
    try:
        checkpointer = get_checkpointer()
        all_threads = set()
        
        for checkpoint in checkpointer.list(None):
            thread_id = checkpoint.config["configurable"]["thread_id"]
            all_threads.add(thread_id)
        
        return list(all_threads)
    
    except Exception as e:
        logger.error(f"❌ Error retrieving threads: {e}")
        return []


def check_status_langgraph() -> Dict[str, Any]:
    """
    Check the status of the LangGraph RAG system.
    
    Returns:
        Status dictionary with initialization state
    """
    index_path = RAG_DOCUMENTS_DIR / "faiss_index_langgraph"
    index_file = index_path / "index.faiss"
    
    pdf_exists = LALLA_CARE_PDF.exists()
    index_exists = index_file.exists()
    
    # Check if components are initialized (not just files exist)
    chatbot_initialized = _chatbot_graph is not None
    llm_initialized = _llm is not None
    embeddings_initialized = _embeddings is not None
    retriever_initialized = _retriever is not None
    
    # Count threads without initializing checkpointer if not needed
    threads_count = 0
    if _checkpointer is not None:
        try:
            threads_count = len(get_all_threads())
        except Exception:
            threads_count = 0
    
    # System is fully ready if files exist AND components are initialized
    files_ready = pdf_exists and index_exists
    components_ready = chatbot_initialized and llm_initialized
    fully_ready = files_ready and components_ready
    
    return {
        "status": "ready" if fully_ready else ("initializing" if files_ready else "not_ready"),
        "pdf_exists": pdf_exists,
        "pdf_path": str(LALLA_CARE_PDF),
        "index_exists": index_exists,
        "index_path": str(index_file),
        "database_path": str(CHATBOT_DB),
        "threads_count": threads_count,
        "initialized": {
            "chatbot_graph": chatbot_initialized,
            "llm": llm_initialized,
            "embeddings": embeddings_initialized,
            "retriever": retriever_initialized
        }
    }


if __name__ == "__main__":
    # Test the system
    import asyncio
    
    print("Testing LangGraph RAG Chatbot...")
    print(check_status_langgraph())
    
    # Test questions
    test_questions = [
        "What is Lalla Care?",
        "How do I set up the camera?",
        "What's the weather like today?",  # Out of scope
        "Tell me about movement detection features"
    ]
    
    for q in test_questions:
        print(f"\n\nQ: {q}")
        result = asyncio.run(ask_chatbot_langgraph(q))
        print(f"A: {result['answer']}")
        print(f"Routing: {result.get('routing', 'unknown')}")

