import discord # pip install py-cord
import json
import difflib
import re
import random as rnd
from datetime import datetime
from datetime import date
import time
import os
import math
import rolldice # pip install py-rolldice
from func_timeout import func_timeout, FunctionTimedOut # pip install func-timeout
import qrcode # pip install qrcode
import copy

def log(msg):
	print(date.today(), datetime.now().strftime("| %H:%M:%S |"), msg)

log("Initializing...")
boot_time = int(time.time())

bot = discord.Bot(activity=discord.Game(name='FIST: Ultra Edition'))

log("Loading token")
token_file = open('token.json')
token_file_data = json.load(token_file)
ownerid = token_file_data["owner_id"]
token = token_file_data["token"]
token_file.close()

log("Loading traits")
trait_file = open('traits.json')
trait_data = json.load(trait_file)
trait_file.close()

trait_file = open('secret_trait.json')
secret_trait = json.load(trait_file)
trait_file.close()

log("Loading roles")
role_file = open('roles.json')
role_data = json.load(role_file)
role_file.close()

log("Creating role and trait metadata")
trait_names = []
traits_by_name = {}
traits_by_number = {}
traits_by_numstr = {}
for trait in trait_data:
	trait_names.append(trait["Name"])
	traits_by_name[trait["Name"]] = trait
	traits_by_number[trait["Number"]] = trait
	traits_by_numstr[str(trait["Number"])] = trait

role_names = []
roles_by_name = {}
roles_by_number = {}
roles_by_numstr = {}
for role in role_data:
	role_names.append(role["Name"])
	roles_by_name[role["Name"]] = role
	roles_by_number[role["Number"]] = role
	roles_by_numstr[str(role["Number"])] = role

num_to_die = {
	1: "<:revolver_dice_1:1029946656277405726>",
	2: "<:revolver_dice_2:1029946657439223858>",
	3: "<:revolver_dice_3:1029946659087601714>",
	4: "<:revolver_dice_4:1029946660341690368>",
	5: "<:revolver_dice_5:1029946661541269554>",
	6: "<:revolver_dice_6:1029946662531113011>"
}

log("Defining helper functions")
def d6():
	return rnd.randint(1,6)

def trait_message_format(trait):
	return f"**{trait['Name']}** ({trait['Number']})\n{trait['Effect']}\n- {trait['Item']}, {trait['Stat']}"

def role_message_format(role):
	return f"**{role['Name']}** ({role['Number']})\n{role['Text']}"

def search_for_trait(trait):
	message = ""
	trait = trait.upper()
	if re.match("^\d+$", trait):
		number = int(trait)
		if number in traits_by_number:
			return trait_message_format(traits_by_number[number])
		else:
			return "No trait exists with the given number. Trait numbers must be possible d666 roll outputs."
	elif trait in traits_by_name:
		return trait_message_format(traits_by_name[trait])
	else:
		best_match = difflib.get_close_matches(trait.upper(), trait_names, n=1, cutoff=0.0)

		if len(best_match) > 0 and best_match[0] in traits_by_name:
			return trait_message_format(traits_by_name[best_match[0]])
		else:
			message = "Could not find a trait with an approximately similar name."
	return message

def search_for_role(role):
	message = ""
	role = role.upper()
	if re.match("^\d+$", role):
		number = int(role)
		if number in roles_by_number:
			return role_message_format(roles_by_number[number])
		else:
			return "No role exists with the given number. Role numbers must be possible d66 roll outputs."
	elif role in roles_by_name:
		return role_message_format(roles_by_name[role])
	else:
		best_match = difflib.get_close_matches(role.upper(), role_names, n=1, cutoff=0.0)

		if len(best_match) > 0 and best_match[0] in roles_by_name:
			return role_message_format(roles_by_name[best_match[0]])
		else:
			message = "Could not find a role with an approximately similar name."
	return message

def roll_intelligence_matrix(table):
	roll_type = table["Roll"].upper()
	if roll_type == "2D6":
		roll_result = d6() + d6()
		return table["Values"][str(roll_result)]
	else:
		return rnd.choice(list(table["Values"].values()))

def roll_all_matrices(table_list):
	out = []
	for table in table_list:
		out.append(roll_intelligence_matrix(table))
	return out
	
def decap_first(string):
	if len(string) > 1:
		if string[1].islower() or not string[1].isalpha():
			return string[0].lower() + string[1:]
	return string

def remove_duplicates(lst):
	return list(set(lst))

def roll_extra_possibility(input_string):
	regex_pattern = r"(.+)\s\((\d+)-in-1D6:\s(.+)\)"
	match = re.match(regex_pattern, input_string)
	if match:
		standard = match.group(1)
		num = int(match.group(2))
		alt = match.group(3)
		roll_result = rnd.randint(1, 6)
		if roll_result <= num:
			return f"{standard} *({alt})*"
		else:
			return standard
	else:
		return input_string

support_server_id = 1101249440230154300
support_server_obj = None

log("Loading user character data")
character_data = {}
if os.path.exists('player_data.json'):
	file = open('player_data.json')
	character_data = json.load(file)
	file.close()
else:
	log("Player data does not exist. Using empty data.")

reporting_channel = 1101250179899867217
async def save_character_data():
	try:
		with open("player_data.json", "w") as outfile:
			outfile.write(json.dumps(character_data,indent=2))
		total_users = 0
		total_characters = 0
		total_traits = 0
		for userid in character_data:
			total_users += 1
			total_characters += len(character_data[userid]['chars'])
			total_traits += len(character_data[userid]['traits'])
		log(f"Character data saved. Storing data about {total_characters} characters & {total_traits} custom traits created by {total_users} users")
	except Exception as e:
		log(f"PLAYER DATA SAVING THREW AN ERROR: {e}")
		report_channel = await bot.fetch_channel(reporting_channel)
		await report_channel.send(f"**<@{ownerid}> An error occurred while saving character data!**\n```{e}```")

log("Creating generic commands")
@bot.event
async def on_ready():

	log("Checking to see if character data needs to be updated...")
	changed = False
	for player in character_data:
		if 'traits' not in character_data[player]:
			character_data[player]['traits'] = {}
			log(f"{player} updated to include custom traits field")
			changed = True
	
	if changed:
		await save_character_data()

	try:
		log("Checking for support server...")
		support_server_obj = await bot.fetch_guild(support_server_id)
		log("Support server found")
	except Exception as e:
		log(f"Support server could not be found: {e}")
		support_server_obj = None
	log(f"{bot.user} is ready and online!")
	boot_time = int(time.time())

@bot.command(description="Checks how long the bot has been online")
async def uptime(ctx):
	log("/uptime")
	await ctx.respond(f"Online since <t:{boot_time}:D> at <t:{boot_time}:T> (<t:{boot_time}:R>)",ephemeral=True)

@bot.command(description="Measures this bot's latency")
async def ping(ctx):
	log("/ping")
	await ctx.respond(f"Pong! Latency is {bot.latency}")

@bot.command(description="Shuts down the bot. Will not work unless you own the bot.")
async def shutdown(ctx):
	log(f"/shutdown ({ctx.author.id})")
	if ctx.author.id == ownerid:
		await save_character_data()
		await ctx.respond(f"Restarting.")
		await bot.close()
	else:
		await ctx.respond(f"Only <@{ownerid}> may use this command.",ephemeral=True)

@bot.command(description="Links to the Help document for this bot")
async def help(ctx):
	log("/help")
	await ctx.respond("[Full command documentation](https://docs.google.com/document/d/15pm5o5cJuQF_J3l-NMpziPEuxDkcWJVE3TNT7_IerbQ/edit?usp=sharing)",ephemeral=True)

@bot.command(description="Links to the invite page for this bot")
async def invite(ctx):
	log("/invite")
	await ctx.respond("[Invite page](https://discord.com/api/oauth2/authorize?client_id=1096635021395251352&permissions=274877908992&scope=bot%20applications.commands)",ephemeral=True)

@bot.command(description="Links to the support server for this bot")
async def server(ctx):
	log("/server")
	await ctx.respond("https://discord.gg/VeedQmQc7k",ephemeral=True)

@bot.command(description="Pin (or unpin) a message inside a thread, if you own the thread")
async def threadpin(ctx, id: discord.Option(str, "The ID of the message to pin.", required=True)):
	log(f"/threadpin {id}")
	try:
		channel = ctx.channel
		if type(channel) != discord.Thread:
			await ctx.respond("This command does not work outside of a thread.",ephemeral=True)
		elif channel.owner_id != ctx.author.id:
			await ctx.respond(f"Only <@{channel.owner_id}> may use that command within this thread.",ephemeral=True)
		else:
			id = int(id.strip())
			msg = await channel.fetch_message(id)
			if not msg.pinned:
				await msg.pin(reason=f"/threadpin performed by {ctx.author.name}#{ctx.author.discriminator}")
				await ctx.respond(f"📌 Pinned a message: {msg.jump_url}")
			else:
				await msg.unpin(reason=f"/threadpin performed by {ctx.author.name}#{ctx.author.discriminator}")
				await ctx.respond(f"❌ Unpinned a message: {msg.jump_url}")
	except discord.Forbidden as e:
		log(f"Caught: {e}")
		await ctx.respond(f"There was an error processing this command:\n```{e}```\nThis command does not function properly by default. This bot must have **manage messages** permission.")
	except (discord.NotFound,ValueError) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"There was an error processing this command:\n```{e}```\nYou must provide a valid message ID. Check [this article](<https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->) for more details.")
	except Exception as e:
		log(f"Caught: {e}")
		await ctx.respond(f"There was an error processing this command:\n```{e}```")

@bot.command(description="Roll 1d66")
async def d66(ctx, instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1)):
	log(f"/d66 {instances}")
	outs = []
	
	if instances > 1000:
		await ctx.respond("Please roll 1000 or less instances.",ephemeral=True)
		return
	elif instances < 1:
		instances = 1
	
	for i in range(instances):
		outs.append(str(d6()) + str(d6()))
	message = ", ".join(outs)
	if len(message) > 2000:
		message = message.replace("*","").replace("# ","")
		with open("message.txt","w") as file:
			file.write(message)
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'))
		os.remove('message.txt')
		log("Sent character sheet as file")
	else:
		await ctx.respond(message)

@bot.command(description="Roll 1d666")
async def d666(ctx, instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1)):
	log(f"/d666 {instances}")
	outs = []

	if instances > 1000:
		await ctx.respond("Please roll 1000 or less instances.",ephemeral=True)
		return
	elif instances < 1:
		instances = 1

	for i in range(instances):
		outs.append(str(d6()) + str(d6()) + str(d6()))
	message = ", ".join(outs)
	if len(message) > 2000:
		message = message.replace("*","").replace("# ","")
		with open("message.txt","w") as file:
			file.write(message)
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'))
		os.remove('message.txt')
		log("Sent character sheet as file")
	else:
		await ctx.respond(message)

# character_data structure:
# - main object is a dict, keys are user IDs
# - user IDs point to dicts with 2 keys: "active" and "chars"
# - "chars" is a dict that contains all characters, with keys being codenames
# - "active" is a dict; keys are channel IDs, values are character codenames

def output_character(codename, data):
	out = f"# {codename.upper()}"
	if data["role"] == {}:
		out += "\nROLE: *No role yet.*"
	else:
		r = data["role"]
		out += f"\nROLE: **{r['Name']}**\n{r['Text']}"
	
	out += f"\n\nHP: {data['hp']}/{data['maxhp']}"
	out += f"\nWAR DICE: {data['wd']}"
	out += f"\nARMOR: {data['armor_name']} ({data['armor']})"
	out += f"\nWEAPON: {data['weapon_name']} ({data['damage']})"
	
	if data['frc'] != 0 or data['tac'] != 0 or data['cre'] != 0 or data['rfx'] != 0:
		out += "\n"
	
	if data['frc'] != 0:
		out += f"\nFRC: {'+' if data['frc'] > 0 else ''}{data['frc']}"
	if data['tac'] != 0:
		out += f"\nTAC: {'+' if data['tac'] > 0 else ''}{data['tac']}"
	if data['cre'] != 0:
		out += f"\nCRE: {'+' if data['cre'] > 0 else ''}{data['cre']}"
	if data['rfx'] != 0:
		out += f"\nRFX: {'+' if data['rfx'] > 0 else ''}{data['rfx']}"
	
	out += "\n\nTRAITS:\n"
	if len(data['traits']) <= 0:
		out += "- *No traits yet.*"
	else:
		for trait in data['traits']:
			out += f"- **{trait['Name']}** ({trait['Number']}): {trait['Effect']} ({trait['Stat']})\n"
	
	out += "\nITEMS:"
	if len(data['items']) <= 0:
		out += "\n- *No items yet.*"
	else:
		for item in data['items']:
			out += f"\n- {item}"
	return out

def get_active_codename(ctx):
	uid = str(ctx.author.id)
	if uid in character_data:
		your_actives = character_data[uid]['active']
		if str(ctx.channel_id) in your_actives:
			return your_actives[str(ctx.channel_id)]
	return None

def get_active_char_object(ctx):
	codename = get_active_codename(ctx)
	if codename == None:
		return None
	else:
		return character_data[str(ctx.author.id)]['chars'][codename]

async def roll_with_skill(ctx, extra_mod, superior_dice, inferior_dice, stat):
	log(f"/{stat.lower()} {' superior_dice' if superior_dice else ''}{' inferior_dice' if inferior_dice else ''}")
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	modifier = character[stat.lower()] + extra_mod
	
	results = [d6(), d6()]
	if superior_dice ^ inferior_dice:
		results.append(d6())
	
	dice_string = ""
	for d in results:
		dice_string += " " + num_to_die[d]
	dice_string = dice_string.strip()
	
	sorted_results = sorted(results)
	if superior_dice and not inferior_dice:
		results = sorted_results[-2:]
	elif inferior_dice and not superior_dice:
		results = sorted_results[:2]
	
	total = sum(results) + modifier
	
	message = f"**{codename.upper()}** rolling +{stat.upper()}:\n> "
	
	if extra_mod != 0:
		message += f"({dice_string}) + {character[stat.lower()]} ({stat.upper()}) + {extra_mod} (bonus) = **{total}**: "
	else:
		message += f"({dice_string}) + {character[stat.lower()]} ({stat.upper()}) = **{total}**: "
	
	if results == [6,6]:
		message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
	elif total <= 6:
		message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
	elif total <= 9:
		message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
	else:
		message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."
	await ctx.respond(message)

