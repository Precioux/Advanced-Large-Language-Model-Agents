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
    print('Problem:')
    print('________________________________________________')
    print(problem_description)
    print('________________________________________________')
    ################################################################
    print('Planning Step')
    print('________________________________________________')
    # Step 2-1 : Generate a high-level coding plan
    planning_prompt_code = f"""You are a planning agent, your task is propose a solution to a lean 4 programming task so the coding agent can generate it accurately. You must describe the instruction so an ai agent can completely understand it.
    Here is the problem description from a theorem proving task:

    {problem_description}

    - Describe the approach to implement the function:
    """
    plan_messages_code = [
        {"role": "system", "content": "You are a helpful Lean 4 planning assistant."},
        {"role": "user", "content": planning_prompt_code},
    ]
    plan_code = planner.get_response(plan_messages_code)
    print(f'Coding Plan: {plan_code}')
    print('________________________________________________')
    print('________________________________________________')
    # Step 2-2 : Generate a high-level proofing plan
    planning_prompt_proof = f"""You are a planning agent, your task is propose a proof for a solution on a lean 4 programming task so the coding agent can generate it accurately.You must describe the instruction so an ai agent can completely understand it.
    Here is the problem description from a theorem proving task:

    {problem_description}
    
    Here is the solution for this problem: 
    
    {plan_code}
    
    - Describe how the proof can be structured and which Lean tactics or properties might help
    
    Attention!:
    - Examples will help the proofing agent to implement the proof in a better way!
    """
    plan_messages_proof = [
        {"role": "system", "content": "You are a helpful Lean 4 planning assistant."},
        {"role": "user", "content": planning_prompt_proof},
    ]
    plan_proof = planner.get_response(plan_messages_proof)
    print(f'Proofing Plan: {plan_proof}')
    print('________________________________________________')

    ################################################################
    print('Generating Step')
    print('________________________________________________')
    lean_code = remove_imports(task_lean_code)
    # Step 3-1 : Generate Lean code using the LLM agent
    generation_prompt_code = f"""You are a Lean 4 coding agent. Based on the given instructions, complete the base code. 
    Here is the problem description:

    {problem_description}

    Here is the coding instruction:

    {plan_code}

    Complete the base code, fill {{code}} with correct code
    
    Base code:

    {lean_code}

    Attention!:
     - Generate a code that will be feed to lean runner directly. 
     - do not add ```lean in the start of the code. 
     - do not add ``` at the end of the code. 
     - Do not change the code structure.
     - Be careful about code generation, do not make repetitive statements.
     - Code clearly
     - No explanation is accepted! 
     

    """

    generation_messages_code = [
        {"role": "system", "content": "You are a Lean 4 code and proof generator."},
        {"role": "user", "content": generation_prompt_code}
    ]
    response_code = generator.get_response(generation_messages_code)
    print(f'Generation code: {response_code}')
    print('________________________________________________')
    print('________________________________________________')
    generation_prompt_proof = f"""You are a Lean 4 proofing agent. Based on the given instructions, complete the base code. 
    Here is the problem description:

    {problem_description}

    Here is the proofing instruction:

    {plan_proof}

    Complete the base code, fill {{proof}} with correct code

    Base code:

    {response_code}

    Attention!
     - Generate a code that will be feed to lean runner directly. 
     - do not add ```lean in the start of the code. 
     - do not add ``` at the end of the code.     
     - Do not change the code structure.
     - Be careful about code generation, do not make repetitive statements.
     - Code clearly
     - No explanation is accepted! 

    """

    generation_messages_proof = [
        {"role": "system", "content": "You are a Lean 4 code and proof generator."},
        {"role": "user", "content": generation_prompt_proof}
    ]
    response_proof = generator.get_response(generation_messages_proof)
    print(f'Generation proof: {response_proof}')
    print('________________________________________________')
    ##########################################################################################
    final_code = response_proof
    # Initialize feedback loop flags
    attempt = 1
    max_attempts = 3
    code_fixed = False
    proof_fixed = False

    # Initial extraction
    final_output = extract_code_and_proof_from_lean(final_code)
    current_code = final_output["code"]
    current_proof = final_output["proof"]

    while attempt <= max_attempts and not (code_fixed and proof_fixed):
        print(f"\nFeedback Loop Attempt {attempt} ---")

        code_fixed = True
        proof_fixed = True

        # Replace code and proof in template
        test_code = task_lean_code.replace("{{code}}", current_code).replace("{{proof}}", current_proof)

        # Write and test with Lean
        with open("lean_playground/TempTest.lean", "w") as f:
            f.write(test_code)

        lean_output = execute_lean_code("lean_playground/TempTest.lean")
        print(f"Lean Output:\n{lean_output}")

        if "error" not in lean_output.lower():
            print("Lean code and proof verified successfully.")
            break

        # Check for code errors
        if "definition" in lean_output.lower() or "code" in lean_output.lower():
            code_fixed = False
            print("Code error detected. Revising code...")
            feedback_prompt_code = f"""The following Lean code has an error. Revise the code only.

    Problem:
    {problem_description}

    Code:
    {current_code}

    Error:
    {lean_output}

    Provide only the corrected code inside << CODE START >> and << CODE END >>."""
            code_feedback = generator.get_response([
                {"role": "system", "content": "You are a Lean 4 code reviser."},
                {"role": "user", "content": feedback_prompt_code}])
            current_code = extract_code_and_proof_from_lean(code_feedback)["code"]

        # Check for proof errors
        if "theorem" in lean_output.lower() or "proof" in lean_output.lower():
            proof_fixed = False
            print("Proof error detected. Revising proof...")
            feedback_prompt_proof = f"""The following Lean proof has an error. Revise the proof only.

    Problem:
    {problem_description}

    Proof:
    {current_proof}

    Error:
    {lean_output}

    Provide only the corrected proof inside << PROOF START >> and << PROOF END >>."""
            proof_feedback = generator.get_response([
                {"role": "system", "content": "You are a Lean 4 proof reviser."},
                {"role": "user", "content": feedback_prompt_proof}])
            current_proof = extract_code_and_proof_from_lean(proof_feedback)["proof"]

        attempt += 1

    # Final output
    final_output = {"code": current_code, "proof": current_proof}
    print(f'Final Code:\n{final_output["code"]}')
    print(f'Final Proof:\n{final_output["proof"]}')
    print('________________________________________________')
    return final_output



def remove_imports(task_lean_code: str) -> str:
    """
    Removes all lines in the Lean code that start with 'import' (Lean library imports).

    Args:
        task_lean_code: The Lean code string (template or generated code)

    Returns:
        Lean code string with all 'import' lines removed
    """
    lines = task_lean_code.splitlines()
    cleaned_lines = [line for line in lines if not re.match(r'^\s*import\s+\S+', line)]
    print('Cleaning libs...')
    print(cleaned_lines)
    return '\n'.join(cleaned_lines)


def extract_code_and_proof_from_lean(text: str) -> LeanCode:
    """
    Extracts the content inside << CODE START >>...<< CODE END >> and << PROOF START >>...<< PROOF END >> blocks.
    """
    code_match = re.search(r'-- << CODE START >>\s*(.*?)\s*-- << CODE END >>', text, re.DOTALL)
    proof_match = re.search(r'-- << PROOF START >>\s*(.*?)\s*-- << PROOF END >>', text, re.DOTALL)

    code = code_match.group(1).strip() if code_match else ""
    proof = proof_match.group(1).strip() if proof_match else ""

    return {"code": code, "proof": proof}


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