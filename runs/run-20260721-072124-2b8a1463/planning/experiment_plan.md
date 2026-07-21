# Experiment Plan

Goal: 复现P4Transformer论文的主要实验结果，包括在MSR-Action3D、NTU RGB+D 60、NTU RGB+D 120和Synthia 4D数据集上的动作识别和4D语义分割任务。

## Environment

### 1. 设置Python环境并安装依赖

- Action: 创建一个Python 3.8环境，并根据README.md安装必要的依赖包，包括PyTorch、CUDA工具包以及编译仓库中的C++扩展（pointnet2模块）。
- Source: readme
- Risk: high

## Data

### 1. 下载和预处理MSR-Action3D数据集

- Action: 根据仓库中的数据集处理脚本（datasets/msr.py, datasets/preprocess_file.py），下载MSR-Action3D数据集并进行必要的预处理，生成模型所需的输入格式。
- Source: inferred
- Risk: high

### 2. 下载和预处理NTU RGB+D 60/120数据集

- Action: 根据仓库中的数据集处理脚本（datasets/ntu60.py），下载NTU RGB+D 60和120数据集并进行必要的预处理。
- Source: inferred
- Risk: high

### 3. 下载和预处理Synthia 4D数据集

- Action: 获取Synthia 4D数据集并进行预处理，以用于4D语义分割任务。
- Source: inferred
- Risk: high

## Train

### 1. 在MSR-Action3D上训练动作识别模型

- Action: 使用训练脚本train-msr-small.py，在MSR-Action3D数据集上训练P4Transformer模型进行动作识别任务。
- Source: readme
- Risk: medium

### 2. 在NTU RGB+D 60上训练动作识别模型

- Action: 使用训练脚本train-ntu60.py，在NTU RGB+D 60数据集上训练P4Transformer模型进行动作识别任务。
- Source: readme
- Risk: medium

## Eval

### 1. 在测试集上评估动作识别模型

- Action: 使用训练好的模型在MSR-Action3D和NTU RGB+D 60/120数据集的测试集上评估动作识别的准确率。
- Source: inferred
- Risk: low

## Run Commands

```bash
python train-msr-small.py
```
- cwd: `/data/tianshaoqi24/P4Transformer`
- source: inferred
- risk: medium
- reason: 基于训练脚本文件名推断的训练命令。具体参数（如数据集路径、超参数）需要从脚本内部或配置中确认。

```bash
python train-ntu60.py
```
- cwd: `/data/tianshaoqi24/P4Transformer`
- source: inferred
- risk: medium
- reason: 基于训练脚本文件名推断的训练命令。具体参数（如数据集路径、超参数）需要从脚本内部或配置中确认。

## Unresolved Questions

- 训练脚本train-msr-small.py和train-ntu60.py的具体命令行参数是什么？（例如数据路径、batch size、学习率、GPU设置）
- README.md中关于环境设置和数据准备的完整、确切步骤是什么？
- 用于4D语义分割任务（在Synthia 4D数据集上）的训练和评估代码在哪里？仓库地图中未找到相关脚本。
- 数据集MSR-Action3D、NTU RGB+D和Synthia 4D的官方下载链接或仓库内具体的下载/预处理脚本是什么？
- 模型训练中使用的优化器、学习率调度策略和总训练轮数的具体设置是什么？
- 代码仓库中是否包含预训练模型checkpoint？如果有，其路径是什么？