async def character_names_autocomplete(ctx: discord.AutocompleteContext):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		return list(character_data[uid]['chars'].keys())
	else:
		return []

async def ext_character_management(id):
	if id == str(ownerid):
		return True
	if support_server_obj is None:
		return False
	user = await support_server.fetch_member(id)
	if user is None:
		return False
	role = user.get_role(1120763025465557062)
	if role is None:
		return False
	return True

async def traits_and_customs_autocomp(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		user_traits = sorted(list(character_data[uid]['traits'].keys()))
		return user_traits + trait_names
	else:
		return trait_names

async def current_trait_item_autocomp(ctx):
	cur_traits_by_name = traits_by_name | character_data[str(ctx.interaction.user.id)]['traits']
	lookup_trait = ctx.options['trait']
	found_trait = None
	if lookup_trait == "ABRACADABRA":
		found_trait = secret_trait
	elif lookup_trait in cur_traits_by_name:
		found_trait = cur_traits_by_name[lookup_trait]
	elif lookup_trait in traits_by_numstr:
		found_trait = traits_by_numstr[lookup_trait]
	
	if found_trait is None:
		return []
	else:
		item_split = found_trait['Item'].split(' (')
		return [item_split[0]]

@bot.command(description="Add a core book trait to your active character")
async def add_trait(ctx, 
	trait: discord.Option(str, "The core book name or number of the trait to add.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=True),
	rename_item: discord.Option(str, "Renames the item this trait provides. Autocomplete displays the item's default name.",autocomplete=discord.utils.basic_autocomplete(current_trait_item_autocomp), required=False, default=None)):
	log(f"/add_trait {trait}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	if len(character['traits']) >= trait_limit:
		await ctx.respond(f"Characters cannot have more than {trait_limit} traits.",ephemeral=True)
		return
	
	trait = trait.upper()
	current_traits_by_name = traits_by_name | character_data[str(ctx.author.id)]['traits']
	
	my_new_trait = None
	if trait == "ABRACADABRA":
		my_new_trait = secret_trait
	elif trait in current_traits_by_name:
		my_new_trait = current_traits_by_name[trait]
	elif trait in traits_by_numstr:
		my_new_trait = traits_by_numstr[trait]
	
	if my_new_trait == None:
		await ctx.respond(f'No trait with the exact name or D666 number "{trait.upper()}" exists. Double-check your spelling.',ephemeral=True)
		return
	
	for existing_trait in character['traits']:
		if existing_trait['Name'] == my_new_trait['Name']:
			await ctx.respond(f'**{codename.upper()}** already has the trait **{my_new_trait["Name"]} ({my_new_trait["Number"]})**.',ephemeral=True)
			return
	
	my_new_trait = copy.deepcopy(my_new_trait)
	if rename_item is not None:
		if '(' in rename_item or ')' in rename_item:
			await ctx.respond("For organizational reasons, please do not use parenthesis in item names.",ephemeral=True)
			return
		else:
			old_item = my_new_trait['Item'].split(' (')
			old_item[0] = rename_item
			new_item = ' ('.join(old_item)
			my_new_trait['Item'] = new_item
	
	character['traits'].append(my_new_trait)
	character['items'].append(my_new_trait['Item'])
	
	stats = ["MAX","WAR","FORCEFUL","TACTICAL","CREATIVE","REFLEXIVE"]
	
	stats_translator = {
		"MAX":"maxhp",
		"WAR":"wd",
		"FORCEFUL":"frc",
		"TACTICAL":"tac",
		"CREATIVE":"cre",
		"REFLEXIVE":"rfx"
	}
	
	old_max_hp = character['maxhp']
	
	bonus = my_new_trait["Stat"].split(" ")
	num = 0
	if bonus[1] in stats:
		translated_stat_bonus = stats_translator[bonus[1]]
		try: 
			num = rolldice.roll_dice(bonus[0])[0]
		except Exception as e:
			num = 0
			log(f"Caught dice-rolling exception: {e}")
		character[translated_stat_bonus] += num
		if translated_stat_bonus == 'maxhp':
			character['hp'] += num
	
	out = f"**{codename.upper()}** has gained a trait!"
	if old_max_hp > character['maxhp'] and character['maxhp'] <= 0:
		out += f"\n**This character now has a Max HP of {character['maxhp']}!!**"
	out += f"\n>>> {trait_message_format(my_new_trait)}"
	await ctx.respond(out)
	await save_character_data()

standard_character_limit = 10
premium_character_limit = 50

@bot.command(description="Create a new character to manage")
async def create_character(ctx, codename: discord.Option(str, "The character's codename, used for selecting them with other commands.",required=True),
	starter_trait_1: discord.Option(str, "The core book name or number of a trait to add to the character immediately.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None),
	starter_trait_2: discord.Option(str, "The core book name or number of a trait to add to the character immediately.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None),
	set_as_active: discord.Option(bool, "If TRUE, the new character will become your active character in this channel. FALSE by default.", required=False, default=True)):
	log(f"/create {codename} {starter_trait_1 if starter_trait_1 is not None else '[no first trait]'} {starter_trait_2 if starter_trait_2 is not None else '[no second trait]'} {'set_as_active' if set_as_active else ''}")
	userid = str(ctx.author.id)
	
	name_limit = 50
	if len(codename) > name_limit:
		await ctx.respond(f"Codenames must be no longer than {name_limit} characters.",ephemeral=True)
		return
	
	if userid not in character_data:
		character_data[userid] = {
			"active": {},
			"chars": {},
			"traits": {}
		}
	
	premium_character = False
	if len(character_data[userid]["chars"]) >= standard_character_limit:
		premium_user = await ext_character_management(userid)
		if not premium_user:
			await ctx.respond(f"You may not create more than {standard_character_limit} characters.\nYou can increase your character limit to {premium_character_limit} by enrolling in a [server subscription](<https://discord.com/servers/sonder-s-garage-1101249440230154300>) at Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
			return
		elif len(character_data[userid]["chars"]) >= premium_character_limit:
			await ctx.respond(f"You may not create more than {premium_character_limit} characters.",ephemeral=True)
			return
		else:
			premium_character = True
	
	codename = codename.lower()
	if codename in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the codename '{codename}'.",ephemeral=True)
		return
	
	character_data[userid]["chars"][codename] = {
		"role": {},
		"maxhp": 6,
		"hp": 6,
		"wd": 0,
		"frc": 0,
		"tac": 0,
		"rfx": 0,
		"cre": 0,
		"weapon_name": "Unarmed",
		"damage": "2d6k1",
		"armor_name": "Nothing",
		"armor": 0,
		"traits": [],
		"items": [],
		"premium": premium_character,
		"creation_time": time.time()
	}
	
	msg = f"Created character with the codename '{codename}'."
	msg += f"\nYou now have {len(character_data[userid]['chars'])} characters."
	if premium_character:
		msg += "\n*This character uses a premium slot!*"
	await ctx.respond(msg)
	if set_as_active:
		await switch_character(ctx, codename)
	if starter_trait_1 is not None:
		await add_trait(ctx, starter_trait_1, None)
	if starter_trait_2 is not None:
		await add_trait(ctx, starter_trait_2, None)
	if not set_as_active and not starter_trait_1 and not starter_trait_2:
		await save_character_data()
	
@bot.command(description="Make a copy of an existing character")
async def clone(ctx,
	codename: discord.Option(str, "The codename of the character to duplicate.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	new_codename: discord.Option(str, "The new codename of the duplicated character.",required=True)):
	log(f"/clone {codename} {new_codename}")
	userid = str(ctx.author.id)
	
	name_limit = 50
	if len(new_codename) > name_limit:
		await ctx.respond(f"Codenames must be no longer than {name_limit} characters.",ephemeral=True)
		return
	
	codename = codename.lower()
	if userid not in character_data or codename not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'. You can view what characters you've made with `/list`. Check your spelling, or try creating a new one with `/create`.",ephemeral=True)
		return
	
	premium_character = False
	if len(character_data[userid]["chars"]) >= standard_character_limit:
		premium_user = await ext_character_management(userid)
		if not premium_user:
			await ctx.respond(f"You may not create more than {standard_character_limit} characters.\nYou can increase your character limit to {premium_character_limit} by enrolling in a [server subscription](<https://discord.com/servers/sonder-s-garage-1101249440230154300>) at Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
			return
		elif len(character_data[userid]["chars"]) >= premium_character_limit:
			await ctx.respond(f"You may not create more than {premium_character_limit} characters.",ephemeral=True)
			return
		else:
			premium_character = True
	
	new_codename = new_codename.lower()
	if new_codename in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the codename '{codename}'.",ephemeral=True)
		return
	
	character_data[userid]['chars'][new_codename] = copy.deepcopy(character_data[userid]['chars'][codename])
	character_data[userid]['chars'][new_codename]['premium'] = premium_character
	
	msg = f"Cloned character with the codename '{codename}' with new codename '{new_codename}'."
	msg += f"\nYou now have {len(character_data[userid]['chars'])} characters."
	if premium_character:
		msg += "\n*This character uses a premium slot!*"
	await ctx.respond(msg)
	await switch_character(ctx, new_codename)
	

@bot.command(description="Delete a character from your roster")
async def delete_character(ctx, codename: discord.Option(str, "The character's codename, used for selecting them with other commands.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True),
	i_am_sure: discord.Option(bool, "Confirmation that you want the character deleted.", required=True),
	i_am_very_sure: discord.Option(bool, "Confirmation that you want the character deleted.", required=True),
	i_am_completely_absolutely_sure: discord.Option(bool, "Confirmation that you want the character deleted.", required=True)):
	log(f"/delete {codename}{' affirmative' if i_am_sure else ''}{' affirmative' if i_am_very_sure else ''}{' affirmative' if i_am_completely_absolutely_sure else ''}")
	
	if i_am_sure and i_am_very_sure and i_am_completely_absolutely_sure:
		yourid = str(ctx.author.id)
		codename = codename.lower()
		if yourid not in character_data:
			await ctx.respond("You do not have any character data to delete.",ephemeral=True)
			return
		yourstuff = character_data[yourid]
		if codename not in yourstuff['chars']:
			await ctx.respond(f"You do not have a character named '{codename}' to delete.",ephemeral=True)
			return
		else:
			message = f"Successfully deleted **{codename.upper()}**."
			was_premium = yourstuff['chars'][codename]['premium']
			del yourstuff['chars'][codename]
			channel_unbinds = 0
			keys_to_purge = []
			for key in yourstuff['active']:
				if yourstuff['active'][key] == codename:
					channel_unbinds += 1
					keys_to_purge.append(key)
			if channel_unbinds > 0:
				message += f"\nThis action has cleared your active character across {channel_unbinds} channels:"
			for key in keys_to_purge:
				message += f" <#{key}>"
				del yourstuff['active'][key]
			
			earliest_time = math.inf
			earliest_premium_char = None
			earliest_prem_codename = None
			if not was_premium:
				for codename in yourstuff['chars']:
					if yourstuff['chars'][codename]['premium'] and yourstuff['chars'][codename]['creation_time'] < earliest_time:
						earliest_time = yourstuff['chars'][codename]['creation_time']
						earliest_premium_char = yourstuff['chars'][codename]
						earliest_prem_codename = codename
				if earliest_premium_char is not None:
					earliest_premium_char['premium'] = False
					message += f"\nYou have freed up a non-premium slot. **{codename.upper()}** is no longer a premium character."
			
			if len(yourstuff['chars']) <= 0 and len(yourstuff['traits']) <= 0:
				del character_data[yourid]
				message += "\nYou no longer have any characters or traits. All data associated with your User ID has been deleted."
			else:
				message += f"\nYou now have {len(yourstuff['chars'])} characters."
				
			await ctx.respond(message)
			await save_character_data()
	else:
		await ctx.respond("You must triple-confirm that you want to delete your character.",ephemeral=True)

@bot.command(description="List all characters you've created")
async def my_characters(ctx):
	log("/my_characters")
	yourid = str(ctx.author.id)
	if yourid in character_data and len(character_data[yourid]['chars']) > 0:
		yourchars = character_data[yourid]['chars']
		msg = f"Characters created by <@{yourid}> ({len(yourchars)}):"
		for codename in yourchars:
			char_traits = character_data[yourid]['chars'][codename]['traits']
			msg += f"\n- **{codename.upper()}**"
			if len(char_traits) > 0:
				char_trait_names = []
				for t in char_traits:
					char_trait_names.append(t['Name'])
				msg += f" ({'/'.join(char_trait_names)})"
			else:
				msg += f" (No traits)"
			if yourchars[codename]['premium']:
				msg += " *(premium)*"
		if len(msg) > 2000:
			msg = msg.replace("*","")
			with open("message.txt","w") as file:
				file.write(msg)
			await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'))
			os.remove('message.txt')
			log("Sent character sheet as file")
		else:
			await ctx.respond(msg)
	else:
		await ctx.respond("You haven't created any characters yet.",ephemeral=True)
	
@bot.command(description="Displays your current active character's sheet")
async def sheet(ctx, codename: discord.Option(str, "The codename of a specific character to view instead.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=False, default=""), qr: discord.Option(bool, "Sends a QR code of the final output instead.", required=False, default=False)):
	log(f"/sheet {codename}")
	codename = codename.lower()
	yourid = str(ctx.author.id)
	if codename == "":
		codename = get_active_codename(ctx)
	if codename == None:
		await ctx.respond("You have not set an active character in this channel. Either set your active character with `/switch`, or specify which character's sheet you want to view using the optional `codename` argument for this command.",ephemeral=True)
		return
	if yourid not in character_data or codename not in character_data[yourid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'. You can view what characters you've made with `/list`. Check your spelling, or try creating a new one with `/create`.",ephemeral=True)
		return
	
	ch = character_data[yourid]['chars'][codename]
	message = output_character(codename, ch)
	if qr:
		message = message.replace("*","").replace("# ","")
		if len(message) > 2331:
			await ctx.respond(f"Cannot produce a QR code that encodes more than 2331 characters. Requested sheet is {len(message)} characters.",ephemeral=True)
		else:
			img = qrcode.make(message)
			img.save('qr.png')
			await ctx.respond(f"QR code of character sheet for **{codename.upper()}**:",file=discord.File('qr.png'))
			os.remove('qr.png')
	else:
		if len(message) > 2000:
			message = message.replace("*","").replace("# ","")
			with open("message.txt","w") as file:
				file.write(message)
			await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'))
			os.remove('message.txt')
			log("Sent character sheet as file")
		else:
			await ctx.respond(message)

@bot.command(description="Switch which character is active in this channel")
async def switch_character(ctx, codename: discord.Option(str, "The codename of the character to switch to.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True)):
	log(f"/switch {codename}")
	userid = str(ctx.author.id)
	if userid not in character_data or len(character_data[userid]['chars']) <= 0:
		await ctx.respond("You have no characters available. Use `/create` to make one.",ephemeral=True)
		return
		
	codename = codename.lower()
	if codename not in character_data[userid]["chars"]:
		await ctx.respond(f"You have not created a character with the codename '{codename}'. You can view what characters you've made with `/list`. Check your spelling, or try creating a new one with `/create`.",ephemeral=True)
		return
	else:
		character_data[userid]['active'][str(ctx.channel_id)] = codename
		await ctx.respond(f"Your active character in this channel is now **{codename.upper()}**.")
		await save_character_data()
	return

@bot.command(description="Check your current active character")
async def active_character(ctx, show_all: discord.Option(bool, "If TRUE, lists all channels you have active characters in. FALSE by default.", required=False, default=False)):
	log(f"/active_character{' show_all' if show_all else ''}")
	if show_all:
		your_actives = character_data[str(ctx.author.id)]['active']
		if len(your_actives) > 0:
			message = f"Your characters are active in the following {len(your_actives)} channels:"
			for channel in your_actives:
				message += f"\n- <#{channel}> -> {your_actives[channel].upper()}"
			if len(message) < 2000:
				await ctx.respond(message,ephemeral=True)
			else:
				message = f"Your characters are active in the following {len(your_actives)} channels:"
				for channel in your_actives:
					try:
						channel_object = await bot.fetch_channel(int(channel))
						channel_name = channel_object.name
						message += f"\n- #{channel_name} ({channel}) -> {your_actives[channel].upper()}"
					except Exception as e:
						log(f"Could not resolve name of channel {channel}")
						message += f"\n- Unknown channel ({channel}) -> {your_actives[channel].upper()}"
				with open("message.txt","w") as file:
					file.write(message)
				await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'),ephemeral=True)
				os.remove('message.txt')
				log("Sent actives list as file")
		else:
			await ctx.respond(f"You do not have active characters in any channels.",ephemeral=True)
	else:
		codename = get_active_codename(ctx)
		if codename != None:
			await ctx.respond(f"Your active character in this channel is **{codename.upper()}**.",ephemeral=True)
		else:
			await ctx.respond(f"You do not have an active character in this channel.",ephemeral=True)

async def role_autocomp(ctx):
	return role_names

@bot.command(description="Set your active character's role")
async def set_role(ctx,
	name: discord.Option(str,"The name of your role.",autocomplete=discord.utils.basic_autocomplete(role_autocomp),required=True),
	description: discord.Option(str,"The role's description.",required=True)):
	log(f"/set_role '{name}' '{description}'")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	name = name.upper()
	character['role'] = {
		"Name": name,
		"Text": description
	}
	
	out = f"**{codename.upper()}** has changed their role:"
	out += f"\n>>> **{name}**\n{description}"
	await ctx.respond(out)
	await save_character_data()

async def trait_autocomp(ctx):
	return trait_names

trait_limit = 15

async def stat_type_autocomp(ctx):
	return ["CREATIVE","FORCEFUL","TACTICAL","REFLEXIVE","MAX HP","to chosen attribute","WAR DIE per mission","ARMOR at all times","when you roll WAR DICE","DAMAGE with melee weapons","DAMAGE with ranged weapons"]

async def stat_amount_autocomp(ctx):
	return ["+1","-1","+2","-2","+1D6","-1D6"]

standard_custrait_limit = 2 * standard_character_limit
premium_custrait_limit = 2 * premium_character_limit

@bot.command(description="Create a custom trait")
async def create_custom_trait(ctx,	
		title: discord.Option(str, "The name of the trait", required=True), 
		description: discord.Option(str, "The trait's description", required=True),
		stat_type: discord.Option(str, "The stat this trait changes", autocomplete=discord.utils.basic_autocomplete(stat_type_autocomp), required=True),
		stat_amount: discord.Option(str, "The amount that the stat is changed (accepts dice syntax)", autocomplete=discord.utils.basic_autocomplete(stat_amount_autocomp), required=True),
		item_name: discord.Option(str, "The name of the item that this trait grants you", required=True),
		item_effect: discord.Option(str, "The effect of the item that this trait grants you", required=True)):
	userid = str(ctx.author.id)
	log(f"/create_custom_trait {title} {description} {stat_type} {stat_amount} {item_name} {item_effect}")
	
	if userid in character_data and len(character_data[userid]['traits']) >= standard_custrait_limit:
		premium_user = await ext_character_management(userid)
		if not premium_user:
			await ctx.respond(f"You may not create more than {standard_custrait_limit} custom traits.\nYou can increase your custom trait limit to {premium_custrait_limit} by enrolling in a [server subscription](<https://discord.com/servers/sonder-s-garage-1101249440230154300>) at Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
			return
		elif len(character_data[userid]['traits']) >= premium_custrait_limit:
			await ctx.respond(f"You may not create more than {premium_custrait_limit} custom traits.",ephemeral=True)
			return
	
	if stat_amount[0] not in ['+','-']:
		stat_amount = '+' + stat_amount
	
	title = title.upper()
	
	concat = item_name+item_effect
	if "(" in concat or ")" in concat:
		await ctx.respond("For organizational reasons, please do not use parenthesis in the `item_name` or `item_effect`.\nTo include an item's effect, use the `item_effect` argument for this command instead.",ephemeral=True)
		return
	
	if title in traits_by_name:
		await ctx.respond(f"**{title}** already exists in the core book.",ephemeral=True)
		return
	elif title in ["MAGICIAN","ABRACADABRA"]:
		await ctx.respond(f"**{title}** is a reserved name.",ephemeral=True)
		return
	elif userid in character_data and title in character_data[userid]['traits']:
		await ctx.respond(f"You have already made a trait called **{title}**.",ephemeral=True)
		return
	
	new_trait = {
		"Number": "Custom",
		"Name": title,
		"Effect": description,
		"Item": f"{item_name} ({item_effect})",
		"Stat": f"{stat_amount} {stat_type}"
	}
	
	roll_dice_failure = False
	try:
		rolldice.roll_dice(stat_amount)
	except Exception as e:
		log(f"Caught dice-rolling exception: {e}")
		roll_dice_failure = True
	
	if userid not in character_data:
		character_data[userid] = {
			"active": {},
			"chars": {},
			"traits": {}
		}
	
	character_data[userid]['traits'][title] = new_trait
	
	out = f"Created the custom trait {title}."
	out += f"\nYou now have {len(character_data[userid]['traits'])} custom traits.\n>>> "
	out += trait_message_format(new_trait)
	await ctx.respond(out)
	await save_character_data()

async def custom_traits_list_autocomp(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		return list(character_data[uid]['traits'].keys())
	else:
		return []

@bot.command(description="Delete one of your custom traits")
async def delete_custom_trait(ctx,	
		name: discord.Option(str, "The name of the trait to delete",autocomplete=discord.utils.basic_autocomplete(custom_traits_list_autocomp), required=True)):
	log(f"/delete_custom_trait {name}")
	uid = str(ctx.author.id)
	if uid not in character_data or len(character_data[uid]['traits']) <= 0:
		await ctx.respond("You do not have any custom traits on file.",ephemeral=True)
		return
	
	yourtraits = character_data[uid]['traits']
	name = name.upper()
	if name not in yourtraits:
		await ctx.respond(f"You do not have a custom trait called {name}.",ephemeral=True)
	
	del yourtraits[name]

	message = f"Successfully deleted custom trait {name}."
	if len(character_data[uid]['chars']) <= 0 and len(character_data[uid]['traits']) <= 0:
		del character_data[uid]
		message += "\nYou no longer have any characters or traits. All data associated with your User ID has been deleted."
	else:
		message += f"\nYou now have {len(character_data[uid]['traits'])} custom traits."
	
	await ctx.respond(message)
	await save_character_data()

@bot.command(description="View your custom traits")
async def my_traits(ctx, name: discord.Option(str, "The name of a specific trait to view",autocomplete=discord.utils.basic_autocomplete(custom_traits_list_autocomp), required=False, default=None)):
	log(f"/my_traits {name if name is not None else ''}")
	uid = str(ctx.author.id)
	if uid not in character_data or len(character_data[uid]['traits']) <= 0:
		await ctx.respond("You do not have any custom traits on file.",ephemeral=True)
		return
	
	yourtraits = character_data[uid]['traits']
	if name is None:
		msg = f"Custom traits created by <@{uid}> ({len(yourtraits)}):"
		for t in yourtraits:
			msg += f"\n- {t.upper()}"
		if len(msg) > 2000:
			msg = msg.replace("*","")
			with open("message.txt","w") as file:
				file.write(msg)
			await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'))
			os.remove('message.txt')
			log("Sent character sheet as file")
		else:
			await ctx.respond(msg)
	else:
		name = name.upper()
		if name not in yourtraits:
			await ctx.respond(f"You do not have a custom trait called {name}.",ephemeral=True)
		else:
			await ctx.respond(trait_message_format(yourtraits[name]))

item_limit = 50

@bot.command(description="Add an item your active character")
async def add_item(ctx,
		name: discord.Option(str, "The name of the item", required=True), 
		effect: discord.Option(str, "The effect of the item", required=False, default="")):
	log(f"/add_item {name} {effect}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	if len(character['items']) >= item_limit:
		await ctx.respond(f"Characters cannot carry more than {item_limit} items.",ephemeral=True)
		return
	
	concat = name+effect
	if "(" in concat or ")" in concat:
		await ctx.respond("For organizational reasons, please do not use parenthesis in the `name` or `effect` of your item.\nTo include an item's effect, use the optional `effect` argument for this command instead.",ephemeral=True)
		return
	
	item_to_add = name
	if len(effect) > 0:
		item_to_add += f" ({effect})"
	
	character['items'].append(item_to_add)
	
	await ctx.respond(f"**{codename.upper()}** has added **{item_to_add}** to their inventory.")
	await save_character_data()

async def active_character_traits_autocomp(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		# gotta get active character manually cus this is a different kind of ctx. ugh
		your_actives = character_data[uid]['active']
		if str(ctx.interaction.channel_id) in your_actives:
			current_active = your_actives[str(ctx.interaction.channel_id)]
			if current_active in character_data[uid]['chars']:
				current_char = character_data[uid]['chars'][current_active]
				trait_list = current_char['traits']
				output = []
				for trait in trait_list:
					output.append(trait['Name'])
				return output
			else:
				return []
		else:
			return []
	else:
		return []

@bot.command(description="Remove a trait from your active character")
async def remove_trait(ctx, trait: discord.Option(str, "The name of the trait to remove.",autocomplete=discord.utils.basic_autocomplete(active_character_traits_autocomp), required=True),
	keep_item: discord.Option(bool, "If TRUE, the Trait's associated item will not be removed from your inventory.", required=False, default=False)):
	
	log(f"/remove_trait {trait}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	if len(character['traits']) <= 0:
		await ctx.respond(f"{codename.upper()} does not have any traits.",ephemeral=True)
		return
	
	target_trait = None
	for current in character['traits']:
		if current['Name'].lower() == trait.lower():
			target_trait = current
			break
	
	if target_trait == None:
		await ctx.respond(f"{codename.upper()} does not a trait called '{trait}'.",ephemeral=True)
		return
	else:
		stats = ["MAX","WAR","FORCEFUL","TACTICAL","CREATIVE","REFLEXIVE"]
		
		stats_translator = {
			"MAX":"maxhp",
			"WAR":"wd",
			"FORCEFUL":"frc",
			"TACTICAL":"tac",
			"CREATIVE":"cre",
			"REFLEXIVE":"rfx"
		}
		
		bonus = target_trait["Stat"].split(" ")
		num = 0
		if bonus[1] in stats:
			translated_stat_bonus = stats_translator[bonus[1]]
			try: 
				num = rolldice.roll_dice(bonus[0])[0]
			except Exception as e:
				num = 0
				log(f"Caught dice-rolling exception: {e}")
			if translated_stat_bonus != 'wd':
				character[translated_stat_bonus] -= num
			if translated_stat_bonus == 'maxhp':
				character['hp'] -= num
	
		character['traits'].remove(target_trait)
		await ctx.respond(f"{codename.upper()} has lost the trait **{trait.upper()}**.")
		
		if not keep_item:
			try:
				character['items'].remove(target_trait['Item'])
			except ValueError as e:
				log("Caught ValueError in attempt to remove trait item")
		
		await save_character_data()
		return

async def full_item_autocomplete(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		# gotta get active character manually cus this is a different kind of ctx. ugh
		your_actives = character_data[uid]['active']
		if str(ctx.interaction.channel_id) in your_actives:
			current_active = your_actives[str(ctx.interaction.channel_id)]
			if current_active in character_data[uid]['chars']:
				current_char = character_data[uid]['chars'][current_active]
				return current_char['items']
			else:
				return []
		else:
			return []
	else:
		return []

@bot.command(description="Remove an item from your active character")
async def remove_item(ctx,
		item: discord.Option(str, "The item to be removed",autocomplete=discord.utils.basic_autocomplete(full_item_autocomplete), required=True)):
	log(f"/remove_item {item}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	if len(character['items']) <= 0:
		await ctx.respond(f"**{codename.upper()}** does not have any items.",ephemeral=True)
		return
	
	try:
		character['items'].remove(item)
	except ValueError as e:
		log(f"Caught ValueError: {e}")
		out = "The item that you wanted to remove could not be found. Your current items are:"
		for x in character['items']:
			out += "\n- x"
		await ctx.respond(out,ephemeral=True)
		return
	
	await ctx.respond(f"**{codename.upper()}** has removed **{item}** from their inventory.")
	await save_character_data()

@bot.command(description="Spend a War Die from your active character")
async def war_die(ctx):
	log(f"/war_die")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if character['wd'] > 0:
		character['wd'] -= 1
		result = d6()
		remaining = character['wd']
		await ctx.respond(f"**{codename.upper()}** spends a War Die: **{num_to_die[result]} ({result})**\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left.")
		await save_character_data()
	else:
		await ctx.respond(f"{codename.upper()} has no War Dice to spend!",ephemeral=True)

editable_stats = ["CURRENT HP","MAX HP","WAR DICE","FORCEFUL","TACTICAL","REFLEXIVE","CREATIVE","ARMOR"]
async def stats_autocomplete(ctx):
	return editable_stats

@bot.command(description="Adjust one of your character's stats")
async def adjust(ctx,
	stat: discord.Option(str, "The stat to change.", autocomplete=discord.utils.basic_autocomplete(stats_autocomplete), required=True),
	amount: discord.Option(str, "Amount to increase the stat by. Supports dice syntax. Negative values will decrease.", required=True)):
	log(f"/adjust {stat} {amount}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	stat = stat.upper()
	stats_translator = {
		"CURRENT HP":"hp",
		"MAX HP":"maxhp",
		"WAR DICE":"wd",
		"FORCEFUL":"frc",
		"TACTICAL":"tac",
		"REFLEXIVE":"rfx",
		"CREATIVE":"cre",
		"ARMOR":"armor"
	}
	
	if stat not in stats_translator:
		opts = ", ".join(editable_stats)
		await ctx.respond(f"There is no adjustable character stat called '{stat}'.\nYour options are: {opts}",ephemeral=True)
		return
	
	translated_stat = stats_translator[stat]
	output = ()
	timeout = 2
	try:
		output = func_timeout(timeout, rolldice.roll_dice, args=[amount])
	except rolldice.rolldice.DiceGroupException as e:
		log(f"Caught: {e}")
		await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return
	
	character[translated_stat] += output[0]
	
	message = f"{codename.upper()} has **{'in' if output[0] >= 0 else 'de'}creased** their **{stat}** by {abs(output[0])}!"
	if 'd' in amount or 'D' in amount:
		message += f"\n\nDice results: `{output[1]}`"
	
	await ctx.respond(message)
	await save_character_data()

@bot.command(description="Reset your active character's stats and items to the trait defaults")
async def refresh(ctx, 
	reset_hp: discord.Option(bool, "If TRUE, sets your base HP to 6 and recalculates it. FALSE by default.", required=False, default=False), 
	reset_war_dice: discord.Option(bool, "If TRUE, sets your War Dice to 0 and recalculates it. FALSE by default.", required=False, default=False)):
	log(f"/refresh {'reset_hp' if reset_hp else ''}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	weapon_reset = False
	if character['weapon_name'] != "Unarmed" or character['damage'] != "2d6k1":
		weapon_reset = True
	armor_reset = False
	if character['armor_name'] != "Nothing" or character['armor'] != 0:
		armor_reset = True
	
	character['frc'] = 0
	character['tac'] = 0
	character['rfx'] = 0
	character['cre'] = 0
	character['weapon_name'] = "Unarmed"
	character['damage'] = "2d6k1"
	character['armor_name'] = "Nothing"
	character['armor'] = 0
	
	if reset_hp:
		character['maxhp'] = 6
	if reset_war_dice:
		character['wd'] = 0
	
	stats = ["MAX","WAR","FORCEFUL","TACTICAL","CREATIVE","REFLEXIVE"]
	stats_translator = {
		"MAX":"maxhp",
		"WAR":"wd",
		"FORCEFUL":"frc",
		"TACTICAL":"tac",
		"CREATIVE":"cre",
		"REFLEXIVE":"rfx"
	}
	
	for trait in character['traits']:
		if trait['Item'] not in character['items']:
			character['items'].append(trait['Item'])
		
		bonus = trait["Stat"].split(" ")
		num = 0
		# bonus is ELSE (0) and user says no (0) -> 1
		# bonus is ELSE (0) and user says yes (1) -> 1
		# bonus is MAX (1) and user says no (0) -> 0
		# bonus is MAX (1) and user says yes (1) -> 1
		hp_adjust_is_ok = (not bonus[1] == 'MAX') or reset_hp
		wd_adjust_is_ok = (not bonus[1] == 'WAR') or reset_war_dice
		if bonus[1] in stats and hp_adjust_is_ok and wd_adjust_is_ok:
			translated_stat_bonus = stats_translator[bonus[1]]
			try: 
				num = rolldice.roll_dice(bonus[0])[0]
			except Exception as e:
				num = 0
				log(f"Caught dice-rolling exception: {e}")
			character[translated_stat_bonus] += num
			if translated_stat_bonus == 'maxhp':
				character['hp'] += num
	
	character['hp'] = character['maxhp']
	
	message = f"**{codename.upper()}** has been reset to their default stats. Use `/sheet` to view updated information."
	if weapon_reset:
		message += "\nThis action has reset your equipped weapon to **Unarmed (2d6k1 DAMAGE)**."
	if armor_reset:
		message += "\nThis action has reset your equipped weapon to **Nothing (0 ARMOR)**."
	if reset_hp:
		message += f"\nYour Max HP has been recalculated from the base 6, and is now **{character['maxhp']}**."
	if reset_war_dice:
		message += f"\nYour War Dice have been recalculated from the base 0, and is now **{character['wd']}**."
	await ctx.respond(message)
	await save_character_data()

@bot.command(description="Roll +FORCEFUL with your active character")
async def frc(ctx, 
	modifier: discord.Option(discord.SlashCommandOptionType.integer, "Extra modifiers for the roll", required=False, default=0),
	superior_dice: discord.Option(bool, "Roll 3d6 and take the best two.", required=False, default=False),
	inferior_dice: discord.Option(bool, "Roll 3d6 and take the worst two.", required=False, default=False)
	):
	await roll_with_skill(ctx, modifier, superior_dice, inferior_dice, 'frc')

@bot.command(description="Roll +REFLEXIVE with your active character")
async def rfx(ctx, 
	modifier: discord.Option(discord.SlashCommandOptionType.integer, "Extra modifiers for the roll", required=False, default=0),
	superior_dice: discord.Option(bool, "Roll 3d6 and take the best two.", required=False, default=False),
	inferior_dice: discord.Option(bool, "Roll 3d6 and take the worst two.", required=False, default=False)
	):
	await roll_with_skill(ctx, modifier, superior_dice, inferior_dice, 'rfx')

@bot.command(description="Roll +TACTICAL with your active character")
async def tac(ctx, 
	modifier: discord.Option(discord.SlashCommandOptionType.integer, "Extra modifiers for the roll", required=False, default=0),
	superior_dice: discord.Option(bool, "Roll 3d6 and take the best two.", required=False, default=False),
	inferior_dice: discord.Option(bool, "Roll 3d6 and take the worst two.", required=False, default=False)
	):
	await roll_with_skill(ctx, modifier, superior_dice, inferior_dice, 'tac')

@bot.command(description="Roll +CREATIVE with your active character")
async def cre(ctx, 
	modifier: discord.Option(discord.SlashCommandOptionType.integer, "Extra modifiers for the roll", required=False, default=0),
	superior_dice: discord.Option(bool, "Roll 3d6 and take the best two.", required=False, default=False),
	inferior_dice: discord.Option(bool, "Roll 3d6 and take the worst two.", required=False, default=False)
	):
	await roll_with_skill(ctx, modifier, superior_dice, inferior_dice, 'cre')

@bot.command(description="Take damage on your active character")
async def damage(ctx, 
	amount: discord.Option(str, "Amount of damage to take. Supports dice syntax.", required=True),
	armor_piercing: discord.Option(bool, "Skip armor when applying this damage.", required=False, default=False),
	bonus_armor: discord.Option(discord.SlashCommandOptionType.integer, "Extra armor that applies to this instance of damage.", required=False, default=0)):
	log(f"/damage {amount}{' armor_piercing' if armor_piercing else ''}")
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	timeout = 2
	output = ()
	try:
		output = func_timeout(timeout, rolldice.roll_dice, args=[amount])
	except rolldice.rolldice.DiceGroupException as e:
		log(f"Caught: {e}")
		await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return
	
	before_armor = output[0]
	if before_armor < 0:
		before_armor = 0
	damage_taken = output[0] - character['armor'] - bonus_armor
	if damage_taken < 0:
		damage_taken = 0
	dice_results = output[1]
	
	if armor_piercing:
		character['hp'] -= before_armor
	else:
		character['hp'] -= damage_taken
	
	message = f"**{codename.upper()}** has taken **{before_armor} damage!**"
	if (not armor_piercing and character['armor'] > 0 and before_armor != damage_taken):
		message += f" (Reduced to **{damage_taken}** by {character['armor']}{f' (+{bonus_armor} bonus)' if bonus_armor > 0 else ''} armor from {character['armor_name']}!)"
	elif (armor_piercing and character['armor'] > 0):
		message += f" (Ignores {character['armor']}{f' (+{bonus_armor} bonus)' if bonus_armor > 0 else ''} armor from {character['armor_name']}!)"
	message += f"\nHP: {character['hp']}/{character['maxhp']}"
	if ('d' in amount or 'd' in amount):
		message += f"\n\nDice results: `{dice_results}`"
		limit = 300
		if len(message) > limit:
			message = message[:limit-5]+"...]`"
	await ctx.respond(message)
	await save_character_data()

@bot.command(description="Heal your active character")
async def heal(ctx, 
	amount: discord.Option(str, "Amount of healing to receive. Supports dice syntax.", required=True),
	):
	log(f"/heal {amount}")
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	timeout = 2
	output = ()
	try:
		output = func_timeout(timeout, rolldice.roll_dice, args=[amount])
	except rolldice.rolldice.DiceGroupException as e:
		log(f"Caught: {e}")
		await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return
	
	healing_taken = output[0]
	if healing_taken < 0:
		healing_taken = 0
	dice_results = output[1]
	
	if character['hp'] < 0 and healing_taken > 0:
		character['hp'] = 0
	
	character['hp'] += healing_taken
	if character['hp'] > character['maxhp']:
		character['hp'] = character['maxhp']
	
	message = f"**{codename.upper()}** has healed **{healing_taken} HP.**"
	message += f"\nHP: {character['hp']}/{character['maxhp']}"
	if character['hp'] >= character['maxhp']:
		message += " (Full restore!)"
	if ('d' in amount or 'd' in amount):
		message += f"\n\nDice results: `{dice_results}`"
		limit = 300
		if len(message) > limit:
			message = message[:limit-5]+"...]`"
	await ctx.respond(message)
	await save_character_data()

@bot.command(description="Roll your active character's weapon damage")
async def attack(ctx,
	bonus_damage: discord.Option(str, "Amount of extra damage to deal; supports dice syntax.", required=False, default="0"),
	multiplier: discord.Option(int, "Amount to multiply the final damage by.", required=False, default=1)
	):
	log(f"/attack {bonus_damage} {multiplier}")
	try:
		character = get_active_char_object(ctx)
		if character == None:
			await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
			return
		codename = get_active_codename(ctx)
	
		if character['premium'] and not await ext_character_management(ctx.author.id):
			await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
			return
		
		base_damage = character['damage']
		base_damage = rolldice.roll_dice(base_damage)
		
		bonus_damage_result = rolldice.roll_dice(bonus_damage)
		
		final_damage = (base_damage[0] + bonus_damage_result[0]) * multiplier
		
		message = f"**{codename.upper()}** has dealt **{final_damage} damage** using **{character['weapon_name']}**!\n\nBase damage: `{character['damage']}` -> `{base_damage[1]}`"
		if bonus_damage != "0":
			message += f"\nBonus damage: `{bonus_damage}` -> `{bonus_damage_result[1]}`"
		if multiplier != 1:
			message += f"\nFinal damage multiplier: `{multiplier}`"
		await ctx.respond(message)
	except Exception as e:
		await ctx.respond(f"There was an error performing this command.\n```{e}```",ephemeral=True)

async def held_items_autocomplete(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		# gotta get active character manually cus this is a different kind of ctx. ugh
		your_actives = character_data[uid]['active']
		if str(ctx.interaction.channel_id) in your_actives:
			current_active = your_actives[str(ctx.interaction.channel_id)]
			if current_active in character_data[uid]['chars']:
				current_char = character_data[uid]['chars'][current_active]
				item_list = current_char['items']
				output = []
				for item in item_list:
					cut = item.split(" (")
					output.append(cut[0])
				return output
			else:
				return []
		else:
			return []
	else:
		return []

async def held_dice_autocomplete(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		# gotta get active character manually cus this is a different kind of ctx. ugh
		your_actives = character_data[uid]['active']
		if str(ctx.interaction.channel_id) in your_actives:
			current_active = your_actives[str(ctx.interaction.channel_id)]
			if current_active in character_data[uid]['chars']:
				current_char = character_data[uid]['chars'][current_active]
				item_list = current_char['items']
				dice_outs = set()
				num_outs = set()
				current_item_selected = ctx.options["name"]
				dice_pattern = r'(\d*)[dD](\d+)([+-]\d+)?'
				number_pattern = r'(\d+)'
				for item in item_list:
					cut = item.split(" (")
					effect = cut[1] if len(cut) > 1 else ""
					dice_matches = re.findall(dice_pattern, effect)
					number_matches = re.findall(number_pattern, effect)
					if current_item_selected != None and item.startswith(current_item_selected):
						dice_outs = set()
						num_outs = set()
						for match in dice_matches:
							dice_outs.add(f"{match[0]}D{match[1]}{match[2]}")
						for match in number_matches:
							num_outs.add(match)
						break
					else:
						for match in dice_matches:
							dice_outs.add(f"{match[0]}D{match[1]}{match[2]}")
						for match in number_matches:
							num_outs.add(match)
				return list(dice_outs) + list(num_outs)
			else:
				return []
		else:
			return []
	else:
		return []

async def held_numbers_autocomplete(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		# gotta get active character manually cus this is a different kind of ctx. ugh
		your_actives = character_data[uid]['active']
		if str(ctx.interaction.channel_id) in your_actives:
			current_active = your_actives[str(ctx.interaction.channel_id)]
			if current_active in character_data[uid]['chars']:
				current_char = character_data[uid]['chars'][current_active]
				item_list = current_char['items']
				num_outs = set()
				current_item_selected = ctx.options["name"]
				number_pattern = r'(\d+)'
				for item in item_list:
					cut = item.split(" (")
					effect = cut[1] if len(cut) > 1 else ""
					number_matches = re.findall(number_pattern, effect)
					if current_item_selected != None and item.startswith(current_item_selected):
						num_outs = set()
						for match in number_matches:
							num_outs.add(int(match))
						break
					else:
						for match in number_matches:
							num_outs.add(int(match))
				return list(num_outs)
			else:
				return []
		else:
			return []
	else:
		return []
	
@bot.command(description="Set your equipped weapon")
async def equip_weapon(ctx, 
	name: discord.Option(str, "The weapon's name.", autocomplete=discord.utils.basic_autocomplete(held_items_autocomplete), required=True),
	damage: discord.Option(str, "Amount of damage to deal; supports dice syntax.", autocomplete=discord.utils.basic_autocomplete(held_dice_autocomplete), required=True)):
	
	character = get_active_char_object(ctx)
	log(f"/equip_weapon {name} {damage}")
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	timeout = 2
	try:
		func_timeout(timeout, rolldice.roll_dice, args=[damage])
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"You cannot equip this weapon because attemping to roll its damage takes too long (>{timeout}s). Try using less dice.",ephemeral=True)
		return
	except Exception as e:
		await ctx.respond(f"You cannot equip this weapon because attemping to roll its damage throws the following error:\n```{e}```",ephemeral=True)
		return
	
	character['weapon_name'] = name
	character['damage'] = damage
	
	await ctx.respond(f"**{codename.upper()}** has equipped **{name} ({damage} DAMAGE)**")
	
	await save_character_data()

@bot.command(description="Set your equipped armor")
async def equip_armor(ctx, 
	name: discord.Option(str, "The armor's name.", autocomplete=discord.utils.basic_autocomplete(held_items_autocomplete), required=True),
	damage: discord.Option(int, "Amount of damage it reduces.", autocomplete=discord.utils.basic_autocomplete(held_numbers_autocomplete), required=True)):
	log(f"/equip_armor {name} {damage}")
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch`.",ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-subscribe to Expanded Character Management in Sonder's Garage.\nhttps://discord.gg/VeedQmQc7k",ephemeral=True)
		return
	
	character['armor_name'] = name
	character['armor'] = damage
	
	await ctx.respond(f"**{codename.upper()}** has equipped **{name} ({damage} ARMOR)**")
	
	await save_character_data()

log("Creating trait commands")
trait_group = discord.SlashCommandGroup("trait", "Trait Commands")

trait_group = discord.SlashCommandGroup("trait", "Trait Commands")

@trait_group.command(description="Looks up a trait by name or d666 number")
async def lookup(ctx, trait: discord.Option(str,"The trait to search for",autocomplete=discord.utils.basic_autocomplete(trait_autocomp))):
	log(f"/trait lookup {trait}")
	message = search_for_trait(trait)
	hidden = message in ["No trait exists with the given number. Trait numbers must be possible d666 roll outputs.","Could not find a trait with an approximately similar name."]
	
	await ctx.respond(message,ephemeral=hidden)

@trait_group.command(description="Produces a random trait")
async def random(ctx):
	log("/trait random")
	result = rnd.choice(trait_data)
	if (rnd.randint(1,10000) == 1):
		result = secret_trait
	message = trait_message_format(result)
	await ctx.respond(message)

bot.add_application_command(trait_group)

log("Creating role commands")
role_group = discord.SlashCommandGroup("role", "Role Commands")

@role_group.command(description="Looks up a role by name or d66 number")
async def lookup(ctx, role: discord.Option(str,"The role to search for",autocomplete=discord.utils.basic_autocomplete(role_autocomp))):
	log(f"/role lookup {role}")
	message = search_for_role(role)
	hidden = message in ["No role exists with the given number. Role numbers must be possible d66 roll outputs.","Could not find a role with an approximately similar name."]
	await ctx.respond(message,ephemeral=hidden)

@role_group.command(description="Produces a random role")
async def random(ctx):
	log("/role random")
	result = rnd.choice(role_data)
	message = role_message_format(result)
	await ctx.respond(message)

bot.add_application_command(role_group)

log("Creating player commands")
player_group = discord.SlashCommandGroup("player", "Player Commands")

def trait_sort_key(trait):
	return trait["Name"]

log("Loading Ripley's codenames")
file = open('ripley_codenames.json')
merc_codenames = json.load(file)
file.close()

@player_group.command(description="Produces a random character sheet")
async def character(ctx, traitcount: discord.Option(discord.SlashCommandOptionType.integer, "The number of traits this character should have. Defaults to 2.", required=False, default=2)):
	log(f"/player character {traitcount}")
	
	message = f"# {rnd.choice(merc_codenames)}"
	if traitcount < 1:
		await ctx.respond("Generated characters must have at least 1 trait.",ephemeral=True)
		return
	if traitcount > 40:
		await ctx.respond("Cannot generate a character with that many traits.",ephemeral=True)
		return
	message += "\nROLE: "
	
	traits = rnd.sample(trait_data, traitcount)
	role = rnd.choice(role_data)
	
	for i in range(len(traits)):
		if (rnd.randint(1,10000) == 1):
			traits[i] = secret_trait
			break
	
	traits.sort(key=trait_sort_key)
	
	extra_thing = rnd.randint(1,3)
	
	message += role_message_format(role) + "\n\n"
	
	stats = {
		"MAX": 6,
		"WAR": 0,
		"FORCEFUL": 0,
		"TACTICAL": 0,
		"CREATIVE": 0,
		"REFLEXIVE": 0
	}
	
	if extra_thing == 1:
		stats["MAX"] += d6()
	elif extra_thing == 2:
		stats["WAR"] += d6()
	
	for trait in traits:
		bonus = trait["Stat"].split(" ")
		num = 0
		if bonus[1] in stats:
			try: 
				num = rolldice.roll_dice(bonus[0])[0]
			except Exception as e:
				num = 0
				log(f"Caught dice-rolling exception: {e}")
			stats[bonus[1]] += num
	
	message += f"MAX HP: {stats['MAX']}\n"
	message += f"WAR DICE: {stats['WAR']}\n\n"
	
	if stats['FORCEFUL'] != 0:
		message += f"FORCEFUL: {'+' if stats['FORCEFUL'] > 0 else ''}{stats['FORCEFUL']}\n"
	if stats['TACTICAL'] != 0:
		message += f"TACTICAL: {'+' if stats['TACTICAL'] > 0 else ''}{stats['TACTICAL']}\n"
	if stats['CREATIVE'] != 0:
		message += f"CREATIVE: {'+' if stats['CREATIVE'] > 0 else ''}{stats['CREATIVE']}\n"
	if stats['REFLEXIVE'] != 0:
		message += f"REFLEXIVE: {'+' if stats['REFLEXIVE'] > 0 else ''}{stats['REFLEXIVE']}\n"
	
	if stats['FORCEFUL'] != 0 or stats['TACTICAL'] != 0 or stats['CREATIVE'] != 0 or stats['REFLEXIVE'] != 0:
		message += '\n'
	
	message += "TRAITS:\n"
	altmessage = message
	for trait in traits:
		message += f"- **{trait['Name']}** ({trait['Number']}): {trait['Effect']} ({trait['Stat']})\n"
		altmessage += f"- **{trait['Name']}** ({trait['Number']}, {trait['Stat']})\n"
	
	altmessage += "\nITEMS:"
	message += "\nITEMS:"
	for trait in traits:
		altmessage += f"\n- {trait['Item']}"
		message += f"\n- {trait['Item']}"
	if extra_thing == 3:
		standard_issue_items = ["Balaclava (hides identity)", "Flashlight (can be used as a weapon attachment)", "Knife (1D6 DAMAGE)", "MRE field rations (+1D6 HP, one use)", "Pistol (1D6 DAMAGE)", "Riot shield (1 ARMOR, equip as weapon)"]
		altmessage += f"\n- {rnd.choice(standard_issue_items)}"
		message += f"\n- {rnd.choice(standard_issue_items)}"
	if len(message) > 2000:
		message = message.replace("FORCEFUL", "FRC")
		message = message.replace("CREATIVE", "CRE")
		message = message.replace("REFLEXIVE", "RFX")
		message = message.replace("TACTICAL", "TAC")
		message = message.replace("DAMAGE", "DMG")
		if len(message) > 2000:
			message = altmessage
	if len(message) > 2000:
		message = message.replace("FORCEFUL", "FRC")
		message = message.replace("CREATIVE", "CRE")
		message = message.replace("REFLEXIVE", "RFX")
		message = message.replace("TACTICAL", "TAC")
		message = message.replace("DAMAGE", "DMG")
		if len(message) > 2000:
			await ctx.respond("The generated character does not fit in the 2,000 character limit for messages. Try lowering the amount of traits.",ephemeral=True)
			return
	await ctx.respond(message)

@player_group.command(description="Rolls against the Emergency Insertion table")
async def emergencyinsertion(ctx):
	log("/player emergencyinsertion")
	results = [d6(), d6()]
	sum = results[0] + results[1]
	
	message = f"{num_to_die[results[0]]} + {num_to_die[results[1]]} = **{sum}**: "
	
	if sum <= 6:
		message += "Deployment goes wrong somehow."
	elif sum <= 9:
		message += "Deploy normally."
	else:
		message += "Deploy with an extra standard issue item"
		if results == [6,6]:
			message += ", **and +3 to your first roll.**"
		else:
			message += "."
	await ctx.respond(message)

@player_group.command(description="Rolls a skill check")
async def roll(ctx, 
	modifier: discord.Option(discord.SlashCommandOptionType.integer, "The skill modifier for the roll", required=False, default=0),
	superior_dice: discord.Option(bool, "Roll 3d6 and take the best two.", required=False, default=False),
	inferior_dice: discord.Option(bool, "Roll 3d6 and take the worst two.", required=False, default=False)
	):
	log(f"/player roll {modifier}{' superior_dice' if superior_dice else ''}{' inferior_dice' if inferior_dice else ''}")
	results = [d6(), d6()]
	if superior_dice ^ inferior_dice:
		results.append(d6())
	
	dice_string = ""
	for d in results:
		dice_string += " " + num_to_die[d]
	dice_string = dice_string.strip()
	
	sorted_results = sorted(results)
	if superior_dice and not inferior_dice:
		results = sorted_results[-2:]
	elif inferior_dice and not superior_dice:
		results = sorted_results[:2]
	
	total = sum(results) + modifier
	
	message = ""
	
	if modifier != 0:
		message = f"({dice_string}) + {modifier} = **{total}**: "
	else:
		message = f"{dice_string} = **{total}**: "
	
	if results == [6,6]:
		message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
	elif total <= 6:
		message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
	elif total <= 9:
		message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
	else:
		message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."
	await ctx.respond(message)

def roll_multiple_dice(syntax, amount):
	out = []
	for i in range(amount):
		out.append(rolldice.roll_dice(syntax))
	return out

@player_group.command(description="Rolls dice using common dice syntax")
async def dice(ctx, syntax: discord.Option(str,"The dice syntax"),
	instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1),
	hidden: discord.Option(bool, "If TRUE, the output of this command is hidden to others", required=False, default=False)):
	
	if instances < 1:
		instances = 1
	
	log(f"/player dice {syntax} {instances} {hidden}")
	timeout = 2
	output = ()
	if instances > 1:
		output = []
	try:
		if instances > 1:
			output = func_timeout(timeout, roll_multiple_dice, args=[syntax,instances])
		else:
			output = func_timeout(timeout, rolldice.roll_dice, args=[syntax])
	except rolldice.rolldice.DiceGroupException as e:
		log(f"Caught: {e}")
		await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return
	
	message = ""
	if instances > 1:
		strings_to_join = []
		counter = 1
		for item in output:
			strings_to_join.append(f"{counter}. **{item[0]}** (`{item[1]}`)")
			counter += 1
		message = "\n".join(strings_to_join)
	else:
		message = f"**Total: {output[0]}**\n`{output[1]}`"
	if not ('d' in syntax or 'D' in syntax):
		message += f"\n\nIt seems your input didn't actually roll any dice. Did you mean `1d{syntax}` or `{syntax}d6`?\nSee [py-rolldice](<https://github.com/mundungus443/py-rolldice#dice-syntax>) for an explanation of dice syntax."
	
	if len(message) > 2000:
		message = message.replace("*","").replace("`","")
		with open("message.txt","w") as file:
			file.write(message)
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File('message.txt'),ephemeral=hidden)
		os.remove('message.txt')
		log("Sent dice results as file")
	else:
		await ctx.respond(message,ephemeral=hidden)

bot.add_application_command(player_group)

log("Creating matrix commands")
matrix_group = discord.SlashCommandGroup("matrix", "Intelligence Matrix Rollers")

intelligence = {}

file = open('matrices/mission_generator.json')
intelligence["mission"] = json.load(file)
file.close()

@matrix_group.command(description="Provides a random Mission Dossier")
async def mission(ctx):
	log("/matrix mission")
	results = roll_all_matrices(intelligence["mission"])
	instigator = decap_first(results[0])
	activity = decap_first(results[1])
	effect = decap_first(results[2])
	twist = decap_first(results[3])
	reward = results[4]
	message = f"The dossier says that **{instigator}** is trying to **{activity}**, which will **{effect}**. However, **{twist}**.\n- Reward: **{reward}**"
	await ctx.respond(message)

file = open('matrices/mission_prompts.json')
intelligence["prompt"] = json.load(file)
file.close()

@matrix_group.command(description="Provides a random Mission Prompt")
async def prompt(ctx):
	log("/matrix prompt")
	result = roll_intelligence_matrix(intelligence["prompt"][0])
	await ctx.respond(result)

file = open('matrices/misc.json')
intelligence["misc"] = json.load(file)
file.close()

@matrix_group.command(description="Incants a Magical Word")
async def syllables(ctx):
	log("/matrix syllables")
	result = ""
	count = d6()
	for i in range(count):
		result += roll_intelligence_matrix(intelligence["misc"][0])
	await ctx.respond(result)

@matrix_group.command(description="Gives a random Operation Codename")
async def codename(ctx):
	log("/matrix codename")
	result = roll_intelligence_matrix(intelligence["misc"][1])
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Combat Behavior")
async def tactics(ctx):
	log("/matrix tactics")
	result = roll_intelligence_matrix(intelligence["misc"][2])
	await ctx.respond(result)

@matrix_group.command(description="Strikes a random Hit Location")
async def hit(ctx):
	log("/matrix hit")
	result = [roll_intelligence_matrix(intelligence["misc"][3])]
	while "Compound injury (roll two hit locations)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.remove("Compound injury (roll two hit locations)")
	result = "You've been hit in the **" + "** __*and*__ **".join(result) + "**!"
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Faction Action")
async def factionaction(ctx):
	log("/matrix factionaction")
	result = [roll_intelligence_matrix(intelligence["misc"][4])]
	while "Fake-out zig-zag (roll two actions)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.remove("Compound injury (roll two hit locations)")
	result = " __*and*__ ".join(result)
	result = f"A faction (any `/matrix faction`) tasks you with the following: **{result}**"
	await ctx.respond(result)

@matrix_group.command(description="Discloses a random Faction Mission")
async def factionmission(ctx):
	log("/matrix factionmission")
	result = [roll_intelligence_matrix(intelligence["misc"][5])]
	while "Double mission (roll two objectives)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.remove("Double mission (roll two objectives)")
	result = " __*and*__ ".join(result)
	message = f"A faction tasks you with this objective: **{result}**"
	await ctx.respond(message)

@matrix_group.command(description="Assigns a random CHOKE Score")
async def choke(ctx):
	log("/matrix choke")
	result = roll_intelligence_matrix(intelligence["misc"][10])
	await ctx.respond(result)

async def part_success_autocomplete(ctx: discord.AutocompleteContext):
	return ["COMBAT","GENERAL","MENTAL","MOVEMENT","SOCIAL","WEIRD"]

@matrix_group.command(description="Causes random consequences for a Partial Success")
async def partial(ctx, type: discord.Option(str,"The type of consequence that should be inflicted",autocomplete=discord.utils.basic_autocomplete(part_success_autocomplete),required=False,default="")):
	log(f"/matrix partial {type}")
	hidden = False
	type = type.upper()
	message = ""
	if type == "":
		message = roll_intelligence_matrix(intelligence["misc"][11])
	elif type in ["COMBAT","GENERAL","MENTAL","MOVEMENT","SOCIAL","WEIRD"]:
		all = intelligence["misc"][11]["Values"].values()
		outcomes = []
		for item in all:
			if item.startswith(type):
				split_point = len(type) + 1
				outcomes.append(item[split_point:])
		message = rnd.choice(outcomes)
	else:
		hidden = True
		message = "Valid partial success types are COMBAT, GENERAL, MOVEMENT, SOCIAL, and WEIRD."
	await ctx.respond(message,ephemeral=hidden)

@matrix_group.command(description="Spawns a Random Encounter")
async def encounter(ctx):
	log("/matrix encounter")
	result = roll_intelligence_matrix(intelligence["misc"][12])
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Downtime Event")
async def downtime(ctx):
	log("/matrix downtime")
	result = roll_intelligence_matrix(intelligence["misc"][13])
	await ctx.respond(result)

file = open('matrices/cassettes.json')
intelligence["cassettes"] = json.load(file)
file.close()

file = open('matrices/cassette_links.json')
intelligence["cassette_links"] = json.load(file)
file.close()

@matrix_group.command(description="Plays a random Cassette Tape")
async def cassette(ctx):
	log("/matrix cassette")
	audio = rnd.choice(intelligence["cassettes"])
	if audio == "[Combination tape, roll 1D6 tapes]":
		tapes = ["[Combination tape, roll 1D6 tapes]"]
		while "[Combination tape, roll 1D6 tapes]" in tapes:
			tapes = rnd.sample(intelligence["cassettes"], rnd.randint(2,6))
		for i in range(len(tapes)):
			if tapes[i] in intelligence["cassette_links"]:
				tapes[i] = f"[{tapes[i]}](<{intelligence['cassette_links'][tapes[i]]}>)"
		audio = "Combination tape:\n- " + "\n- ".join(tapes)
	elif audio in intelligence["cassette_links"]:
		audio = f"[{audio}](<{intelligence['cassette_links'][audio]}>)"
	await ctx.respond(audio)

gear_group = matrix_group.create_subgroup("gear", "Gear Intelligence Matrices")

file = open('matrices/gear/items.json')
intelligence["gear_items"] = json.load(file)
file.close()

file = open('matrices/gear/weapons_and_armor.json')
intelligence["gear_weapons_and_armor"] = json.load(file)
file.close()

file = open('matrices/gear/vehicles.json')
intelligence["gear_vehicles"] = json.load(file)
file.close()

file = open('matrices/gear/base_upgrades.json')
intelligence["gear_bupgrades"] = json.load(file)
file.close()

bupgrade_names = []
for bupgrade in intelligence["gear_bupgrades"]:
	bupgrade_names.append(bupgrade["Name"])

async def bupgrade_autocomp(ctx):
	return bupgrade_names

@gear_group.command(description="Applies a random Base Upgrade")
async def baseupgrade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific Base Upgrade instead",autocomplete=discord.utils.basic_autocomplete(bupgrade_autocomp),required=False,default="")):
	log("/matrix gear baseupgrade")
	message = ""
	if len(lookup) < 1:
		result = rnd.choice(intelligence["gear_bupgrades"])
		message = f"**{result['Name']}:** {result['Effect']}"
	else:
		best_match = difflib.get_close_matches(lookup.upper(), bupgrade_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodbup = {}
			for bup in intelligence["gear_bupgrades"]:
				if best_match[0] == bup["Name"]:
					goodbup = bup
					break
			message = f"**{goodbup['Name']}:** {goodbup['Effect']}"
	await ctx.respond(message)

@gear_group.command(description="Divulges the contents of a random Crate")
async def crate(ctx):
	log("/matrix gear crate")
	result = roll_intelligence_matrix(intelligence["gear_items"][1])
	message = f"You crack open a crate, revealing **{result}** inside."
	await ctx.respond(message)

@gear_group.command(description="Grants a random Common Item")
async def item(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of items to produce (allows duplicates)", required=False, default=1)):
	log(f"/matrix gear item {count}")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} items.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_items"][0])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

@gear_group.command(description="Grants a random piece of Armor")
async def armor(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of armor pieces to produce (allows duplicates)", required=False, default=1)):
	log("/matrix gear armor")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} armor pieces.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][0])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

@gear_group.command(description="Grants a random Weapon")
async def weapon(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of weapons to produce (allows duplicates)", required=False, default=1)):
	log(f"/matrix gear weapon {count}")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} weapons.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][1])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

wep_tag_names = []
for tag in intelligence["gear_weapons_and_armor"][2]["Values"].values():
	wep_tag_names.append(tag['Name'])

async def tag_lookup_autocomp(ctx):
	return wep_tag_names

@gear_group.command(description="Applies a random Weapon Tag")
async def tag(ctx, lookup: discord.Option(str,"Including this argument searches for a specific tag instead",autocomplete=discord.utils.basic_autocomplete(tag_lookup_autocomp),required=False,default="")):
	log("/matrix gear tag")
	tags = intelligence["gear_weapons_and_armor"][2]["Values"]
	message = ""
	hidden = False
	if lookup == "":
		result = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][2])
		message = f"**{result['Name']}**: {result['Effect']}"
	else:
		if re.match("^\d+$", lookup):
			if lookup in tags:
				result = tags[lookup]
				message = f"**{result['Name']}**: {result['Effect']}"
			else:
				message = "No tag exists with the given number. Tag numbers must be possible d66 roll outputs."
				hidden = True
		else:
			best_match = difflib.get_close_matches(lookup.upper(), wep_tag_names, n=1, cutoff=0.0)
			
			if len(best_match) > 0:
				for tag in tags.values():
					if tag["Name"] == best_match[0]:
						result = tag
						message = f"**{result['Name']}**: {result['Effect']}"
						break
			else:
				message = "Could not find a tag with an approximately similar name."
				hidden = True
	await ctx.respond(message,ephemeral=hidden)

@gear_group.command(description="Grants a random Vehicle")
async def vehicle(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of vehicles to produce (allows duplicates)", required=False, default=1)):
	log(f"/matrix gear vehicle {count}")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} vehicles.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_vehicles"][0])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

@gear_group.command(description="Grants a random Vehicle Weapon")
async def vehicleweapon(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of vehicle weapons to produce (allows duplicates)", required=False, default=1)):
	log(f"/matrix gear vehicleweapon {count}")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} vehicle weapons.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_vehicles"][1])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

@gear_group.command(description="Applies a random Weapon Skin")
async def skin(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of weapon skins to produce (allows duplicates)", required=False, default=1)):
	log(f"/matrix gear skin {count}")
	max = 50
	if count < 1:
		count = 1
	elif count > max:
		await ctx.respond(f"You may only generate a maximum of {max} weapon skins.",ephemeral=True)
		return
	results = {}
	for i in range(count):
		item = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
		if item not in results:
			results[item] = 1
		else:
			results[item] = results[item] + 1
	joinlist = []
	for key in sorted(list(results.keys())):
		if results[key] > 1:
			joinlist.append(f"{key} **(x{results[key]})**")
		else:
			joinlist.append(key)
	message = "\n".join(joinlist)
	await ctx.respond(message)

@gear_group.command(description="Generates a fully unique Weapon")
async def weaponsmith(ctx):
	log("/matrix gear weaponsmith")
	model = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][1])
	tag = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][2])
	tag = f"**{tag['Name']}**: {tag['Effect']}"
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	message = f"**{model}** (adorned with **{skin}**)\n- {tag}"
	await ctx.respond(message)

@gear_group.command(description="Generates a fully unique Vehicle")
async def hangar(ctx):
	log("/matrix gear weaponsmith")
	model = roll_intelligence_matrix(intelligence["gear_vehicles"][0])
	weapon = roll_intelligence_matrix(intelligence["gear_vehicles"][1])
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	message = f"**{model}**\n- Equipped with **{weapon}**\n- Adorned with **{skin}**"
	await ctx.respond(message)

cyclops_group = matrix_group.create_subgroup("cyclops", "CYCLOPS Intelligence Matrices")

file = open('matrices/cyclops/gadgets.json')
intelligence["cyclops_gadgets"] = json.load(file)
file.close()

file = open('matrices/cyclops/rumors.json')
intelligence["cyclops_rumors"] = json.load(file)
file.close()

@cyclops_group.command(description="Grants a random CYCLOPS Gadget")
async def gadget(ctx, 
	count: discord.Option(discord.SlashCommandOptionType.integer, "The number of CYCLOPS Gadgets to produce", required=False, default=1),
	duplicates: discord.Option(bool, "Mark FALSE to prevent duplicate items being rolled if count > 1", required=False, default=True)
	):
	log(f"/matrix cyclops gadget {count}{' no_duplicates' if not duplicates else ''}")
	message = ""
	limit = 250
	if count > limit:
		await ctx.respond(f"Please do not produce more than {limit} gadgets.",ephemeral=True)
		return
	elif count <= 1:
		result = roll_intelligence_matrix(intelligence["cyclops_gadgets"][0])
		message = f"**{result['Name']}**: {result['Effect']}"
	else:
		if duplicates:
			results = {}
			for i in range(count):
				g = roll_intelligence_matrix(intelligence["cyclops_gadgets"][0])
				name = g["Name"]
				if name in results:
					results[name] = results[name] + 1
				else:
					results[name] = 1
			for key in results:
				if results[key] > 1:
					message += f"{key} **(x{results[key]})**\n"
				else:
					message += f"{key}\n"
		else:
			gs = list(intelligence["cyclops_gadgets"][0]["Values"].values())
			outs = rnd.sample(gs, min([len(gs),count]))
			for item in outs:
				message += f"{item['Name']}\n"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges where CYCLOPS High Command is (allegedly) located")
async def location(ctx):
	log("/matrix cyclops location")
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][0])
	message = f"Rumored location of CYCLOPS High Command: **{result}**"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges the (alleged) origin of CYCLOPS")
async def origin(ctx):
	log("/matrix cyclops origin")
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][1])
	message = f"Rumored origin of CYCLOPS: **{result}**"
	await ctx.respond(message)

world_group = matrix_group.create_subgroup("world", "World Intelligence Matrices")

file = open('matrices/world/hazards.json')
intelligence["world_hazards"] = json.load(file)
file.close()

@world_group.command(description="Spawns a random Hazard")
async def hazard(ctx):
	log("/matrix world hazard")
	result = roll_intelligence_matrix(intelligence["world_hazards"][0])
	message = f"Tread carefully; the area ahead contains **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Reveals a random Trap")
async def trap(ctx):
	log("/matrix world trap")
	result = roll_intelligence_matrix(intelligence["world_hazards"][1])
	message = f"You've sprung a trap! You suffer the effects of **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Starts in a random Year")
async def year(ctx):
	log("/matrix world year")
	start = int(roll_intelligence_matrix(intelligence["misc"][6]))
	modifier = int(roll_intelligence_matrix(intelligence["misc"][7]))
	year = start + modifier
	await ctx.respond(f"_The year is **{year}**..._")

@world_group.command(description="Randomly modifies the local Temperature and Precipitation")
async def weather(ctx):
	log("/matrix world weather")
	temp = roll_intelligence_matrix(intelligence["misc"][8])
	precip = roll_intelligence_matrix(intelligence["misc"][9])
	result = f"**Temperature:** {temp}\n**Precipitation:** {precip}"
	await ctx.respond(result)

chars_group = matrix_group.create_subgroup("character", "Character Intelligence Matrices")

def format_premade(structure):
	output = "**"
	output += structure["Head"].replace(" (", "** (", 1)
	for feat in structure["Features"]:
		output += "\n- " + feat
	for note in structure["Notes"]:
		output += "\n**" + note.replace(":", ":**", 1)
	return output

file = open('matrices/characters/premade_npcs.json')
intelligence["chars_premade"] = json.load(file)
file.close()

premade_npc_names = []
for char in intelligence["chars_premade"]:
	name = char["Head"].strip()
	index = name.find(" (")
	if index != -1:
		name = name[:index]
	premade_npc_names.append(name)

async def npc_lookup_autocomp(ctx):
	return premade_npc_names

@chars_group.command(description="Spawns a random pre-made NPC")
async def premade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific NPC instead",autocomplete=discord.utils.basic_autocomplete(npc_lookup_autocomp),required=False,default="")):
	log(f"/matrix character premade {lookup}")
	message = ""
	if len(lookup) < 1:
		result = rnd.choice(intelligence["chars_premade"])
		message = format_premade(result)
	else:
		best_match = difflib.get_close_matches(lookup.upper(), premade_npc_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodchar = {}
			for char in intelligence["chars_premade"]:
				if best_match[0] in char["Head"]:
					goodchar = char
					break
			message = format_premade(goodchar)
	await ctx.respond(message)

file = open('matrices/characters/celebrities.json')
intelligence["chars_celebs"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Celebrity")
async def celebrity(ctx):
	log("/matrix character celebrity")
	result = roll_all_matrices(intelligence["chars_celebs"])
	profession = [result[0]]
	while "Roll twice, ignoring duplicates" in profession:
		profession.remove("Roll twice, ignoring duplicates")
		profession.append(roll_intelligence_matrix(intelligence["chars_celebs"][0]))
		profession.append(roll_intelligence_matrix(intelligence["chars_celebs"][0]))
	profession = remove_duplicates(profession)
	profession = ", ".join(profession)
	name = result[1]
	feature = result[2]
	story = result[3]
	message = f"Name: {name}\nProfession: {profession}\nFeature: {feature}\nStory: {story}"
	await ctx.respond(message)

file = open('matrices/characters/civilians.json')
intelligence["chars_civvies"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Civilian")
async def civilian(ctx):
	log("/matrix character civilian")
	result = roll_all_matrices(intelligence["chars_civvies"])
	job = result[0]
	name = result[1]
	feature = result[2]
	story = result[3]
	message = f"Name: {name}\nJob: {job}\nFeature: {feature}\nStory: {story}"
	await ctx.respond(message)

file = open('matrices/characters/politicians.json')
intelligence["chars_politicians"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Politician")
async def politician(ctx):
	log("/matrix character politician")
	result = roll_all_matrices(intelligence["chars_politicians"])
	position = result[0]
	vice = result[1]
	name = result[2]
	feature = result[3]
	secret = result[4]
	message = f"Name: {name}\nPosition: {position}\nVice: {vice}\nFeature: {feature}\nSecret: {secret}"
	await ctx.respond(message)

file = open('matrices/characters/scientists.json')
intelligence["chars_scientists"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Scientist")
async def scientist(ctx):
	log("/matrix character scientist")
	result = roll_all_matrices(intelligence["chars_scientists"])
	alleg = result[0]
	career = result[1]
	name = result[2]
	feature = result[3]
	discovery = roll_extra_possibility(result[4])
	message = f"Name: {name}\nAllegiance: {alleg}\nCareer: {career}\nFeature: {feature}\nDiscovery: {discovery}"
	await ctx.respond(message)

file = open('matrices/characters/soldiers.json')
intelligence["chars_soldiers"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Soldier")
async def soldier(ctx):
	log("/matrix character soldier")
	result = roll_all_matrices(intelligence["chars_soldiers"])
	rank = result[0]
	name = result[1]
	feature = result[2]
	anecdote = result[3]
	message = f"Name: {name}\nRank: {rank}\nFeature: {feature}\nAnecdote: {anecdote}"
	await ctx.respond(message)
	
file = open('matrices/characters/spies.json')
intelligence["chars_spies"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Spy")
async def spy(ctx):
	log("/matrix character spy")
	result = roll_all_matrices(intelligence["chars_spies"])
	code = result[0]
	clearance = result[1]
	name = result[2]
	feature = result[3]
	modus = result[4]
	message = f"Name: {name}\nCodename: {code}\nClearance: {clearance}\nFeature: {feature}\nModus: {modus}"
	await ctx.respond(message)

enemy_group = matrix_group.create_subgroup("enemy", "Enemy Intelligence Matrices")

file = open('matrices/characters/premade_enemies.json')
intelligence["chars_enemy_premade"] = json.load(file)
file.close()

premade_enemy_names = []
for char in intelligence["chars_enemy_premade"]:
	name = char["Head"].replace("(BOSS) ", "").strip()
	index = name.find(" (")
	if index != -1:
		name = name[:index]
	premade_enemy_names.append(name)

async def enemy_lookup_autocomp(ctx):
	return premade_enemy_names

@enemy_group.command(description="Spawns a random pre-made Enemy")
async def premade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific Enemy instead",autocomplete=discord.utils.basic_autocomplete(enemy_lookup_autocomp),required=False,default="")):
	log(f"/matrix enemy premade {lookup}")
	message = ""
	if len(lookup) < 1:
		result = rnd.choice(intelligence["chars_enemy_premade"])
		message = format_premade(result)
	else:
		best_match = difflib.get_close_matches(lookup.upper(), premade_enemy_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodchar = {}
			for char in intelligence["chars_enemy_premade"]:
				if best_match[0] in char["Head"]:
					goodchar = char
					break
			message = format_premade(goodchar)
	await ctx.respond(message)

file = open('matrices/characters/animals.json')
intelligence["chars_animals"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Animal")
async def animal(ctx):
	log("/matrix enemy animal")
	result = roll_all_matrices(intelligence["chars_animals"])
	amount = result[0]
	desc = result[1]
	feature = result[2]
	mal = result[3]
	message = f"Description: {desc}\nAmount: {amount}\nFeature: {feature}\nMalady: {mal}"
	await ctx.respond(message)

file = open('matrices/characters/anomalies.json')
intelligence["chars_anomalies"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Anomaly")
async def anomaly(ctx):
	log("/matrix enemy anomaly")
	result = roll_all_matrices(intelligence["chars_anomalies"])
	signature = result[0]
	desc = result[1]
	feature = result[2]
	sighting = result[3]
	message = f"Description: {desc}\nSignature: {signature}\nFeature: {feature}\nSighting: {sighting}"
	await ctx.respond(message)

file = open('matrices/characters/experiments.json')
intelligence["chars_experiments"] = json.load(file)
file.close()

@enemy_group.command(description="Performs a random Experiment")
async def experiment(ctx):
	log("/matrix enemy experiment")
	result = roll_all_matrices(intelligence["chars_experiments"])
	creation = result[0]
	desc = result[1]
	feature = result[2]
	mistake = result[3]
	if creation == "Uncontrolled\u2014Roll 1D6 extra features":
		feature = [feature]
		more = d6()
		for i in range(more):
			feature.append(roll_intelligence_matrix(intelligence["chars_experiments"][2]))
		feature = ", ".join(feature)
	elif creation == "Accidental\u2014Roll 1D6 extra mistakes":
		mistake = [mistake]
		more = d6()
		for i in range(more):
			mistake.append(roll_intelligence_matrix(intelligence["chars_experiments"][3]))
		mistake = ", ".join(mistake)
	message = f"Description: {desc}\nCreation: {creation}\nFeature: {feature}\nMistake: {mistake}"
	await ctx.respond(message)

file = open('matrices/characters/monsters.json')
intelligence["chars_monsters"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Monster")
async def monster(ctx):
	log("/matrix enemy monster")
	result = roll_all_matrices(intelligence["chars_monsters"])
	amount = result[0]
	desc = result[1]
	feature = result[2]
	horror = result[3]
	if amount == "Dire (3-6 ARMOR, 6D6-10D6 HP, roll another horror)":
		horror += " __*and*__ " + roll_intelligence_matrix(intelligence["chars_monsters"][3])
	message = f"Description: {desc}\nAmount: {amount}\nFeature: {feature}\nHorror: {horror}"
	await ctx.respond(message)

file = open('matrices/characters/robots.json')
intelligence["chars_robots"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Robot")
async def robot(ctx):
	log("/matrix enemy robot")
	result = roll_all_matrices(intelligence["chars_robots"])
	budget = result[0]
	desc = result[1]
	feature = result[2]
	prog = result[3]
	
	if budget == "Federal\u2014roll again for conflicting programming":
		prog_conflict = roll_intelligence_matrix(intelligence["chars_robots"][3])
		while prog_conflict == prog:
			prog_conflict = roll_intelligence_matrix(intelligence["chars_robots"][3])
		prog = f"{prog} (conflicts with: {prog_conflict})"
	elif budget == "CYCLOPS\u2014add 1D6 additional features":
		possible_features = list(intelligence["chars_robots"][2]["Values"].values())
		feature = rnd.sample(possible_features,1+d6())
		feature = ", ".join(feature)
	elif budget == "Corporate\u2014mash together 1D6 descriptions":
		possible_descs = list(intelligence["chars_robots"][1]["Values"].values())
		desc = rnd.sample(possible_descs,rnd.randint(2,6))
		desc = ", ".join(desc)
	
	message = f"Description: {desc}\nBudget: {budget}\nFeature: {feature}\nProgramming: {prog}"
	await ctx.respond(message)

file = open('matrices/characters/squads.json')
intelligence["chars_squads"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Squad")
async def squad(ctx):
	log("/matrix enemy squad")
	result = roll_all_matrices(intelligence["chars_squads"])
	rep = result[0]
	command = result[1]
	name = result[2]
	feature = result[3]
	if d6() <= 3:
		feature = f"{feature} __*and*__ {roll_intelligence_matrix(intelligence['chars_squads'][3])}"
	theme = result[4]
	message = f"Name: {name}\nReputation: {rep}\nFeature: {feature}\nTheme: {theme}"
	await ctx.respond(message)

fact_group = matrix_group.create_subgroup("faction", "Faction Intelligence Matrices")

file = open('matrices/factions/aliens.json')
intelligence["facs_aliens"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Alien faction")
async def aliens(ctx):
	log("/matrix faction aliens")
	result = roll_all_matrices(intelligence["facs_aliens"])
	origin = result[0]
	mission = result[1]
	desc = result[2]
	feature = result[3]
	truth = roll_extra_possibility(result[4])
	message = f"Description: {desc}\nFeature: {feature}\nMission: {mission}\nOrigin: {origin}\nTruth: {truth}"
	await ctx.respond(message)

file = open('matrices/factions/agencies.json')
intelligence["facs_agencies"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Agency")
async def agency(ctx):
	log("/matrix faction agency")
	result = roll_all_matrices(intelligence["facs_agencies"])
	parent = result[0]
	name = result[1]
	feature = result[2]
	function = result[3]
	message = f"Name: {name}\nFeature: {feature}\nParent: {parent}\nFunction: {function}"
	await ctx.respond(message)

file = open('matrices/factions/corporations.json')
intelligence["facs_corporations"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Corporation")
async def corporation(ctx):
	log("/matrix faction corporation")
	result = roll_all_matrices(intelligence["facs_corporations"])
	sector = result[0]
	if sector == "Megacorp (roll 1D6 sectors)":
		possible_sectors = list(intelligence["facs_corporations"][0]["Values"].values())
		possible_sectors.remove("Megacorp (roll 1D6 sectors)")
		subsectors = rnd.sample(possible_sectors,rnd.randint(2,6))
		sector = f"Megacorp ({', '.join(subsectors)})"
	name = result[1]
	feature = result[2]
	scheme = result[3]
	message = f"Name: {name}\nSector: {sector}\nFeature: {feature}\nScheme: {scheme}"
	await ctx.respond(message)

file = open('matrices/factions/criminals.json')
intelligence["facs_criminals"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Criminal organization")
async def criminals(ctx):
	log("/matrix faction criminals")
	result = roll_all_matrices(intelligence["facs_criminals"])
	honor = result[0]
	name = result[1]
	feature = result[2]
	racket = result[3]
	message = f"Name: {name}\nFeature: {feature}\nRacket: {racket}\nHonor: {honor}"
	await ctx.respond(message)

file = open('matrices/factions/cults.json')
intelligence["facs_cults"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Cult")
async def cult(ctx):
	log("/matrix faction cult")
	result = roll_all_matrices(intelligence["facs_cults"])
	lead = result[0]
	size = result[1]
	desc = result[2]
	feature = result[3]
	prophecy = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nLeadership: {lead}\nSize: {size}\nProphecy: *\"{prophecy}!\"*"
	await ctx.respond(message)

file = open('matrices/factions/insurgents.json')
intelligence["facs_insurgents"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Insurgent group")
async def insurgents(ctx):
	log("/matrix faction insurgents")
	result = roll_all_matrices(intelligence["facs_insurgents"])
	foothold = result[0]
	desc = result[1]
	feature = result[2]
	strategy = result[3]
	if strategy == "Spin a new image of their ideology, reroll description":
		desc2 = roll_intelligence_matrix(intelligence['facs_insurgents'][1])
		while desc2 == desc:
			desc2 = roll_intelligence_matrix(intelligence['facs_insurgents'][1])
		desc = f"{desc} (being spun as {desc2})"
	message = f"Description: {desc}\nFeature: {feature}\nFoothold: {foothold}\nStrategy: {strategy}"
	await ctx.respond(message)

loc_group = matrix_group.create_subgroup("location", "Location Intelligence Matrices")

file = open('matrices/locations/battlefields.json')
intelligence["locs_battlefields"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Battlefield")
async def battlefield(ctx):
	log("/matrix location battlefield")
	result = roll_all_matrices(intelligence["locs_battlefields"])
	layout = result[0]
	desc = result[1]
	feature = result[2]
	grave = roll_extra_possibility(result[3])
	message = f"Layout: {layout}\nDescription: {desc}\nFeature: {feature}\nGrave: {grave}"
	await ctx.respond(message)

file = open('matrices/locations/cities.json')
intelligence["locs_cities"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random City")
async def city(ctx):
	log("/matrix location city")
	result = roll_all_matrices(intelligence["locs_cities"])
	cyclops = result[0]
	name = result[1]
	feature = result[2]
	headline = result[3]
	message = f"Name: {name}\nFeature: {feature}\nCyclops Surveillance Level: {cyclops}\nHeadline: *{headline}*"
	await ctx.respond(message)

file = open('matrices/locations/nature.json')
intelligence["locs_nature"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random location in Nature")
async def nature(ctx):
	log("/matrix location nature")
	result = roll_all_matrices(intelligence["locs_nature"])
	situation = result[0]
	desc = result[1]
	feature = result[2]
	claim = result[3]
	if situation == "Shaky\u2014roll two claims, situation deteriorating":
		claim += " __*and*__ " + roll_intelligence_matrix(intelligence["locs_nature"][3])
	elif situation in ["Powder keg\u2014roll 1D6 claims, tensions are high","War\u2014roll 1D6 claims, active conflict in the area"]:
		possible_claims = list(intelligence["locs_nature"][3]["Values"].values())
		subclaims = rnd.sample(possible_claims, d6())
		claim = '\n- ' + '\n- '.join(subclaims)
	message = f"Description: {desc}\nFeature: {feature}\nSituation: {situation}\nClaim: {claim}"
	await ctx.respond(message)

file = open('matrices/locations/rooms.json')
intelligence["locs_rooms"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Room")
async def room(ctx):
	log("/matrix location room")
	result = roll_all_matrices(intelligence["locs_rooms"])
	exits = result[0]
	doors = result[1]
	desc = result[2]
	feature = result[3]
	event = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nDoors: {doors}\nExits: {exits}\nEvent: {event}"
	await ctx.respond(message)

file = open('matrices/locations/structures.json')
intelligence["locs_structures"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Structure")
async def structure(ctx):
	log("/matrix location structure")
	result = roll_all_matrices(intelligence["locs_structures"])
	owner = result[0]
	security = result[1]
	desc = result[2]
	feature = result[3]
	history = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nOwner: {owner}\nSecurity: {security}\nHistory: {history}"
	await ctx.respond(message)


file = open('matrices/locations/zones.json')
intelligence["locs_zones"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Zone")
async def zone(ctx):
	log("/matrix location zone")
	result = roll_all_matrices(intelligence["locs_zones"])
	size = result[0]
	integrity = result[1]
	desc = result[2]
	feature = result[3]
	center = result[4]
	message = f"Size: {size}\nDescription: {desc}\nFeature: {feature}\nIntegrity: {integrity}\nCenter: {center}"
	await ctx.respond(message)

lore_group = matrix_group.create_subgroup("lore", "Lore Intelligence Matrices")

file = open('matrices/lore/artifacts.json')
intelligence["lore_artifacts"] = json.load(file)
file.close()

def starts_with_vowel(word):
	vowels = ['a', 'e', 'i', 'o', 'u']
	if word[0].lower() in vowels:
		return "an"
	else:
		return "a"

@lore_group.command(description="Forges a random Artifact")
async def artifact(ctx):
	log("/matrix lore artifact")
	result = roll_all_matrices(intelligence["lore_artifacts"])
	interest = result[0]
	desc = result[1]
	feature = result[2]
	rumor = result[3]
	if rumor == "Conflicting archaeological accounts, reroll feature":
		second_feature = feature
		while feature == second_feature:
			second_feature = roll_intelligence_matrix(intelligence["lore_artifacts"][2])
		feature = f"{feature} *(but some say... {second_feature})*"
	elif rumor == "Hearsay has warped its image, reroll description":
		second_desc = desc
		while desc == second_desc:
			second_desc = roll_intelligence_matrix(intelligence["lore_artifacts"][1])
		a = starts_with_vowel(second_desc)
		desc = f"{desc} *(but lately, people believe it's {a} {second_desc})*"
	elif rumor == "Secret race to claim it, reroll interest":
		second_interest = interest
		while interest == second_interest:
			second_interest = roll_intelligence_matrix(intelligence["lore_artifacts"][0])
		interest = f"{interest} *(but more recently, it's {second_interest})*"
	message = f"Description: {desc}\nFeature: {feature}\nRumor: {rumor}\nInterest: {interest}"
	await ctx.respond(message)

file = open('matrices/lore/coverups.json')
intelligence["lore_coverups"] = json.load(file)
file.close()

@lore_group.command(description="Uncovers a random Coverup")
async def coverup(ctx):
	log("/matrix lore coverup")
	result = roll_all_matrices(intelligence["lore_coverups"])
	suppression = result[0]
	witness = result[1]
	if witness == "1D6 witnesses":
		witness = f"{rnd.randint(2,6)} witnesses"
	desc = result[2]
	feature = result[3]
	hook = result[4]
	message = f"Suppression: {suppression}\nWitness: {witness}\nDescription: {desc}\nFeature: {feature}\nHook: {hook}"
	await ctx.respond(message)

file = open('matrices/lore/diplomacy.json')
intelligence["lore_diplomacy"] = json.load(file)
file.close()

@lore_group.command(description="Establishes a random Diplomacy")
async def diplomacy(ctx):
	log("/matrix lore diplomacy")
	result = roll_all_matrices(intelligence["lore_diplomacy"])
	coverage = result[0]
	desc = result[1]
	feature = result[2]
	drama = result[3]
	message = f"Description: {desc}\nFeature: {feature}\nCoverage: {coverage}\nDrama: {drama}"
	await ctx.respond(message)

file = open('matrices/lore/disasters.json')
intelligence["lore_disasters"] = json.load(file)
file.close()

@lore_group.command(description="Causes a random Disaster")
async def disaster(ctx):
	log("/matrix lore disaster")
	result = roll_all_matrices(intelligence["lore_disasters"])
	scale = result[0]
	response = result[1]
	desc = result[2]
	feature = result[3]
	impact = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nScale: {scale}\nResponse: {response}\nImpact: {impact}"
	await ctx.respond(message)

file = open('matrices/lore/legends.json')
intelligence["lore_legends"] = json.load(file)
file.close()

@lore_group.command(description="Tells a random Legend")
async def legend(ctx):
	log("/matrix lore legend")
	result = roll_all_matrices(intelligence["lore_legends"])
	fate = result[0]
	if fate == "Many threads (roll two fates)":
		possible_fates = list(intelligence["lore_legends"][0]["Values"].values())
		possible_fates.remove("Many threads (roll two fates)")
		fates = rnd.sample(possible_fates, 2)
		fate = f"Many threads ({' and '.join(fates)})"
	desc = result[1]
	feature = result[2]
	achieve = result[3]
	while d6() <= 2:
		possible_achieves = list(intelligence["lore_legends"][3]["Values"].values())
		achieve += f" (or maybe {rnd.choice(possible_achieves)})"
	message = f"Description: {desc}\nFeature: {feature}\nAchievement: {achieve}\nUltimate Fate: {fate}"
	await ctx.respond(message)

file = open('matrices/lore/spells.json')
intelligence["lore_spells"] = json.load(file)
file.close()

@lore_group.command(description="Casts a random Spell")
async def spell(ctx):
	log("/matrix lore spell")
	result = roll_all_matrices(intelligence["lore_spells"])
	level = result[0]
	obscurity = result[1]
	name = result[2]
	if d6() <= 2:
		names = rnd.sample(list(intelligence["lore_spells"][2]["Values"].values()),2)
		names[0] = names[0].rsplit(" ", 1)
		names[1] = names[1].rsplit(" ", 1)
		name = names[0][0] + " " + names[1][1]
	feature = result[3]
	effect = result[4]
	message = f"Name: {name}\nEffect: {effect}\nFeature: {feature}\nLevel: {level}\nObscurity: {obscurity}"
	await ctx.respond(message)

bot.add_application_command(matrix_group)

atrx_group = discord.SlashCommandGroup("ataraxia", "RATIONS #1: ATARAXIA Commands")

file = open('rations/ataraxia.json')
intelligence["ataraxia"] = json.load(file)
file.close()

@atrx_group.command(description="Listens to a rumor from Vizhay")
async def rumor(ctx):
	log("/ataraxia rumor")
	result = roll_intelligence_matrix(intelligence["ataraxia"][0])
	message = f"You pick up on a rumor in Vizhay: {result}"
	await ctx.respond(message)

@atrx_group.command(description="Encounter something in Dyatlov Pass")
async def encounter(ctx):
	log("/ataraxia encounter")
	result = roll_intelligence_matrix(intelligence["ataraxia"][1])
	message = f"During your travels through Dyatlov Pass, you run into: **{result}**"
	await ctx.respond(message)

bot.add_application_command(atrx_group)

hzfc_group = discord.SlashCommandGroup("hazfunction", "RATIONS #2: HAZARD FUNCTION Commands")

file = open('rations/hazard_function.json')
intelligence["hazfunction"] = json.load(file)
file.close()

@hzfc_group.command(description="Enter a new chamber")
async def room(ctx):
	log("/hazfunction room")
	result = roll_intelligence_matrix(intelligence["hazfunction"][0])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's hazard")
async def hazard(ctx):
	log("/hazfunction hazard")
	result = roll_intelligence_matrix(intelligence["hazfunction"][1])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a crucible animal")
async def animal(ctx):
	log("/hazfunction animal")
	result = roll_intelligence_matrix(intelligence["hazfunction"][4])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's encounter")
async def encounter(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True)):
	log(f"/hazfunction encounter {rooms_cleared}")
	if rooms_cleared < 0:
		await ctx.respond("Rooms cleared must be non-negative.",ephemeral=True)
		return
	options = intelligence["hazfunction"][2]["Values"]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	result = options[str(roll)]
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's item")
async def item(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True)):
	log(f"/hazfunction item {rooms_cleared}")
	if rooms_cleared < 0:
		await ctx.respond("Rooms cleared must be non-negative.",ephemeral=True)
		return
	options = intelligence["hazfunction"][3]["Values"]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	result = options[str(roll)]
	await ctx.respond(result)

@hzfc_group.command(description="Enter a new chamber, and outfit it with an encounter, hazard, and item")
async def full_room(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True)):
	log(f"/hazfunction full_room {rooms_cleared}")
	if rooms_cleared < 0:
		await ctx.respond("Rooms cleared must be non-negative.",ephemeral=True)
		return
	room = roll_intelligence_matrix(intelligence["hazfunction"][0])
	haz = roll_intelligence_matrix(intelligence["hazfunction"][1])
	encounter_options = intelligence["hazfunction"][2]["Values"]
	item_options = intelligence["hazfunction"][3]["Values"]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	encounter = encounter_options[str(roll)]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	item = item_options[str(roll)]
	await ctx.respond(f"{room}\n\nHazard: **{haz}**\nEncounter: **{encounter}**\nItem: **{item}**")

def hazfunc_codename():
	military_letter_codes = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL", "INDIA", "JULIET", "KILO", "LIMA", "MIKE", "NOVEMBER", "OSCAR", "PAPA", "QUEBEC", "ROMEO", "SIERRA", "TANGO", "UNIFORM", "VICTOR", "WHISKEY", "XRAY", "YANKEE", "ZULU"]
	return f"{rnd.choice(military_letter_codes)}-{rnd.randint(0,9)}"

@hzfc_group.command(description="Produces a random Hazard Function character")
async def character(ctx):
	log(f"/hazfunction character")
	
	message = f"# {hazfunc_codename()}"
	message += "\nROLE: **SURVIVOR**\nDescribe why you want to live. If you live until the end of the mission, take another trait and gain a role, change your MAX HP to 6, then take a standard issue item, +1D6 MAX HP, or +1D6 WAR DICE.\n\n"
	
	traits = [rnd.choice(trait_data)]
	
	stats = {
		"MAX": d6(),
		"WAR": 0,
		"FORCEFUL": 0,
		"TACTICAL": 0,
		"CREATIVE": 0,
		"REFLEXIVE": 0
	}
	
	for trait in traits:
		bonus = trait["Stat"].split(" ")
		num = 0
		if bonus[1] in stats:
			try: 
				num = rolldice.roll_dice(bonus[0])[0]
			except Exception as e:
				num = 0
				log(f"Caught dice-rolling exception: {e}")
			stats[bonus[1]] += num
	
	message += f"MAX HP: {stats['MAX']}\n"
	message += f"WAR DICE: {stats['WAR']}\n\n"
	message += f"FORCEFUL: {stats['FORCEFUL']}\n"
	message += f"TACTICAL: {stats['TACTICAL']}\n"
	message += f"CREATIVE: {stats['CREATIVE']}\n"
	message += f"REFLEXIVE: {stats['REFLEXIVE']}\n\n"
	
	message += "TRAITS:\n"
	altmessage = message
	for trait in traits:
		message += f"- **{trait['Name']}** ({trait['Number']}): {trait['Effect']} ({trait['Stat']})\n"
		altmessage += f"- **{trait['Name']}** ({trait['Number']}, {trait['Stat']})\n"
	
	message += f"\n*Your trait item, **{traits[0]['Item']}**, is not given to you to start. You may be able to acquire it during the Crucible.*"
	altmessage += f"\n\n*Your trait item, **{traits[0]['Item']}**, is not given to you to start. You may be able to acquire it during the Crucible.*"
	
	if len(message) > 2000:
		message = message.replace("FORCEFUL", "FRC")
		message = message.replace("CREATIVE", "CRE")
		message = message.replace("REFLEXIVE", "RFX")
		message = message.replace("TACTICAL", "TAC")
		message = message.replace("DAMAGE", "DMG")
		if len(message) > 2000:
			message = altmessage
	if len(message) > 2000:
		message = message.replace("FORCEFUL", "FRC")
		message = message.replace("CREATIVE", "CRE")
		message = message.replace("REFLEXIVE", "RFX")
		message = message.replace("TACTICAL", "TAC")
		message = message.replace("DAMAGE", "DMG")
		if len(message) > 2000:
			await ctx.respond("The generated character does not fit in the 2,000 character limit for messages. Try lowering the amount of traits.",ephemeral=True)
			return
	await ctx.respond(message)

bot.add_application_command(hzfc_group)

ctsh_group = discord.SlashCommandGroup("colony", "RATIONS #3: CULTURE SHOCK Commands")

file = open('rations/culture_shock.json')
intelligence["cultshock"] = json.load(file)
file.close()

def strain():
	symptom = roll_intelligence_matrix(intelligence["cultshock"][0])
	area = roll_intelligence_matrix(intelligence["cultshock"][1])
	return f"{symptom} {area}"

@ctsh_group.command(description="Provide a new Bacteria Canister from Colony's shop")
async def canister(ctx, amount: discord.Option(discord.SlashCommandOptionType.integer, "The number of canisters to provide", required=False, default=1)):
	log(f"/colony canister {amount}")
	if amount < 1:
		await ctx.respond("Canisters provided must be 1 or more.",ephemeral=True)
	elif amount > 15:
		await ctx.respond("Canisters provided must be 15 or less.",ephemeral=True)
	elif amount == 1:
		await ctx.respond(f"Colony offers you a Bacteria Canister that's labelled... **{strain()}**. Whatever that means.")
	else:
		msg = "Colony offers you several Bacteria Canisters:"
		for i in range(amount):
			msg += f"\n- **{strain()}**"
		await ctx.respond(msg)

@ctsh_group.command(description="Roll to see if Colony will spawn.")
async def spawn(ctx):
	log(f"/colony spawn")
	if d6() % 2 == 1:
		await ctx.respond("Colony **will** spawn in this region.")
	else:
		await ctx.respond("Colony **will not** spawn in this region.")

bot.add_application_command(ctsh_group)

log("Starting bot session")
bot.run(token)