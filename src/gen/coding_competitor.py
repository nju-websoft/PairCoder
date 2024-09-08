import asyncio
import logging
import os
import traceback

from code_contests.data.provider import CodeContestDataProvider
from gen.utils import render, evaluate_public_solutions, evaluate_solution_on_subset
from llm.ai_handler import AiHandler
from log import get_logger
from settings.config_loader import get_settings
from gen.methods_flow import *
class CodeContestsCompetitor:
    def __init__(self, dataset=None, method=None):
        self.prompt = {}
        self.dataset_name = dataset
        self.method = method
        for set in get_settings():
            if 'prompt' in set.lower():
                self.prompt[set.lower()] = get_settings()[set]
        self.ai_handler = AiHandler()

    async def send_inference(self, problem, prompt:str = "code_contests_prompt_reflect"):
        (
            system_prompt, user_prompt, model,
            temperature, frequency_penalty,
            sample_count, top_p
        ) = render(self, problem, prompt)
        try:
            response, finish_reason = await self.ai_handler.chat_completion(
                model=model, system=system_prompt, user=user_prompt,
                temperature=temperature, frequency_penalty=frequency_penalty,
                n=sample_count, top_p=top_p
            )
        except Exception:
            logging.error(
                f"Failed to generate prediction with {model}"
                f"{traceback.format_exc()}"
            )
        return response, finish_reason

    async def run(self, problem, iteration=0):
        logger = get_logger(__name__)
        logger.info(f"Method {self.method}, model {get_settings().config['model']}, embedding model {get_settings().config['embedding_model']}")
        method = self.method
        try:
            if method == 'pair_programming':
                problem = await pair_programming(self, problem, iteration)
            else: 
                pass
            return problem['code_recent_solution']
        except Exception as e:
            logging.error(f"Error: {e}")
            return ""
        
    def solve_problem_in_dataset(self, example, iteration=0):
        problem = {k: example.get(k) for k in ["io_format", "name", "description", "public_tests"]}
        prediction = asyncio.run(self.run(problem=problem, iteration=iteration))
        return prediction


def solve_problem(dataset_name,
                  split_name="valid",
                  problem_name="",
                  problem_number=0):
    logger = get_logger(__name__)
    data_provider = CodeContestDataProvider(dataset_location=dataset_name)
    if problem_number and problem_name:
        logger.info(f"problem_number and problem_name are both specified, using problem_name")
    if not problem_name and problem_number:
        problem_name = data_provider.dataset[split_name][int(problem_number)]['name']
        logger.info(f"problem_name: {problem_name}")
    problem = data_provider.find_problem(ds=data_provider.dataset, problem_name=problem_name, split_name=split_name)
    problem['dataset_name'] = dataset_name
    logger.info(f"problem['name']: {problem['name']}")
    evaluate_prev_solutions = get_settings().get("dataset.evaluate_prev_solutions", False)
    if evaluate_prev_solutions:
        evaluate_public_solutions(problem)
    if 'mbpp' in dataset_name:
        index = problem['description'].find('assert')
        if index== -1:
            example_str = '\nExample:\n' + problem['test_list'][0]
            problem['description'] += example_str
        else:
            example_str = problem['description'][index:]
            problem['description'] = problem['description'][:index] + '\nExample:\n' + example_str
        if problem['test_setup_code']:
            problem['description'] += '\nSetup Code:\n' + problem['test_setup_code']
    if 'human' in dataset_name.lower():
        if not problem['public_tests']['input'] and not problem['public_tests']['output']:
            logger.info(f"There is no public tests in {problem['name']}, use the first private test!")
            problem['public_tests']['input'] = [problem['private_tests']['input'][0]]
            problem['public_tests']['output'] = [problem['private_tests']['output'][0]]

    return solve_and_evaluate(problem)


def solve_and_evaluate(problem):

    base_path = os.getcwd()
    logger = get_logger(__name__)

    solver = CodeContestsCompetitor()
    os.chdir(base_path)
    solution_code = solver.solve_problem_in_dataset(problem)
    logger.info(f"evaluating solution on public tests...")
    test_results, test_passed_public, test_failed_public, test_timeout_public = evaluate_solution_on_subset('public_tests',
                                                                                                       problem,
                                                                                                       solution_code,
                                                                                                       silent=True)
    logger.info(f"test_passed_public: {test_passed_public}"
                f"test_failed_public: {test_failed_public}"
                f"test_timeout_public: {test_timeout_public}")

    return solution_code, test_results
