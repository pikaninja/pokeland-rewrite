import time
from discord.ui import View
from discord.ext.menus.views import ViewMenuPages


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


class EditableMenuPages(ViewMenuPages):
    def __init__(self, source, select=None, message=None):
        super().__init__(source)
        self.select = select
        self.msg = message

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        view = self.build_view()
        if self.select:
            if not view:
                view = RestrictedView(owner=ctx.author)
            view.add_item(self.select)
        if self.msg:
            await self.msg.edit(**kwargs, view=view)
            return self.msg
        return await channel.send(**kwargs, view=view)


class StopWatch:
    def __enter__(self, *args):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()

    @property
    def time(self):
        return self.end - self.start
