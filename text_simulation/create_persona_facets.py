import os
import sys
import json
import argparse
from tqdm import tqdm
from pathlib import Path
from format_question_text import format_question_text

def _create_task_with_questions(blocks: list, block_category: str, task_with_ids: dict, with_answers: bool = False) -> dict:
    task_content = []
    for block in blocks:
        if block_category == "Demographics":
            if block.get("BlockName", "").strip() != "Demographics":
                continue
        elif block_category == "Personality traits":
            if block.get("BlockName", "").strip() != "Personality":
                continue
        elif block_category == "Cognitive abilities":
            if block.get("BlockName", "").strip() not in ["Cognitive tests", "Forward Flow"]:
                continue
        else: # Economic preferences
            if block.get("BlockName", "").strip() not in ["Economic preferences - intro", "Economic preferences"]:
                continue

        questions = block["Questions"]
        for question in questions:
            if question["QuestionID"] in task_with_ids["QuestionIDs"]:
                question_text = format_question_text(question, with_answers)
                task_content.append(question_text)

    return {
        "name": task_with_ids["TaskName"],
        "description": task_with_ids["TaskDescription"],
        "content": ''.join(task_content)
    }

def _create_single_persona_facets(persona_json_path: Path, question_id_mapping: list, with_answers: bool = False) -> list:
    try:
        with open(persona_json_path, "r") as f:
            blocks = json.load(f)

        persona_facets = []
        for group in question_id_mapping:
            block_category = group["BlockCategory"]
            tasks = group["Tasks"]

            for task_with_ids in tasks:
                task_with_questions = _create_task_with_questions(blocks, block_category, task_with_ids, with_answers)
                persona_facets.append(task_with_questions)
        return persona_facets

    except FileNotFoundError:
        print(f"Error: persona_json file not found at {persona_json_path}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {persona_json_path}: {e}")
    
    except Exception as e:
        print(f"Error creating persona facets from {persona_json_path}")
    
def create_persona_facets(persona_json_dir: str, persona_facets_dir: str, mapping_path: str, with_answers: bool = False):
    persona_json_dir = Path(persona_json_dir)
    persona_facets_dir = Path(persona_facets_dir)
    mapping_path = Path(mapping_path)
    try:
        json_files = [f for f in os.listdir(persona_json_dir) 
                    if f.endswith('.json') and f.startswith('pid_')]
        
        persona_facets_dir.mkdir(parents=True, exist_ok=True)

        with open(mapping_path, "r") as f:
            question_id_mapping = json.load(f)

        for json_file in tqdm(json_files, desc="Creating persona facets"):
            person_json_path = persona_json_dir / json_file
            person_facets = _create_single_persona_facets(person_json_path, question_id_mapping, with_answers)

            output_path = persona_facets_dir / json_file.replace("mega_persona", "persona_facets")
            with open(output_path, "w") as f:
                json.dump(person_facets, f, ensure_ascii=False)

    except Exception as e:
        print(f"Error creating persona facets: {e}")
        sys.exit(1)
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona_json_dir", default="data/mega_persona_json/mega_persona")
    parser.add_argument("--persona_facets_dir", default="text_simulation/persona_facets")
    parser.add_argument("--mapping_path", default="text_simulation/question_id_mapping.json")

    args = parser.parse_args()

    create_persona_facets(args.persona_json_dir, args.persona_facets_dir, args.mapping_path, with_answers=True)

