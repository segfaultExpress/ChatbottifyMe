# ChatBottify Me!

Convert all of your Facebook messages into a personalized GPT chatbot.

## 🚀 How to Make Your Own Chatbot

### 🛠️ Requirements

- **[OpenAI API Key](https://platform.openai.com)** (Required)
- **Python (3.12 recommended)**
- **(Optional) Discord Bot Token**: If you want to run this chatbot on Discord, you'll need to set up a bot:
  - [Discord Developer Portal](https://discord.com/developers/docs/intro)

---

## 📥 Step 1: Request Your Facebook Messenger Data

To use the in-built vectorizing code in this repo, you'll need to download your Facebook message history. This process can take up to 15 hours, depending on your account age.

1. Go to **[Facebook Account Center](https://accountscenter.facebook.com/info_and_permissions)**
2. Request a download of your **Messages Data**
3. Wait for the data to be processed (this can take a while)
4. Once ready, download and extract the files into a folder named `messenger_data`

---

## 🔧 Step 2: Prepare Your Environment

Install the required dependencies by running:

```bash
pip install -r requirements.txt
```

> 💡 If you have a GPU, consider using `faiss-gpu` instead of `faiss` for faster processing.

Set up your environment variables:

```bash
export OPENAI_API_KEY='your-openai-api-key'
export DISC_BOT_TOKEN='your-discord-bot-token' # Only needed for Discord
```

Or, if you're using Windows PowerShell:

```powershell
$env:OPENAI_API_KEY='your-openai-api-key'
$env:DISC_BOT_TOKEN='your-discord-bot-token'
```

---

## 📊 Step 3: Vectorize Your Messenger Data

Once your Messenger data is downloaded and extracted, process it by running:

```bash
python convert_messenger_data_to_vector.py
```

Then, convert it into a FAISS dataset:

```bash
python embed_vector_data.py
```

At this point, your chatbot is **ready for use** unless you want to explore fine-tuning.

---

## 🤖 Fine-Tuning (Optional)

Fine-tuning makes the bot sound more like you but comes with **higher costs and erratic responses**. If you want to experiment, follow these steps:

1. Convert your Messenger data into a fine-tuning dataset:

   ```bash
   python convert_messenger_data_to_finetune.py
   ```

2. Upload the `finetune.jsonl` file to OpenAI:
   - Go to: [OpenAI Fine-Tune Page](https://platform.openai.com/finetune)
   - Create a fine-tuned model
   - Once it's created, update your `config.py` with the new model ID:
     ```python
     OPENAI_MODEL_ID = 'your-model-id'
     ```
   - If you want to substitute it in as an optional chaotic version, use:
     ```python
     CHAOS_CHANCE = # >0.0, choose your percentage
     OPENAI_MODEL_CHAOS_ID = 'your-chaos-model-id'
     ```

---

## 💬 Step 5: Run Your Chatbot

Test your chatbot locally:

```bash
python chatbot.py
```

If you're using Discord, start the bot with:

```bash
python start_discord_bot.py
```

---

## 🔌 Integrating with Other Platforms

Want to use the chatbot on other platforms? Implement it with:

```python
from chatbot import Chatbot

chatbot = Chatbot(conversation_limit=5)  # Higher convo limit means better memory but increased cost

response = chatbot.respond_with_context(user_message)
```

Now, you can integrate it into other bots, apps, or services!

---

## 🔮 Future Plans & Limitations

### ✅ Planned Improvements:
- **Multi-source memory:** Currently, the chatbot maintains conversation history per initialized class. This should be refactored for multiple channels in `start_discord_bot.py`.
- **Better fine-tuning controls:** Allow in-app toggling between a normal and a chaotic version of the chatbot.
- **Repo pre-build support for more platforms:** (e.g., Telegram, Slack, or web-based chatbots)

---

## ⚡ Credits & License

This project was created for fun and personal use. Feel free to modify it for your own chatbot adventures! 🚀
