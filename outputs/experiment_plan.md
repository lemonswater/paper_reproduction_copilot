# Experiment Plan

Goal: 复现论文《Point 4D Transformer Networks for Spatio-Temporal Modeling in Point Cloud Videos》的主要实验结果，包括在MSR-Action3D、NTU RGB+D 60、NTU RGB+D 120和Synthia 4D数据集上的3D动作识别和4D语义分割任务性能。

## Environment

### 1. 克隆代码仓库

- Action: 使用git克隆P4Transformer代码仓库到本地目录。
- Source: readme
- Risk: low

### 2. 创建Python环境并安装依赖

- Action: 创建一个Python 3.8的conda环境，并安装PyTorch、CUDA工具包以及其他依赖项。
- Source: readme
- Risk: high

### 3. 编译PointNet2扩展模块

- Action: 进入modules目录，编译并安装pointnet2库的自定义CUDA扩展。
- Source: readme
- Risk: high

## Data

### 1. 下载数据集

- Action: 下载论文中提到的四个数据集（MSR-Action3D，NTU RGB+D 60，NTU RGB+D 120，Synthia 4D）的原始数据。
- Source: need_confirm
- Risk: medium

### 2. 数据预处理

- Action: 运行数据预处理脚本，将原始数据转换为模型训练所需的格式（例如，提取点云序列、生成标签文件等）。
- Source: script
- Risk: medium

## Train

### 1. MSR-Action3D动作识别训练

- Action: 使用train-msr-small.py脚本在MSR-Action3D数据集上训练P4Transformer模型进行3D动作识别。
- Source: script
- Risk: high

### 2. NTU RGB+D 60动作识别训练

- Action: 使用train-ntu60.py脚本在NTU RGB+D 60数据集上训练P4Transformer模型进行3D动作识别。
- Source: script
- Risk: high

### 3. NTU RGB+D 120动作识别训练

- Action: 参考train-ntu60.py脚本，为NTU RGB+D 120数据集准备和运行训练。具体配置需确认。
- Source: inferred
- Risk: high

### 4. Synthia 4D语义分割训练

- Action: 准备并运行Synthia 4D数据集上的4D语义分割训练。目前代码库中未找到明确的分割训练脚本，需确认或自行实现。
- Source: need_confirm
- Risk: high

## Eval

### 1. 动作识别模型评估

- Action: 使用训练好的模型检查点，在MSR-Action3D、NTU RGB+D 60和NTU RGB+D 120测试集上评估动作识别准确率。
- Source: inferred
- Risk: medium

### 2. 语义分割模型评估

- Action: 使用训练好的模型检查点，在Synthia 4D测试集上评估4D语义分割性能（如mIoU）。
- Source: need_confirm
- Risk: medium

## Run Commands

```bash
git clone https://github.com/Zhang-VISLab/P4Transformer.git
```
- cwd: `/data/tianshaoqi24`
- source: need_confirm
- risk: low
- reason: 克隆代码仓库，命令假设来自README，实际命令需确认

```bash
cd /data/tianshaoqi24/P4Transformer/modules && python setup.py install
```
- cwd: `/data/tianshaoqi24/P4Transformer/modules`
- source: inferred
- risk: high
- reason: 编译并安装PointNet2自定义CUDA扩展，这是训练和评估的前提

```bash
cd /data/tianshaoqi24/P4Transformer && python train-msr-small.py
```
- cwd: `/data/tianshaoqi24/P4Transformer`
- source: script
- risk: high
- reason: 运行MSR-Action3D数据集的训练脚本

```bash
cd /data/tianshaoqi24/P4Transformer && python train-ntu60.py
```
- cwd: `/data/tianshaoqi24/P4Transformer`
- source: script
- risk: high
- reason: 运行NTU RGB+D 60数据集的训练脚本

## Unresolved Questions

- 论文核心模块'Point 4D Convolution'的具体代码实现在仓库的哪个文件中？其参数化函数ζ如何实现？
- 训练P4Transformer模型所需的完整超参数配置（学习率、优化器、batch size、epoch、权重衰减等）是什么？
- 如何下载和准备MSR-Action3D，NTU RGB+D 60，NTU RGB+D 120，Synthia 4D这四个数据集？预处理流程的详细步骤是什么？
- NTU RGB+D 120数据集的训练脚本或配置应该如何准备？
- Synthia 4D数据集上进行4D语义分割任务的训练和评估脚本在哪里？
- 语义分割任务中，从子采样点恢复到原始点的'特征传播层'在代码中具体如何实现？
- 论文中提到的MLP（用于动作识别）和Transformer的具体架构细节（层数、维度、激活函数）在代码中如何体现？
- 评估动作识别和语义分割性能的具体指标（准确率、mIoU等）的计算脚本或方法是什么？