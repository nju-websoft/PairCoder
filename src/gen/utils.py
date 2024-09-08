import re
from typing import List
from jinja2 import Environment, StrictUndefined
import yaml

from code_contests.eval.code_test_runners import eval_solution
from settings.config_loader import get_settings
from log import get_logger
import ast, astor
import sys, os, io
logger = get_logger(__name__)


def clip_string(s: str, max_lines: int = None):
    lines = s.split("\n")
    if max_lines is not None and 0 < max_lines < len(lines):
        logger.debug(f"clipping string from {len(lines)} to {max_lines}")
        half_lines = int(max_lines / 2)
        lines = (
                lines[:half_lines] +
                [f"\n.... {len(lines) - max_lines} omitted lines ....\n"] +
                lines[-half_lines:]
        )
        return "\n".join(lines)
    else:
        return s


def render_trace(trace_data):
    if not trace_data:
        return ''

    max_trace_lines = get_settings().code_tester.get("max_trace_lines")
    trace_data = clip_string(trace_data, max_trace_lines)
    return trace_data


def postprocess_response(response):
    response = str(response)
    if response.endswith("stop"):
        response = response[:-4]
    pattern = r'```\w*\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        response = matches[0]
    return response


def evaluate_solution_on_subset(evaluation_test_type, problem, solution, silent=False, break_on_timeout=True, only_failed_cases=False):
    test_results = None
    if evaluation_test_type:
        test_results = eval_solution(evaluation_test_type=evaluation_test_type, example=problem, prediction=solution,
                                     silent=silent, break_on_timeout=break_on_timeout, only_failed_cases=only_failed_cases)

    if test_results[1] == []:
        if not silent:
            logger.info("=====================================")
            logger.info("No tests")
            logger.info("=====================================")
        return test_results, 0, 0, 0

    if (hasattr(test_results[1], 'compilation_result') and
            test_results[1].compilation_result.program_status.name == 'kTimeout'):
        if not silent:
            logger.info("=====================================")
            logger.info("Timeout")
            logger.info("=====================================")
        return test_results, 0, 0, len(test_results[0])

    test_passed = 0
    test_failed = 0
    test_timeout = 0
    if not problem[evaluation_test_type]['input']:
        logger.info(f"No {evaluation_test_type} for this problem")
    else:
        for test in test_results[1].test_results:
            if (hasattr(test, 'program_status') and test.program_status.name == 'kTimeout'):
                test_timeout += 1
            elif not test.passed:
                test_failed += 1
            else:
                test_passed += 1
        if not silent:
            logger.info("=====================================")
            logger.info(f"test_passed: {test_passed}, test_failed: {test_failed}, test_timeout: {test_timeout}")
            logger.info("=====================================")

    return test_results, test_passed, test_failed, test_timeout


def evaluate_on_private_tests(evaluation_test_type, problem, solution, silent=True):
    test_results = None
    if evaluation_test_type:
        test_results = eval_solution(evaluation_test_type=evaluation_test_type, example=problem, prediction=solution, silent=silent)

    test_passed = 0
    test_failed = 0
    test_timeout = 0

    if not test_results[1]:
        logger.info("No tests were run")
        return test_results, 0, 0

    for test in test_results[1].test_results:
        if test.program_status.name=='kTimeout':
            test_timeout += 1
        elif not test.passed:
            test_failed += 1
        else:
            test_passed += 1


    logger.info("=====================================")
    logger.info(f"test_passed: {test_passed}, test_failed: {test_failed}, test_timeout: {test_timeout}")
    logger.info("=====================================")

    return test_results, test_passed, test_failed, test_timeout


def load_yaml(response_text: str, keys_fix_yaml: List[str] = []) -> dict:
    response_text = response_text.rstrip("` \n").lstrip()
    response_text = response_text.removeprefix('```yaml').rstrip('`')
    try:
        data = yaml.safe_load(response_text)
    except Exception as e:
        data = try_fix_yaml(response_text, keys_fix_yaml=keys_fix_yaml)
        if not data:
            get_logger().info(f"Failed to parse AI YAML prediction: {e}")
    return data


