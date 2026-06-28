import requests
import mwparserfromhell
import json
import os
import time

url = "https://bg3.wiki/w/api.php"
script_dir = os.path.dirname(os.path.realpath(__file__))

params = {
    "action": "query",
    "format": "json",
    "generator": "allpages",
    "gaplimit": "50",
    "gapfilternamespace": "0",  
    "gapfilterredir": "nonredirects",
    "prop": "revisions|categories",  
    "rvprop": "content",
    "rvslots": "main",
    "cllimit": "max",  
    "formatversion": "2"
}

total_downloaded = 0
skipped_count = 0
category_counts = {
    "Gameplay/Equipment": 0,
    "Gameplay/Quests": 0,
    "Gameplay/Locations": 0,
    "Gameplay/Creatures": 0,
    "Characters": 0,
    "Character_Creation/Classes": 0,
    "Character_Creation/Races": 0,
    "Character_Creation/Spells": 0,
    "Character_Creation/Feats": 0,
    "Character_Creation/Backgrounds": 0,
    "Character_Creation/Abilities_and_Skills": 0,
    "Gameplay/Books_and_Lore": 0,
    "Mechanics": 0,
    "Uncategorized": 0
}

print("Starting definitive metadata-driven master scrape...\n")

while True:
    response = requests.get(url, params=params).json()
    
    if "query" not in response or "pages" not in response["query"]:
        print("\nNo more pages found or API error.")
        break
        
    pages_batch = response["query"]["pages"]
    
    for page in pages_batch:
        title = page["title"]
        
        # Windows Filename Sanitization (CRASH FIX: Explicitly removing '?')
        safe_title = title.replace(" ", "_")
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '?']
        for char in illegal_chars:
            safe_title = safe_title.replace(char, "-")
        filename = f"{safe_title}.json"

        if "revisions" not in page or not page["revisions"]:
            continue
            
        raw_content = page["revisions"][0]["slots"]["main"]["content"]
        wikicode = mwparserfromhell.parse(raw_content)
        
        # Extract API-provided categories metadata
        native_categories = []
        if "categories" in page:
            for cat in page["categories"]:
                native_categories.append(cat["title"].lower())

        # Extract templates
        templates_dict = {}
        for template in wikicode.filter_templates():
            if len(template.params) < 3: 
                continue
            t_name = str(template.name).strip()
            template_data = {str(p.name).strip(): str(p.value).strip() for p in template.params}
            templates_dict[t_name] = template_data

        # --- METADATA AUTOMATION ROUTING ---
        folder_name = "Uncategorized"
        cat_str = " ".join(native_categories)
        
        if any(k in cat_str for k in ["equipment", "weapons", "armor", "items", "clothing"]):
            folder_name = "Gameplay/Equipment"
        elif "quests" in cat_str:
            folder_name = "Gameplay/Quests"
        elif "locations" in cat_str or "acts" in cat_str:
            folder_name = "Gameplay/Locations"
        elif "classes" in cat_str or "subclasses" in cat_str:
            folder_name = "Character_Creation/Classes"  
        elif "races" in cat_str or "subraces" in cat_str:
            folder_name = "Character_Creation/Races"
        elif "spells" in cat_str:
            folder_name = "Character_Creation/Spells"
        elif "feats" in cat_str:
            folder_name = "Character_Creation/Feats"
        elif "backgrounds" in cat_str:
            folder_name = "Character_Creation/Backgrounds"
        elif any(k in cat_str for k in ["characters", "npcs", "companions", "creatures", "monsters", "bosses"]):
            folder_name = "Characters"
        elif any(k in cat_str for k in ["passives", "abilities", "skills"]):
            folder_name = "Character_Creation/Abilities_and_Skills"
        elif any(k in cat_str for k in ["books", "journals", "notes", "letters", "lore"]):
            folder_name = "Gameplay/Books_and_Lore"
        elif any(k in cat_str for k in ["actions", "conditions", "status", "alchemy", "game mechanics"]):
            folder_name = "Mechanics"

        target_dir = os.path.join(script_dir, folder_name)
        file_path = os.path.join(target_dir, filename)
        
        if os.path.exists(file_path):
            skipped_count += 1
            category_counts[folder_name] += 1
            continue

        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        scraped_data = {
            "page_title": title, 
            "categories": native_categories,  
            "templates": templates_dict,
            "readable_text": raw_content.splitlines(),
            "raw_content": raw_content  
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
            
        total_downloaded += 1
        category_counts[folder_name] += 1
        print(f"[{skipped_count + total_downloaded:04d}] Saved {folder_name}/{filename}")
        
    if "continue" in response:
        params.update(response["continue"])
        time.sleep(0.4)
    else:
        print("\nFinished! System fully populated.")
        break