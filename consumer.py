import os
from google.cloud import pubsub_v1

# Set the correct service account JSON key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sofe4630-8e3862153346.json"

# Define the project and subscription
project_id = "sofe4630"
subscription_id = "occlusion_estimate-sub"

# Initialize the subscriber client
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Callback function to process messages
def callback(message):
    print(f"Received message: {message.data.decode('utf-8')}")
    message.ack()  # Acknowledge the message

# Subscribe to the topic
print(f"Listening for messages on {subscription_path}...")
future = subscriber.subscribe(subscription_path, callback)

# Keep the script running
try:
    future.result()  # Block indefinitely to keep the subscriber running
except KeyboardInterrupt:
    future.cancel()  # Exit on keyboard interrupt
