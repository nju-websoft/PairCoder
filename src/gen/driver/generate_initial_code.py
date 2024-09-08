import logging
from log import get_logger
from gen.utils import extract_code

logger = get_logger(__name__)


async def generate_initial_solve(self, problem):
    counter_retry = 0
    while True:
        try:
            logger.info("--[DRIVER] initial solve stage--")
            response_solve, _ = await self.send_inference(
                problem=problem, 
                prompt='prompt_driver_generate_initial_code'
            )
            response_solve = extract_code(response_solve, 'python')
            response_solve = response_solve.rstrip("` \n")
            if response_solve.startswith("```python"):
                response_solve = response_solve[10:]
            elif response_solve.startswith("python"):
                response_solve = response_solve[6:]
            problem['code_recent_solution'] = response_solve
            problem['code_prev_solution'] = response_solve
            return problem
        except Exception as e:
            logging.error(f"[DRIVER] initial solve stage, counter_retry {counter_retry}, Error: {e}")
            if response_solve:
                logging.info(f"Parsing the response may fail: {response_solve}")
            counter_retry += 1
            if counter_retry > 2:
                raise e