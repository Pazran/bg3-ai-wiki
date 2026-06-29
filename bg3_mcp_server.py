from mcp.server.fastmcp import FastMCP
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# Initialize your DB exactly as you did before
chroma_client = chromadb.PersistentClient(path="D:/Scripts/bg3-wiki/bg3_vector_db")
embedding_fn = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider"])
collection = chroma_client.get_collection(name="bg3_wiki_data", embedding_function=embedding_fn)

# Create the MCP Server
mcp = FastMCP("BG3-Knowledge-Base")

# Define the tool
@mcp.tool()
def search_bg3_wiki(query: str) -> str:
    """Useful for answering questions about BG3 items, builds, or mechanics."""
    results = collection.query(query_texts=[query], n_results=3)
    return "\n\n---\n\n".join(results['documents'][0])

if __name__ == "__main__":
    mcp.run()