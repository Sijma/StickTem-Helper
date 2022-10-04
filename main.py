import discord
import config
import helpers

from discord import app_commands, Embed
from discord.ui import View, Select


class StickerClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default(), activity=discord.Activity(type=discord.ActivityType.listening, name="/start"))
        self.synced = True

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync()
            self.synced = True
        print(f"Ready! {self.user}")


bot = StickerClient()
tree = app_commands.CommandTree(bot)


async def null_callback(interaction):
    await interaction.response.defer()


class User:
    def __init__(self, user_id):
        self.user_id = user_id
        doc = helpers.database_init(user_id)

        self.data = doc

        self.unsaved = False

    message = None


select_text_dict = {
    "have_mint": "your duplicate mint stickers",
    "have_damaged": "your duplicate damaged stickers",
    "need_mint": "the mint stickers you need",
    "need_damaged": "the damaged stickers you need"
}

timeout_embed = Embed(title="Bot has timed out", description="Type **/start** to start again.", colour=discord.Color.blue())


class SelectionMenu(View):
    def __init__(self, user, sticker_type):
        super().__init__()

        self.timeout = 300

        self.user = user
        self.sticker_type = sticker_type
        self.current_page = 1

        self.embed = Embed(title=f"Select {select_text_dict.get(sticker_type)}", description=f"Use the arrows to navigate the pages.\n\nPress **\"Submit\"** to save your settings when you're done adding everything!", colour=discord.Color.blue())
        self.embed.set_thumbnail(url=bot.user.avatar.url)

        self.sticker_select = Select(options=helpers.get_options(self.current_page, self.user.data[sticker_type]), min_values=0, max_values=25)
        self.sticker_select.callback = self.select_callback
        self.add_item(self.sticker_select)

        submit_button = [x for x in self.children if x.custom_id == "submit_button"][0]
        submit_button.disabled = not self.user.unsaved

    async def select_callback(self, interaction):
        range_high = self.current_page * 25
        range_low = range_high - 25
        for index in range(range_low, range_high):
            self.user.data[self.sticker_type][index] = str(index) in self.sticker_select.values
        self.sticker_select.options = helpers.get_options(self.current_page, self.user.data[self.sticker_type])
        self.user.unsaved = True
        submit_button = [x for x in self.children if x.custom_id == "submit_button"][0]
        submit_button.disabled = False
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="back_button")
    async def back_callback(self, interaction, button):
        await main_menu(interaction, self.user, True)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, custom_id="left_button", disabled=True)
    async def left_callback(self, interaction, left_button):
        self.current_page -= 1
        left_button.disabled = self.current_page == 1
        right_button = [x for x in self.children if x.custom_id == "right_button"][0]
        right_button.disabled = False
        self.sticker_select.options = helpers.get_options(self.current_page, self.user.data[self.sticker_type])
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, custom_id="right_button")
    async def right_callback(self, interaction, right_button):
        self.current_page += 1
        right_button.disabled = self.current_page == 8
        left_button = [x for x in self.children if x.custom_id == "left_button"][0]
        left_button.disabled = False
        self.sticker_select.options = helpers.get_options(self.current_page, self.user.data[self.sticker_type])
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.green, custom_id="submit_button")
    async def submit_callback(self, interaction, submit_button):
        helpers.update_db(self.user.user_id, self.user.data)
        self.user.unsaved = False
        submit_button.disabled = True
        await interaction.response.edit_message(view=self)


