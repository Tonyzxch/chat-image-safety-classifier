import os
import time
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, ImageFile
import torch
from torchvision import models, transforms

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


DANGER_LABELS = ["非常安全", "比较安全", "不太安全", "很不安全"]
TYPE_LABELS = ["虚拟", "现实", "文本"]
INPUT_SIZE = (224, 224)
OUT_FEATURES = 7


class Predictor:
    def __init__(self, model_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = transforms.Compose(
            [
                transforms.Resize(INPUT_SIZE),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
        self.model = models.resnet101()
        in_features = self.model.fc.in_features
        self.model.fc = torch.nn.Linear(in_features, OUT_FEATURES)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def predict(self, image_path: str):
        img = Image.open(image_path).convert("RGB")
        tensor = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            output = self.model(tensor)
            _, danger_idx = torch.max(output[:, :4], 1)
            _, type_idx = torch.max(output[:, -3:], 1)
        return {
            "danger": DANGER_LABELS[danger_idx.item()],
            "type": TYPE_LABELS[type_idx.item()],
        }


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    model_path = os.getenv("MODEL_PATH", "")
    predictor = Predictor(model_path) if model_path and Path(model_path).exists() else None

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "model_loaded": predictor is not None})

    @app.post("/predict")
    def predict_image():
        if predictor is None:
            return jsonify({"error": "未配置可用的模型文件"}), 503

        image = request.files.get("file")
        if image is None:
            return jsonify({"error": "缺少上传文件"}), 400

        ext = Path(image.filename or "upload.jpg").suffix or ".jpg"
        filename = f"{int(time.time() * 1000)}{ext}"
        file_path = upload_dir / filename
        image.save(file_path)

        result = predictor.predict(str(file_path))
        return jsonify({"filename": filename, **result})

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port)
