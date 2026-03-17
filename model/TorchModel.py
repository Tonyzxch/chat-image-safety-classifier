import argparse
import copy
import csv
import os
import random
import sys
from collections import Counter
from configparser import ConfigParser
from pathlib import Path

import numpy as np
import pymysql
import torch
from PIL import Image, ImageFile
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

DANGER_LABELS = ["very_safe", "mostly_safe", "unsafe", "high_risk"]
TYPE_LABELS = ["virtual", "real", "text"]


class ImgDataset(Dataset):
    def __init__(self, data_dir, is_test, config_path="config.ini"):
        self.data_dir = data_dir
        self.is_test = is_test
        self.config = ConfigParser()
        self.config.read(config_path, encoding="utf-8")

        dataset_config = dict(self.config.items("dataset"))
        self.input_size = eval(dataset_config["input_size"])
        self.crop_ratio = float(dataset_config["crop_ratio"])
        self.best_ratio = float(dataset_config["best_ratio"])

        meta_data = self._get_info()
        self.img_name = meta_data[:, 0]
        type_label = np.array(meta_data[:, -3:], dtype=float)
        self.type_label = np.argmax(type_label, axis=1).reshape(-1, 1)
        self.danger_label = np.array(meta_data[:, 1], dtype=float).reshape(-1, 1)
        self.label = np.hstack((self.danger_label, self.type_label))

        self.transform = transforms.Compose(
            [
                transforms.Resize(self.input_size),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.Pad(10),
                transforms.RandomCrop(self.input_size),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

        virtual_limit = 1200 if self.is_test else 4500
        keep_indices = []
        for idx in range(len(self.img_name)):
            if virtual_limit >= 0 and self.label[idx][1] == 0:
                virtual_limit -= 1
            else:
                keep_indices.append(idx)
        self.img_name = self.img_name[keep_indices]
        self.label = self.label[keep_indices]

    def __len__(self):
        return len(self.img_name)

    def __getitem__(self, idx):
        while True:
            img_path = os.path.join(self.data_dir, self.img_name[idx])
            if not os.path.exists(img_path):
                idx = random.randint(0, self.__len__() - 1)
            else:
                break

        img = Image.open(img_path).convert("RGB")
        size = img.size[0:2]
        short_side = np.argmin(size)
        long_side = np.argmax(size)
        ratio = size[long_side] / size[short_side]

        if ratio > self.crop_ratio:
            length = np.min(size) * self.best_ratio
            new_size = list(copy.copy(size))
            new_size[long_side] = length
            img = img.crop((0, 0, new_size[0], new_size[1]))

        return self.transform(img), self.label[idx]

    def _get_info(self):
        db_config = dict(self.config.items("database"))
        try:
            db = pymysql.connect(
                host=db_config["host"],
                user=db_config["user"],
                password=db_config["password"],
                db=db_config["db"],
            )
            print("Database connected")
            cursor = db.cursor()
            cursor.execute(
                "SELECT name,danger_level,is_virtual,is_real,is_text "
                "FROM picdata "
                "WHERE is_labled=1 AND is_other=0 AND is_test={}".format(int(self.is_test))
            )
            meta_data = cursor.fetchall()
            db.close()
            return np.array(meta_data)
        except pymysql.err.OperationalError as exc:
            raise RuntimeError("Database connection failed. Check config.ini.") from exc

    def count_labels(self):
        return Counter(self.label[:, 0]), Counter(self.label[:, 1])


class TrainModel:
    def __init__(self, config_path="config.ini"):
        self.config_path = config_path
        self.extensions = ["pt", "pth"]
        self.epoch_done = 0

        self.config = ConfigParser()
        self.config.read(self.config_path, encoding="utf-8")
        train_config = dict(self.config.items("train"))

        self.data_dir = train_config["data_dir"]
        self.epochs = int(train_config["epochs"])
        self.batch_size = int(train_config["batch_size"])
        self.pretrained_pth = train_config["pretrained_pth"]
        self.params_freeze = train_config["params_freeze"] == str(True)
        self.lr = float(train_config["lr"])
        self.momentum = float(train_config["momentum"])
        self.weight_decay = float(train_config["weight_decay"])
        self.model_save_dir = train_config["model_save_dir"]
        self.checkpoint_epoch = int(train_config["checkpoint_epoch"])
        self.history_pth = train_config["history_pth"]
        self.out_features = int(train_config["out_features"])

        os.makedirs(self.model_save_dir, exist_ok=True)
        history_dir = Path(self.history_pth).parent
        if str(history_dir) not in ("", "."):
            history_dir.mkdir(parents=True, exist_ok=True)

        self.train_dataset = ImgDataset(self.data_dir, is_test=False, config_path=self.config_path)
        self.test_dataset = ImgDataset(self.data_dir, is_test=True, config_path=self.config_path)
        self.train_dataloader = DataLoader(self.train_dataset, batch_size=self.batch_size, shuffle=True)
        self.test_dataloader = DataLoader(self.test_dataset, batch_size=self.batch_size, shuffle=True)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._init_model().to(self.device)
        self.optimizer = torch.optim.SGD(
            self.model.parameters(),
            lr=self.lr,
            momentum=self.momentum,
            weight_decay=self.weight_decay,
        )
        self.loss_func = torch.nn.CrossEntropyLoss().to(self.device)

    def _init_model(self):
        model = models.resnet101()
        in_features = model.fc.in_features
        model.fc = torch.nn.Linear(in_features, self.out_features)

        saved_models = [
            f for f in os.listdir(self.model_save_dir) if f.split(".")[-1].lower() in self.extensions
        ]
        saved_models = sorted(
            saved_models,
            key=lambda x: os.path.getmtime(os.path.join(self.model_save_dir, x)),
            reverse=True,
        )

        if not saved_models:
            print("First training run")
            if os.path.exists(self.pretrained_pth):
                model.load_state_dict(torch.load(self.pretrained_pth, map_location=self.device))
                print("Pretrained weights loaded")
                if self.params_freeze:
                    for param in model.parameters():
                        param.requires_grad = False

            with open(self.history_pth, "w", encoding="utf8", newline="") as log:
                csv.writer(log).writerow(
                    ["epoch", "train_loss", "train_danger_acc", "train_type_acc", "test_danger_acc", "test_type_acc"]
                )
        else:
            load_model_name = saved_models[0]
            model.load_state_dict(
                torch.load(os.path.join(self.model_save_dir, load_model_name), map_location=self.device)
            )
            self.epoch_done = int(load_model_name.split(".")[0].split("_")[-1])
            print(f"Loaded latest checkpoint: {load_model_name}")

        return model

    def train(self, show=True):
        checkpoint_cnt = 0

        for epoch in range(self.epochs):
            self.model.train()
            total_loss = 0.0
            danger_corrects = 0
            type_corrects = 0
            cur_epoch = self.epoch_done + epoch + 1
            data_num = len(self.train_dataset)

            train_dataloader = self.train_dataloader
            if show:
                train_dataloader = tqdm(train_dataloader, file=sys.stdout)
                train_dataloader.set_description(f"Epoch {cur_epoch}")

            for images, labels in train_dataloader:
                images = images.to(self.device)
                labels = labels.to(self.device)

                outputs = self.model(images)
                danger_labels = labels[:, 0]
                type_labels = labels[:, 1]
                danger_outputs = outputs[:, :4]
                type_outputs = outputs[:, -3:]

                danger_loss = self.loss_func(danger_outputs, danger_labels.long())
                type_loss = self.loss_func(type_outputs, type_labels.long())
                loss = danger_loss + type_loss

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                _, danger_predicts = torch.max(danger_outputs, 1)
                _, type_predicts = torch.max(type_outputs, 1)
                danger_corrects += (danger_predicts == danger_labels.long()).sum().item()
                type_corrects += (type_predicts == type_labels.long()).sum().item()
                total_loss += loss.item() * images.size(0)

                if show:
                    train_dataloader.set_postfix(batch_size=self.batch_size, loss=loss.item())

            train_loss = total_loss / data_num
            train_danger_acc = danger_corrects / data_num
            train_type_acc = type_corrects / data_num
            test_danger_acc, test_type_acc = self.test(show=show)

            print(
                "Epoch: {}, Train Loss: {:.2f}, Train Danger Acc: {:.2%}, Train Type Acc: {:.2%}, "
                "Test Danger Acc: {:.2%}, Test Type Acc: {:.2%}".format(
                    cur_epoch,
                    train_loss,
                    train_danger_acc,
                    train_type_acc,
                    test_danger_acc,
                    test_type_acc,
                )
            )

            with open(self.history_pth, "a", encoding="utf8", newline="") as log:
                csv.writer(log).writerow(
                    [cur_epoch, train_loss, train_danger_acc, train_type_acc, test_danger_acc, test_type_acc]
                )

            checkpoint_cnt += 1
            if checkpoint_cnt == self.checkpoint_epoch:
                checkpoint_cnt = 0
                save_path = os.path.join(self.model_save_dir, f"epoch_{cur_epoch}.pth")
                torch.save(self.model.state_dict(), save_path)
                print(f"Checkpoint saved: {save_path}")

    def test(self, show=True):
        self.model.eval()
        danger_corrects = 0
        type_corrects = 0
        data_num = len(self.test_dataset)

        test_dataloader = self.test_dataloader
        if show:
            test_dataloader = tqdm(test_dataloader, file=sys.stdout)
            test_dataloader.set_description("Testing")
            test_dataloader.set_postfix(batch_size=self.batch_size)

        for images, labels in test_dataloader:
            images = images.to(self.device)
            labels = labels.to(self.device)

            with torch.no_grad():
                outputs = self.model(images)

            danger_labels = labels[:, 0]
            type_labels = labels[:, 1]
            danger_outputs = outputs[:, :4]
            type_outputs = outputs[:, -3:]

            _, danger_predicts = torch.max(danger_outputs, 1)
            _, type_predicts = torch.max(type_outputs, 1)
            danger_corrects += (danger_predicts == danger_labels.long()).sum().item()
            type_corrects += (type_predicts == type_labels.long()).sum().item()

        return danger_corrects / data_num, type_corrects / data_num

    def dataset_count(self):
        train_danger_cnt, train_type_cnt = self.train_dataset.count_labels()
        test_danger_cnt, test_type_cnt = self.test_dataset.count_labels()
        print("Train danger distribution =", train_danger_cnt)
        print("Train type distribution =", train_type_cnt)
        print("Test danger distribution =", test_danger_cnt)
        print("Test type distribution =", test_type_cnt)


def predict(image_path, model_path, config_path="config.ini"):
    config = ConfigParser()
    config.read(config_path, encoding="utf-8")
    predict_config = dict(config.items("predict"))
    input_size = eval(predict_config["input_size"])
    out_features = int(predict_config["out_features"])

    transform = transforms.Compose(
        [
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.resnet101()
    in_features = model.fc.in_features
    model.fc = torch.nn.Linear(in_features, out_features)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)

    img = Image.open(image_path).convert("RGB")
    img = transform(img).unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad():
        output = model(img)
        _, danger_pred = torch.max(output[:, :4], 1)
        _, type_pred = torch.max(output[:, -3:], 1)

    print("Prediction result:")
    print("Danger level -> {}".format(DANGER_LABELS[danger_pred.item()]))
    print("Content type -> {}".format(TYPE_LABELS[type_pred.item()]))


def build_parser():
    parser = argparse.ArgumentParser(description="Training and inference entry point")
    parser.add_argument("--mode", choices=["train", "stats", "predict"], default="train", help="Execution mode")
    parser.add_argument("--config", default="config.ini", help="Config file path")
    parser.add_argument("--image", help="Input image path for predict mode")
    parser.add_argument("--model", help="Checkpoint path for predict mode")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()

    if args.mode == "predict":
        if not args.image or not args.model:
            raise ValueError("predict mode requires both --image and --model")
        predict(args.image, args.model, config_path=args.config)
    else:
        runner = TrainModel(config_path=args.config)
        if args.mode == "train":
            runner.train()
        elif args.mode == "stats":
            runner.dataset_count()