def try_fix_yaml(response_text: str, keys_fix_yaml: List[str] = []) -> dict:
    response_text_lines = response_text.split('\n')

    keys = keys_fix_yaml
    response_text_lines_copy = response_text_lines.copy()
    for i in range(0, len(response_text_lines_copy)):
        for key in keys:
            if response_text_lines_copy[i].strip().startswith(key) and not '|' in response_text_lines_copy[i]:
                response_text_lines_copy[i] = response_text_lines_copy[i].replace(f'{key}',
                                                                                  f'{key} |-\n        ')
    try:
        data = yaml.safe_load('\n'.join(response_text_lines_copy))
        get_logger().info(f"Successfully parsed AI prediction after adding |-\n")
        return data
    except:
        raise "yaml parsing error"

def parse_index(index):
    if isinstance(index, int):
        return index
    
    if isinstance(index, str):
        index = index.strip(':, |')
    try:
        result = int(index)
        return result
    except ValueError:
        return None 

def dict_to_yaml(solution: dict) -> str:
    result = ''
    for key, value in solution.items():
        if isinstance(value, list):
            result += f"- {key}:\n"
            for item in value:
                result += f"    - {item}\n"
        else:
            result += f"- {key}: \n{value}\n"
    return result


def extract_code(markdown_text, language):
    pattern = rf"```{language}\s*([\s\S]*)\s*```"
    match = re.search(pattern, markdown_text)
    if match:
        return match.group(1).strip()
    else:
        return markdown_text


def set_configurations(problem, iteration=0):
    problem['iteration'] = iteration
    problem['passed_tests'] = {}
    problem['passed_tests']['inputs'] = []
    problem['passed_tests']['outputs'] = []
    if '\nExample\n' in problem['description']:
        problem['description_short'] = problem['description'].split('\nExample\n')[0].strip()
    elif '\nExamples\n' in problem['description']:
        problem['description_short'] = problem['description'].split('\nExamples\n')[0].strip()
    else:
        logger.info(f"could not split description to short description, description: {problem['description']}")
        problem['description_short'] = problem['description']
    return problem

def render(self, problem_json, prompt: str):
    environment = Environment(undefined=StrictUndefined)
    environment.globals["zip"] = zip
    environment.globals["enumerate"] = enumerate
    sys_prompt = environment.from_string(self.prompt[prompt].system).render(problem_json)
    usr_prompt = environment.from_string(self.prompt[prompt].user).render(problem_json)
    model = self.prompt[prompt].get('model', get_settings().config['model'])
    temperature = self.prompt[prompt].get('temperature', 0.8)
    frequency_penalty = self.prompt[prompt].get('frequency_penalty', get_settings().config["frequency_penalty"])
    sample_count = self.prompt[prompt].get('n', 1)
    top_p = self.prompt[prompt].get('top_p', 0.95)
    return sys_prompt, usr_prompt, model, temperature, frequency_penalty, sample_count, top_p


def evaluate_public_solutions(problem):
    logger = get_logger(__name__)
    try:
        if not problem['solutions']['solution']:
            logger.info("No public solutions for this problem")
        found_solution = False
        for index_published, sol_published in enumerate(problem['solutions']['solution']):
            if 'python' not in problem['solutions']['language'][index_published].lower():
                found_solution = True
                continue
            logger.info(f"evaluating public solution {index_published} on private tests...")
            test_results, test_passed_private, test_failed_private, test_timeout_private \
                = evaluate_solution_on_subset('private_tests', problem, sol_published, silent=True)
            logger.info(f"evaluating public solution {index_published} on generated tests...")
            test_results, test_passed_generate, test_failed_generate, test_timeout_generate = (
                evaluate_solution_on_subset('generated_tests', problem, sol_published, silent=True))

            if (test_failed_private == test_failed_generate == test_timeout_private == test_timeout_generate == 0) \
                    and test_passed_private + test_passed_generate > 0:
                logger.info(f"sol_published index {index_published} passed all tests:\n{sol_published}")
                found_solution = True
                break

        if not found_solution:
            logger.info(f"None of the public solutions passed all tests")
    except Exception as e:
        logger.error(f"Error evaluating public solutions: {e}")
        pass

