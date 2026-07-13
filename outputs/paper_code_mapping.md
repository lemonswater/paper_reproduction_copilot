# Paper-Code Mapping

## Point 4D Convolution

### Unresolved Questions
- 未找到任何代码文件或相关实现细节来定位该模块。
- 论文中描述的'参数化函数ζ'的具体实现形式未知。
- 是否使用了最远点采样（Farthest Point Sampling）以及其具体实现在哪里未知。
- 缺少关于池化方法（sum, max, average）和MLP增强细节的代码证据。

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|

## Transformer

### Unresolved Questions
- 论文中提到的 Transformer 与代码中的 'transformer_v1.py' 是否完全一致？是否存在其他版本或变体？
- 论文中提到的 '4D coordinate embedding' 在代码中具体如何实现？Transformer 的输入是否严格对应论文描述的 'embedded local features'？

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
| `modules/transformer_v1.py` | Transformer, Attention, FeedForward | high | 该文件定义了 Transformer 类，其 forward 方法接收点云坐标 (xyzs) 和特征 (features)，并通过自注意力机制处理整个视频序列，与论文模块描述的视频级自注意力机制高度一致。 |
| `models/sequence_classification.py` | P4Transformer | medium | 该文件中的 P4Transformer 模型类将 Transformer 模块作为其核心组件，并在 forward 方法中调用 Transformer 处理从点 4D 卷积中提取的嵌入特征，这与论文中 Transformer 模块的定位一致。 |

## Application Heads

### Unresolved Questions
- 没有找到明确的用于动作识别的独立分类头（max pooling + MLP）的实现，现有最大池化是PointNet++模块的一部分。
- 没有找到明确的用于语义分割的独立特征传播层实现，现有的插值函数是PointNet++工具的一部分。
- 论文中描述的MLP具体架构（层数、维度）在代码中未明确体现。
- 论文中描述的特征传播层的详细实现（如插值方法的具体使用）在代码中不清晰。

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
| `modules/pointnet2_modules.py` | PointnetSAModuleMSG, PointnetSAModule | medium | 该文件中的模块实现了最大池化（max pooling）和MLP，与论文中描述的用于动作识别的应用头部中的操作一致。此外，文件中提到了'learnable feature propagation layer'，这可能对应于语义分割中的特征传播层。 |
| `modules/pytorch_utils.py` | SharedMLP | medium | 该文件定义了SharedMLP类，是构建MLP的基础组件，可能用于动作识别头部中的MLP部分。 |
| `modules/pointnet2_utils.py` | ThreeInterpolate, three_nn | medium | 该文件中的ThreeInterpolate函数实现了加权线性插值，可能用于语义分割中恢复子采样点的特征传播。 |
| `modules/pointnet2_test.py` | test_interpolation_grad | low | 该文件测试了插值操作的梯度，表明项目中有插值功能的实现，可能与特征传播相关。 |
