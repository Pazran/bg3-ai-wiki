"""
BG3 Wiki Metadata Scraper
=========================
This script performs a comprehensive metadata-driven scrape of the Baldur's Gate 3 wiki,
extracting structured data from all pages and organizing them into category-based folders.

Author: Pazran
Purpose: Create a searchable, programmatic database of BG3 game content
Dependencies: requests, mwparserfromhell, json, os, time
"""

import requests
import mwparserfromhell
import json
import os
import time


# API Configuration
url = "https://bg3.wiki/w/api.php"
script_dir = os.path.dirname(os.path.realpath(__file__))


# Wiki API Query Parameters
params = {
    # Action and format settings
    "action": "query",           # Request query action
    "format": "json",            # Return JSON response
    "generator": "allpages",     # Generate list of all pages
    
    # Pagination control (API returns 50 pages per batch by default)
    "gaplimit": "50",            # Number of pages to fetch per request
    
    # Namespace and redirect filtering
    "gapfilternamespace": "0",   # Filter for main namespace only (articles, not talk pages)
    "gapfilterredir": "nonredirects",  # Exclude redirect pages from results
    
    # Content retrieval options
    "prop": "revisions|categories",  # Request revision data and category information
    "rvprop": "content",          # Include full content in revisions
    "rvslots": "main",            # Extract content from main slot (primary wikitext)
    
    # Category metadata optimization
    "cllimit": "max",             # Fetch all categories for each page
    
    # API versioning
    "formatversion": "2"          # Use newer API format with better error handling
}


# Tracking variables for progress monitoring and statistics
total_downloaded = 0            # Counter for successfully saved files
skipped_count = 0               # Counter for duplicate/skipped files

# Category bucketing system - maps scraped content to organized folders
category_counts = {
    "Gameplay/Equipment": 0,     # Weapons, armor, items, consumables
    "Gameplay/Quests": 0,        # Main quests, side quests, daily quests
    "Gameplay/Locations": 0,     # Towns, dungeons, acts, areas
    "Gameplay/Creatures": 0,     # Enemies, monsters, NPCs (non-combat)
    "Characters": 0,             # Character profiles, story characters
    
    "Character_Creation/Classes": 0,      # Fighter, Wizard, Rogue, etc.
    "Character_Creation/Races": 0,        # Human, Elf, Dwarf, Tiefling, etc.
    "Character_Creation/Spells": 0,       # Cantrips, spells by level
    "Character_Creation/Feats": 0,        # Action feats, skill feats
    "Character_Creation/Backgrounds": 0,  # Noble, Soldier, Outlander, etc.
    "Character_Creation/Abilities_and_Skills": 0,  # Passive abilities, skill descriptions
    
    "Gameplay/Books_and_Lore": 0,   # Journals, notes, lore entries
    "Mechanics": 0,                 # Game mechanics, conditions, actions
    "Uncategorized": 0              # Fallback for pages that don't match any category
}


print("Starting definitive metadata-driven master scrape...\n")


