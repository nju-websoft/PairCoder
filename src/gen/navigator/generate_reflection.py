import logging
import yaml

from gen.utils import postprocess_response
from log import get_logger
from gen.utils import extract_code

logger = get_logger(__name__)

async def generate_reflection(self, problem):
    counter_retry = 0
    while True:
        try:
            logger.info("--[NAVIGATOR] reflection stage--")
            actual_number_of_tests = len(problem['public_tests']['input'])
            problem['actual_number_of_tests'] = actual_number_of_tests
            response_reflect, _ = await self.send_inference(
                problem=problem, 
                prompt="prompt_navigator_generate_reflection"
            )
            response_reflect = extract_code(response_reflect, 'yaml')
            response_reflect = response_reflect.rstrip("'` \n")
            if response_reflect.startswith("```yaml"):
                response_reflect = response_reflect[8:]
            try:
                response_reflect_yaml = yaml.safe_load(response_reflect)
            except yaml.YAMLError:
                response_reflect = postprocess_response(response_reflect)
                response_reflect_yaml = yaml.safe_load(response_reflect)

            problem['response_reflect'] = response_reflect
            try:
                problem['self_reflection'] = '- ' + '\n- '.join(response_reflect_yaml['self_reflection'])[:500]
                if problem['self_reflection'].startswith('- - '):
                    problem['self_reflection'] = problem['self_reflection'][2:]
            except:
                problem['self_reflection'] = response_reflect_yaml['self_reflection']
            problem['tests_explanations'] = response_reflect_yaml['tests_explanations']
            problem['tests_explanations_str'] = response_reflect.split('tests_explanations:')[1]

            for s in problem['tests_explanations']:
                if 'input' in s and 'output' in s and 'explanation' in s:
                    s['input'] = s['input'].replace('\\n', '\n')
                    s['output'] = s['output'].replace('\\n', '\n')
                    s['explanation'] = s['explanation'].replace('\\n', '\n')

            return problem
        except Exception as e:
            logging.error(f"[NAVIGATOR] reflection stage, counter_retry {counter_retry}, Error: {e}")
            seq = response_reflect.find('tests_explanations')
            if seq != -1:
                problem['tests_explanations_str'] = response_reflect[seq:]
                problem['self_reflection'] = response_reflect[:seq]
            else:
                problem['tests_explanations_str'] = ' '
                problem['self_reflection'] = response_reflect
            if 'tests_explanations_str' in problem and 'self_reflection' in problem \
                    and problem['tests_explanations_str'] and problem['self_reflection']:
                logger.info(f"self_reflection and tests_explanations_str have been done, so go on")
                return problem
            if response_reflect:
                logging.info(f"Parsing the response may fail: {response_reflect}")
            counter_retry += 1
            if counter_retry > 2:
                raise e
