"""
Module to handle yolov8 converter
"""

import random
import shutil
from pathlib import Path
from typing import Union

import yaml

from .converter import Converter
from .custom_errors import InvalidDirectoryStructureError


class YoloToYolov8Converter(Converter):
    def convert(
        self,
        source_dir: Path,
        dest_dir: Union[None, Path] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
    ) -> None:
        work_dir = dest_dir if dest_dir else source_dir
        self._validate_yolo_dir_structure(source_dir=source_dir)
        self._create_directory_structure(source_dir=source_dir, dest_dir=work_dir, overwrite=True)
        self._split_datasets(
            source_dir=source_dir, dest_dir=dest_dir, train_ratio=train_ratio, val_ratio=val_ratio
        )
        class_file = self._find_text_file(source_dir=source_dir)
        self._create_data_yaml(dest_dir=work_dir, class_file=class_file)

    @staticmethod
    def _validate_yolo_dir_structure(source_dir: Path) -> bool:
        required_paths = {
            "images": source_dir / "images",
            "labels": source_dir / "labels",
            "classes.txt": source_dir / "classes.txt",
        }
        if not source_dir.is_dir():
            raise InvalidDirectoryStructureError("Missing source dir")
        for path in required_paths.values():
            if not path.exists():
                raise InvalidDirectoryStructureError(
                    "Input data must conform to the YOLO export format "
                    "(/images, /labels, classes.txt, notes.json)"
                )

    @staticmethod
    def _create_directory_structure(
        source_dir: Path, dest_dir: Union[Path, None], overwrite: bool = True
    ) -> None:
        work_dir = dest_dir if dest_dir else source_dir
        categories = ["images", "labels"]
        dir_structure = {"train": categories, "test": categories, "valid": categories}
        for cat, folders in dir_structure.items():
            for folder in folders:
                path = work_dir / cat / folder
                if not overwrite:
                    if path.exists():
                        raise FileExistsError("Path already exists! Delete it and retry.")
                else:
                    if path.exists():
                        shutil.rmtree(path)

                    path.mkdir(parents=True, exist_ok=True)

    # Logic to create the directory structure for YOLOv8
    @staticmethod
    def _split_datasets(
        source_dir: Path, dest_dir: Union[Path, None], train_ratio: float, val_ratio: float
    ) -> None:
        input_img_dir = source_dir / "images"
        output_img_dir = source_dir / "labels"

        if not any((input_img_dir.exists(), output_img_dir.exists())):
            raise FileNotFoundError(f"Yolo specific folder not found: {input_img_dir}")

        images = [image for image in input_img_dir.iterdir()]
        labels = [label for label in output_img_dir.iterdir()]

        if any((len(images) == 0, len(labels) == 0)):
            raise FileNotFoundError(
                f"No images or labels found in the source directory: {source_dir}"
            )

        random.shuffle(images)

        train_nr = int(int(len(images)) * train_ratio)
        valid_nr = train_nr + int(int(len(images)) * val_ratio)

        for i, img in enumerate(images):
            image_name = images[i].name
            label_name = images[i].name.replace(img.suffix, ".txt")
            label = source_dir / "labels" / label_name
            if not label.exists():
                raise FileNotFoundError(f"Corresponding label nod found for img: {image_name}")

            if i < train_nr:
                subset = "train"
            elif i < valid_nr:
                subset = "valid"
            else:
                subset = "test"
            shutil.copy(str(img), str(dest_dir / subset / "images" / image_name))
            shutil.copy(str(label), str(dest_dir / subset / "labels" / label_name))

    @staticmethod
    def _create_data_yaml(dest_dir: Path, class_file: Path):
        with class_file.open() as f:
            classes = [line.strip() for line in f.readlines()]

        data = {
            "names": classes,
            "nc": len(classes),
            "train": str(dest_dir / "train" / "images"),
            "val": str(dest_dir / "valid" / "images"),
            "test": str(dest_dir / "test" / "images"),
        }

        with open(dest_dir / "data.yaml", "w") as f:
            yaml.dump(data, f)

    @staticmethod
    def _find_text_file(source_dir: Path):
        try:
            classes_file = [file for file in source_dir.iterdir() if file.name == "classes.txt"]
            if len(classes_file) > 1:
                raise ValueError("Only one classes.txt file expected")
            return classes_file[0]
        except IndexError as exc:
            raise FileNotFoundError("No classes.txt file found") from exc

    @staticmethod
    def is_dir_empty(source_dir: Path):
        imgs = [img for img in source_dir.iterdir()]
        if not imgs:
            raise FileNotFoundError("Source folder is empty")
