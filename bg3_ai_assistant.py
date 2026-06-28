import os
import requests
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# 1. Connect to the database we just built using the exact same GPU configuration
script_dir = os.path.dirname(os.path.realpath(__file__))
chroma_client = chromadb.PersistentClient(path=os.path.join(script_dir, "bg3_vector_db"))

# Keep it on the fast track using your working CUDA layout
embedding_fn = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
collection = chroma_client.get_collection(name="bg3_wiki_data", embedding_function=embedding_fn)

# 2. Fire your question here
user_query = "I want to build a support-focused Cleric who buffs the party whenever they receive healing. Based on my wiki data, which specific items, rings, or gloves provide a buff to allies when I heal them, and where can I find them in the game? Are there any specific items that grant the 'Bless' condition upon healing?"

#"Craft an assassing build using poison as primary theme damage. Please give details guide like gears, class, subclass, talent, feat and also level by level stat to allocate. Suggest also if multiclass is better."

print(f"Searching local knowledge base for: '{user_query}'...")

# Pull the top 4 most relevant files from across your entire folder tree
results = collection.query(query_texts=[user_query], n_results=12) # Default to 4
retrieved_context = "\n\n---\n\n".join(results['documents'][0])

# 3. Hand the raw context off to your active LM Studio local server
lm_studio_url = "http://localhost:1234/v1/chat/completions"

payload = {
    "model": "local-model", # LM Studio automatically defaults to whatever model you have loaded
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
            "content": f"Wiki Data Context:\n{retrieved_context}\n\nQuestion: {user_query}"
        }
    ],
    "temperature": 0.3
}

try:
    print("Streaming data context to LM Studio...")
    response = requests.post(lm_studio_url, json=payload).json()
    
    print("\n" + "="*20 + " AI RESPONSE " + "="*20)
    print(response['choices'][0]['message']['content'])
    print("="*53)
    
except Exception as e:
    print(f"\nCould not connect to LM Studio. Make sure you clicked 'Start Server' inside LM Studio! Error: {e}")