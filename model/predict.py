import argparse
import copy
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFile
from torchvision import models, transforms

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

DANGER_LABELS = ["very_safe", "mostly_safe", "unsafe", "high_risk"]
TYPE_LABELS = ["virtual", "real", "text"]
INPUT_SIZE = (224, 224)
OUT_FEATURES = 7
CROP_RATIO = 2.5
BEST_RATIO = 1.78


def predict(image_path, model_path):
    image_path = Path(image_path)
    model_path = Path(model_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    transform = transforms.Compose(
        [
            transforms.Resize(INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.resnet101()
    in_features = model.fc.in_features
    model.fc = torch.nn.Linear(in_features, OUT_FEATURES)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)

    img = Image.open(image_path).convert("RGB")
    size = img.size[0:2]
    short_side = np.argmin(size)
    long_side = np.argmax(size)
    ratio = size[long_side] / size[short_side]

    if ratio > CROP_RATIO:
        length = np.min(size) * BEST_RATIO
        new_size = list(copy.copy(size))
        new_size[long_side] = length
        img = img.crop((0, 0, new_size[0], new_size[1]))

    img = transform(img).unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad():
        output = model(img)
        _, danger_pred = torch.max(output[:, :4], 1)
        _, type_pred = torch.max(output[:, -3:], 1)

    result = {
        "danger": DANGER_LABELS[danger_pred.item()],
        "type": TYPE_LABELS[type_pred.item()],
    }
    print("Prediction result:")
    print(f"Danger level: {result['danger']}")
    print(f"Content type: {result['type']}")
    return result


def build_parser():
    parser = argparse.ArgumentParser(description="Single image inference script")
    parser.add_argument("--image", required=True, help="Path to an input image")
    parser.add_argument("--model", required=True, help="Path to model weights")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    predict(args.image, args.model)
