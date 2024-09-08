import logging
from log import get_logger
from gen.utils import load_yaml, dict_to_yaml, parse_index
logger = get_logger(__name__)

async def choose_best_solution_by_LLM(self, problem):
    counter_retry = 0
    while True:
        try:
            logger.info("--[NAVIGATOR] choose best solution stage--")

            problem['candidate_solutions_str'] = ''
            for idx, sol in enumerate(problem['representative_solutions']):
                if problem['solutions_details'][idx]['tried'] == False:
                    problem['candidate_solutions_str'] += f"INDEX_NUMBER: {idx}\n {dict_to_yaml(sol)}\n"
            remaining_untried = [i for i, detail in enumerate(problem['solutions_details']) if not detail['tried']]
            if len(remaining_untried) == 0:
                logger.info("--All representative solutions have been tried!--")
                problem['current_solution_index'] = (problem['current_solution_index'] + 1) % len(problem['solutions_details']) 
            elif len(remaining_untried) == 1:
                problem['current_solution_index'] = remaining_untried[0]
            else:
                response_best_solution, _ = await self.send_inference(
                    problem=problem, 
                    prompt='prompt_navigator_choose_best_solution'
                )
                response_best_solution_yaml = load_yaml(
                    response_best_solution,
                    keys_fix_yaml=["INDEX_NUMBER:", "why:", "name:", "- "]
                )
                problem['current_solution_index'] = parse_index(response_best_solution_yaml['INDEX_NUMBER'])
            problem['current_solution_str'] = get_solution_str(problem)
            return problem
        except Exception as e:
            logging.error(f"[NAVIGATOR] choose best solution stage, counter_retry {counter_retry}, Error: {e}")
            if response_best_solution:
                logging.info(f"Parsing the response may fail: {response_best_solution}")
            counter_retry += 1
            if counter_retry > 2:
                raise e

def get_solution_str(problem, _all=False): 
    def extract_keys(input_dict, keys):
        return {key: input_dict[key] for key in keys if key in input_dict}
    original_solution = problem['representative_solutions'][problem['current_solution_index']]
    if _all == False:
        original_solution = extract_keys(original_solution,
                                        ['name', 'key_observations', 'content'])
    return dict_to_yaml(original_solution)