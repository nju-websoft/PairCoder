# PairCoder
A Pair Programming Framework for Code Generation via Multi-Plan Exploration and Feedback-Driven Refinement 

## Overview
In this paper, we draw on pair programming practices to propose **PairCoder**, a novel LLM-based framework for code generation. PairCoder incorporates two collaborative LLM agents, namely a *Navigator* agent for high-level planning and a *Driver* agent for specific implementation. 

The *Navigator* is responsible for proposing promising solution plans, selecting the current optimal plan, and directing the next iteration round based on execution feedback. 
The *Driver* follows the guidance of *Navigator* to undertake initial code generation, code testing, and refinement. This interleaved and iterative workflow involves multi-plan exploration and feedback-based refinement, which mimics the collaboration of pair programmers.
![model](assets/method_flow.gif)
## Prepare Environment

PairCoder is developed on Ubuntu 16.04 LTS. 
Please follow these steps to set up the Python environment:

```
conda create -n PairCoder python=3.10
conda activate PairCoder
pip install -r requirements.txt
```

Please set your API KEY in `settings/configuration.toml`.
This file also contains numerous other configurable options that allow you to fine-tune and precisely control the behavior of PairCoder.

## Quick Start

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
