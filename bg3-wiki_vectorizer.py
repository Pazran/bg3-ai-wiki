import os
import re
import json
import chromadb
# Import the explicit ONNX class rather than the generic default function wrapper
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

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

# --- FORCE EXPLICIT CUDA ORDERING BYPASSING TENSORRT NATIVELY ---
embedding_fn = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

# Connect or build collection with our explicit hardware instructions
collection = chroma_client.get_or_create_collection(name="bg3_wiki_data", embedding_function=embedding_fn)

print("Starting dynamic master indexing with locked CUDA providers...")

doc_id_counter = 0

# Folders we want to strictly ignore so the AI doesn't parse code/metadata
ignored_dirs = {".venv", "bg3_vector_db", "__pycache__", ".git"}

# --- NEW DYNAMIC SYSTEM USING OS.WALK ---
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
            
            # --- NEW CLEANING STEP RUNS HERE ---
            cleaned_line = clean_wiki_syntax(line_strip)
            if cleaned_line.strip():
                clean_lines.append(cleaned_line)
            
        clean_text = "\n".join(clean_lines)
        if not clean_text.strip():
            continue  
            
        # --- STRUCTURE FOR CROSS-REFERENCING ---
        structured_document = f"DOCUMENT TITLE: {page_title}\n"
        structured_document += f"GAME CATEGORIES: {', '.join(categories)}\n"
        structured_document += f"DATA SOURCE FOLDER: {relative_folder}\n" # Tracks dynamic folder structure
        structured_document += f"CONTENT:\n{clean_text}"
        
        metadata = {
            "title": page_title,
            "folder": relative_folder,
            "primary_category": categories[0] if categories else "unknown"
        }
        
        collection.add(
            documents=[structured_document],
            metadatas=[metadata],
            ids=[f"doc_{doc_id_counter}"]
        )
        doc_id_counter += 1

print(f"\nSuccess! Dynamically crawled all folders and indexed {doc_id_counter} game files.")