import os
import re
import json
import chromadb
# Import the explicit ONNX class rather than the generic default function wrapper
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
import onnxruntime as ort

def clean_wiki_syntax(text):
    """Transforms raw wiki templates into clean, readable text."""
    # 1. Convert {{RarityItem|Whispering Promise}} -> "Whispering Promise"
    text = re.sub(r'\{\{RarityItem\|([^}]+)\}\}', r'\1', text)
    
    # 2. Convert {{HeavyArmour}} -> "Heavy Armour"
    text = re.sub(r'\{\{HeavyArmour\}\}', 'Heavy Armour', text)
    text = re.sub(r'\{\{MediumArmour\}\}', 'Medium Armour', text)
    text = re.sub(r'\{\{LightArmour\}\}', 'Light Armour', text)
    
    # 3. Strip out any remaining generic double curly brackets text {{...}}
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    
    # 4. Clean up any leftover internal wiki links [[Item Name|Display Name]] -> "Display Name"
    text = re.sub(r'\[\[[^\]|]+\|([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    
    return text

# 1. Connect to local storage database folder
script_dir = os.path.dirname(os.path.realpath(__file__))
chroma_client = chromadb.PersistentClient(path=os.path.join(script_dir, "bg3_vector_db"))

# --- ROBUST PROVIDER SELECTION ---
def get_embedding_function():
    # Automatically detect if CUDA is available, otherwise fall back to CPU
    available_providers = ort.get_available_providers()
    if "CUDAExecutionProvider" in available_providers:
        provider = "CUDAExecutionProvider"
        print("Using CUDAExecutionProvider for embedding extraction...", flush=True)
    else:
        provider = "CPUExecutionProvider"
        print("Using CPUExecutionProvider for embedding extraction...", flush=True)
    
    return ONNXMiniLM_L6_V2(preferred_providers=[provider])

embedding_fn = get_embedding_function()

# Connect or build collection with our dynamic hardware instructions
collection = chroma_client.get_or_create_collection(name="bg3_wiki_data", embedding_function=embedding_fn)

print("Starting dynamic master indexing with chunking strategy...")

chunk_id_counter = 0

# Folders we want to strictly ignore so the AI doesn't parse code/metadata
ignored_dirs = {".venv", "bg3_vector_db", "__pycache__", ".git"}

# --- DYNAMIC SYSTEM USING OS.WALK ---
for root, dirs, files in os.walk(script_dir):
    # Modifying dirs in-place lets os.walk skip ignored paths entirely
    dirs[:] = [d for d in dirs if d not in ignored_dirs]
    
    # Calculate the dynamic folder category path relative to your project root
    relative_folder = os.path.relpath(root, script_dir)
    if relative_folder == ".":
        continue # Skip files sitting loose in the root directory
        
    print(f"\nDynamically parsing folder: {relative_folder}...")
    
    for filename in files:
        if not filename.endswith(".json"):
            continue
            
        file_path = os.path.join(root, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                continue # Skip corrupt files
            
        page_title = data.get("page_title", "")
        readable_lines = data.get("readable_text", [])
        categories = data.get("categories", [])
        
        # --- JUNK FILTERING BLOCK ---
        clean_lines = []
        for line in readable_lines:
            line_strip = line.strip()
            if any(line_strip.startswith(x) for x in ["{{PageSeo", "{{TOC", "{{Companion tab", "[[File:", "| image"]):
                continue
            if line_strip == "}}" or line_strip == "":
                continue
            
            # --- CLEANING STEP RUNS HERE ---
            cleaned_line = clean_wiki_syntax(line_strip)
            if cleaned_line.strip():
                clean_lines.append(cleaned_line)
            
        # Reconstruct the cleaned text and split it cleanly into structural paragraphs
        clean_full_text = "\n".join(clean_lines)
        paragraphs = clean_full_text.split("\n\n")
        
        # --- PARAGRAPH CHUNKING LOOP ---
        paragraph_index = 0
        for para in paragraphs:
            clean_para = para.strip()
            
            # Skip empty paragraphs or trivial snippets (under 40 characters)
            if len(clean_para) < 40:
                continue
                
            # Inject structural cross-referencing metadata into every individual chunk
            structured_chunk = f"DOCUMENT TITLE: {page_title}\n"
            structured_document = f"DOCUMENT TITLE: {page_title}\n"
            structured_chunk += f"GAME CATEGORIES: {', '.join(categories)}\n"
            structured_chunk += f"DATA SOURCE FOLDER: {relative_folder}\n"
            structured_chunk += f"CONTENT CHUNK:\n{clean_para}"
            
            metadata = {
                "title": page_title,
                "folder": relative_folder,
                "primary_category": categories[0] if categories else "unknown",
                "chunk_index": paragraph_index
            }
            
            collection.add(
                documents=[structured_chunk],
                metadatas=[metadata],
                ids=[f"chunk_{chunk_id_counter}"]
            )
            chunk_id_counter += 1
            paragraph_index += 1

print(f"\nSuccess! Dynamically crawled all folders and indexed {chunk_id_counter} precise chunks.")