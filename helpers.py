import discord
import config
import constants
import pymongo
from numpy import full
import heapq


client = pymongo.MongoClient("mongodb://localhost:27017/", username=config.database_username, password=config.database_password)
db = client["sticktem"]
col = db["users"]


def default_list():
    array = full(200, False, dtype=bool)
    return array.tolist()


def disable_all_children(view):
    for item in view.children:
        item.disabled = True
    return view


def get_options(page, enabled):
    options = []
    range_high = page*25
    range_low = range_high - 25
    for index in range(range_low, range_high):
        options.append(discord.SelectOption(label=constants.stickers[index], value=str(index), default=enabled[index]))
    return options


def database_init(user_id):
    doc = col.find_one({"_id": user_id})
    if doc is None:
        array = default_list()
        entry = {"_id": user_id, "have_mint": array.copy(), "have_damaged": array.copy(), "need_mint": array.copy(), "need_damaged": array.copy()}
        col.insert_one(entry)
        return entry
    return doc


def update_db(user_id, data):
    temp_dict = data.copy()
    del temp_dict["_id"]
    new_value = {"$set": temp_dict}
    query = {"_id": user_id}
    col.update_one(query, new_value)


# Returns a list of indices where both lists' elements are True
def get_matches(list1, list2):
    return [i for i, (x, y) in enumerate(zip(list1, list2)) if x and y]


class Match:
    def __init__(self, user_id, give_mint, take_mint, give_damaged, take_damaged, mint_trades_amount, damaged_trades_amount, total_trades):
        self.user_id = user_id
        self.give_mint = give_mint
        self.take_mint = take_mint
        self.give_damaged = give_damaged
        self.take_damaged = take_damaged
        self.mint_trades_amount = mint_trades_amount
        self.damaged_trades_amount = damaged_trades_amount

        self.total_trades = total_trades

    def evaluation_function(self):
        # Using negative numbers in evaluation to "trick" heapq as it only creates ascending order heaps.
        return self.total_trades * -1

    def __lt__(self, other):
        return self.evaluation_function() < other.evaluation_function()


def search_matches(user):
    user_stickers = user.data
    found = False
    potential_matches = col.find({"_id": {"$ne": user.user_id}})

    matches = []

    for potential_match in potential_matches:
        give_mint = get_matches(user_stickers["have_mint"], potential_match["need_mint"])
        take_mint = get_matches(user_stickers["need_mint"], potential_match["have_mint"])
        give_damaged = get_matches(user_stickers["have_damaged"], potential_match["need_damaged"])
        take_damaged = get_matches(user_stickers["need_damaged"], potential_match["have_damaged"])

        mint_trades_amount = min(len(give_mint), len(take_mint))
        damaged_trades_amount = min(len(give_damaged), len(take_damaged))
        total_trades = mint_trades_amount + damaged_trades_amount

        if total_trades > 0:
            match = Match(potential_match["_id"], give_mint, take_mint, give_damaged, take_damaged, mint_trades_amount, damaged_trades_amount, total_trades)
            matches.append(match)
            found = True
    if found:
        final_matches = []
        heapq.heapify(matches)
        for _ in range(min(len(matches), 5)):
            final_matches.append(heapq.heappop(matches))
        return final_matches
    else:
        return matches


# Returns indices of all True elements in array
def get_true_indices(array):
    return [i for i, x in enumerate(array) if x]


def get_sticker_name_by_id(sticker_id):
    return constants.stickers.get(sticker_id)


def format_sticker_matches(sticker_list, amount):
    final_string = constants.stickers.get(int(sticker_list[0]))
    for i in range(1, amount):
        final_string += f", {constants.stickers.get(int(sticker_list[i]))}"
    return final_string
