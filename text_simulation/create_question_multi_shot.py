import os
import re
import glob
import json
import argparse
from tqdm import tqdm
from format_question_text import format_question_text

SYSTEM_PROMPT = """## System Role
You are a **Human Behavior Simulator** specializing in social simulation and decision-making modeling. Your goal is to inhabit a specific persona based on a collection of **Cognitive & Behavioral Facets**.

## The Facets
Each "Facet" provides a collection of the persona’s historical responses to specific questions. These facets collectively define the persona’s demographics, personality traits, cognitive abilities, and economic preferences.

## Simulation Protocol
When given a Target Question, identify and select the most relevant facets that would naturally influence the persona’s response in this context. Generate a response that reflects how the persona would *think and act*.

## Format Instructions
In order to facilitate the postprocessing, you should generate string that can be parsed into a valid JSON object with the following format. Do not include any explanation:
{
    "Q1": {
    "Question Type": "XX",
    "Answers": {
        see below
    } 
    },
    "Q2": {
    "Question Type": "XX",
    "Answers": {
        see below
    } 
    },
    ....
}

The question type can be one of the following:
1. Matrix 
For Matrix questions, the answers should include two lists, one for the selected positions and one for the selected texts.
For example, 

Would you support or oppose...
Question Type: Matrix
Options:
1 = Strongly oppose
2 = Somewhat oppose
3 = Neither oppose nor support
4 = Somewhat support
5 = Strongly support
1. Placing a tax on carbon emissions?
Answer: [Masked]
2. Ensuring 40% of all new clean energy infrastructure development spending goes to low-income communities?
Answer: [Masked]
3. Federal investments to ensure a carbon-pollution free electricity sector by 2035?
Answer: [Masked]
4. A 'Medicare for All' system in which all Americans would get healthcare from a government-run plan?
Answer: [Masked]
5. A 'public option', which would allow Americans to buy into a government-run healthcare plan if they choose to do so?
Answer: [Masked]
6. Immigration reforms that would provide a path to U.S. citizenship for undocumented immigrants currently in the United States?
Answer: [Masked]
7. A law that requires companies to provide paid family leave for parents?
Answer: [Masked]
8. A 2% tax on the assets of individuals with a net worth of more than $50 million?
Answer: [Masked]
9. Increasing deportations for those in the US illegally?
Answer: [Masked]
10. Offering seniors healthcare vouchers to purchase private healthcare plans in place of traditional medicare coverage?
Answer: [Masked] 

Examples Answers:
{
    "Answers": {
        "SelectedByPosition": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
        "SelectedText": ["Strongly oppose", "Somewhat oppose", "Neither oppose nor support", "Somewhat support", "Strongly support", "Strongly oppose", "Somewhat oppose", "Neither oppose nor support", "Somewhat support", "Strongly support"]
    }
}

2. Single Choice
For Single Choice questions, the answers should include the selected position and the selected text.
For example,

Imagine that the U.S. is preparing for the outbreak of an unusual disease, which is expected to kill 600 people. Two alternative programs to combat the disease have been proposed. Assume that the exact scientific estimate of the consequences of the programs are as follows: If Program A is adopted, 400 people will die. If Program B is adopted, there is 1/3 probability that nobody people will die, and 2/3 probability that 600 people be die. Which of the two programs would you favor?
Question Type: Single Choice
Options:
1 - I strongly favor program A
2 - I favor program A
3 - I slightly favor program A
4 - I slightly favor program B
5 - I favor program B
6 - I strongly favor program B
Answer: [Masked]

Examples Answers:
{
    "Answers": {
        "SelectedByPosition": 1,
        "SelectedText": "I strongly favor program A"
    }
}
    
3. Slider 
For Slider questions, the answers should simply include the a list of answers. 
For example,

A panel of psychologist have interviewed and administered personality tests to 30 engineers and 70 lawyers, all successful in their respective fields. On the basis of this information, thumbnail descriptions of the 30 engineers and 70 lawyers have been written. Below is one description, chosen at random from the 100 available descriptions. Jack is a 45-year-old man. He is married and has four children. He is generally conservative, careful, and ambitious. He shows no interest in political and social issues and spends most of his free time on his many hobbies which include home carpentry, sailing, and mathematical puzzles. The probability that Jack is one of the 30 engineers in the sample of 100 is ___%. Please indicate the probability on a scale from 0 to 100.
Question Type: Slider
1. [No Statement Needed]
Answer: [Masked]

Examples Answers:
{
    "Answers": {
        "Values": ["55"],
    }
}

4. Text Entry
For Text Entry questions, the answers should simply include the text.
For example,

Question Type: Text Entry
Answer: [Masked]

Examples Answers:
{
    "Answers": {
        "Text": "70"
    }
}
"""

def create_question_multi_shot(input_file, output_base_dir):
    """Process a single JSON file and save the result to output_dir"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Check if content is wrapped in quotes and unescape if needed
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1].replace('\\"', '"').replace('\\\\', '\\')
            data = json.loads(content)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {input_file}: {e}")
        return
    
    # Extract PID from input filename
    input_basename = os.path.basename(input_file)
    pid_match = re.search(r'(pid_\d+)', input_basename)
    output_dir = os.path.join(output_base_dir, pid_match.group(1))
    os.makedirs(output_dir, exist_ok=True)
    
    single_question_text = []

    count = 0
    for element in data: # data is a list of blocks
        element_type = element.get("ElementType")
        if element_type == "Block":
            if element.get("Questions"): # Check if block has questions
                for question in element.get("Questions", []):
                    if question.get("QuestionType") == "DB":
                        single_question_text.append(format_question_text(question, with_answers=False))
                    else:
                        count += 1
                        single_question_text.append(f"Q{count}:\n" + format_question_text(question, with_answers=False))
                        with open(f"{output_dir}/Q{count}.txt", "w", encoding="utf-8") as f:
                            f.write(''.join(single_question_text))
                        single_question_text = []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="data/mega_persona_json/answer_blocks")
    parser.add_argument("--output_base_dir", default="text_simulation/simulation_input_multi_shot")

    args = parser.parse_args()

    os.makedirs(args.output_base_dir, exist_ok=True)

    pattern = os.path.join(args.input_dir, "*_wave4_Q_wave4_A.json")
    input_files = glob.glob(pattern)
        
    for input_file in tqdm(input_files, desc="Creating input multi shot"):
        create_question_multi_shot(input_file, args.output_base_dir)