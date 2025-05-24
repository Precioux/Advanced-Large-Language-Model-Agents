import os
import argparse
from src.agents import Reasoning_Agent, LLM_Agent
from src.lean_runner import execute_lean_code
from typing import Dict, List, Tuple
import re

LeanCode = Dict[str, str]

def main_workflow(problem_description: str, task_lean_code: str = "") -> LeanCode:
    """
    Main workflow for the coding agent. This workflow takes in the problem description in natural language (description.txt) 
    and the corresponding Lean code template (task.lean). It returns the function implementation and the proof in Lean.
    
    Args:
        problem_description: Problem description in natural language. This file is read from "description.txt"
        task_lean_code: Lean code template. This file is read from "task.lean"
    
    Returns:
        LeanCode: Final generated solution, which is a dictionary with two keys: "code" and "proof".
    """
    planner = Reasoning_Agent()
    generator = LLM_Agent()

    ################################################################

    # Step 2: Generate a high-level plan
    planning_prompt = f"""You are a Lean 4 planning assistant.
    Here is the problem description from a theorem proving task:

    {problem_description}

    Please:
    1. Summarize the task in 1-2 lines.
    2. Describe the approach to implement the function.
    3. Describe how the proof can be structured and which Lean tactics or properties might help.
    """
    plan_messages = [
        {"role": "system", "content": "You are a helpful Lean 4 planning assistant."},
        {"role": "user", "content": planning_prompt}
    ]
    plan = planner.get_response(plan_messages)

    ################################################################

    # Step 3: Generate Lean code and proof using the LLM agent
    generation_prompt = f"""You are a Lean 4 code and proof generator.
    Here is the problem description:

    {problem_description}

    Here is a suggested plan from a planning agent:

    {plan}

    Here is the Lean template with placeholders ({{code}} and {{proof}}):

    {task_lean_code}

    Fill in the code and proof sections. Respond in this format:

    code:
    ```lean
    <your Lean code here>
    ```

    proof:
    ```lean
    <your Lean proof here>
    ```"""

    generation_messages = [
        {"role": "system", "content": "You are a Lean 4 code and proof generator."},
        {"role": "user", "content": generation_prompt}
    ]
    response = generator.get_response(generation_messages)

    ################################################################

    # Step 4: Extract code and proof
    generated_function_implementation = extract_section(response, "code")
    generated_proof = extract_section(response, "proof")

    ################################################################

    # Step 5: Verification and Feedback Loop
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        filled_lean_code = task_lean_code.replace("{{code}}", generated_function_implementation).replace("{{proof}}",
                                                                                                         generated_proof)
        execution_result = execute_lean_code(filled_lean_code)

        if "error" not in execution_result.lower():
            break

        feedback_prompt = f"""The following Lean code has errors:
            {execution_result}

            Please revise both the code and proof based on the errors and previous context:
            Problem Description:
            {problem_description}

            Plan:
            {plan}

            Current code:
            {generated_function_implementation}

            Current proof:
            {generated_proof}

            Respond in the same format:
            code:
            ```lean
            <your corrected Lean code here>
            ```

            proof:
            ```lean
            <your corrected Lean proof here>
            ```"""

        feedback_messages = [
            {"role": "system", "content": "You are a Lean 4 code and proof generator."},
            {"role": "user", "content": feedback_prompt}
        ]
        response = generator.get_response(feedback_messages)

        generated_function_implementation = extract_section(response, "code")
        generated_proof = extract_section(response, "proof")
        attempt += 1

        ################################################################


    return {
        "code": generated_function_implementation,
        "proof": generated_proof
    }


    # # TODO Implement your coding workflow here. The unit tests will call this function as the main workflow.
    # # Feel free to chain multiple agents together, use the RAG database (.pkl) file, corrective feedback, etc.
    # # Please use the agents provided in the src/agents.py module, which include GPT-4o and the O3-mini models.
    # ...
    #
    # # Example return for task_id_0
    # generated_function_implementation = "x"
    # generated_proof = "rfl"
    #
    # return {
    #     "code": generated_function_implementation,
    #     "proof": generated_proof
    # }

def extract_section(text: str, section: str) -> str:
    """
    Extracts the code or proof block from the generator response.
    """
    pattern = rf"{section}:\s*```lean\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

def get_problem_and_code_from_taskpath(task_path: str) -> Tuple[str, str]:
    """
    Reads a directory in the format of task_id_*. It will read the file "task.lean" and also read the file 
    that contains the task description, which is "description.txt".
    
    After reading the files, it will return a tuple of the problem description and the Lean code template.
    
    Args:
        task_path: Path to the task file
    """
    problem_description = ""
    lean_code_template = ""
    
    with open(os.path.join(task_path, "description.txt"), "r") as f:
        problem_description = f.read()

    with open(os.path.join(task_path, "task.lean"), "r") as f:
        lean_code_template = f.read()

    return problem_description, lean_code_template

def get_unit_tests_from_taskpath(task_path: str) -> List[str]:
    """
    Reads a directory in the format of task_id_*. It will read the file "tests.lean" and return the unit tests.
    """
    with open(os.path.join(task_path, "tests.lean"), "r") as f:
        unit_tests = f.read()
    
    return unit_tests

def get_task_lean_template_from_taskpath(task_path: str) -> str:
    """
    Reads a directory in the format of task_id_*. It will read the file "task.lean" and return the Lean code template.
    """
    with open(os.path.join(task_path, "task.lean"), "r") as f:
        task_lean_template = f.read()
    return task_lean_template