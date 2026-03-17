# Model

模型模块包含训练、测试、单图预测和图片预处理脚本。

## 包含内容

- `TorchModel.py`：训练、统计与预测入口
- `predict.py`：独立单图预测脚本
- `ImgPreprocess.py`：图片预处理工具
- `config.example.ini`：配置文件示例

## 配置说明

使用前请先复制配置文件：

```bash
copy config.example.ini config.ini
```

然后根据本地环境填写：

- 数据集路径
- 数据库连接信息
- 预训练权重路径
- 模型保存路径

## 常用命令

### 训练模型

```bash
python TorchModel.py --mode train --config config.ini
```

### 查看数据分布

```bash
python TorchModel.py --mode stats --config config.ini
```

### 单图预测

```bash
python TorchModel.py --mode predict --config config.ini --image 图片路径 --model 权重路径
```

或使用独立预测脚本：

```bash
python predict.py --image 图片路径 --model 权重路径
```

### 图片预处理

```bash
python ImgPreprocess.py --input-dir 原始目录 --output-dir 输出目录 --action unify
```

## 任务定义

- 风险等级：4 类
- 内容类型：3 类
- 总输出维度：7
