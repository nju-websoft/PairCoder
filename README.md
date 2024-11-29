# PairCoder 🤖💻

**This paper has been accepted by ASE 2024 and awarded the 🏆 ACM SIGSOFT Distinguished Paper Award.**
<p align="center">
    <a href="https://arxiv.org/abs/2409.05001"><img src="https://img.shields.io/badge/arXiv-2409.05001-b31b1b.svg"></a>
    <a href="https://conf.researchr.org/home/ase-2024"><img src="https://img.shields.io/badge/ASE-2024-blue.svg"></a>
    <a href="https://conf.researchr.org/info/ase-2024/awards"><img src="https://img.shields.io/badge/-ACM%20SIGSOFT%20Distinguished%20Paper%20%F0%9F%8F%86-brightgreen"></a>
</p>

<p align="center">
  <a href="#overview">📖Overview</a> •
  <a href="#prepare-environment">🧪Environment</a> •
  <a href="#dataset-setup">📂Dataset Setup</a> •
  <a href="#quick-start">🚀Quick Start</a> •
  <a href="#citation">📝Citation</a>
</p>


## 📖Overview

In this paper, we draw on pair programming practices to propose **PairCoder**, a novel LLM-based framework for code generation. PairCoder incorporates two collaborative LLM agents, namely a *Navigator* agent for high-level planning and a *Driver* agent for specific implementation. 

The *Navigator* is responsible for proposing promising solution plans, selecting the current optimal plan, and directing the next iteration round based on execution feedback. 
The *Driver* follows the guidance of *Navigator* to undertake initial code generation, code testing, and refinement. This interleaved and iterative workflow involves multi-plan exploration and feedback-based refinement, which mimics the collaboration of pair programmers.

![model](assets/method_flow.gif)

## 🧪Prepare Environment

PairCoder is developed on Ubuntu 16.04 LTS. 
Please follow these steps to set up the Python environment:

```bash
conda create -n PairCoder python=3.10
conda activate PairCoder
pip install -r requirements.txt
```

Please set your API KEY in `settings/configuration.toml`.
This file also contains numerous other configurable options that allow you to fine-tune and precisely control the behavior of PairCoder.

## 📂Dataset Setup

1. Download the dataset file from [releases](<https://github.com/nju-websoft/PairCoder/releases/tag/v0.1.0>).  
2. Unzip the file and place the `dataset` directory in the project root:  

   ```
   PairCoder/
   ├─assets
   ├─dataset
   ├─src
   ```

The dataset is required for running the experiments. Ensure that the directory structure matches the project requirements.

## 🚀Quick Start

Use the following command to perform code generation:

```bash
python src/solve_dataset.py \
    --dataset_name mbpp \
    --split_name test \
    --dir_path results
```

For the given `split_name` of the `dataset_name`, the logs and the final `solutions.json` are stored in `dir_path`. You can set `id_list` for ids to solve.

## 📝Citation

If you find the code helpful, please cite our paper:

```bibtex
@inproceedings{zhang2024paircoder,
  title     = {A Pair Programming Framework for Code Generation via
                Multi-Plan Exploration and Feedback-Driven Refinement},
  author    = {Zhang, Huan and Cheng, Wei and Wu, Yuhan and Hu, Wei},
  booktitle = {The 39th IEEE/ACM International Conference on Automated Software Engineering (ASE 2024)},
  year      = {2024}
}
```
