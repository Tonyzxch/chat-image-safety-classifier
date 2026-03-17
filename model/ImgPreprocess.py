import argparse
import copy
import os
import sys
import warnings

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

os.environ["OMP_NUM_THREADS"] = "1"

from PIL import Image, ImageFile
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


class ImgPreprocess:
    def __init__(self, input_dir):
        self.extensions = ["jpg", "png", "bmp", "jpeg"]
        self.input_dir = input_dir

    def _get_current_images(self, path):
        files = os.listdir(path)
        return [f for f in files if f.split(".")[-1].lower() in self.extensions]

    def _process_images(self, read_path, write_path, extension, show):
        img_names = self._get_current_images(read_path)
        if show and img_names:
            img_names = tqdm(img_names, file=sys.stdout)
            img_names.set_description(f"Current directory: {os.path.abspath(read_path)}")

        for img_name in img_names:
            img_read_path = os.path.join(read_path, img_name)
            img_write_name = img_name.split(".")[0] + "." + extension
            img_write_path = os.path.join(write_path, img_write_name)

            img = Image.open(img_read_path).convert("RGB")
            size = img.size[0:2]
            short_side = np.argmin(size)
            long_side = np.argmax(size)
            ratio = size[long_side] / size[short_side]

            if ratio > 1.78:
                length = np.min(size) * 1.78
                new_size = list(copy.copy(size))
                new_size[long_side] = length
                img = img.crop((0, 0, new_size[0], new_size[1]))

            img = img.resize((224, 224))
            img.save(img_write_path, type="jpeg")

    def _collect_ratios_and_sizes(self, show):
        ratios = {}
        sizes = []
        for root, _, _ in os.walk(self.input_dir):
            img_names = self._get_current_images(root)
            if show and img_names:
                img_names = tqdm(img_names, file=sys.stdout)
                img_names.set_description(f"Current directory: {os.path.abspath(root)}")

            for img_name in img_names:
                img = Image.open(os.path.join(root, img_name))
                size = img.size[0:2]
                sizes.append(size)
                ratio = np.max(size) / np.min(size)
                ratios[ratio] = ratios.get(ratio, 0) + 1

        ratios = np.array(sorted(ratios.items(), key=lambda item: item[0]))
        sizes = np.array([[max(w, h), min(w, h)] for w, h in sizes])
        return ratios, sizes

    def imgs_verify(self, auto_delete=False, show=True):
        damaged_count = 0
        deleted_count = 0

        for root, _, _ in os.walk(self.input_dir):
            img_names = self._get_current_images(root)
            if show and img_names:
                img_names = tqdm(img_names, file=sys.stdout)
                img_names.set_description(f"Current directory: {os.path.abspath(root)}")

            for img_name in img_names:
                img_read_path = os.path.join(root, img_name)
                warnings.filterwarnings("error", category=UserWarning)
                try:
                    img = Image.open(img_read_path).convert("RGB")
                    img.verify()
                except (UserWarning, SyntaxError):
                    print(f"Damaged image detected: {img_read_path}")
                    damaged_count += 1
                    if auto_delete:
                        os.remove(img_read_path)
                        deleted_count += 1

        if show:
            print(f"Damaged images: {damaged_count}, deleted images: {deleted_count}")
        print("Image verification finished")

    def imgs_unify(self, output_dir, extension="jpg", show=True):
        os.makedirs(output_dir, exist_ok=True)

        if show:
            print(f"Processed images will be stored in: {os.path.abspath(output_dir)}")

        for root, _, _ in os.walk(self.input_dir):
            save_path = root.replace(self.input_dir, output_dir)
            os.makedirs(save_path, exist_ok=True)
            self._process_images(root, save_path, extension, show)

        print("Image resizing finished")

    def imgs_count(self, show=True):
        ratios, sizes = self._collect_ratios_and_sizes(show)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            max_idx = np.argmax(ratios[:, 1])

            plt.figure(figsize=(6, 8))
            plt.subplot(211)
            for idx in range(len(ratios)):
                ratio = ratios[idx][0]
                times = ratios[idx][1]
                if idx == max_idx:
                    plt.text(ratio, 400, "peak ratio={:.2f}, count={}".format(ratio, int(times)))
                plt.vlines(ratio, 0, times, linewidth=1)
            plt.xlim((0.95, 4))
            plt.ylim((0, 500))
            plt.xlabel("ratio")
            plt.ylabel("count")

            plt.subplot(212)
            plt.scatter(sizes[:, 0], sizes[:, 1], s=2)
            plt.xlim((0, 6000))
            plt.ylim((0, 6000))
            plt.xlabel("long side")
            plt.ylabel("short side")
            plt.show()

        print("Image statistics finished")

    def img_classify(self, show=True, n_clusters=2, eps=0.2, min_samples=5):
        _, sizes = self._collect_ratios_and_sizes(show)
        scaler = StandardScaler()
        std_sizes = scaler.fit_transform(sizes)

        kmeans_clf = KMeans(n_clusters=n_clusters, random_state=42)
        kmeans_clf.fit(std_sizes)
        centers = scaler.inverse_transform(kmeans_clf.cluster_centers_)

        dbscan_clf = DBSCAN(eps=eps, min_samples=min_samples)
        dbscan_clf.fit(std_sizes)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            plt.figure(figsize=(6, 15))
            plt.subplot(311)
            plt.scatter(sizes[:, 0], sizes[:, 1], s=2)
            plt.xlim((0, 6000))
            plt.ylim((0, 6000))
            plt.title("origin")
            plt.xlabel("long side")
            plt.ylabel("short side")

            plt.subplot(312)
            plt.scatter(sizes[:, 0], sizes[:, 1], s=2, c=kmeans_clf.labels_, cmap=plt.cm.Paired)
            plt.xlim((0, 6000))
            plt.ylim((0, 6000))
            plt.scatter(centers[:, 0], centers[:, 1], marker="*", s=60)
            for idx in range(len(centers)):
                plt.annotate(
                    "({}, {})".format(int(centers[idx, 0]), int(centers[idx, 1])),
                    (centers[idx, 0], centers[idx, 1]),
                )
            plt.title("k-means")
            plt.xlabel("long side")
            plt.ylabel("short side")

            plt.subplot(313)
            plt.scatter(sizes[:, 0], sizes[:, 1], s=2, c=dbscan_clf.labels_, cmap=plt.cm.Paired)
            plt.xlim((0, 6000))
            plt.ylim((0, 6000))
            plt.title("dbscan")
            plt.xlabel("long side")
            plt.ylabel("short side")
            plt.show()


def build_parser():
    parser = argparse.ArgumentParser(description="Image preprocessing utility")
    parser.add_argument("--input-dir", required=True, help="Input image directory")
    parser.add_argument("--output-dir", help="Output directory for processed images")
    parser.add_argument(
        "--action",
        choices=["verify", "unify", "count", "classify"],
        default="unify",
        help="Preprocessing action",
    )
    parser.add_argument("--auto-delete", action="store_true", help="Delete damaged images automatically")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    preprocess = ImgPreprocess(args.input_dir)

    if args.action == "verify":
        preprocess.imgs_verify(auto_delete=args.auto_delete)
    elif args.action == "unify":
        if not args.output_dir:
            raise ValueError("--output-dir is required when action is unify")
        preprocess.imgs_unify(args.output_dir)
    elif args.action == "count":
        preprocess.imgs_count()
    elif args.action == "classify":
        preprocess.img_classify()
