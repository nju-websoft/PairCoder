import json
import os
from collections import OrderedDict

from code_contests.data.provider import CodeContestDataProvider
from gen.coding_competitor import CodeContestsCompetitor
from gen.utils import evaluate_solution_on_subset
from log import setup_logger
from settings.config_loader import get_settings
import toml

def solve_dataset(dataset_name='codecontest',
                  split_name='valid',
                  solution_file_name='solutions.json',
                  id_range=None,
                  id_list=None,
                  dir_path=None,
                  method=None
                  ):
    data_provider = CodeContestDataProvider(dataset_location=dataset_name)
    setting = get_settings()
    num_problems = len(data_provider.dataset[split_name])
    base_path = os.getcwd()
    setting.solve.reduce_verbose = True
    log_root = f'./logs/{dataset_name}/{split_name}/{setting.get("config.model", "PATH_ERROR")}'
    if dir_path:
        log_root += f'/{dir_path}/'
    os.makedirs(log_root, exist_ok=True)
    if len(solution_file_name) == 0:
        solution_file_name = 'solutions.json'
    solution_file_name = f'{log_root}/{solution_file_name}'
    config_dict = setting.to_dict()
    with open(f'{log_root}/config.toml', 'w') as toml_file:
        toml.dump(config_dict, toml_file)
    try:
        with open(solution_file_name, 'r') as f:
            database = json.load(f)
            database[split_name] = OrderedDict(sorted(database[split_name].items(), key=lambda x: int(x[0])))
    except:
        print(f"Failed to load database from {solution_file_name}")
        database = {split_name: {}}
    for problem_number in range(0, num_problems):
        if id_range is not None:
            id_num = problem_number
            low, high = id_range
            if id_num < low or id_num >= high:
                print(f"Skipping {problem_number} as it is not in {id_range}")
                continue
        if id_list and problem_number not in id_list:
            continue
        logger = setup_logger(logger_path=f"{log_root}/{split_name}_{problem_number}.log")
        num_iterations =  setting.get("dataset.num_iterations", 1)
        prev = database[split_name].get(str(problem_number), {})
        if not ((prev == {}) or (prev is None)):
            print(f"problem_number {problem_number} already ran")
            continue

        os.chdir(base_path)
        logger.info(f"problem_number: {problem_number}")
        problem_name = data_provider.dataset[split_name][int(problem_number)]['name']
        logger.info(f"problem_name: {problem_name}")
        problem = data_provider.find_problem(ds=data_provider.dataset, problem_name=problem_name, split_name=split_name)
        problem['dataset_name'] = dataset_name
        if 'humaneval' in dataset_name.lower() or 'mbpp' in dataset_name.lower():
            problem['io_format'] = 'normal'
        else:
            problem['io_format'] = 'contest'
        problem_database = {problem_number: {}}
        solver = CodeContestsCompetitor(dataset=dataset_name, method=method)
        for iteration in range(num_iterations):
            it_str = f"iteration_{iteration}"
            problem_database[problem_number][it_str] = {}
            prev_iter = database[split_name].get(str(problem_number), {}).get(it_str, {})
            if not ((prev_iter == {}) or (prev_iter is None)):
                print(f"prev_iter {iteration} already ran")
                problem_database[problem_number][it_str] = prev_iter
                if is_solved(prev_iter):
                    logger.info(f"solved problem {problem_number}")
                    break
                continue
            if 'mbpp' in dataset_name:
                index = problem['description'].find('assert')
                if index== -1:
                    example_str = '\nExample:\n' + problem['test_list'][0].replace('\"', "'")
                    problem['description'] += example_str
                    if problem['test_setup_code']:
                        problem['description'] += '\nSetup Code:\n' + problem['test_setup_code']
                else:
                    example_str = problem['description'][index:]
                    problem['description'] += 'Here are some public test cases:'
                    for i, case in enumerate(zip(problem['public_tests']['input'], problem['public_tests']['output'])):
                        problem['description'] += f'\nExample{i}:\n' + f'  Input: {case[0]}\n' + f'  Output: {case[1]}'
            if 'human' in dataset_name.lower():
                if not problem['public_tests']['input'] and not problem['public_tests']['output']:
                    logger.info(f"There is no public tests in {problem['name']}, use the first private test!")
                    problem['public_tests']['input'] = [problem['private_tests']['input'][0]]
                    problem['public_tests']['output'] = [problem['private_tests']['output'][0]]
            solution = solver.solve_problem_in_dataset(problem, iteration)
            logger.info(f"solution code:\n{solution}")
            if not solution:
                logger.info(f"Failed to solve problem {problem_number} in iteration {iteration}")
                continue
            logger.info(f"Evaluating solution on public tests...")
            silent = True
            test_results, test_passed_public, test_failed_public, test_timeout_public = evaluate_solution_on_subset(
                'public_tests', problem, solution, silent=silent, only_failed_cases=True)
            
            problem_database[problem_number][it_str]['solution'] = solution
            problem_database[problem_number][it_str]['test_passed_public'] = test_passed_public
            problem_database[problem_number][it_str]['test_failed_public'] = test_failed_public
            problem_database[problem_number][it_str]['test_timeout_public'] = test_timeout_public
            if not is_iterative_method(method):
                if not is_solved(problem_database[problem_number][it_str], domain="public"):
                    if iteration == num_iterations-1:
                        logger.info(f"Failed to solve problem {problem_number}'s public cases in all {setting.get('dataset.num_iterations', 1)} iterations. Submit it!")
                    else:
                        logger.info(f"Failed to solve problem {problem_number}'s public cases in iteration {iteration}")
                        logger.info(f"\ntest_passed_public: {test_passed_public}, test_failed_public: {test_failed_public}, test_timeout_public: {test_timeout_public}\n")
                        continue
                else:
                    logger.info(f"solved problem {problem_number}'s public cases in iteration {iteration}. Submit it!")

            logger.info(f"evaluating solution on private tests...")
            test_results, test_passed_private, test_failed_private, test_timeout_private = evaluate_solution_on_subset(
                'private_tests', problem, solution, silent=silent, only_failed_cases=True)

            logger.info(f"evaluating solution on generated tests...")
            test_results, test_passed_generate, test_failed_generate, test_timeout_generate = evaluate_solution_on_subset(
                'generated_tests', problem, solution, silent=silent, only_failed_cases=True)

            logger.info(
                f"\ntest_passed_public: {test_passed_public}, test_failed_public: {test_failed_public}, test_timeout_public: {test_timeout_public}\n"
                f"test_passed_private: {test_passed_private}, test_failed_private: {test_failed_private}, test_timeout_private: {test_timeout_private}\n"
                f"test_passed_generate: {test_passed_generate}, test_failed_generate: {test_failed_generate}, test_timeout_generate: {test_timeout_generate}\n")

            problem_database[problem_number][it_str]['test_passed_private'] = test_passed_private
            problem_database[problem_number][it_str]['test_failed_private'] = test_failed_private
            problem_database[problem_number][it_str]['test_timeout_private'] = test_timeout_private
            problem_database[problem_number][it_str]['test_passed_generate'] = test_passed_generate
            problem_database[problem_number][it_str]['test_failed_generate'] = test_failed_generate
            problem_database[problem_number][it_str]['test_timeout_generate'] = test_timeout_generate
            problem_database[problem_number][it_str]['test_passed_public'] = test_passed_public
            problem_database[problem_number][it_str]['test_failed_public'] = test_failed_public
            problem_database[problem_number][it_str]['test_timeout_public'] = test_timeout_public
            os.chdir(base_path)
            if is_solved(problem_database[problem_number][it_str]):
                logger.info(f"PairCoder solved problem {problem_number} in iteration {iteration}")
                break
            else:
                logger.info(f"PairCoder failed to solve problem {problem_number} in iteration {iteration}")
                break
        database[split_name][problem_number] = problem_database[problem_number]
        os.chdir(base_path)
        with open(solution_file_name, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=4)


def is_iterative_method(method):
    if method in ['direct', 'cot', 'scot', 'self_planning']:
        return False
    else:
        return True

def is_solved(s, domain='all'):
    if domain == 'public':
        if s['test_failed_public'] == 0 and \
            s['test_timeout_public'] == 0 and \
            s['test_passed_public'] > 0:
            return True
        else:
            return False
    else:
        if s['test_failed_private'] == 0 and s['test_failed_generate'] == 0 and \
                s['test_timeout_private'] == 0 and s['test_timeout_generate'] == 0 and \
                (s['test_passed_private'] + s['test_passed_generate']) > 0:
            return True
        else:
            return False
