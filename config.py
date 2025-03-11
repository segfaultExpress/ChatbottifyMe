# General
CHATTER_NAME = 'Matthew Elias'

# File paths
PROCESSING_FOLDER = "processing"
FINETUNE_PROCESSING_FILE = "finetune.jsonl"
VECTOR_PROCESSING_FILE = "vector.jsonl"
EMBEDDINGS_FILE = "faiss_index.faiss"
TEXTS_FILE = "conversation_texts.pkl"
CHECKPOINT_FILE = "processed_count.txt"

# OpenAI
OPENAI_MODEL_ID = 'gpt-4o-mini'

CHAOS_CHANCE = 0.0 # Fine-tuning seems to be much more chaotic - use if you want some weird messages
OPENAI_MODEL_CHAOS_ID = 'ft:gpt-4o-mini-2024-07-18:personal:mattgptv2:B9mwo2F9' # 4.0 v2

# Facebook bot (violates TOS, excluded from repo)
FB_USER = ''
FB_PASS = ''
THREAD_ID = ''