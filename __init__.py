from .heyredllm import HeyRedLLM

async def setup(bot):
    await bot.add_cog(HeyRedLLM(bot))