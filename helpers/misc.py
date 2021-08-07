import time
from discord.ui import View


class RestrictedView(View):
    def __init__(self, *, timeout=180, owner):
        self.owner = owner
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction):
        if interaction.user != self.owner:
            await interaction.response.send_message(
                f"This is {self.owner.mention}'s interaction, you cannot use it",
                ephemeral=True,
            )
            return False
        return True


class StopWatch:
    def __enter__(self, *args):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()

    @property
    def time(self):
        return self.end - self.start
