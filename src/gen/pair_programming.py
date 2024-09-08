import logging
from log import get_logger
from gen.utils import choose_best_solution
from settings.config_loader import get_settings
from gen import navigator
from gen import driver
from gen.navigator.decide_direction import DecisionMaker
from gen.utils import *
logger = get_logger(__name__)


async def run_iterative_code_finder(self, problem):
    counter_retry = 0
    plan = 0
    max_coding_count = get_settings().get("solve.max_coding_count")
    max_plans = min(len(problem['representative_solutions']),
                         get_settings().get("public_tests.max_plan_attempts", 3))
    max_attempts = get_settings().get('initial_code_generation.max_attempts', 5)
    if_decision = get_settings().get('public_tests.decision_maker', True)
    static_analysis = get_settings().get('initial_code_generation.static_analysis', True)
    problem['coding_count'] = 0
    if if_decision:
        decision_method = get_settings().get('public_tests.decision_method', 'Function')
        decisionMaker = DecisionMaker(decision_method)
    test_input = problem['public_tests']['input']
    test_output = problem['public_tests']['output']
    while True:
        try:
            logger.info("======= Solution Finding Process Started =======")
            while plan < max_plans:
                logger.info(f"--Attempting plan:{plan}, there are {max_plans} plans--")
                problem = await navigator.choose_best_solution_by_LLM(self, problem)
                problem = await driver.generate_initial_solve(self, problem)
                problem['coding_count'] += 1
                if problem['coding_count'] >= max_coding_count:
                    logger.info(f'current coding count has reached max count {max_coding_count}. Exiting and choose the best one')
                    choose_best_solution(problem, max_plans)
                    return problem
                attempt_count = 0
                while attempt_count < max_attempts:
                    if static_analysis:
                        static_fix_count = 0
                        prev_error_strs = []
                        while static_fix_count < max_attempts:
                            success, error_str = driver.analyze_code_from_string(problem['code_recent_solution'])
                            logger.info(f"[DRIVER] static analyze the code, success: {success}")
                            if not success:
                                prev_error_strs.append(error_str)
                                if prev_error_strs.count(error_str) > 1:
                                    break
                                problem['error_str'] = error_str
                                logger.error(f"--[DRIVER] static analyze the code error: {error_str}")
                                if not get_settings().get("public_tests.pair_fix", True):
                                    pass
                                else:
                                    problem = await navigator.analyze_code_errors(self, problem, prompt_type='static')
                                    problem = await driver.fix_code_errors(self, problem, prompt_type='static')
                            else:
                                break
                            problem['coding_count'] += 1
                            if problem['coding_count'] >= max_coding_count:
                                logger.info(f'current coding count has reached max count {max_coding_count}. Exiting choose the best one')
                                choose_best_solution(problem, max_plans)
                                return problem
                            static_fix_count += 1
                    
                    problem, passed_tests = driver.run_test_details(self, problem, test_input, test_output)
                    if passed_tests:
                        logger.info(f"Passed tests in plan:{plan} after {attempt_count } attempts")
                        break
                    else:
                        # navigator decide change plan or fix code
                        if if_decision and decisionMaker.should_switch_plan(problem):
                            logger.info(f"[NAVIGATOR] think should change plan:{plan}")
                            break
                        logger.info(f"Failed to pass tests in plan:{plan} after {attempt_count } attempts, try to fix it")
                        if not get_settings().get("public_tests.pair_fix", True):
                            pass
                        else:
                            problem = await navigator.analyze_code_errors(self, problem, prompt_type='runtime')
                            problem = await driver.fix_code_errors(self, problem, prompt_type='runtime')
                    attempt_count += 1
                    problem['coding_count'] += 1
                    if problem['coding_count'] >= max_coding_count:
                        logger.info(f'current coding count has reached max count {max_coding_count}. Exiting choose the best one')
                        choose_best_solution(problem, max_plans)
                        return problem
                if attempt_count  >= max_attempts:
                    logger.info(f"Failed to pass tests in plan:{plan} after all {max_attempts} attempts. Exit this plan!")
                if passed_tests:
                    break
                else:
                    current_solution_index = problem['current_solution_index']
                    problem['solutions_details'][current_solution_index]['tried'] = True
                    plan += 1
            if not passed_tests:
                logger.info(f"all {plan} plans failed")
                if problem['coding_count'] < max_coding_count:
                    logger.info(f"there are {max_coding_count-problem['coding_count']} counts left, try directly.")
                    response_direct, _ = await self.send_inference(
                        problem=problem, 
                        prompt="prompt_direct_generate_code" # prompt_direct_generate_code or prompt_direct_generate_code_contest
                    )
                    response_solve = extract_code(response_direct, 'python')
                    response_solve = response_solve.rstrip("` \n")
                    if response_solve.startswith("```python"):
                        response_solve = response_solve[10:]
                    elif response_solve.startswith("python"):
                        response_solve = response_solve[6:]
                    problem['code_recent_solution'] = response_solve
                    problem['coding_count'] += 1
                while True:
                    problem, passed_tests = driver.run_test_details(self, problem, test_input, test_output)
                    if passed_tests:
                        logger.info(f"Passed tests directly")
                        return problem
                    if problem['coding_count'] >= max_coding_count:
                        break
                    problem = await navigator.analyze_code_errors(self, problem, prompt_type='runtime') 
                    problem = await driver.fix_code_errors(self, problem, prompt_type='runtime')
                    problem['coding_count'] += 1
                logger.info(f"all {max_coding_count} attempts failed, choose the best one")
                choose_best_solution(problem, max_plans)
            return problem
        except Exception as e:
            logging.error(f"'Solution Finding' stage, counter_retry {counter_retry}, Error: {e}")
            counter_retry += 1
            if counter_retry > 2:
                raise e
            

