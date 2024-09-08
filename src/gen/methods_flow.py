from gen.pair_programming import *
from gen.navigator.generate_reflection import generate_reflection
from gen.navigator.generate_possible_solutions import generate_possible_solutions
from gen.utils import *

async def pair_programming(self, problem, iteration):
    problem = set_configurations(problem, iteration)
    problem = await generate_reflection(self, problem)
    problem = await generate_possible_solutions(self, problem)
    problem = await run_iterative_code_finder(self, problem)
    return problem

async def pair_programming_wo_multiplans(self, problem, iteration):
    problem = set_configurations(problem, iteration)
    problem = await generate_reflection(self, problem)
    problem = await generate_possible_solutions(self, problem)
    problem = await run_iterative_code_finder_wo_multiplans(self, problem)
    return problem