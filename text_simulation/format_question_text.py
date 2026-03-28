import re

def strip_html(text: any) -> str:
    """Strip HTML tags from text and normalize whitespace. Handles non-string inputs.
    """
    if text is None:
        return "" # Return empty string if input is None
    if not isinstance(text, str):
        text = str(text) # Convert to string if not already a string
    
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _format_question_text_Matrix(question: dict, with_answers: bool = False) -> str:
    """Formats a single question with Matrix type into a readable string."""
    columns = question.get("Columns", [])
    answers = question.get("Answers", {})
    output_options = []
    output_options.append("Question Type: Matrix\n")
    if columns:
        output_options.append("Options:\n")
        for i, column_text in enumerate(columns, 1):
            output_options.append(f"  {i} = {strip_html(column_text)}\n")
        
        rows = question.get("Rows", [])
        selected_texts = answers.get("SelectedText", [])
        selected_positions = answers.get("SelectedByPosition", [])

        for i, row_text_content in enumerate(rows):
            row_display_id = str(i + 1)
            output_options.append(f"{row_display_id}. {strip_html(row_text_content)}\n")
            
            answer_detail = "[No Answer Provided]"
            if i < len(selected_positions) and i < len(selected_texts):
                answer_detail = f"{selected_positions[i]} - {strip_html(selected_texts[i])}"
            if with_answers:
                output_options.append(f"Answer: {answer_detail}\n")
            else:
                output_options.append(f"Answer: [Masked]\n")
        output_options.append("\n")

    return ''.join(output_options)

def _format_question_text_MC(question: dict, with_answers: bool = False) -> str:
    """Formats a single question with MC type into a readable string."""
    options = question.get("Options", [])
    answers = question.get("Answers", {})
    output_options = []
    selector = question.get("Settings", {}).get("Selector")
    if selector == "MAVR" or selector == "MAHR":
        output_options.append("Question Type: Multiple Choice\n")
    elif selector == "SAVR" or selector == "SAHR":
        output_options.append("Question Type: Single Choice\n")
    if options:
        output_options.append("Options:\n")
        for i, option_text in enumerate(options, 1):
            output_options.append(f"  {i} - {strip_html(option_text)}\n")
        
        selected_positions = answers.get("SelectedByPosition", [])
        selected_texts = answers.get("SelectedText", [])
        if with_answers:
            if selected_positions is not None:
                if (selector == "SAVR" or selector == "SAHR"):
                    selected_positions = [selected_positions]
                    selected_texts = [selected_texts]
                for i, selected_position in enumerate(selected_positions):
                    if i < len(selected_texts):
                        output_options.append(f"Answer: {selected_position} - {strip_html(selected_texts[i])}\n")
            else:
                output_options.append("Answer: [No Answer Provided]\n")
        else:
            output_options.append("Answer: [Masked]\n")

    output_options.append("\n")
    return ''.join(output_options)

def _format_question_text_TE(question: dict, with_answers: bool = False) -> str:
    """Formats a single question text into a readable string."""
    settings = question.get("Settings", {})
    answers = question.get("Answers", {})
    output_options = []

    selector = settings.get("Selector")
    if selector == "FORM":
        output_options.append("Question Type: Text Entry (Form)\n")
    else:
        output_options.append("Question Type: Text Entry\n")

    if selector == "FORM":
        form_rows = question.get("Rows", [])
        form_answers_text = answers.get("Text", []) # This is a list of dicts
        
        # Create a lookup for answers for easier access
        answer_lookup = {}
        for ans_item in form_answers_text:
            if isinstance(ans_item, dict):
                answer_lookup.update(ans_item)

        for i, row_label in enumerate(form_rows):
            clean_row_label = strip_html(row_label)
            answer_value = strip_html(str(answer_lookup.get(row_label, "[No Answer Provided]")))
            if with_answers:
                output_options.append(f"{clean_row_label}: {answer_value}\n")
            else:
                output_options.append(f"{clean_row_label}: [Masked]\n")

    elif selector == "SL" or selector == "ML": # Single Line or Multi Line
        text_answer = answers.get("Text")
        if with_answers:
            if text_answer is not None:
                output_options.append(f"Answer: {strip_html(str(text_answer))}\n")
            else:
                output_options.append("Answer: [No Answer Provided]\n")
        else:
            output_options.append("Answer: [Masked]\n")
    output_options.append("\n")
    return ''.join(output_options)

def _format_question_text_Slider(question: dict, with_answers: bool = False) -> str:
    """Formats a single question text into a readable string."""
    answers = question.get("Answers", {})
    output_options = []
    values = answers.get("Values")
    output_options.append("Question Type: Slider\n")
    if values:
        statements = question.get("Statements")
        for i, value_item in enumerate(values):
            statement_text_content = statements[i]
            stmt_display_id = str(i + 1)
            if statement_text_content == "":
                statement_text_content = "[No Statement Needed]"
            output_options.append(f"{stmt_display_id}. {strip_html(statement_text_content)}\n")
            if with_answers:
                output_options.append(f"Answer: {strip_html(str(value_item))}\n")
            else:
                output_options.append(f"Answer: [Masked]\n")
    else:
        output_options.append("Answer: [No Answer Provided]\n")
    output_options.append("\n")
    return ''.join(output_options)
    
def _format_question_text_DB(question: dict, with_answers: bool = False) -> str:
    """Formats a single question text into a readable string."""
    return "[Descriptive Information]\n\n"

def format_question_text(question: dict, with_answers: bool = False) -> str:
    """Formats a single question text into a readable string."""
    question_text = strip_html(question.get('QuestionText', ''))
    if question_text is None:
        question_text = ""

    question_type = question.get("QuestionType")

    if question_type == "Matrix":
        output_options = _format_question_text_Matrix(question, with_answers)
    elif question_type == "MC": # Multiple Choice
        output_options = _format_question_text_MC(question, with_answers)
    elif question_type == "TE": # Text Entry
        output_options = _format_question_text_TE(question, with_answers)
    elif question_type == "Slider":
        output_options = _format_question_text_Slider(question, with_answers)
    elif question_type == "DB":
        output_options = _format_question_text_DB(question, with_answers)
    else:
        raise ValueError(f"Unhandled question type: {question_type}")

    return question_text + "\n" + output_options
