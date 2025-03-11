import json
import os
import glob
from config import CHATTER_NAME, PROCESSING_FOLDER, FINETUNE_PROCESSING_FILE

# Directory containing JSON files
input_dir = "messenger_data/"
input_file_name = "message_*.json"

output_file_path = os.path.join(PROCESSING_FOLDER, FINETUNE_PROCESSING_FILE)

convo_context = 3

fine_tune_data = []

# Iterate through all JSON files in the directory
for file_path in glob.glob(os.path.join(input_dir, "**", input_file_name), recursive=True):
    print(f"Processing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping {file_path} due to JSON decoding error.")
            continue

    # Extract messages from user with context
    messages = data.get("messages", [])
    
    for i in range(len(messages)):  # Start from 0 to capture full conversation
        message = messages[i]

        if message.get("sender_name") == CHATTER_NAME and "content" in message:
            if "content" not in message:
                continue

            # Collect up to the last three messages as context
            context_messages = messages[max(0, i - convo_context):i]  # Last x or fewer
            
            structured_messages = [{"role": "system", "content": f"You are {CHATTER_NAME}, a chatbot who seeks to message your friends, talk hobbies, and troll them."}]
            
            for ctx_msg in context_messages:
                if "content" not in ctx_msg:
                    continue

                role = "assistant" if ctx_msg.get("sender_name") == CHATTER_NAME else "user"
                structured_messages.append({"role": role, "content": ctx_msg["content"]})

            structured_messages.append({"role": "assistant", "content": message["content"]})
            
            fine_tune_data.append({"messages": structured_messages})

# Save messages in GPT fine-tune JSONL format
with open(output_file_path, "w", encoding="utf-8") as f:
    for entry in fine_tune_data:
        f.write(json.dumps(entry) + "\n")

print(f"Fine-tuning data saved to: {output_file_path}")
