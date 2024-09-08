import argparse
import ast
from gen.dataset_solver import solve_dataset
from log import get_logger, setup_logger
import datetime
logger = get_logger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--dataset_name", type=str, default="codecontest")
parser.add_argument("--split_name", type=str, default="valid")
parser.add_argument("--solution_file_name", type=str, default="solutions.json")
parser.add_argument("--id_range", default=None, nargs="+", type=int)
parser.add_argument('--id_list', default=None, type=str)
parser.add_argument('--dir_path', default=None, type=str)
parser.add_argument('--method', default='pair_programming')

if __name__ == "__main__":
    args = parser.parse_args()
    if args.id_list:
        id_list = ast.literal_eval(args.id_list)
        print("Parsed ID list:", id_list)
    else:
        id_list = None
        print("No ID list provided.")
    
    if args.dir_path:
        print(f"current dir id: {args.dir_path}")
        dir_path = args.dir_path
    else:
        timestamp = datetime.datetime.now().strftime("%m-%d_%H-%M")
        dir_path = f"{args.method}-{timestamp}"
        print(f"auto dir id: {args.dir_path}")
    
    solve_dataset(dataset_name=args.dataset_name,
                  split_name=args.split_name,
                  solution_file_name=args.solution_file_name,
                  id_range=args.id_range,
                  id_list=id_list,
                  dir_path=dir_path,
                  method=args.method
                  )
