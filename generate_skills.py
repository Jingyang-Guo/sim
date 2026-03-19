import os
import re
import json
import pathlib
from tqdm import tqdm

PROJECT_ROOT = "persona_profiles"
project_root = pathlib.Path(PROJECT_ROOT)
output_dir = pathlib.Path("skills")
os.makedirs(output_dir, exist_ok=True)

def process_skill_text(skill_text: str):
    if skill_text.startswith("---"):
        parts = skill_text.split("---", 2)
        if len(parts) >= 3:
            front_matter = parts[1].strip()
            content = parts[2].strip()
            
            name = "unnamed_skill"
            description = ""
            
            for line in front_matter.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "name":
                        name = value
                    elif key == "description":
                        description = value

            return {
                "name": name,
                "description": description,
                "content": content,
            }


if __name__ == "__main__":
    pids = os.listdir(project_root)

    for pid in tqdm(pids, desc="Processing skills"):
        id = re.search(r"pid_(\d+)", pid).group(1)
        skills_dir = project_root / pid / ".claude" / "skills"
        skills = os.listdir(skills_dir)

        skill_data_list = []
        for skill in skills:
            skill_path = skills_dir / skill / "SKILL.md"
            with open(skill_path, "r") as f:
                text = f.read()
            skill_data = process_skill_text(text)
            skill_data_list.append(skill_data)
            
        with open(output_dir / f"pid_{id}_skills.json", "w", encoding="utf-8") as f:
            json.dump(skill_data_list, f, ensure_ascii=False)    