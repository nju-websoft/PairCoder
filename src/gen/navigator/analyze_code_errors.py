import logging
import yaml

from log import get_logger
from gen.utils import extract_code

logger = get_logger(__name__)


async def analyze_code_errors(self, problem, prompt_type):
    counter_retry = 0
    prompt = choose_prompt(prompt_type)
    while True:
        try:
            logger.info(f"--[NAVIGATOR] analyze {prompt_type} failure--")
            response_analysis, _ = await self.send_inference(
                problem=problem, 
                prompt=prompt
            )
            response_analysis = extract_code(response_analysis, 'yaml')
            response_analysis = response_analysis.rstrip("'` \n")
            if response_analysis.startswith("```yaml"):
                response_analysis = response_analysis[8:]
            problem['response_analyze_failure'] = response_analysis
            response_analyze_failure_yaml = yaml.safe_load(response_analysis)
            problem['what_went_wrong'] = response_analyze_failure_yaml['what_went_wrong'][:500]
            problem['fixed_flow'] = response_analyze_failure_yaml['fixed_flow'][:500]
            return problem
        except Exception as e:
            logging.error(f"[NAVIGATOR] analyze {prompt_type} failure stage, counter_retry {counter_retry}, Error: {e}")
            seq = response_analysis.find('fixed_flow')
            if seq != -1:
                problem['fixed_flow'] = response_analysis[seq:][:500]
                problem['what_went_wrong'] = response_analysis[:seq][:500]
            if 'fixed_flow' in problem and 'what_went_wrong' in problem \
                    and problem['fixed_flow'] and problem['what_went_wrong']:
                logger.info(f"what_went_wrong and fixed_flow have been done, so go on")
                return problem
            if response_analysis:
                logging.info(f"Parsing the response may fail: {response_analysis}")
            counter_retry += 1
            if counter_retry > 2:
                raise e

def choose_prompt(prompt_type):
    prompt = ""
    if prompt_type == "runtime":
        prompt = "prompt_navigator_analyze_test_failure"
    elif prompt_type == "static":
        prompt = "prompt_navigator_analyze_static_error"
    else:
        logger.error(f"prompt_type can only be chosen as 'test' or 'static', {prompt_type} is provided.")
    return prompt