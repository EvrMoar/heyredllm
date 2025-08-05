# heyredllm

A [Redbot](https://github.com/Cog-Creators/Red-DiscordBot) cog that adds a local LLM brain to your Discord bot using [KoboldCpp](https://github.com/LostRuins/koboldcpp) as the backend.

My discord wanted functionality to listen to music, or basic commands, and I wasn't happy with Red bot feeling so "stiff". This is my attempt to liven up the bot, and it was a great opportunity to learn about LLM's. Eventually I would love to integrate this into Red bot, or write my own discord bot, but for now this was more of a "for fun". Eventually I will add a database type memory system to see if I can keep track of various information or feed it certain things to be able to answer questions more tailored to the users or areas that I want it to focus on.

Redbot + LLM = Turns Red into a AI and tries to give the bot some personality.

You must run !heyredllmsetup first, or edit your config.json with your model and koboldcpp host location.

WARNING: I AM USING THIS AS A CHANCE TO LEARN LLM'S AND THERE IS CURRENTLY A LACK OF SAFETIES/Q&A. I RECOMMEND NOT USING THIS IN DISCORDS WHERE YOU DON'T TRUST EVERYONE WHO WILL BE ENGAGING WITH THE BOT.

UNSURE IF I WILL SUPPORT THIS, BUT I DO WANT TO DO ROLE AND CHANNEL FUNCTIONALITY; RIGHT NOW ANYONE ANYWHERE CAN SPAM THE BOT WHICH IS ONE OF THE WORST PROBLEMS AND WHY IT IS NOT GOOD IN A PUBLIC SERVER.

---

## Features

- **Local LLM Integration**: Connects your Discord bot to a local large language model running via KoboldCpp.
- **Three Personalities**:
(I used a LLM to generate the personalities because I tested 10+ LLM models and wanted to try a variety of personalities quickly. They are all temp for now.)
  - **Red Personality**: Playful, witty, meme responses.(personality is a little rough, I need to fix)
  - **Helpful Mode**: Clear, direct, user-friendly answers.
  - **Serious/Scholar Mode**: Analytical, professional, and thorough answers.
- **Flexible Triggers**: Responds to bot commands, @mentions, and replies to the bot in any server channel or DM.
- **Customizable**: You can edit the prompt in `heyredllm.py` to change Red’s vibe and behavior.

---

## Requirements

- **Redbot v3.5+** (tested with 3.5+)
- **KoboldCpp** running as a local API server (see below)
- **Python 3.8+** (same as required for Redbot)
- A compatible LLM model (e.g., Llama 3, Mistral, DeepHermes)

---

## Setup Instructions

1. **Set up KoboldCpp**
   - Download and run [KoboldCpp](https://github.com/LostRuins/koboldcpp) on your machine or server.
   - Start KoboldCpp with API mode enabled:
     ```
     ./koboldcpp --api --model "YourModelFile.gguf" --port 5001
     ```
   - Confirm it’s running by visiting `http://localhost:5002` in your browser.

2. **Install Redbot**  
   Follow the official [Redbot install guide](https://docs.discord.red/en/stable/).

3. **Install this cog**
   - Copy the `heyredllm` folder into your `cogs` directory (`/appdata/redbot/cogs/CogManager/cogs/` or wherever your Redbot cogs live).
   - Add the cog to Redbot:
     ```
     [p]cog install local heyredllm
     [p]load heyredllm
     ```
   - *(Replace `[p]` with your bot's actual prefix.)*

4. **Edit API URL (Optional)**
   - If KoboldCpp is running somewhere else, open `heyredllm.py` and change the line:
     ```python
     self.api_url = "http://localhost:5001/v1/chat/completions"
     ```
     to match your KoboldCpp instance.

5. **Choose Your Model**
   - Adjust the `.gguf` model filename in the cog to match the model you're running.

---

## Usage

### Commands

- `!heyred <prompt>`  
  **Talk to Red** (sassy, humorous, Deadpool energy).

- `!askred <prompt>`  
  **Get a helpful, clear, less sassy answer.**

- `!askredserious <prompt>`  
  **Get an analytical,scholar like answer(cuts a lot of personality and tries to prompt from the perspective of a professor)f**
