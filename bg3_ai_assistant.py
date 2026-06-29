"""
BG3 RAG Testing Harness (Proof-of-Concept)
==========================================
This script tests the full Retrieval-Augmented Generation (RAG) pipeline locally.
It queries the vector database, retrieves context, and sends it to an external LLM 
(LM Studio) for a final answer.

Author: Pazran
Purpose: Validate that scraping > indexing > querying > generation works end-to-end.
Dependencies: requests, chromadb, onnxruntime
"""

import os
import requests
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2


# 1. Connect to the database we just built using the exact same GPU configuration
script_dir = os.path.dirname(os.path.realpath(__file__))
chroma_client = chromadb.PersistentClient(path=os.path.join(script_dir, "bg3_vector_db"))

# Keep it on the fast track using your working CUDA layout
# Note: Providing a fallback ["CPUExecutionProvider"] ensures robustness if GPU is busy/unavailable during testing
embedding_fn = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
collection = chroma_client.get_collection(name="bg3_wiki_data", embedding_function=embedding_fn)


# 2. Fire your question here
# This is the "User Query" input for testing purposes. 
# In a production app, this would come from an API request or chat interface.
user_query = """I want to build a support-focused Cleric who buffs the party whenever they receive healing. Based on my wiki data, which specific items, rings, or gloves provide a buff to allies when I heal them, and where can I find them in the game? Are there any specific items that grant the 'Bless' condition upon healing?"""

# "Craft an assassing build using poison as primary theme damage. Please give details guide like gears, class, subclass, talent, feat and also level by level stat to allocate. Suggest also if multiclass is better."
# (Commented out example query for variety)

print(f"Searching local knowledge base for: '{user_query}'...")

# Pull the top 4 most relevant files from across your entire folder tree
# Note: n_results=12 retrieves more context than needed, allowing the LLM to filter. 
# This is a common testing strategy to ensure no critical info is missed.
results = collection.query(query_texts=[user_query], n_results=12) 

retrieved_context = "\n\n---\n\n".join(results['documents'][0])

# 3. Hand the raw context off to your active LM Studio local server
lm_studio_url = "http://localhost:1234/v1/chat/completions"

payload = {
    "model": "local-model", # LM Studio automatically defaults to whatever model you have loaded (e.g., Llama 3, Mistral)
    "messages": [
        {
            "role": "system", 
            "content": (
                "You are a Baldur's Gate 3 strategy expert analyzer. Use the provided raw "
                "wiki data blocks to answer the user's question. Rely strictly on the true "
                "facts provided in the text context. Do not hallucinate external details."
            )
        },
        {
            "role": "user", 
            # Injects the retrieved wiki chunks directly into the prompt (RAG pattern)
            "content": f"Wiki Data Context:\n{retrieved_context}\n\nQuestion: {user_query}"
        }
    ],
    "temperature": 0.3 # Low temperature for more deterministic, factual answers based on context
}

try:
    print("Streaming data context to LM Studio...")
    response = requests.post(lm_studio_url, json=payload).json()
    
    print("\n" + "="*20 + " AI RESPONSE " + "="*20)
    # Extract and display the generated answer
    print(response['choices'][0]['message']['content'])
    print("="*53)
    
except Exception as e:
    # Graceful failure handling for local testing environments
    print(f"\nCould not connect to LM Studio. Make sure you clicked 'Start Server' inside LM Studio! Error: {e}")
