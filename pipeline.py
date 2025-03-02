# Standard Library Imports
import logging
import base64
import json
import subprocess

# Third-Party Library Imports (Global)
import cv2
import numpy as np
from PIL import Image
import torch
import torchvision.transforms as transforms
from ultralytics import YOLO

# Apache Beam Imports
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions

# Set logging level to INFO
logging.basicConfig(level=logging.INFO)


class DetectPedestrians(beam.DoFn):
    def setup(self):
        """Setup is called once per worker before processing begins."""
        import subprocess
        import sys

        # Print Python version to confirm worker setup
        logging.info(f"Python Version in Worker: {sys.version}")

        # Force install torch inside the worker
        logging.info("Installing Torch inside worker...")
        try:
            subprocess.run(
                ["pip", "install", "--no-cache-dir", "--index-url", "https://download.pytorch.org/whl/cpu", "torch", "torchvision"],
                check=True
            )
            logging.info("Torch installed successfully inside the worker.")
        except Exception as e:
            logging.error(f"[ERROR] Failed to install Torch inside worker: {e}")

        # Verify if torch is now available
        try:
            import torch
            import torchvision
            logging.info(f"Torch Version After Manual Install: {torch.__version__}")
        except ModuleNotFoundError as e:
            logging.error("[ERROR] Torch is STILL missing in the worker!")
            raise e

        # Load YOLO model for pedestrian detection
        logging.info("Loading YOLO model for pedestrian detection...")
        self.model = YOLO("yolov5su.pt")
        logging.info("YOLO model loaded successfully.")

    def process(self, element):
        """Processes image and detects pedestrians."""
        logging.info("DetectPedestrians: Received a new image from Pub/Sub.")

        try:
            image_data = base64.b64decode(element)
            image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)

            if image is None:
                logging.error("[ERROR] Unable to decode image from Pub/Sub message.")
                return []

            logging.info("Running YOLO model for pedestrian detection...")
            results = self.model(image)
            ped_bboxes = []

            for box in results[0].boxes:
                cls_id = box.cls
                conf = box.conf
                bbox = box.data
                label = results[0].names[int(cls_id)]

                if label == 'person':
                    x1, y1, x2, y2, _, _ = bbox[0]
                    ped_bboxes.append({'box': bbox[0][0:4], 'conf': float(conf)})

            logging.info(f"Pedestrian Detection Complete: Found {len(ped_bboxes)} pedestrians.")

            return [{'image': image, 'boxes': ped_bboxes}]

        except Exception as e:
            logging.error(f"[ERROR] Failed to process image: {e}")
            return []


class EstimateDepth(beam.DoFn):
    def setup(self):
        """Setup is called once per worker before processing begins."""
        logging.info("Loading MiDaS depth estimation model...")
        self.device = torch.device("cpu")
        self.model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small").to(self.device)
        self.model.eval()
        logging.info("MiDaS model loaded successfully.")

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5])
        ])

    def process(self, element):
        """Takes the detected bounding boxes and estimates the depth."""
        logging.info("EstimateDepth: Processing detected pedestrians for depth estimation.")

        image = element['image']
        boxes = element['boxes']

        if not boxes:
            logging.info("No persons detected, skipping depth estimation.")
            return [element]

        updated_boxes = []

        for box in boxes:
            x1, y1, x2, y2 = map(int, box['box'])
            cropped_person = image[y1:y2, x1:x2]

            if cropped_person.size == 0:
                logging.warning("Skipped empty bounding box.")
                continue

            try:
                logging.info(f"Processing bounding box {box['box']} for depth estimation...")

                cropped_person_rgb = cv2.cvtColor(cropped_person, cv2.COLOR_BGR2RGB)
                input_tensor = self.transform(cropped_person_rgb).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    depth_prediction = self.model(input_tensor)

                depth_map = depth_prediction.squeeze().cpu().numpy()
                depth_map = depth_map - np.min(depth_map)
                depth_map = depth_map / np.max(depth_map)
                depth_map = 1 - depth_map
                depth_resized = cv2.resize(depth_map, (x2 - x1, y2 - y1))
                avg_depth = np.mean(depth_resized) * 10

                logging.info(f"Estimated avg depth: {avg_depth:.2f}m for bounding box {box['box']}")

                updated_boxes.append({"box": [float(coord) for coord in box["box"]],
                                      "conf": float(box["conf"]),
                                      "avg_depth": float(avg_depth)})

            except Exception as e:
                logging.error(f"[ERROR] Failed to process depth estimation: {e}")
                updated_boxes.append({"box": [float(coord) for coord in box["box"]],
                                      "conf": float(box["conf"]),
                                      "avg_depth": None})

        output_dict = {"box_conf_depth": updated_boxes}
        json_output = json.dumps(output_dict).encode("utf-8")

        return [json_output]


def run():
    """Main entry point; defines and runs the Apache Beam pipeline."""

    pipeline_options = PipelineOptions(
        project="sofe4630",
        region="us-central1",
        temp_location="gs://sofe4630-bucket/temp",
        streaming=True,
        num_workers=1,
        autoscaling_algorithm="NONE",
    )

    pipeline_options.view_as(SetupOptions).save_main_session = False

    # Define the pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        logging.info("Starting Apache Beam pipeline...")
        (
            p
            | "Read from PubSub" >> beam.io.ReadFromPubSub(topic="projects/sofe4630/topics/occlusion_image")
            | "DetectPedestrians" >> beam.ParDo(DetectPedestrians())
            | "EstimateDepth" >> beam.ParDo(EstimateDepth())
            | "Write to PubSub" >> beam.io.WriteToPubSub(topic="projects/sofe4630/topics/occlusion_estimate")
        )
        logging.info("Pipeline execution started.")

if __name__ == "__main__":
    run()