def choose_best_solution(problem, max_plans):
    best_d = float('inf')
    best_solution = problem['code_recent_solution']
    for plan in range(max_plans):
        for attempt in problem['solutions_details'][plan]['attempts']:
            if attempt['run_results']['d_tot'] < best_d:
                best_d = attempt['run_results']['d_tot']
                best_solution = attempt['code']
    problem['code_recent_solution'] = best_solution
    return problem

def wrap_main_code(code):
    '''
    TRANSFER CODE:
        if __name__ == '__main__':
            func()
    TO:
        def main():
            func()
        if __name__ == '__main__':
            main()
    '''
    try:
        tree = ast.parse(code)
        has_main_call = False
        main_body = []
        for node in tree.body:
            if (isinstance(node, ast.If) and
                    isinstance(node.test, ast.Compare) and
                    isinstance(node.test.left, ast.Name) and
                    node.test.left.id == '__name__' and
                    isinstance(node.test.ops[0], ast.Eq) and
                    isinstance(node.test.comparators[0], ast.Constant) and
                    node.test.comparators[0].s == '__main__'):
                if_main_node = node
                if len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call):
                    has_main_call = True
                    main_func_name = node.body[0].value.func.id
                else:
                    main_body = node.body
                    node.body = [ast.Expr(value=ast.Call(func=ast.Name(id='main', ctx=ast.Load()), args=[], keywords=[]))]

        if not has_main_call:
            args = ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[]
            )
            main_func = ast.FunctionDef(
                name='main',
                args=args,
                body=main_body,
                decorator_list=[],
                returns=None
            )
            tree.body.remove(if_main_node)
            tree.body.append(main_func)
            tree.body.append(if_main_node)
        else:
            return code
        new_code = astor.to_source(tree)
        return new_code
    except Exception as e:
        print("Error:", e)
        return code
    
def get_help_output(func):
    help_output = io.StringIO()
    sys.stdout = help_output
    help(func)
    help_text = help_output.getvalue()
    sys.stdout = sys.__stdout__
    return help_text

if __name__ == '__main__':
    problem_json = {
            "name": 14,
            "description": "Write a python function to find the volume of a triangular prism.",
            "canonical_solution": "def find_Volume(l,b,h) : \r\n    return ((l * b * h) / 2) ",
            "test_setup_code": "",
            "test_list": [
                "assert find_Volume(10,8,6) == 240",
                "assert find_Volume(3,2,2) == 6",
                "assert find_Volume(1,2,1) == 1"
            ],
            "private_tests": {
                "input": [
                    "[10,8,6]",
                    "[3,2,2]",
                    "[1,2,1]"
                ],
                "output": [
                    "240",
                    "6",
                    "1"
                ],
                "is_valid_test": None
            },
            "public_tests": {
                "input": [
                    "[10,8,6]"
                ],
                "output": [
                    "240"
                ],
                "is_valid_test": None
            },
            "generated_tests": {
                "input": [],
                "output": [],
                "is_valid_test": None
            },
            "error_type" : 'runtime',
            "error_str": 'balabala',
            "code_recent_solution": 'this is a test'
        }
    from coding_competitor import CodeContestsCompetitor 
    solver = CodeContestsCompetitor()
    environment = Environment(undefined=StrictUndefined)
    environment.globals["zip"] = zip
    environment.globals["enumerate"] = enumerate
    user_prompt = environment.from_string(solver.prompt['prompt_navigator_analyze_test_failure'].user).render(problem_json)
    print(user_prompt)