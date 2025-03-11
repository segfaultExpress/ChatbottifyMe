import json
import os
import glob
import openai
import numpy as np
import pickle
from config import CHATTER_NAME, PROCESSING_FOLDER, VECTOR_PROCESSING_FILE

# Directory containing JSON files
input_dir = "messenger_data/"
input_file_name = "message_*.json"

output_file_path = os.path.join(PROCESSING_FOLDER, VECTOR_PROCESSING_FILE)

conversations = []

# Iterate through all JSON files in the directory
for file_path in glob.glob(os.path.join(input_dir, "**", input_file_name), recursive=True):
    print(f"Processing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping {file_path} due to JSON decoding error.")
            continue

    messages = data.get("messages", [])

    for i in range(len(messages) - 1):  # Ensures there's a response after each message
        message = messages[i]
        next_message = messages[i + 1]

        # Check if this is a message from someone else and the next message is from Matt
        if message.get("sender_name") != CHATTER_NAME and next_message.get("sender_name") == CHATTER_NAME:
            conversation_entry = {
                "timestamp": next_message.get("timestamp_ms"),
                "other_person": message.get("content", ""),
                "your_reply": next_message.get("content", "")
            }
            conversations.append(conversation_entry)

# Save in JSONL format for retrieval use
with open(output_file_path, "w", encoding="utf-8") as f:
    for entry in conversations:
        f.write(json.dumps(entry) + "\n")

print(f"Context-aware data saved to: {output_file_path}")

