import aiohttp
import re
from redbot.core import commands, checks
from collections import OrderedDict
import os
import json
import time
import random

# Hello, I used a lot of comments because this project was to learn Red Bot and Cogs for the bot, as well as LLM's
# I also wanted to have a lot of comments incase someone wants to take this further, because this is a fun project for my discord and learnings.

# FIXME: Red isn't properly ending cut-off, it deletes the whole message instead of adding the warning at the end.

# Immediate
# TODO: Improve installer text/prompts.(how are people doing those menus???)
# TODO: Create functionality "only these roles can interact with red" and command to set those roles.
# TODO: Put chirp settings in config
# TODO: Make commands to change various settings
# TODO: Make a command that can prompt the user questions to build a peresonality for the Red LLM

# Longterm
# TODO: Create a database to save notes or important conversations about users or the server, to recall them later.(Make red feel more "Real")
# TODO: Make it so Red can join a voice channel, listen, and respond to users

# First we need to prompt the user for the setup info needed to run the bot.
# This will let the user put their KoboldCPP Host location, as well as theier model info
# The LLM will not be able to run until the config is setup correctly
# Location of Config Json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Load the Config
# Must have api_url and model set in the config to run
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"api_url": "", "model": ""}
    with open(CONFIG_PATH) as f:
        return json.load(f)

# Save the Config
def save_config(data):
    # with closes the file, because that's a thing in python(or you use f.close)
    # LEARN: go learn more about config file stuff. Also if there are better ways to handle talking between various file types. Lets do some tables later, we love expensive table lookups!
    # "w" opens the file as writable, don't forget that.
    with open(CONFIG_PATH, "w") as f:
        # indent is telling python to print the JSON with 2 spaces of indentation, for easier readability.(thanks random reddit convo)
        json.dump(data, f, indent=2)

