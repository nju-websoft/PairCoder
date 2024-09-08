from log import get_logger


logger = get_logger(__name__)

class DecisionMaker:
    def __init__(self, method) -> None:
        self.method = method
        return None
    
    def if_consistent(current_plan, attempts, window_size=2):
        window = attempts[-window_size:]
        codes = [attempt['code'] for attempt in window]
        if len(set(codes)) <= 1:
            logger.info(f"Plan {current_plan}: Code consistency detected in attempts in window {len(attempts)--window_size, len(attempts)}")
            return True
        error_strs = [attempt['run_results']['error_str'] for attempt in window]
        if len(set(error_strs)) <= 1:
            logger.info(f"Plan {current_plan}: Function consistency detected in attempts in window {len(attempts)-window_size, len(attempts)}")
            return True

    def decide_function(self, problem, window_size=2):
        current_plan = problem['current_solution_index']
        attempts = problem['solutions_details'][current_plan]['attempts']
        if len(attempts) < window_size:
            return False
        prev_attempts = attempts[:-1]
        cur_code = attempts[-1]['code']
        cur_error = attempts[-1]['run_results']['error_str']
        for attempt in prev_attempts:
            if cur_code == attempt['code']:
                return True
            if cur_error == attempt['run_results']['error_str']:
                return True
        return False
    
    def decide_llm(self, problem):
        return False
    
    def should_switch_plan(self, problem):
        if self.method == 'Function':
            return self.decide_function(problem)
        elif self.method == 'LLM':
            return self.decide_llm(problem)