# Main scraping loop - continues until all wiki pages are processed
while True:
    response = requests.get(url, params=params).json()
    
    # Check if API returned valid data structure or if we've exhausted all pages
    if "query" not in response or "pages" not in response["query"]:
        print("\nNo more pages found or API error.")
        break
        
    pages_batch = response["query"]["pages"]
    
    # Process each page in the current batch
    for page in pages_batch:
        title = page["title"]
        
        # Windows Filename Sanitization
        # Replace spaces with underscores and remove/replace illegal filesystem characters
        safe_title = title.replace(" ", "_")
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']  # Note: '?' was duplicated in original
        for char in illegal_chars:
            safe_title = safe_title.replace(char, "-")
        filename = f"{safe_title}.json"

        # Skip pages without content (e.g., disambiguation pages with no revisions)
        if "revisions" not in page or not page["revisions"]:
            continue
            
        raw_content = page["revisions"][0]["slots"]["main"]["content"]
        wikicode = mwparserfromhell.parse(raw_content)
        
        # Extract API-provided categories metadata (more reliable than parsing wikitext)
        native_categories = []
        if "categories" in page:
            for cat in page["categories"]:
                native_categories.append(cat["title"].lower())  # Normalize to lowercase
        
        # Parse templates from wikitext and extract their parameters
        # Only processes templates with at least 3 parameters (filters out simple templates)
        templates_dict = {}
        for template in wikicode.filter_templates():
            if len(template.params) < 3: 
                continue
            t_name = str(template.name).strip()
            template_data = {str(p.name).strip(): str(p.value).strip() for p in template.params}
            templates_dict[t_name] = template_data
        
        # METADATA AUTOMATION ROUTING - Categorization Logic
        # Determines which folder to save the page based on its wiki categories
        folder_name = "Uncategorized"  # Default fallback category
        cat_str = " ".join(native_categories)  # Join categories for substring matching
        
        # Equipment detection (weapons, armor, items, clothing)
        if any(k in cat_str for k in ["equipment", "weapons", "armor", "items", "clothing"]):
            folder_name = "Gameplay/Equipment"
        # Quest content
        elif "quests" in cat_str:
            folder_name = "Gameplay/Quests"
        # Location-based pages (towns, dungeons, acts)
        elif "locations" in cat_str or "acts" in cat_str:
            folder_name = "Gameplay/Locations"
        # Creature and enemy pages
        elif any(k in cat_str for k in ["creatures", "monsters", "bosses"]):
            folder_name = "Gameplay/Creatures"
        # Character creation - Classes
        elif "classes" in cat_str or "subclasses" in cat_str:
            folder_name = "Character_Creation/Classes"    
        # Character creation - Races
        elif "races" in cat_str or "subraces" in cat_str:
            folder_name = "Character_Creation/Races"
        # Character creation - Spells
        elif "spells" in cat_str:
            folder_name = "Character_Creation/Spells"
        # Character creation - Feats
        elif "feats" in cat_str:
            folder_name = "Character_Creation/Feats"
        # Character creation - Backgrounds
        elif "backgrounds" in cat_str:
            folder_name = "Character_Creation/Backgrounds"
        # Character creation - Abilities and Skills
        elif any(k in cat_str for k in ["passives", "abilities", "skills"]):
            folder_name = "Character_Creation/Abilities_and_Skills"
        # Books, journals, lore entries
        elif any(k in cat_str for k in ["books", "journals", "notes", "letters", "lore"]):
            folder_name = "Gameplay/Books_and_Lore"
        # Game mechanics and systems
        elif any(k in cat_str for k in ["actions", "conditions", "status", "alchemy", "game mechanics"]):
            folder_name = "Mechanics"
        # NPC and companion pages (catch-all for character-related content)
        elif any(k in cat_str for k in ["characters", "npcs", "companions"]):
            folder_name = "Characters"
        
        target_dir = os.path.join(script_dir, folder_name)
        file_path = os.path.join(target_dir, filename)
        
        # Skip if file already exists (avoid duplicates on re-runs)
        if os.path.exists(file_path):
            skipped_count += 1
            category_counts[folder_name] += 1
            continue

        # Create directory structure if it doesn't exist
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        # Structure scraped data for consistent JSON output
        scraped_data = {
            "page_title": title,              # Original wiki page title
            "categories": native_categories,  # Wiki categories (lowercase)
            "templates": templates_dict,      # Extracted template parameters
            "readable_text": raw_content.splitlines(),  # Line-by-line text representation
            "raw_content": raw_content        # Full wikitext for reference/regeneration
        }

        # Write to JSON file with proper encoding and formatting
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
            
        total_downloaded += 1
        category_counts[folder_name] += 1
        
        # Progress indicator showing cumulative count and target folder
        print(f"[{skipped_count + total_downloaded:04d}] Saved {folder_name}/{filename}")
        
    # Handle pagination - API returns 'continue' token for next batch
    if "continue" in response:
        params.update(response["continue"])  # Update parameters with continuation data
        time.sleep(0.4)                      # Rate limiting to avoid API throttling
    else:
        print("\nFinished! System fully populated.")
        break