class MatchMenu(View):
    def __init__(self, user, matches):
        super().__init__()

        self.timeout = 300

        self.user = user
        self.matches = matches
        self.current_page = 0
        self.embeds = []

    def new_embed_base(self, number):
        embed = Embed(title=f"Match Results {number}/{len(self.matches)}", colour=discord.Color.blue())
        embed.set_thumbnail(url=bot.user.avatar.url)
        return embed

    async def construct_embeds(self):
        if len(self.matches) == 0:
            self.embeds.append(self.new_embed_base(0))
            self.embeds[0].description = "No matches found. Try again when more people register!"
        else:
            for match in self.matches:
                embed = self.new_embed_base(self.matches.index(match)+1)
                match_username = await bot.fetch_user(match.user_id)
                embed.description = f"Match found with {match_username}! You can trade for {match.mint_trades_amount} mint and {match.damaged_trades_amount} damaged stickers."

                if match.mint_trades_amount > 0:
                    embed.add_field(name="Give Mint", value=helpers.format_sticker_matches(match.give_mint, match.mint_trades_amount), inline=True)
                    embed.add_field(name="Receive Mint", value=helpers.format_sticker_matches(match.take_mint, match.mint_trades_amount), inline=True)

                if match.damaged_trades_amount > 0:
                    embed.add_field(name="Give Damaged", value=helpers.format_sticker_matches(match.give_damaged, match.damaged_trades_amount), inline=True)
                    embed.add_field(name="Receive Damaged", value=helpers.format_sticker_matches(match.take_damaged, match.damaged_trades_amount), inline=True)

                self.embeds.append(embed)
        right_button = [x for x in self.children if x.custom_id == "right_button"][0]
        right_button.disabled = len(self.embeds) <= 1

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="back_button")
    async def back_callback(self, interaction, button):
        await main_menu(interaction, self.user, True)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, custom_id="left_button", disabled=True)
    async def left_callback(self, interaction, left_button):
        self.current_page -= 1
        left_button.disabled = self.current_page == 0
        right_button = [x for x in self.children if x.custom_id == "right_button"][0]
        right_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, custom_id="right_button")
    async def right_callback(self, interaction, right_button):
        self.current_page += 1
        right_button.disabled = self.current_page == len(self.embeds) - 1
        left_button = [x for x in self.children if x.custom_id == "left_button"][0]
        left_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class MainMenu(View):
    def __init__(self, user):
        super().__init__()

        self.timeout = 300

        self.user = user
        self.embed = Embed(title="Welcome to StickTem! Helper", description="You can use this bot to help you manage your sticker collection and find trading partners!", colour=discord.Color.blue())
        self.embed.set_thumbnail(url=bot.user.avatar.url)

    async def on_timeout(self) -> None:
        await self.user.message.edit(view=None, embed=timeout_embed)

    @discord.ui.button(label="Have Mint", style=discord.ButtonStyle.primary, custom_id="have_mint")
    async def callback1(self, interaction, button):
        selection_menu = SelectionMenu(self.user, button.custom_id)
        await interaction.response.edit_message(view=selection_menu, embed=selection_menu.embed)

    @discord.ui.button(label="Have Damaged", style=discord.ButtonStyle.primary, custom_id="have_damaged")
    async def callback2(self, interaction, button):
        selection_menu = SelectionMenu(self.user, button.custom_id)
        await interaction.response.edit_message(view=selection_menu, embed=selection_menu.embed)

    @discord.ui.button(label="Need Mint", style=discord.ButtonStyle.primary, custom_id="need_mint")
    async def callback3(self, interaction, button):
        selection_menu = SelectionMenu(self.user, button.custom_id)
        await interaction.response.edit_message(view=selection_menu, embed=selection_menu.embed)

    @discord.ui.button(label="Need Damaged", style=discord.ButtonStyle.primary, custom_id="need_damaged")
    async def callback4(self, interaction, button):
        selection_menu = SelectionMenu(self.user, button.custom_id)
        await interaction.response.edit_message(view=selection_menu, embed=selection_menu.embed)

    @discord.ui.button(label="Find Matches", style=discord.ButtonStyle.green, custom_id="find_matches_button")
    async def find_callback(self, interaction, button):
        helpers.disable_all_children(self)
        button.label = "Loading.."

        await interaction.response.edit_message(view=self)
        matches = helpers.search_matches(self.user)

        match_menu = MatchMenu(self.user, matches)
        await match_menu.construct_embeds()

        await interaction.edit_original_response(view=match_menu, embed=match_menu.embeds[0])


async def main_menu(interaction, user, edit):
    menu = MainMenu(user)
    if edit:
        await interaction.response.edit_message(embed=menu.embed, view=menu)
    else:
        await interaction.response.send_message(embed=menu.embed, view=menu, ephemeral=True)

        user.message = await interaction.original_response()


@tree.command(name="start", description="Initiate StickTem! Helper.")
async def start(interaction):
    user = User(interaction.user.id)
    await main_menu(interaction, user, False)

bot.run(config.token)
