def create_prompt_from_file(prompt_file_path, examples, question):
    """
    Creates a prompt by loading a base prompt from a text file and dynamically inserting formatted examples and a single question.
    The text file contains placeholders for where to insert examples and questions.

    Args:
        prompt_file_path (str): The path to the text file containing the base prompt and instructions.
        examples (list of dict): Each dictionary contains 'query' and 'IR' for few-shot learning examples.
            - For IR2PyRel translation, each example dictionary has 'Similar_IDs' and 'PyRel' keys
        question (dict): This dictionary contains 'query' for the question that needs PyRel translations.
            - For IR2PyRel translation, each example dictionary has 'Similar_IDs' and 'PyRel' keys

    Returns:
        str: The complete prompt with dynamically inserted examples and questions.
    """
    # Load the base prompt from the specified file
    with open(prompt_file_path, 'r', encoding='utf-8') as file:
        prompt_template = file.read()

    # Generate formatted examples
    formatted_examples = ""
    for example in examples:
        formatted_examples += f"- **NL query:** {example['query']}\n"
        formatted_examples += f"  **IR:** {example['IR']}\n"
        
        if "Similar_IDs" in example.keys():
            item = "Similar_IDs"
            formatted_examples += f"  **{item}:**\n"
            for clause in example[item]:
                for key, value in clause.items():
                    formatted_examples += f"    - {key}: {value}\n"
        
        if "PyRel" in example.keys():
            item = "PyRel"
            example[item] = example[item].replace(r'\n', '\n')
            formatted_examples += f"  **{item} query:** \n {example[item]}\n\n"

    # Generate formatted question
    formatted_question = f"- **NL query:** {question['query']}\n"

    if "IR" in question.keys():
        item = "IR"
        formatted_question += f"  **IR:** {question[item]}\n"
    if "Similar_IDs" in example.keys():
        item = "Similar_IDs"
        formatted_question += f"  **{item}:**\n"
        for clause in question[item]:
            for key, value in clause.items():
                formatted_question += f"    - {key}: {value}\n"

    # Replace placeholders in the template with generated content
    prompt = prompt_template.replace("{list of examples}", formatted_examples)
    prompt = prompt.replace("{question}", formatted_question)

    return prompt
