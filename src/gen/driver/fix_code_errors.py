import difflib
import logging
from log import get_logger
from gen.utils import extract_code
logger = get_logger(__name__)


async def fix_code_errors(self, problem, prompt_type):
    counter_retry = 0
    prompt = choose_prompt(prompt_type)
    while True:
        try:
            logger.info(f"--[DRIVER] fix code {prompt_type} errors--")
            response_fixed_code, _ = await self.send_inference(
                problem=problem, 
                prompt=prompt
            )
            response_fixed_code = extract_code(response_fixed_code, 'python')
            response_fixed_code = response_fixed_code.rstrip("'` \n")
            if response_fixed_code.startswith("```python"):
                response_fixed_code = response_fixed_code[10:]
            problem['code_prev_solution'] = problem['code_recent_solution']
            problem['code_recent_solution'] = response_fixed_code
            diff = difflib.unified_diff(problem['code_prev_solution'].splitlines(keepends=True),
                                        response_fixed_code.splitlines(keepends=True))
            return problem
        except Exception as e:
            logging.error(f"[DRIVER] fix code {prompt_type} errors, counter_retry {counter_retry}, Error: {e}")
            if response_fixed_code:
                logging.info(f"Parsing the response may fail: {response_fixed_code}")
            counter_retry += 1
            if counter_retry > 2:
                raise e


def choose_prompt(prompt_type):
    prompt = ""
    if prompt_type == "runtime":
        prompt = "prompt_driver_fix_test_failure"
    elif prompt_type == "static":
        prompt = "prompt_driver_fix_static_error"
    else:
        logger.error(f"prompt_type can only be chosen as 'test' or 'static', {prompt_type} is provided.")
    return prompt