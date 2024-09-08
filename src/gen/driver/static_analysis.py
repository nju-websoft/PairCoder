from io import StringIO
from pylint.lint import Run
from pylint.reporters.text import TextReporter
from mypy import api
import tempfile
import os

def check_code_pylint(file_path):
    pylint_output = StringIO()
    reporter = TextReporter(pylint_output)
    options = [
        "--errors-only",
        "--exit-zero",
        "--msg-template='BEGIN[{obj} occured {msg_id}({symbol})] {msg}'",
        file_path
    ]
    try:
        Run(options, reporter=reporter, exit=False)
        pylint_analysis = pylint_output.getvalue()
        temp_name = os.path.basename(file_path)
        return pylint_analysis.replace(temp_name+', ', '')
    except Exception as e:
        print(f"An error occurred while running Pylint: {e}")
        return ""

# Deprecated, always return nothing
def check_code_mypy(file_path):
    return (
        '', 
        '', 
        0
    )
    mypy_args = [
        file_path, 
        # "--check-untyped-defs",
        "--pretty"
    ]
    try:
        result = api.run(mypy_args)
        return (
            result[0].replace(file_path, 'Line'), 
            result[1], 
            result[2]
        )
    except Exception as e:
        print(f"An error occurred while running Mypy: {e}")
        return ""

def analyze_code_from_string(python_code):
    success = False
    error_str = ''
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(python_code)
            temp_file_path = temp_file.name
        pylint_results = check_code_pylint(temp_file_path)
        mypy_results = check_code_mypy(temp_file_path)
        os.remove(temp_file_path)
        if not pylint_results and mypy_results[2] == 0:
            success = True
        else:
            if not pylint_results:
                error_str = mypy_results[0]
            else:
                error_str = ''.join(pylint_results.split('BEGIN')[1:]) + \
                        '\n' + mypy_results[0]
        return success, error_str
    except Exception as e:
        print(f"An error occurred during code analysis: {e}")
        return success, error_str

if __name__ == '__main__':
    code='print([1, 2, 3])'
    analyze_code_from_string(code)