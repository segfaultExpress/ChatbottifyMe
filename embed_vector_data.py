import logging
import json
import faiss
import numpy as np
import pickle
import os
import time
from openai import OpenAI
from config import PROCESSING_FOLDER, EMBEDDINGS_FILE, TEXTS_FILE, CHECKPOINT_FILE, VECTOR_PROCESSING_FILE

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing API key! Set the OPENAI_API_KEY environment variable.")

VECTOR_PROCESSING_FILE_PATH = os.path.join(PROCESSING_FOLDER, VECTOR_PROCESSING_FILE)
EMBEDDINGS_FILE_PATH = os.path.join(PROCESSING_FOLDER, EMBEDDINGS_FILE)
TEXTS_FILE_PATH = os.path.join(PROCESSING_FOLDER, TEXTS_FILE)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Load the saved JSONL data
logging.info("Loading JSONL conversation data...")
conversations = []
with open(VECTOR_PROCESSING_FILE_PATH, "r", encoding="utf-8") as f:
    for line in f:
        conversations.append(json.loads(line))

logging.info(f"Loaded {len(conversations)} conversations.")

# ** Load previous progress **
processed_count = 0
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r") as f:
        processed_count = int(f.read().strip())
    logging.info(f"Resuming from checkpoint: {processed_count} messages processed.")

# ** Load previous FAISS index and texts if they exist **
if os.path.exists(EMBEDDINGS_FILE_PATH) and os.path.exists(TEXTS_FILE_PATH):
    index = faiss.read_index(EMBEDDINGS_FILE_PATH)
    with open(TEXTS_FILE_PATH, "rb") as f:
        conversation_texts = pickle.load(f)
    logging.info(f"Loaded previous FAISS index ({index.ntotal} entries) and conversation texts ({len(conversation_texts)}).")
else:
    index = None  # Will be created later
    conversation_texts = []

# ** Ensure FAISS and conversation_texts.pkl are in sync **
if index is not None and index.ntotal != len(conversation_texts):
    logging.warning("🚨 FAISS index and conversation texts are mismatched! Consider rebuilding FAISS.")

# Convert conversation pairs into embeddings
LOG_EVERY = 50  # Log progress every N messages
SAVE_EVERY = 50  # Save checkpoint every N messages

logging.info("Starting embedding generation...")

for i in range(processed_count, len(conversations)):  # Resume from last saved position
    convo = conversations[i]
    full_text = f"User: {convo['other_person']}\nMatt: {convo['your_reply']}"

    try:
        start_time = time.time()
        response = client.embeddings.create(input=full_text, model="text-embedding-ada-002")
        elapsed_time = time.time() - start_time

        embedding = response.data[0].embedding

        # Ensure we don't duplicate stored texts
        if i >= len(conversation_texts):  
            conversation_texts.append(full_text)

        # Store embeddings safely
        if index is None:
            index = faiss.IndexFlatL2(len(embedding))  # L2 distance for similarity search
        index.add(np.array([embedding], dtype="float32"))  # Only add new embedding

        # Log progress every LOG_EVERY messages
        if (i + 1) % LOG_EVERY == 0:
            logging.info(f"Processed {i + 1}/{len(conversations)} messages ({elapsed_time:.2f}s per embedding)")

        # Save checkpoint every SAVE_EVERY messages
        if (i + 1) % SAVE_EVERY == 0:
            logging.info("Saving checkpoint...")

            # Save FAISS index and conversation texts
            faiss.write_index(index, EMBEDDINGS_FILE_PATH)
            with open(TEXTS_FILE_PATH, "wb") as f:
                pickle.dump(conversation_texts, f)

            # Save progress marker
            with open(CHECKPOINT_FILE, "w") as f:
                f.write(str(i + 1))

            logging.info(f"Checkpoint saved at {i + 1} messages.")

    except Exception as e:
        logging.error(f"Error processing conversation {i}: {e}")
        continue  # Skip failed message and continue

# Final save after all messages are processed
logging.info("Finalizing and saving embeddings...")

faiss.write_index(index, EMBEDDINGS_FILE_PATH)
with open(TEXTS_FILE_PATH, "wb") as f:
    pickle.dump(conversation_texts, f)

# Save final progress
with open(CHECKPOINT_FILE, "w") as f:
    f.write(str(len(conversations)))

logging.info(f"✅ All embeddings stored successfully. FAISS Entries: {index.ntotal}, Stored Texts: {len(conversation_texts)}.")
if index.ntotal != len(conversation_texts):
    logging.warning("🚨 Final mismatch detected! You may need to fully rebuild FAISS.")

