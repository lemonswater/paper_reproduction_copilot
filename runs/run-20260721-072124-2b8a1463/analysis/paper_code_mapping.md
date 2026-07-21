# Paper-Code Mapping

## Point 4D Convolution

### Unresolved Questions
- 论文描述中提到'parameterized function to generate kernels based on input 4D displacements and point features'，代码中通过conv_d处理4D位移（displacement），conv_f处理特征（feature），然后通过加法或乘法结合，这符合描述，但kernel生成是否完全参数化需要进一步确认。

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
| `modules/point_4d_convolution.py` | P4DConv | high | 该文件实现了P4DConv类，其forward方法直接处理点云视频的时空局部区域，使用FPS进行空间采样，并具有temporal_stride参数，与论文模块描述高度一致。 |

## Transformer

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
| `modules/transformer_v1.py` | Transformer, Attention, FeedForward | high | 该文件直接定义了Transformer类及其核心组件（Attention、FeedForward），其forward逻辑对嵌入的时空局部特征执行自注意力，与论文模块描述的视频级自注意力机制一致。 |
| `models/sequence_classification.py` | P4Transformer | medium | 该文件定义了P4Transformer模型，其中明确包含一个Transformer模块（self.transformer），用于处理嵌入的时空特征，是论文中Transformer模块的主要调用方。 |

## 4D Coordinate and Local Feature Embedding

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
| `modules/point_4d_convolution.py` | P4DConv | high | 该文件中的P4DConv类实现了4D卷积操作，处理时空锚点坐标和局部特征，并通过线性层（卷积层）进行融合，这与论文模块描述的组合4D坐标和局部特征以形成输入表示的功能高度一致。 |

## Feature Propagation for Segmentation

### Unresolved Questions
- 当前搜索结果和代码片段中没有发现任何与特征传播、点插值、上采样或语义分割MLP相关的代码实现，无法定位对应文件。

| Candidate File | Symbols | Confidence | Reason |
|---|---|---|---|
