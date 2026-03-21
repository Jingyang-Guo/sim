import os
import json
import copy
from typing import Union, List, Dict, Any

def is_valid_number(value: Any) -> bool:
    """Check if a value is a valid number (integer or float)."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False

def is_in_range(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> bool:
    """Check if a numeric value is within the specified range."""
    if not is_valid_number(value):
        return False
    num_value = float(value)
    return min_val <= num_value <= max_val

def validate_matrix_response(response: Dict, question: Dict) -> bool:
    """
    Validate Matrix question responses.
    
    Args:
        response: The response to validate
        question: The question dictionary containing validation rules
    
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        return False
    
    # Check required fields
    if "SelectedByPosition" not in response or "SelectedText" not in response:
        return False
    
    # Check that both lists have the same length
    if len(response["SelectedByPosition"]) != len(response["SelectedText"]):
        return False
    
    # Check that all positions are valid numbers
    if not all(isinstance(pos, (int, str)) for pos in response["SelectedByPosition"]):
        return False
    
    # Check that all texts are strings
    if not all(isinstance(text, str) for text in response["SelectedText"]):
        return False
    
    return True

def validate_single_choice_response(response: Dict, question: Dict) -> bool:
    """
    Validate Single Choice question responses.
    
    Args:
        response: The response to validate
        question: The question dictionary containing validation rules
    
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        return False
    
    # Check required fields
    if "SelectedByPosition" not in response or "SelectedText" not in response:
        return False
    
    # Check that position is a valid number (can be string or int)
    if not isinstance(response["SelectedByPosition"], (int, str)):
        return False
    
    # If position is a string, try to convert to int
    if isinstance(response["SelectedByPosition"], str):
        try:
            int(response["SelectedByPosition"])
        except ValueError:
            return False
    
    # Check that text is a string
    if not isinstance(response["SelectedText"], str):
        return False
    
    return True

def validate_slider_response(response: Dict, question: Dict) -> bool:
    """
    Validate Slider question responses.
    
    Args:
        response: The response to validate
        question: The question dictionary containing validation rules
    
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        return False
    
    # Check required field
    if "Values" not in response:
        return False
    
    # Check that Values is a list
    if not isinstance(response["Values"], list):
        return False
    
    # Check that all values are valid numbers
    if not all(is_valid_number(val) for val in response["Values"]):
        return False
    
    # Check numeric constraints if they exist
    if "NumericConstraints" in question:
        constraints = question["NumericConstraints"]
        if "MinValue" in constraints and "MaxValue" in constraints:
            if not all(is_in_range(val, constraints["MinValue"], constraints["MaxValue"]) for val in response["Values"]):
                return False
    
    return True

def validate_text_entry_response(response: Dict, question: Dict) -> bool:
    """
    Validate Text Entry question responses.
    
    Args:
        response: The response to validate
        question: The question dictionary containing validation rules
    
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        return False
    
    # Check required field
    if "Text" not in response:
        return False
    
    # Check that Text is a string
    if not isinstance(response["Text"], str):
        return False
    
    return True

def validate_response(response: Any, question: Dict) -> bool:
    """
    Validate response based on question type.
    
    Args:
        response: The response to validate
        question: The question dictionary containing validation rules
    
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        return False
        
    # Handle both "Question Type" and "QuestionType" formats
    question_type = response.get("QuestionType") or response.get("Question Type")
    answers = response.get("Answers")
    
    if not question_type or not answers:
        return False
    
    validation_functions = {
        "Matrix": validate_matrix_response,
        "Single Choice": validate_single_choice_response,
        "Slider": validate_slider_response,
        "Text Entry": validate_text_entry_response
    }
    
    validation_func = validation_functions.get(question_type)
    if not validation_func:
        return False
    
    return validation_func(answers, question)

def update_question_json_with_response(qid, answer_block_json_path, simulation_response_data, output_dir):
    """
    Loads an original answer block JSON, updates its "Answers" field based on 
    parsed answers from the simulation response_text, and saves it.

    Args:
        answer_block_json_path (str): Path to the original answer block JSON file.
        simulation_response_data (dict): Parsed JSON data from the simulation output file,
                                         containing at least 'response_text'.
        output_dir (str): Directory to save the updated question JSON.
    """
    try:
        with open(answer_block_json_path, 'r', encoding='utf-8') as f:
            answer_block_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Answer block JSON not found: {answer_block_json_path}")
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not decode answer block JSON: {answer_block_json_path}")
        return False

    response_text = simulation_response_data.get("response_text")
    if not response_text:
        print(f"Warning: No response_text found in simulation data for {answer_block_json_path}. Skipping.")
        return False

    # Save raw response text for debugging
    raw_response_text_dir = os.path.join(output_dir, "llm_response_text")
    if not os.path.exists(raw_response_text_dir):
        os.makedirs(raw_response_text_dir)
    with open(os.path.join(raw_response_text_dir, f"{qid}_response_text.txt"), "w", encoding="utf-8") as f:
        f.write(response_text)

    try:
        if "```json" in response_text:
            response_text_json = json.loads(response_text.split("```json")[1].split("```")[0])
        else:
            response_text_json = json.loads(response_text)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing response JSON for {qid}: {e}")
        return False

    question_items = []
    count = 0
    failed_responses = 0
    validation_failures = 0

    for block in answer_block_data:
        for question in block['Questions']:
            if question['QuestionType'] != 'DB':
                count += 1
                try:
                    retrieved_response = response_text_json[f"Q{count}"]
                    if retrieved_response is None:
                        failed_responses += 1
                        continue

                    # Validate response based on question type
                    if not validate_response(retrieved_response, question):
                        print(f"Warning: Invalid response for {qid} Q{count} ({question['QuestionType']}): {retrieved_response['Answers']}")
                        validation_failures += 1
                        continue

                    question["Original_Answers"] = copy.deepcopy(question["Answers"])
                    question['Answers'] = retrieved_response["Answers"]
                    if "Reasoning" in retrieved_response:
                        question['LLM_Reasoning'] = retrieved_response["Reasoning"]
                    question_items.append(question)
                except KeyError as e:
                    print(f"Error accessing response for {qid} Q{count}: {e}")
                    failed_responses += 1
                    continue

    if failed_responses > 0 or validation_failures > 0:
        print(f"Warning: {failed_responses} failed responses and {validation_failures} validation failures for {qid}")

    # Export the updated answer block json
    output_path = os.path.join(output_dir, os.path.basename(answer_block_json_path))
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(answer_block_data, f, indent=2)

    if failed_responses > 0 or validation_failures > 0:
        return False
    return True


def postprocess_llm_responses():
    