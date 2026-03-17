# Backend

后端模块用于提供图片推理接口，并保留了部分原始服务代码作为参考。

## 包含内容

- `app.py`：当前使用的 Flask 推理接口
- `predict_api_legacy.py`：原始预测服务代码
- `label_service_legacy.py`：原始标注后端代码
- `bot_legacy.py`：原始消息推送脚本

## 运行方式

```bash
pip install -r requirements.txt
set MODEL_PATH=权重文件路径
python app.py
```

## 接口说明

### `GET /health`

返回服务状态和模型加载状态。

### `POST /predict`

上传图片并返回预测结果。

返回字段示例：

```json
{
  "filename": "1710000000000.jpg",
  "danger": "比较安全",
  "type": "虚拟"
}
```

## 说明

- `app.py` 是推荐使用的入口
- `legacy` 文件保留用于展示原始项目结构，不建议直接用于生产环境