# Runs when the user installs and loads the cog(or on boot of red, if preivously installed+loaded)
class HeyRedLLM(commands.Cog):
    # main everything

    # Init our variables for use later
    # LEARN: If there is a better way to do this
    def __init__(self, bot):
        # Standard info needed all over
        self.bot = bot
        self._config = load_config()
        # Needed config settings in order to run
        self.api_url = self._config.get("api_url", "")
        self.model = self._config.get("model", "")
        # How long the bot can respond, more tokens = more length. Each token is about 4 characters of text(including spaces+symbols)
        # If messages are getting cut-off often, increase this potentially.
        # More tokens = more processing time/power; reduce this to speed it up
        # Anything over 400-500 is probably overkill for a discord bot.
        self.max_tokens = self._config.get("max_tokens", 200)
        # How "Creative" the LLM gets. The closer to 1 the more unique the answers get, but the more inaccuracies occur.
        # 0.6 - 0.8 is a good safezone for personality vs. accuracy.
        self.temperature = self._config.get("temperature", 0.75)
        # If for some reason the prompt gets lost or ingested wrong
        self.prompt_failed = self._config.get("prompt_failed", "User Prompt Failed, Tell Them Nicely.")
        # Red ran out of tokens, so instead of the message being clipped off, Red will write a second message to "wrap up"
        self.prompt_followup = self._config.get("prompt_followup", "You are following up to a message you didn't finish.")
        # A prompt that gets appended when Red randomly decides to "chime in"(responds randomly to conversations happening in discord)
        self.prompt_chirp = "\n".join(self._config.get("prompt_chirp", ["You are Red, a Discord Bot, responding to a users message randomly." ]))
        # The standard personality, that gets prompted when talking to Red.
        self.personality_sassy = "\n".join(self._config.get("normal_personality_prompt", ["You are Red, a Discord Bot, answer in a sassy way." ]))
        # The helpful personality, when you try to ask Red a question(reduces potential frustration if you are trying to genuinly ask a question)
        self.personality_helpful = "\n".join(self._config.get("helpful_prompt", ["You are Red, a Discord Bot, answer in a helpful way."]))
        # The "Smart" personality, when you want a answer with less personality and a more professional demanor
        self.personality_scholar = "\n".join(self._config.get("scholar_prompt", ["You are Red, a Discord Bot, answer like a scholar."]))
        # We cache what personality was used in which messages, so that Red knows what personality to maintain if a reply chain is going.(Wouldn't want a serious question reply chain to turn sassy)
        self.personality_cache = OrderedDict()
        self.cache_size = 300

        # Random Engagement Settings; Red will randomly respond to users in chat unmprompted, to feel more "lively"
        self.last_chirp = time.time()
        self.base_chirp_chance = 0.0003  # 0.03%
        self.chirp_chance = self.base_chirp_chance
        self.chirp_cooldown = 10 * 60  # 10 minutes in seconds
        self.chirp_increment = 0.03    # 3% increase per period
        self.chirp_period = 3 * 60 * 60  # 3 hours in seconds
        self.max_chirp_chance = 0.12    # 12%

        # Channels RedLLM is allowed to respond in
        self.allowed_channel_ids = set(self._config.get("allowed_channel_ids", []))
        self.allow_dm = self._config.get("allow_dm", True)
        
    # This makes the function a [p] command for red.
    # Example: !heyredllmsetup, if run on red would run this function and set up the cog
    @commands.command()
    # Makes this function only able to run by the owner of Red
    @checks.is_owner()
    # This command prompts the user for the API_URL and MODEL config settings and lets them set them in discord(without having to open the config.json)
    async def heyredllmsetup(self, ctx):
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # ctx.send is how we send messages to discord through Red
        await ctx.send("Let's set up heyredllm!\n\nExample: http://123.45.6.789:5001/v1/chat/completions\n\nJust send messages like normal, whatever messages you send will be used for your settings so be careful!!!\n\n(Type 'cancel' at any time to stop.)")

        # API URL
        await ctx.send("Enter the LLM API URL\n\n(current: `{}`):".format(self.api_url or "not set"))
        msg = await ctx.bot.wait_for("message", check=check, timeout=120)
        if msg.content.lower() == "cancel":
            await ctx.send("Setup cancelled.")
            return
        self.api_url = msg.content.strip()

        # Model Name
        await ctx.send("Enter the LLM model and folder name that KoboldCPP uses.\n\nExample: koboldcpp/KobbleTiny-Q4_K.gguf\n\n(current: `{}`):".format(self.model or "not set"))
        msg = await ctx.bot.wait_for("message", check=check, timeout=120)
        if msg.content.lower() == "cancel":
            await ctx.send("Setup cancelled.")
            return
        self.model = msg.content.strip()

        # Save config
        self._config["api_url"] = self.api_url
        self._config["model"] = self.model
        save_config(self._config)

        await ctx.send("Setup complete! API URL and Model Name have been saved.")

    def is_llm_configured(self):
        return bool(self.api_url and self.model)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def heyredallowhere(self, ctx: commands.Context):
        
        # Allow Red to respond in this channel
        self.allowed_channel_ids.add(ctx.channel.id)
        self._save_allow_config()
        await ctx.send(f"✅ Red will now respond in {ctx.channel.mention}.")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def heyreddenyhere(self, ctx: commands.Context):
        
        # Remove this channel from the allow list
        self.allowed_channel_ids.discard(ctx.channel.id)
        self._save_allow_config()
        await ctx.send(f"🚫 Red will no longer respond in {ctx.channel.mention}.")

    @commands.command()
    async def heyredallowed(self, ctx: commands.Context):
        
        # Show allowed channels (empty = allowed everywhere)
        if not self.allowed_channel_ids:
            await ctx.send("No allow list set — Red will respond everywhere by default.")
            return

        # Only mention channels that exist in this server
        mentions = []

        if ctx.guild:
            for cid in sorted(self.allowed_channel_ids):
                ch = ctx.guild.get_channel(cid)
                if ch:
                    mentions.append(ch.mention)

        text = ", ".join(mentions) if mentions else "(none from this server)"

        await ctx.send(f"Allowed channels: {text}")

    @commands.command()
    @checks.is_owner()
    async def heyreddms(self, ctx: commands.Context, toggle: str):
        
        # Enable/disable DM's
        val = toggle.lower()

        if val not in ("on","off","true","false","yes","no"):
            await ctx.send("Usage: `[p]heyreddms on|off`")
            return

        self.allow_dm = val in ("on","true","yes")
        self._save_allow_config()
        await ctx.send(f"DM responses {'enabled' if self.allow_dm else 'disabled'}.")

    def _save_allow_config(self):
        self._config["allowed_channel_ids"] = sorted(self.allowed_channel_ids)
        self._config["allow_dm"] = self.allow_dm
        save_config(self._config)

    def _channel_is_allowed(self, obj):
        
        # Accepts a message, context, or channel.
        # Rule: if allowlist is empty -> allow everywhere (back-compat).
        
        # Figure out channel + guild
        channel = getattr(obj, "channel", obj)
        guild = getattr(channel, "guild", getattr(obj, "guild", None))

        # DMs have no guild
        if guild is None:
            return self.allow_dm if self.allowed_channel_ids else True

        # If no allowlist yet, allow everywhere (so you don't lock yourself out)
        if not self.allowed_channel_ids:
            return True

        return channel.id in self.allowed_channel_ids

    # Used to track what messages Red responded to using which personality
    # Helps continue personality used in chains of responses
    def cache_personality(self, msg_id, personality):
        self.personality_cache[msg_id] = personality
        if len(self.personality_cache) > self.cache_size:
            self.personality_cache.popitem(last=False)  #Remove oldest

    # Detect if Red needs to send a follow-up message.
    # Looks for phrases set in the personality prompt rules like 'I've hit my word limit and will continue in a follow-up message.'
    # Add key phrases or variations of the prompt/sentence you instructed Red to use in the Red rule's section    
    def needs_followup(self, reply: str):
        triggers = [
            "my word limit",
            "follow-up message",
            "let me finish",
            "hold up, i hit my word limit",
            "will continue"
        ]
        reply_lower = reply.lower()
        return any(trigger in reply_lower for trigger in triggers)
    
    # This function sends a prompt to the LLM
    # Will Return the LLM response
    # Making this was a pain, remember this pain and do it right next time(because you'll be back, I think there is an on_message bug in here)
    async def send_red_prompt(
        self,
        username,
        userid,
        payload,
        ctx=None,
        message=None,
        personality="sassy",
        allow_followup=True
    ):

        #
        if not ctx and not message:
            print("Warning: send_red_prompt called with neither ctx nor message!")
            return None
        
        headers = {"Content-Type": "application/json"}

        # This is a hornets nest, there are quiet a few things I'm not sure how they are doing it and need to learn more
        # LEARN: I don't really do stuff with HTTP, I know this is sending my payload as a JSON to the LLM API, but I want to know more about all of this.
        # Need to check out other ways to run an LLM besides KoboldCPP and compare
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_msg = f"Error: {response.status}"
                    if ctx:
                        await ctx.send(error_msg, reference=ctx.message)
                    elif message:
                        await message.reply(error_msg)
                    return None

                data = await response.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "No response.")
                reply = re.sub(rf"@?{re.escape(username)}\b", f"<@{userid}>", reply, flags=re.IGNORECASE)
                # Send reply
                # This confused me, ctx and message are discord specific info for the specific message Red is responding to.
                # ctx is short for context it's a command like !heyred
                # message is for general messages sent in discord, that got through the on_message filter below
                # It contains what channel, who sent the message, and essentially lets us know how to respond to the message.
                if ctx:
                    sent_msg = await ctx.send(reply.strip(), reference=ctx.message)
                elif message:
                    sent_msg = await message.reply(reply.strip())
                    await self.bot.process_commands(message)

                self.cache_personality(sent_msg.id, personality)

                # one (and only one) follow-up if cut-off detected
                if allow_followup and self.needs_followup(reply):
                    follow_payload = {
                        "model": self.model,
                        "messages": payload["messages"] + [
                            {"role": "system", "content": "Be brief. Only finish the previous answer."},
                            {"role": "user", "content": self.prompt_followup}
                        ],
                        "max_tokens": min(128, self.max_tokens // 2),
                        "temperature": self.temperature,
                    }


                    async with aiohttp.ClientSession() as session2:
                        async with session2.post(self.api_url, json=follow_payload, headers={"Content-Type":"application/json"}) as resp2:
                            if resp2.status == 200:
                                data2 = await resp2.json()
                                reply2 = data2.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                                reply2 = re.sub(rf"@?{re.escape(username)}\b", f"<@{userid}>", reply2, flags=re.IGNORECASE)
                                if reply2:
                                    if ctx:
                                        sent2 = await ctx.send(reply2, reference=sent_msg)
                                    else:
                                        sent2 = await message.reply(reply2)
                                    self.cache_personality(sent2.id, personality)

                return reply.strip()

    # formats the prompt how it needs to be, in order to properly be sent koboldcpp
    def build_prompt_payload(self, user_prompt, system_prompt, *, max_tokens=None, temperature=None, assistant=None):
        messages = [{"role": "system", "content": system_prompt}]

        if assistant:
            messages.append({"role": "assistant", "content": assistant})

        messages.append({"role": "user", "content": user_prompt})

        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature
        }

    # could be written better to add more personalities in the future
    def get_personality_prompt(self, personality, userid):
        if personality == "helpful":
            return self.personality_helpful.format(userid=userid, botid=self.bot.user.id, max_tokens=self.max_tokens)
        elif personality == "scholar":
            return self.personality_scholar.format(userid=userid, botid=self.bot.user.id, max_tokens=self.max_tokens)
        else:
            # Default to sassy
            return self.personality_sassy.format(userid=userid, botid=self.bot.user.id, max_tokens=self.max_tokens)

    # The normal personality prompt
    @commands.command()
    async def heyred(self, ctx: commands.Context, *, prompt: str):
        
        if not self._channel_is_allowed(ctx):
            await ctx.send("This isn’t an approved channel for Red. An admin can run `[p]heyredallowhere` to enable it here.")
            return

        if not self.is_llm_configured():
            await ctx.send("Red's LLM isn't set up yet! Please ask the bot owner to run `[p]heyredllmsetup` to finish configuration.")
            return

        userid = ctx.author.id
        username = ctx.author.display_name
        personality = "sassy"
        system_prompt = self.get_personality_prompt(personality, userid)

        payload = self.build_prompt_payload(prompt, system_prompt)

        reply = await self.send_red_prompt(username, userid, payload, ctx, None, personality)

    # A command that lets you send a prompt trying to make Red a little more helpful, to answer questions better
    @commands.command()
    async def askred(self, ctx: commands.Context, *, prompt: str):

        if not self._channel_is_allowed(ctx):
            await ctx.send("This isn’t an approved channel for Red. An admin can run `[p]heyredallowhere` to enable it here.")
            return

        if not self.is_llm_configured():
            await ctx.send("Red's LLM isn't set up yet! Please ask the bot owner to run `[p]heyredllmsetup` to finish configuration.")
            return

        userid = ctx.author.id
        username = ctx.author.display_name
        personality = "helpful"
        system_prompt = self.get_personality_prompt(personality, userid)

        payload = self.build_prompt_payload(prompt, system_prompt)

        reply = await self.send_red_prompt(username, userid, payload, ctx, None, personality)

    # A Prompt command that turns Red into a "Scholar" to answer serious and informatively
    @commands.command()
    async def askredserious(self, ctx: commands.Context, *, prompt: str):

        if not self.is_llm_configured():
            await ctx.send("Red's LLM isn't set up yet! Please ask the bot owner to run `[p]heyredllmsetup` to finish configuration.")
            return

        userid = ctx.author.id
        username = ctx.author.display_name
        personality = "scholar"
        system_prompt = self.get_personality_prompt(personality, userid)

        payload = self.build_prompt_payload(prompt, system_prompt)

        reply = await self.send_red_prompt(username, userid, payload, ctx, None, personality)

    # checks to see if Red can randomly respond to random users talking
    # has a timer and a % chance, settings above
    def check_and_chirp(self):
        now = time.time()
        can_chirp = (now - self.last_chirp) > self.chirp_cooldown

        if can_chirp:
            hours_since = (now - self.last_chirp) / self.chirp_period
            self.chirp_chance = min(
                self.base_chirp_chance + (self.chirp_increment * hours_since),
                self.max_chirp_chance,
            )
            roll = random.random()
            if roll < self.chirp_chance:
                self.last_chirp = now
                self.chirp_chance = self.base_chirp_chance  # Reset after chirp
                return True
        return False

    # Does the random response
    async def red_chirp(self, username, userid, prompt, message, personality="sassy"):
        
        system_prompt = f"{self.get_personality_prompt(personality, userid)}\n{self.prompt_chirp}"
        payload = self.build_prompt_payload(prompt, system_prompt)
        reply = await self.send_red_prompt(username, userid, payload, ctx=None, message=message, personality=personality)

    @commands.Cog.listener()
    # watches messages and responds to replys, @'s, and random messages(chirp) on a random timer system.
    async def on_message(self, message):
        # Ignore messages from bots (including yourself)
        if message.author.bot:
            return

        if not self.is_llm_configured():
            return

        # Check if this message is a command; if so, do nothing (avoid double reply)
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if not self._channel_is_allowed(message):
            return

        # Only react to direct @mentions or replies to the bot
        bot_id = self.bot.user.id
        mentioned = self.bot.user.mentioned_in(message)
        replied_to_bot = (
            message.reference
            and (ref := getattr(message.reference, "resolved", None))
            and hasattr(ref, "author")
            and ref.author.id == bot_id
        )
        
        username = message.author.display_name
        userid = message.author.id
        prompt = message.clean_content.replace(f"@{self.bot.user.display_name}", "").strip()

        if not (mentioned or replied_to_bot):
            # If not a mention or reply to Red, check to see if random engage, or just let commands process and do nothing
            if self.check_and_chirp() and prompt:
                await self.red_chirp(username, userid, prompt, message)
                return
            else:
                await self.bot.process_commands(message)
                return

        if not prompt:
            prompt = self.prompt_failed

        # Get a personality, if replying to a chain of messages that a specific personality was used.
        if message.reference and message.reference.resolved:
            replied_message_id = message.reference.resolved.id
            personality = self.personality_cache.get(replied_message_id, "sassy")
        else:
            personality = "sassy"

        system_prompt = self.get_personality_prompt(personality, userid)
        messages = [{"role": "system", "content": system_prompt}]
        user_content = prompt

        # assistant is letting the LLM know the chain of conversation.
        # LLM's expect conversation history like user->assistant->user->assistant
        # Asstant is the bots messages in this case, gives the LLM more info to respond properly
        # This may be super messed up, will investigate later
        ref = None
        if message.reference:
            ref = getattr(message.reference, "resolved", None)
            if not ref and message.reference and message.reference.message_id:
                try:
                    ref = await message.channel.fetch_message(message.reference.message_id)
                except Exception:
                    ref = None
            if ref and hasattr(ref, "author") and hasattr(ref, "content"):
                if ref.author.id == bot_id:
                    messages.append({
                        "role": "assistant",
                        "content": ref.content
                    })
                    user_content = f"(The user is replying directly to your last message above.)\n{prompt}"
                else:
                    messages.append({
                        "role": "user",
                        "content": f"(Context: This user is replying to {ref.author.display_name}'s message:\n \"{ref.content}\")"
                    })
                    user_content = prompt
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        assistant_text = ref.content if (ref and ref.author.id == bot_id) else None
        payload = self.build_prompt_payload(user_content, system_prompt, assistant=assistant_text)

        reply = await self.send_red_prompt(username, userid, payload, ctx=ctx, message=message, personality=personality)