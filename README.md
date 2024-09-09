# PairCoder
A Pair Programming Framework for Code Generation via Multi-Plan Exploration and Feedback-Driven Refinement 

## Prepare Environment

PairCoder is developed on Ubuntu 16.04 LTS. 
Please follow these steps to set up the Python environment:

```
conda create -n PairCoder python=3.10
conda activate PairCoder
pip install -r requirements.txt
```

Please set your API KEY in `settings/configuration.toml`.
There are also other configurable options to control the behavior of our PairCoder.

## Code Generation

Use the following command to perform code generation:

```
python src/solve_dataset.py \
    --dataset_name mbpp \ 
    --split_name test \
    --dir_path results
```

For the given `$split_name` of the `$dataset_name`, the logs and the final `solutions.json` are stored in `$dir_path`. You can set `$id_list` for ids to solve.

## Reference

If you find the code helpful, please cite our paper:
```
@inproceedings{zhang2024paircoder,
  title     = { A Pair Programming Framework for Code Generation via
                Multi-Plan Exploration and Feedback-Driven Refinement },
  author    = { Zhang, Huan and Cheng, Wei and Wu, Yuhan and Hu, Wei },
  booktitle = { ASE },
  year      = { 2024 }
}
```