async def run_iterative_code_finder_wo_multiplans(self, problem):
    counter_retry = 0
    # max coding count = initial coding count + fix count
    max_coding_count = get_settings().get("solve.max_coding_count")
    # max attempt plans' count
    max_plans = min(len(problem['representative_solutions']),
                         get_settings().get("public_tests.max_plan_attempts", 3))
    static_analysis = get_settings().get('initial_code_generation.static_analysis', True)
    problem['coding_count'] = 0
    test_input = problem['public_tests']['input']
    test_output = problem['public_tests']['output']
    try:
        logger.info("======= Solution Finding Process Started =======")
        problem = await navigator.choose_best_solution_by_LLM(self, problem) # navigator choose best solution from the leaving candidate
        problem = await driver.generate_initial_solve(self, problem) # driver generate an initial code
        problem['coding_count'] += 1
        while True: # iterative fix without change plans
            if problem['coding_count'] >= max_coding_count:
                logger.info(f'current coding count has reached max count {max_coding_count}. Exiting and choose the best one')
                choose_best_solution(problem, max_plans)
                return problem
            if static_analysis:
                while True:
                    success, error_str = driver.analyze_code_from_string(problem['code_recent_solution']) # driver static analysis
                    if "'(' was never closed" in error_str:
                        problem['code_recent_solution'] = problem['code_recent_solution'].rstrip()+')'
                        success = True
                    logger.info(f"[DRIVER] static analyze the code, success: {success}")
                    if not success:
                        problem['error_str'] = error_str
                        logger.error(f"--[DRIVER] static analyze the code error: {error_str}")
                        problem = await navigator.analyze_code_errors(self, problem, prompt_type='static') # navigator analyze static errors
                        problem = await driver.fix_code_errors(self, problem, prompt_type='static') # driver fix errors
                    else:
                        break
                    problem['coding_count'] += 1
                    if problem['coding_count'] >= max_coding_count:
                        logger.info(f'current coding count has reached max count {max_coding_count}. Exiting choose the best one')
                        choose_best_solution(problem, max_plans)
                        return problem
            problem, passed_tests = driver.run_test_details(self, problem, test_input, test_output) # driver run the code on the public test cases
            if passed_tests:
                logger.info(f"Passed tests in after { problem['coding_count'] } coding count")
                break
            else: # fix code
                logger.info(f"Failed to pass tests after {problem['coding_count'] } coding count, try to fix it")
                if get_settings().get("config.use_func_trace", False): # use func trace to analyze
                    problem['use_func_trace'] = True 
                    problem['func_trace_str'] = driver.exec_code(problem['code_recent_solution'], test_input)
                else:
                    problem['use_func_trace'] = False 
                problem = await navigator.analyze_code_errors(self, problem, prompt_type='runtime') # navigator analyze the execution result on test cases
                problem = await driver.fix_code_errors(self, problem, prompt_type='runtime') # driver fix code by guidance
            problem['coding_count'] += 1
            if problem['coding_count'] >= max_coding_count:
                logger.info(f'current coding count has reached max count {max_coding_count}. Exiting choose the best one')
                choose_best_solution(problem, max_plans)
                return problem
            if passed_tests:
                break
        if not passed_tests:
            logger.info(f"all {max_coding_count} attempts failed, choose the best one")
            choose_best_solution(problem, max_plans)
        return problem
    except Exception as e:
        logging.error(f"'Solution Finding' stage, counter_retry {counter_retry}, Error: {e}")
        counter_retry += 1
        if counter_retry > 2:
            raise e