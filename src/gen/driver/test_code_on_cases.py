import logging
import numpy as np
from code_contests.eval.code_test_runners import eval_solution
from gen.utils import render_trace
from log import get_logger
import copy

logger = get_logger(__name__)

def run_test_details(self, problem, test_input, test_output):
    current_plan = problem['current_solution_index']
    attempt_details = {}
    attempt_details['code'] = copy.deepcopy(problem['code_recent_solution'])
    problem, passed_tests, non_empty_output, error_str, trace_str, tests_timeout, d_tot \
                    = test_code_on_cases(self, problem, current_plan, test_input, test_output)
    error_type = ''
    if not passed_tests:
        if tests_timeout:
            error_type = 'timeout'
        elif not non_empty_output or 'Error' in error_str:
            error_type = 'runtime'
        else:
            error_type = 'logic'
    problem['error_type'] = error_type
    problem['error_str'] = error_str
    run_results = {
                    'test_input': test_input,
                    'test_output': test_output,
                    'passed_tests': passed_tests,
                    'non_empty_output': non_empty_output,
                    'error_str': error_str,
                    'error_type': error_type,
                    'trace_str': trace_str,
                    'tests_timeout': tests_timeout,
                    'd_tot': d_tot
                }
    attempt_details['run_results'] = run_results
    problem['solutions_details'][current_plan]['attempts'].append(attempt_details)
    return problem, passed_tests


def test_code_on_cases(self, problem, counter, test_inputs, test_outputs):
    try:
        logging.info(f"evaluating public tests. attempt {counter}")
        test_inputs, results = eval_solution(example=problem,
                                             prediction=problem['code_recent_solution'],
                                             test_inputs=test_inputs,
                                             test_outputs=test_outputs, )
        error_str = trace_str = ""
        timeout_ids, failed_ids = [], []
        all_passed = True
        non_empty_output = False
        tests_timeout = False
        if str(results.compilation_result.program_status) == 'ProgramStatus.kTimeout':
            tests_timeout = True
            all_passed = False
            for i, t in enumerate(results.test_results):
                error_str += f'Example {i}:\n'
                error_str += f"test input:\n{test_inputs[i]}\n" \
                             f"expected output:\n{t.expected_output}\n"
                if t.actual_output:
                    error_str += f"code output:\n{t.actual_output}\n'Timeout, took too long to run next test'\n"
                else:
                    error_str += f"code output:\n'Timeout, took too long to run the test'\n"
                error_str += f'------\n'
        elif str(results.test_results[0].program_status) == 'ProgramStatus.kFailed':
            logger.error("failed to run solution")
            error_str = results.test_results[0].sandbox_result[:500]
            trace_str = f"trace information:\n{render_trace(results.test_results[0].trace[:500])}\n\n"
            all_passed = False
        else:
            all_passed = True
            non_empty_output = True
            error_str = ""
            trace_str = ""
            for i, t in enumerate(results.test_results):
                if str(t.program_status) == 'ProgramStatus.kTimeout':
                    if t.actual_output.strip():
                        t.actual_output += "\nTimeout, took too long to run the next test"
                    else:
                        t.actual_output = 'Timeout, took too long to run'
                        timeout_ids.append(i)
                    t.passed = False
                elif str(t.program_status) == 'ProgramStatus.kFailed':
                    t.actual_output = t.sandbox_result
                    t.passed = False
                if t.expected_output != t.actual_output:
                    if len(t.actual_output) > 500:
                        error_str += f"Example {i}:\n" \
                                    f"test input:\n{test_inputs[i]}\n" \
                                    f"expected output:\n{t.expected_output}\n" \
                                    f"code output is unreasonably long, here is a part of the output:\n{t.actual_output[:500]}\n" \
                                    f"--------------\n"
                    else:
                        error_str += f"Example {i}:\n" \
                                    f"test input:\n{test_inputs[i]}\n" \
                                    f"expected output:\n{t.expected_output}\n" \
                                    f"code output:\n{t.actual_output}\n" \
                                    f"--------------\n"
                    failed_ids.append(i)
                trace_str += f"trace:\n{render_trace(t.trace)}\n" \
                             f"====================\n====================\n"

                all_passed = all_passed and t.passed
                non_empty_output = bool(t.actual_output)
        tests_timeout = len(failed_ids) > 0 and failed_ids == timeout_ids
        d_tot = calc_distance_between_results(non_empty_output, tests_timeout, test_outputs, results)
        return problem, all_passed, non_empty_output, error_str, trace_str, tests_timeout, d_tot
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(-1)

def calc_distance_between_results(non_empty_output, tests_timeout, test_outputs, results):
    try:
        d_tot = float('inf')
        if non_empty_output and not tests_timeout:
            d_tot = 0
            for i in range(len(test_outputs)):
                expected = test_outputs[i].rstrip().split('\n')
                actual = results.test_results[i].stdout.rstrip().split('\n')
                try:
                    t1 = np.array(list(map(float, actual)))
                    t2 = np.array(list(map(float, expected)))
                    if t1.size == 0:
                        return float('inf')
                    d_tot += np.sum(np.abs(t1 - t2))
                except:
                    t1 = np.array(actual)
                    t2 = np.array(expected)
                    if t1.size == 0:
                        return float('inf')
                    d_tot += np.sum(t1 != t2)
    except:
        d_tot = float('inf')
    return d_tot


if __name__ == '__main__':
    problem ={}
    problem['name'] = 'test'
    problem['code_recent_solution'] = """
from itertools import product
from math import gcd

MOD = 998244353

def count_mathematical_states(n, m, ranges):
    count = 0
    for values in product(*[range(l, r+1) for l, r in ranges]):
        if sum(values) <= m:
            if gcd(*values) == 1:
                count += 1
    return count % MOD

if __name__ == "__main__":
    n, m = map(int, input().split())
    ranges = [list(map(int, input().split())) for _ in range(n)]
    result = count_mathematical_states(n, m, ranges)
    print(result)    
"""
    counter = 0
    test_inputs=["2 4\n1 3\n1 2","5 100\n1 94\n1 96\n1 91\n4 96\n6 97", "5 10\n1 10\n1 10\n1 10\n1 10\n1 10"]
    test_outputs=["4", "47464146", "251"]
    test_code_on_cases('', problem, counter, test_inputs, test_outputs)