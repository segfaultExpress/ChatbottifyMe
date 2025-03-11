import faiss
import pickle
import openai
import numpy as np
import traceback
import logging
import os
from config import OPENAI_MODEL_ID, OPENAI_MODEL_CHAOS_ID, CHATTER_NAME, CHAOS_CHANCE, PROCESSING_FOLDER, EMBEDDINGS_FILE, TEXTS_FILE

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing API key! Set the OPENAI_API_KEY environment variable.")

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

EMBEDDINGS_FILE_PATH = os.path.join(PROCESSING_FOLDER, EMBEDDINGS_FILE)
TEXTS_FILE_PATH = os.path.join(PROCESSING_FOLDER, TEXTS_FILE)

class Chatbot:
    def __init__(self, conversation_limit=5):
        """Initialize chatbot with FAISS index and stored conversation texts."""
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.conversation_limit = conversation_limit
        self.conversation_history = []

        if os.path.exists(EMBEDDINGS_FILE_PATH):
            try:
                self.index = faiss.read_index(EMBEDDINGS_FILE_PATH)
            except Exception as e:
                logging.error(f"Error loading FAISS index: {e}")
                self.index = None
        else:
            self.index = None
            logging.warning("FAISS index not available.")

        if os.path.exists(TEXTS_FILE_PATH):
            try:
                with open(TEXTS_FILE_PATH, "rb") as f:
                    self.conversation_texts = pickle.load(f)
            except Exception as e:
                logging.error(f"Error loading conversation texts: {e}")
                self.conversation_texts = []
        else:
            self.conversation_texts = []
            logging.warning("Conversation texts not available.")

    def _retrieve_similar_conversations(self, query, top_k=3):
        """Finds the most similar past conversations based on FAISS index."""
        if not self.index:
            return []

        try:
            query_embedding_response = self.client.embeddings.create(
                input=[query], model="text-embedding-ada-002"
            )
            query_embedding = query_embedding_response.data[0].embedding

            D, I = self.index.search(np.array([query_embedding]).astype("float32"), k=top_k)
            
            similar_convos = [self.conversation_texts[i] for i in I[0] if i < len(self.conversation_texts)]
            
            return similar_convos
        except Exception as e:
            logging.error(f"Error retrieving similar conversations: {e}")
            return []

    def respond_with_context(self, input_text):
        """Generates a response using OpenAI API with conversation memory and FAISS context."""
        # 1 in 10 chance of chaos mode
        chaos_mode = np.random.random() < CHAOS_CHANCE

        try:
            # Retrieve similar past conversations
            similar_messages = self._retrieve_similar_conversations(input_text)
        except Exception as e:
            logging.error(f"Error retrieving similar conversations: {e}")
            similar_messages = []

        # Append user input to chat history
        self.conversation_history.append({"role": "user", "content": input_text})

        # Keep only the latest N messages
        self.conversation_history = self.conversation_history[-self.conversation_limit:]

        context_prompt = "\n\n".join([f"PAST CONVERSATION:\n{msg}" for msg in similar_messages])

        # Construct final prompt
        full_prompt = f"""
        You are {CHATTER_NAME}. Your responses must closely match the tone, vocabulary, and structure of past conversations. 
        If in doubt, prioritize similarity over creativity. Do not introduce new styles or perspectives.

        Past relevant conversations:
        {context_prompt}

        New User Input:
        USER: {input_text}

        Now generate a response that aligns with the prior conversations:
        """

        try:
            # Ensure the prompt is passed as a message!
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_ID if not chaos_mode else OPENAI_MODEL_CHAOS_ID,
                messages=[{"role": "system", "content": full_prompt}] + self.conversation_history
            )

            response_text = response.choices[0].message.content

            token_usage = response.usage.total_tokens  # Total tokens used
            prompt_tokens = response.usage.prompt_tokens  # Input tokens
            completion_tokens = response.usage.completion_tokens  # Output tokens

            # Append assistant's response to history
            self.conversation_history.append({"role": "assistant", "content": response_text})

            logging.info(f"Token usage: {token_usage} (Prompt: {prompt_tokens}, Completion: {completion_tokens})")
            logging.info(f"Response: {response_text}")
            return response_text
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            traceback.print_exc()
            return "Sorry, an error occurred while generating a response."

    def converse(self):
        """Starts a conversation loop with the user."""
        try:
            while True:
                user_input = input("Enter your prompt (or type 'exit' to quit): ")
                if user_input.lower() == "exit":
                    print("Goodbye!")
                    break
                response = self.respond_with_context(user_input)
                print(response)
        except KeyboardInterrupt:
            logging.info("Conversation ended by user via keyboard interrupt.")
            print("\nConversation ended by user.")
        except Exception as e:
            logging.critical(f"Unexpected error in conversation loop: {e}")
            print("An unexpected error occurred. Check logs for details.")

if __name__ == "__main__":
    chatbot = Chatbot()
    chatbot.converse()
