"""
BG3 Knowledge Base MCP Server
=============================
This script exposes a semantic search interface via Model Context Protocol (MCP).
It allows external applications to query the BG3 Wiki vector database for items, builds, or mechanics.

Author: Pazran
Dependencies: mcp, chromadb, onnxruntime
"""

from mcp.server.fastmcp import FastMCP
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2


# Initialize your DB exactly as you did before
# IMPORTANT: This path must match the 'path' argument in your indexing script (bg3_vector_db)
# to ensure this server queries the same data that was just scraped and indexed.
chroma_client = chromadb.PersistentClient(path="D:/Scripts/bg3-wiki/bg3_vector_db")

# Force CUDA provider for faster inference during query time
embedding_fn = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider"])

# Retrieve the existing collection created by the indexing script.
# If it doesn't exist, this would raise an error (unlike get_or_create_collection).
collection = chroma_client.get_collection(name="bg3_wiki_data", embedding_function=embedding_fn)


# Create the MCP Server instance with a descriptive name for clients
mcp = FastMCP("BG3-Knowledge-Base")


# Define the tool exposed to the MCP client
@mcp.tool()
def search_bg3_wiki(query: str) -> str:
    """
    Use this tool to answer questions about BG3 items, builds, or mechanics.
    
    Args:
        query (str): The natural language question or search term (e.g., "best rogue build", "how to cure blindness").
        
    Returns:
        str: A formatted string containing the top 3 most relevant document chunks from the vector database.
    """
    # Perform semantic similarity search against the indexed BG3 wiki data
    results = collection.query(query_texts=[query], n_results=3)
    
    # Join the retrieved documents with a separator for readability
    # Assumes 'documents' is a list of lists; takes the first batch (index 0)
    return "\n\n---\n\n".join(results['documents'][0])


if __name__ == "__main__":
    mcp.run()
