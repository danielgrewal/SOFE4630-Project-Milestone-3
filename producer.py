import os
import time
from google.cloud import pubsub_v1
from PIL import Image
import base64

# Set the correct service account JSON key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sofe4630-8e3862153346.json"

project_id = "sofe4630"
topic_id = "occlusion_image"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def send_images_from_folder(folder_path):
    for image_name in os.listdir(folder_path):
        image_path = os.path.join(folder_path, image_name)
        if os.path.isfile(image_path):
            encoded_image = encode_image(image_path)
            future = publisher.publish(topic_path, encoded_image.encode('utf-8'))
            print(f"Published {image_name} to {topic_path}")
            time.sleep(1)

if __name__ == "__main__":
    images_folder = "images"
    send_images_from_folder(images_folder)
