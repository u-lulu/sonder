import discord # pip install py-cord
import json
from difflib import get_close_matches
import re
import random as rnd
from datetime import datetime
from datetime import date
from time import time
import os
import math
import rolldice # pip install py-rolldice
from func_timeout import func_timeout, FunctionTimedOut # pip install func-timeout
import qrcode # pip install qrcode
from copy import deepcopy
import asyncio
from io import BytesIO
import zipfile
import requests

STANDARD_CHARACTER_LIMIT = 10
PREMIUM_CHARACTER_LIMIT = 100
standard_custrait_limit = 2 * STANDARD_CHARACTER_LIMIT
premium_custrait_limit = 2 * PREMIUM_CHARACTER_LIMIT

ITEM_LIMIT = 50
logging_channel_id = 1145165620082638928
logging_channel = None
backups_channel_id = 1240474179481108510
backups_channel = None

def log(msg,alert=False):
	msg = str(msg).strip()
	print(date.today(), datetime.now().strftime("| %H:%M:%S |"), msg)
	try:
		if logging_channel is not None and not bot.is_closed():
			full_msg = f"<t:{int(time())}:R> `{msg}`"
			if alert:
				full_msg += f" (<@{ownerid}>)"
			asyncio.create_task(logging_channel.send(full_msg))
	except Exception as e:
		print(date.today(), datetime.now().strftime("| %H:%M:%S |"), f"Could not log previous message: {e}")

log("Initializing...")
boot_time = int(time())

bot = discord.Bot(activity=discord.Game(name='Loading...'),status=discord.Status.dnd)

log("Loading token")
token_file = open('token.json')
token_file_data = json.load(token_file)
ownerid = token_file_data["owner_id"]
token = token_file_data["token"]
token_file.close()
del token_file_data

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
		best_match = get_close_matches(trait.upper(), trait_names, n=1, cutoff=0.0)

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
		best_match = get_close_matches(role.upper(), role_names, n=1, cutoff=0.0)

		if len(best_match) > 0 and best_match[0] in roles_by_name:
			return role_message_format(roles_by_name[best_match[0]])
		else:
			message = "Could not find a role with an approximately similar name."
	return message

def roll_intelligence_matrix(table,generator=rnd):
	roll_type = table["Roll"].upper()
	if roll_type == "2D6":
		roll_result = generator.randint(1,6) + generator.randint(1,6)
		return table["Values"][str(roll_result)]
	else:
		return generator.choice(list(table["Values"].values()))

def roll_all_matrices(table_list,generator=rnd):
	out = []
	for table in table_list:
		out.append(roll_intelligence_matrix(table,generator))
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

def character_has_trait(character, number):
	if type(number) is not int:
		raise ValueError(f"character_has_trait received argument of type {type(number)} for number, expected {int}")
		return
	for trait in character['traits']:
		if trait['Number'] == number:
			return True
	return False

def get_commands_from_string(working_string):
	commands = []
	while '`/' in working_string:
		try:
			start_of_command = working_string.index('`/') + 2
			working_string = working_string[start_of_command:]
			end_of_command = working_string.index('`')
			command_name = working_string[:end_of_command]
			commands.append(command_name)
			working_string = working_string[end_of_command+1:]
		except ValueError as e:
			break
	return commands

def replace_commands_with_mentions(text):
	cmds = set(get_commands_from_string(text))
	for cmd in cmds:
		cmd_object = bot.get_application_command(cmd)
		if type(cmd_object) is discord.SlashCommand:
			cmd_formatted = "`/" + cmd + "`"
			text = text.replace(cmd_formatted,cmd_object.mention)
	return text

async def response_with_file_fallback(ctx:discord.ApplicationContext, message:str, eph=False):
	if len(message) > 2000:
		filedata = BytesIO(message.encode('utf-8'))
		out = await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata,filename='response.md'),ephemeral=eph)
		log(f"Sent response to /{ctx.command.qualified_name} as file")
		return out
	else:
		return await ctx.respond(message,ephemeral=eph)

async def paginated_response(ctx:discord.ApplicationContext, pages:list[str], eph=False):
	class Pager(discord.ui.View):
		pages = []
		current_page = 0
		max_page = 0
		def __init__(self,pages):
			super().__init__(timeout=5*60,disable_on_timeout=True)
			self.pages = pages
			self.max_page = len(pages) - 1
		@discord.ui.button(label="Previous",emoji="⬅️")
		async def page_down_callback(self,button,interaction):
			self.current_page -= 1
			if self.current_page < 0:
				self.current_page = self.max_page
			await interaction.response.edit_message(content=self.pages[self.current_page],view=self)
		@discord.ui.button(label="Next",emoji="➡️")
		async def page_up_callback(self,button,interaction):
			self.current_page += 1
			if self.current_page > self.max_page:
				self.current_page = 0
			await interaction.response.edit_message(content=self.pages[self.current_page],view=self)
	
	while '' in pages:
		# trim out pages with no content
		pages.remove('')

	if len(pages) == 1:
		# if there is only 1 page, simply show that page without buttons
		return await ctx.respond(pages[0],ephemeral=eph)
	elif len(pages) <= 0:
		# if there are no pages, what are you doing?
		raise Exception("paginated_response recieved empty pages list")
	
	for page in pages:
		# ensure no page would exceed message length cap
		if len(page) > 2000:
			raise Exception(f"paginated_response recieved page of size {len(page)} (expected maximum 2000)")

	return await ctx.respond(pages[0],view=Pager(pages),ephemeral=eph)

def replace_ignoring_case(string,thing_to_replace,replacement):
	while thing_to_replace.lower() in string.lower():
		start_index = string.lower().index(thing_to_replace.lower())
		end_index = start_index + len(thing_to_replace)
		before_string = string[:start_index]
		after_string = string[end_index:]
		string = before_string + replacement + after_string
	return string

async def roll_dice_with_context(ctx,syntax,reply=True):
	output = ()
	timeout = 2
	character = get_active_char_object(ctx)

	stats = ['frc','tac','cre','rfx']

	for stat in stats:
		if stat in syntax.lower():
			if character is None:
				if reply:
					await ctx.respond(replace_commands_with_mentions(f"You do not have an active character in this channel that can provide a {stat.upper()} score. Select one with `/switch_character`."),ephemeral=True)
				return None
			else:
				relevant_stat = str(character[stat])
				syntax = replace_ignoring_case(syntax,stat,relevant_stat)

	try:
		result = func_timeout(timeout, rolldice.roll_dice, args=[syntax])

		if len(str(result[0])) > 100 or len(result[1]) > 1000:
			await ctx.respond("The result of your dice syntax is too long. Use smaller numbers.",ephemeral=True)
			return None

		return result
	except rolldice.rolldice.DiceGroupException as e:
		if reply:
			log(f"Caught: {e}")
			await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return None
	except FunctionTimedOut as e:
		if reply:
			log(f"Caught: {e}")
			await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return None
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		if reply:
			log(f"Caught: {e}")
			await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return None

subscription_cache = {}
sub_cache_timeout = 60 * 60 # 1 hour

def select_random_novel_trait(character: dict):
	allowed_traits = list(traits_by_number.keys())
	for t in character['traits']:
		if t['Number'] in allowed_traits:
			allowed_traits.remove(t['Number'])
	
	for item in character['special'].values():
		if (type(item) is dict
	  		and item.get('Number',None) is not None
			and item['Number'] in allowed_traits):
			allowed_traits.remove(item['Number'])
	
	if len(allowed_traits) > 0:
		chosen_number = rnd.choice(allowed_traits)
		chosen_trait = traits_by_number[chosen_number]
		return chosen_trait
	else:
		return None

def apply_stat_change(character: dict, stat: str):
	stats = ["MAX","WAR","FORCEFUL","TACTICAL","CREATIVE","REFLEXIVE"]
	
	stats_translator = {
		"MAX":"maxhp",
		"WAR":"wd",
		"FORCEFUL":"frc",
		"TACTICAL":"tac",
		"CREATIVE":"cre",
		"REFLEXIVE":"rfx"
	}
	
	bonus = stat.split(" ")
	num = 0
	if bonus[1] in stats and "in animal form" not in stat: #ignore LYCANTHROPE since Max HP is not immediate
		translated_stat_bonus = stats_translator[bonus[1]]
		try: 
			num = rolldice.roll_dice(bonus[0])[0]
		except Exception as e:
			num = 0
			log(f"Caught dice-rolling exception: {e}")
		character[translated_stat_bonus] += num
		if translated_stat_bonus == 'maxhp':
			character['hp'] += num
	
	return character

def revoke_stat_change(character: dict, stat: str):
	stats = ["MAX","WAR","FORCEFUL","TACTICAL","CREATIVE","REFLEXIVE"]

	stats_translator = {
		"MAX":"maxhp",
		"WAR":"wd",
		"FORCEFUL":"frc",
		"TACTICAL":"tac",
		"CREATIVE":"cre",
		"REFLEXIVE":"rfx"
	}

	bonus = stat.split(" ")
	num = 0
	if bonus[1] in stats and "in animal form" not in stat: #ignore LYCANTHROPE
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
	
	return character

async def ext_character_management(id):
	try:
		id = int(id)
	except:
		log(f"Could not cast ID to integer for membership check, received value '{id}'")
		return False
	if id in subscription_cache and time() < subscription_cache[id]:
		log("Membership check succeeded via cache")
		return True
	if support_server_obj is None:
		log(f"No support server object exists, membership check fails")
		return False
	user = None
	try:
		user = await support_server_obj.fetch_member(id)
	except discord.HTTPException as e:
		log(f"User is not present on server (threw error), membership check fails")
		if id in subscription_cache:
			del subscription_cache[id]
		return False
	if user is None:
		log(f"User is not present on server, membership check fails")
		if id in subscription_cache:
			del subscription_cache[id]
		return False
	role = user.get_role(1142272148099055666)
	if role is None:
		log(f"User does not have role, membership check fails")
		if id in subscription_cache:
			del subscription_cache[id]
		return False
	log(f"Membership check succeeds")
	subscription_cache[id] = time() + sub_cache_timeout
	return True

support_server_id = 1101249440230154300
support_server_obj = None

log("Loading user character data...")
character_data = {}

async def save_character_data(userid=None):
	if userid is None: #fallback to saving all data
		log("Saving all character data...")
		for userid in character_data:
			await save_character_data(userid)
		return
	
	try:
		if userid in character_data:
			psavestart = time()
			if not os.path.exists('playerdata'):
				os.mkdir('playerdata')
			with open(f"playerdata/{userid}.json", "w") as outfile:
				outfile.write(json.dumps(character_data[userid],indent=2))
			psaveend = time()
			savetime = round(psaveend-psavestart,5)
			this_guys_chars = len(character_data[userid]['chars'])
			this_guys_traits = len(character_data[userid]['traits'])
			sz = os.stat(f"playerdata/{userid}.json").st_size
			size_in_kb = round(sz / (1024), 2)
			size_in_mb = round(sz / (1024*1024), 2)
			log(f"Character data for {userid} saved in {savetime if savetime > 0 else '<0.00001'}s ({size_in_kb if size_in_mb < 1 else size_in_mb} {'KB' if size_in_mb < 1 else 'MB'}). Contains {this_guys_chars} characters & {this_guys_traits} custom traits.")
		else:
			if os.path.exists(f'playerdata/{userid}.json'):
				log(f"Character data for {userid} deleted.")
				os.remove(f'playerdata/{userid}.json')
	except Exception as e:
		log(f"PLAYER DATA SAVING FOR {userid} THREW AN ERROR: {e}")
		await bot.wait_until_ready()
		owner_object = await bot.get_or_fetch_user(ownerid)
		await owner_object.send(f"**An error occurred while saving `{userid}.json`!**\n```{e}```")

if os.path.exists('playerdata'):
	present_files = os.listdir('playerdata')
	for filename in present_files:
		userid = filename.split(".")[0]
		ploadstart = time()
		file = open(f'playerdata/{filename}')
		character_data[userid] = json.load(file)
		file.close()
		ploadend = time()
		loadtime = round(ploadend-ploadstart,5)
		this_guys_chars = len(character_data[userid]['chars'])
		this_guys_traits = len(character_data[userid]['traits'])
		sz = os.stat(f'playerdata/{filename}').st_size
		size_in_kb = round(sz / (1024), 2)
		size_in_mb = round(sz / (1024*1024), 2)
		log(f"Loaded player data for {userid} in {loadtime if loadtime > 0 else '<0.00001'}s ({size_in_kb if size_in_mb < 1 else size_in_mb} {'KB' if size_in_mb < 1 else 'MB'}). Contains {this_guys_chars} characters & {this_guys_traits} custom traits.")
elif os.path.exists('player_data.json'):
	log("Old player data found. Converting...")
	ploadstart = time()
	file = open('player_data.json')
	character_data = json.load(file)
	file.close()
	ploadend = time()
	loadtime = round(ploadend-ploadstart,5)
	total_users = len(character_data)
	total_characters = 0
	total_traits = 0
	for userid in character_data:
		total_characters += len(character_data[userid]['chars'])
		total_traits += len(character_data[userid]['traits'])
	sz = os.stat("player_data.json").st_size
	size_in_kb = round(sz / (1024), 2)
	size_in_mb = round(sz / (1024*1024), 2)
	log(f"Loaded {size_in_kb if size_in_mb < 1 else size_in_mb} {'KB' if size_in_mb < 1 else 'MB'} file in {loadtime if loadtime > 0 else '<0.00001'}s. Storing data about {total_characters} characters & {total_traits} custom traits created by {total_users} users")
	asyncio.run(save_character_data())
	os.rename('player_data.json','player_data_old.json')
	log('Restarting...')
	exit()
else:
	log("Player data does not exist. Using empty data.")
	os.mkdir('playerdata')

log("Checking to see if character data needs to be updated...")
changed = False
for player in character_data:
	if 'traits' not in character_data[player]:
		character_data[player]['traits'] = {}
		log(f"{player} updated to include custom traits field")
		changed = True

	for char in character_data[player]['chars']:
		if 'counters' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['counters'] = {}
			log(f"{char} (owned by {player}) updated to include counters field")
			changed = True
		if 'notes' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['notes'] = ""
			log(f"{char} (owned by {player}) updated to include notes field")
			changed = True
		if 'special' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['special'] = {}
			log(f"{char} (owned by {player}) updated to include special field")
			changed = True
		if 'pronouns' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['pronouns'] = None
			log(f"{char} (owned by {player}) updated to include pronouns field")
			changed = True
		if 'image' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['image'] = None
			log(f"{char} (owned by {player}) updated to include image field")
			changed = True
		if 'embed_color' not in character_data[player]['chars'][char]:
			character_data[player]['chars'][char]['embed_color'] = None
			log(f"{char} (owned by {player}) updated to include embed_color field")
			changed = True
		if 'henshin_trait' not in character_data[player]['chars'][char]['special'] or 'henshin_stored_hp' not in character_data[player]['chars'][char]['special'] or 'henshin_stored_maxhp' not in character_data[player]['chars'][char]['special']:
			for trt in character_data[player]['chars'][char]['traits']:
				if trt['Number'] == 316:
					changed = True
					log(f"{char} (owned by {player}) updated to include HENSHIN sub-fields")
					character_data[player]['chars'][char]['special']['henshin_trait'] = None
					character_data[player]['chars'][char]['special']['henshin_stored_hp'] = 0
					character_data[player]['chars'][char]['special']['henshin_stored_maxhp'] = 0
					break
		if 'volatile_trait' not in character_data[player]['chars'][char]['special']:
			for trt in character_data[player]['chars'][char]['traits']:
				if trt['Number'] == 652:
					changed = True
					log(f"{char} (owned by {player}) updated to include VOLATILE sub-field")
					vtrait = select_random_novel_trait(character_data[player]['chars'][char])
					character_data[player]['chars'][char]['special']['volatile_trait'] = vtrait
					apply_stat_change(character_data[player]['chars'][char],vtrait['Stat'])
					break

if changed:
	asyncio.run(save_character_data())
else:
	log("No required changes to player data found.")

SAVE_INTERVAL = 86400
backups_have_already_started = False

async def backup_generation_loop():
	global backups_have_already_started
	if backups_have_already_started:
		log("Backup generation loop is already running.")
		return
	else:
		backups_have_already_started = True
	while True:
		if backups_channel is None:
			log(f"Backups channel does not exist. Trying again in {SAVE_INTERVAL} seconds.",alert=True)
		else:
			try:
				data_dir = 'playerdata'
				zip_buffer = BytesIO()
				
				save_time = int(time())

				with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_BZIP2, compresslevel=9) as zipf:
					for root,dirs,files in os.walk(data_dir):
						for file in files:
							relative_path = os.path.relpath(os.path.join(root, file), data_dir)
							zipf.write(os.path.join(root, file), arcname=relative_path)
				
				zip_buffer.seek(0)

				n = f'backup-{save_time}.zip'
				backup_file = discord.File(zip_buffer,filename=n)

				await backups_channel.send(file=backup_file)
				log(f"Created backup file '{n}' in backup channel. Repeating in {SAVE_INTERVAL} seconds.")
			except Exception as e:
				log(f"Failed to create a backup. Trying again in {SAVE_INTERVAL} seconds. Error: {e}",alert=True)

		await asyncio.sleep(SAVE_INTERVAL)

log("Creating generic commands")
@bot.event
async def on_ready():
	try:
		log("Checking for support server...")
		global support_server_obj
		support_server_obj = await bot.fetch_guild(support_server_id)
		log(f"Support server found: {support_server_obj.name} ({support_server_obj.id})")
	except Exception as e:
		log(f"Support server could not be found: {e}")
		support_server_obj = None

	try:
		log("Checking for logging channel...")
		global logging_channel
		logging_channel = await bot.fetch_channel(logging_channel_id)
		log(f"Hello logging channel!: {logging_channel.name} ({logging_channel.id})")
	except Exception as e:
		log(f"Logging channel could not be found: {e}")
		logging_channel = None
	
	try:
		log("Checking for backups channel...")
		global backups_channel
		backups_channel = await bot.fetch_channel(backups_channel_id)
		log(f"Found backups channel: {backups_channel.name} ({backups_channel.id})")
	except Exception as e:
		log(f"Backups channel could not be found: {e}")
		backups_channel = None
	
	await bot.change_presence(activity=discord.Game(name='FIST: Ultra Edition'),status=discord.Status.online)
	log(f"{bot.user} is ready and online in {len(bot.guilds)} guilds!")
	boot_time = int(time())
	
	report_player_count = len(character_data)
	report_character_count = 0
	report_trait_count = 0
	for player in character_data:
		report_character_count += len(character_data[player]['chars'])
		report_trait_count += len(character_data[player]['traits'])
	log(f"Currently tracking {report_player_count} players, {report_character_count} characters, and {report_trait_count} custom traits.")

	asyncio.create_task(backup_generation_loop())

@bot.event
async def on_application_command(ctx):
	args = []
	if ctx.selected_options is not None:
		for argument in ctx.selected_options:
			args.append(f"{argument['name']}:{argument['value']}")
	args = ' '.join(args)
	if len(args) > 0:
		log(f"/{ctx.command.qualified_name} {args}")
	else:
		log(f"/{ctx.command.qualified_name}")

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, e):
	await ctx.channel.send(f"⚠️ A command from {ctx.author.mention} could not be fulfilled due to the following error:\n`{e}`\n-# This error has been logged and reported to the developer. If this continues, please submit a bug report on the [Support Server](<https://discord.gg/VeedQmQc7k>) or the [Github issues page](<https://github.com/u-lulu/sonder/issues>).")
	log(f"Uncaught exception thrown: {e}",alert=True)
	raise e

@bot.command(description="Checks how long the bot has been online")
async def uptime(ctx):
	await ctx.respond(f"Online since <t:{boot_time}:D> at <t:{boot_time}:T> (<t:{boot_time}:R>)",ephemeral=True)

@bot.command(description="Measures this bot's latency")
async def ping(ctx):
	await ctx.respond(f"Pong! Latency is {bot.latency}")

@bot.command(description="Shuts down the bot. Will not work unless you own the bot.")
async def shutdown(ctx):
	if ctx.author.id == ownerid:
		log(f"Shutdown request accepted ({ctx.author.id})")
		await ctx.defer()
		await bot.change_presence(activity=discord.Game(name='Shutting down...'),status=discord.Status.dnd)
		await save_character_data()
		await ctx.respond(f"Restarting.")
		await bot.close()
	else:
		log(f"Shutdown request denied ({ctx.author.id})")
		await ctx.respond(f"Only <@{ownerid}> may use this command.",ephemeral=True)

@bot.command(description="Links to the Help document for this bot")
async def help(ctx):
	await ctx.respond("[Full command documentation](https://docs.google.com/document/d/15pm5o5cJuQF_J3l-NMpziPEuxDkcWJVE3TNT7_IerbQ/edit?usp=sharing)",ephemeral=True)

@bot.command(description="Links to the invite page for this bot")
async def invite(ctx):
	await ctx.respond("[Invite page](https://discord.com/api/oauth2/authorize?client_id=1096635021395251352&permissions=274877908992&scope=bot%20applications.commands)",ephemeral=True)

@bot.command(description="Links to the support server for this bot")
async def server(ctx):
	await ctx.respond("https://discord.gg/VeedQmQc7k",ephemeral=True)

credits_file = open('credits.md')
credits_string = credits_file.read()
credits_file.close()

log(f"Got credits text ({len(credits_string)} characters long)")

@bot.command(description="Lists people responsible for this bot's creation")
async def credits(ctx):
	await ctx.defer(ephemeral=True)
	await ctx.respond(credits_string,ephemeral=True)

@bot.command(description="Check to see if you have an active membership")
async def membership(ctx):
	id = ctx.author.id
	await ctx.defer(ephemeral=True)
	if support_server_obj is None:
		log("Result is NO; no support server")
		await ctx.respond("This bot cannot locate the Support Server necessary to facilitate server subscriptions.\n**If you can see this message, something has gone wrong.**\nPlease contact me via the [Support Server]( https://discord.gg/VeedQmQc7k ) as soon as possible.",ephemeral=True)
		return
	try:
		user = await support_server_obj.fetch_member(id)
	except discord.HTTPException as e:
		log("Result is NO; not present on support server (threw exception)")
		await ctx.respond(f"You do not have an active subscription on [Ko-fi]( https://ko-fi.com/solarashlulu/tiers ).\nYou are able to manage {STANDARD_CHARACTER_LIMIT} characters and {standard_custrait_limit} custom traits.\nIf you have paid for a subscription but are seeing this message, you must join the [Support Server]( https://discord.gg/VeedQmQc7k ) and link your Ko-fi account to Discord before you can receive benefits.",ephemeral=True)
		if id in subscription_cache:
			del subscription_cache[id]
		return
	if user is None:
		log("Result is NO; not present on support server")
		await ctx.respond(f"You do not have an active subscription on [Ko-fi]( https://ko-fi.com/solarashlulu/tiers ).\nYou are able to manage {STANDARD_CHARACTER_LIMIT} characters and {standard_custrait_limit} custom traits.\nIf you have paid for a subscription but are seeing this message, you must join the [Support Server]( https://discord.gg/VeedQmQc7k ) and link your Ko-fi account to Discord before you can receive benefits.",ephemeral=True)
		if id in subscription_cache:
			del subscription_cache[id]
		return
	role = user.get_role(1142272148099055666)
	if role is None:
		log("Result is NO; no assigned role")
		await ctx.respond(f"You do not have an active subscription on [Ko-fi]( https://ko-fi.com/solarashlulu/tiers ).\nYou are able to manage {STANDARD_CHARACTER_LIMIT} characters and {standard_custrait_limit} custom traits.\nIf you have paid for a subscription but are seeing this message, you must link your Ko-fi account to Discord before you can receive benefits.",ephemeral=True)
		if id in subscription_cache:
			del subscription_cache[id]
		return
	log("Result is YES")
	await ctx.respond(f"You have an active subscription!\nYou are able to manage {PREMIUM_CHARACTER_LIMIT} characters and {premium_custrait_limit} custom traits.\nYou can manage your subscription on [Ko-fi]( https://ko-fi.com/solarashlulu/tiers ).",ephemeral=True)
	subscription_cache[id] = time() + sub_cache_timeout
	return

@bot.command(description="Pin (or unpin) a message inside a thread, if you own the thread")
async def threadpin(ctx, id: discord.Option(str, "The ID of the message to pin.", required=True, min_length=18, max_length=19)):
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
async def d66(ctx, instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1, min_value=1, max_value=1000)):
	outs = []
	
	for i in range(instances):
		outs.append(str(d6()) + str(d6()))
	message = ", ".join(outs)
	await response_with_file_fallback(ctx,message)

@bot.command(description="Roll 1d666")
async def d666(ctx: discord.ApplicationContext, instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1, min_value=1, max_value=1000)):
	outs = []

	for i in range(instances):
		outs.append(str(d6()) + str(d6()) + str(d6()))
	message = ", ".join(outs)
	await response_with_file_fallback(ctx,message)

def output_character(codename: str, data: dict):
	out = f"# {codename.upper()}"
	if data['pronouns'] is not None:
		out += f"\nPRONOUNS: {data['pronouns']}"
	else:
		out += f"\nPRONOUNS: *Not set.*"
	if data["role"] == {}:
		out += "\nROLE: *No role yet.*"
	else:
		r = data["role"]
		out += f"\nROLE: **{r['Name']}**\n{r['Text']}"
	
	out += f"\n\nHP: {data['hp']}/{data['maxhp']}"
	if 'henshin_stored_hp' in data['special'] and 'henshin_stored_maxhp' in data['special'] and data['special']['henshin_stored_maxhp'] != 0:
		out += f" - *({data['special']['henshin_stored_hp']}/{data['special']['henshin_stored_maxhp']} in normal form)*"
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
	
	if 'henshin_trait' in data['special'] and 'henshin_stored_maxhp' in data['special']:
		htrait = data['special']['henshin_trait']
		if htrait is not None:
			out += f"\nHENSHIN TRAIT ({'**__ACTIVE__**' if data['special']['henshin_stored_maxhp'] != 0 else 'INACTIVE'}):\n- **{htrait['Name']}** ({htrait['Number']}): {htrait['Effect']} ({htrait['Stat']})\n"
		else:
			out += replace_commands_with_mentions(f"\nHENSHIN TRAIT:\n- *Not set. Try out `/henshin`!*\n")
	
	out += "\nINVENTORY:"
	if len(data['items']) <= 0:
		out += "\n- *No items yet.*"
	else:
		for item in data['items']:
			out += f"\n- {item}"
			if item in data['counters']:
				counters = data['counters'][item]
				counter_strings = []
				for counter in counters:
					counter_strings.append(f"{counter.upper()}: {counters[counter]}")
				out += f" ({', '.join(counter_strings)})"
	return out

def output_character_short(codename: str, data: dict):
	out = f"# {codename.upper()}"
	if data['pronouns'] is not None:
		out += f"\nPRONOUNS: {data['pronouns']}"
	else:
		out += f"\nPRONOUNS: *Not set.*"
	if data["role"] == {}:
		out += "\nROLE: *No role yet.*"
	else:
		r = data["role"]
		out += f"\nROLE: **{r['Name']}**"
	
	out += f"\n\nHP: {data['hp']}/{data['maxhp']}"
	if 'henshin_stored_hp' in data['special'] and 'henshin_stored_maxhp' in data['special'] and data['special']['henshin_stored_maxhp'] != 0:
		out += f" - *({data['special']['henshin_stored_hp']}/{data['special']['henshin_stored_maxhp']} in normal form)*"
	out += f"\nWAR DICE: {data['wd']}"
	out += f"\nARMOR: {data['armor_name']} ({data['armor']})"
	out += f"\nWEAPON: {data['weapon_name']} ({data['damage']})"
	
	attribute_strings = []
	for attribute in ['frc','tac','cre','rfx']:
		if data[attribute] != 0:
			attribute_strings.append(f"{attribute.upper()}: {'+' if data[attribute] > 0 else ''}{data[attribute]}")
	attribute_strings = ", ".join(attribute_strings)
	
	if len(attribute_strings) > 0:
		out+= "\n\n" + attribute_strings
	
	out += "\n\nTRAITS:\n"
	if len(data['traits']) <= 0:
		out += "*No traits yet.*"
	else:
		alltraits = []
		for trait in data['traits']:
			alltraits.append(f"**{trait['Name'][0].upper()+trait['Name'][1:].lower()}** ({trait['Number']})")
			#out += f"- **{trait['Name']}** ({trait['Number']}, {trait['Stat']})\n"
		alltraits = ", ".join(alltraits)
		out += alltraits

	if 'henshin_trait' in data['special'] and 'henshin_stored_maxhp' in data['special']:
		htrait = data['special']['henshin_trait']
		if htrait is not None:
			out += f"\n- Henshin trait ({'**__active__**' if data['special']['henshin_stored_maxhp'] != 0 else 'inactive'}): **{htrait['Name'][0].upper()+htrait['Name'][1:].lower()}** ({htrait['Number']})"
		else:
			out += replace_commands_with_mentions(f"\n- Henshin trait: *Not set. Try out `/henshin`!*")
	
	out += "\n\nINVENTORY: "
	if len(data['items']) <= 0:
		out += "\n *No items yet.*"
	else:
		out += replace_commands_with_mentions(f"*{len(data['items'])} items. View with `/inventory`*.")
	return out

def get_embed_length(emb: discord.Embed):
	total = 0
	for field in emb.fields:
		total += len(field.name) + len(field.value)
	if type(emb.title) == str:
		total += len(emb.title)
	if type(emb.description) == str:
		total += len(emb.description)
	if emb.footer is not None:
		total += len(emb.footer.text)
	return total

def get_embed_group_length(embs: list[discord.Embed]):
	total = 0
	for emb in embs:
		total += get_embed_length(emb)
	return total

def any_embed_is_oversize(embs: list[discord.Embed]):
	for emb in embs:
		if get_embed_length(emb) > 6000:
			return True
	return False

def output_character_embed(codename: str, data: dict, author: discord.User):
	output = []

	stats_embed = discord.Embed()

	if data.get('image',None) is not None:
		stats_embed.thumbnail = discord.EmbedMedia(data['image'])

	if data['pronouns'] is not None:
		stats_embed.add_field(
			name="PRONOUNS",
			value=f'{data["pronouns"]}',
			inline=False
		)
	
	if data["role"] != {}:
		role_value = f'__{data["role"]["Name"]}__\n{data["role"]["Text"]}'
		if len(role_value) > 1024:
			role_value = role_value[:1024-3] + "..."
		stats_embed.add_field(
			name="ROLE",
			value=role_value,
			inline=False
		)

	statblock = f"HP: {data['hp']}/{data['maxhp']}"
	if 'henshin_stored_hp' in data['special'] and 'henshin_stored_maxhp' in data['special'] and data['special']['henshin_stored_maxhp'] != 0:
		statblock += f" - *({data['special']['henshin_stored_hp']}/{data['special']['henshin_stored_maxhp']} in normal form)*"
	statblock += f"\nWAR DICE: {data['wd']}"
	statblock += f"\nARMOR: {data['armor_name']} ({data['armor']})"
	if data['armor_name'] == "Nothing" and data['armor'] == 0:
		statblock += replace_commands_with_mentions("\n-# - Equip one with `/equip_armor`!")
	statblock += f"\nWEAPON: {data['weapon_name']} ({data['damage']})"
	if data['weapon_name'] == "Unarmed" and data['damage'] == "2d6k1":
		statblock += replace_commands_with_mentions("\n-# - Equip one with `/equip_weapon`!")
	
	if data['frc'] != 0 or data['tac'] != 0 or data['cre'] != 0 or data['rfx'] != 0:
		statblock += "\n"
	
	if data['frc'] != 0:
		statblock += f"\nFRC: {'+' if data['frc'] > 0 else ''}{data['frc']}"
	if data['tac'] != 0:
		statblock += f"\nTAC: {'+' if data['tac'] > 0 else ''}{data['tac']}"
	if data['cre'] != 0:
		statblock += f"\nCRE: {'+' if data['cre'] > 0 else ''}{data['cre']}"
	if data['rfx'] != 0:
		statblock += f"\nRFX: {'+' if data['rfx'] > 0 else ''}{data['rfx']}"

	stats_embed.add_field(
		name="STATS",
		value=statblock,
		inline=False
	)

	output.append(stats_embed)

	traits_embed = discord.Embed(title="TRAITS")

	if len(data['traits']) > 0:
		for trait in data['traits']:
			traitvalue = f"{trait['Effect']} ({trait['Stat']})"
			if len(traitvalue) > 1024:
				traitvalue = traitvalue[:1024-3] + "..."
			traits_embed.add_field(
				name=f"**{trait['Name']}** ({trait['Number']})",
				value=traitvalue,
				inline=False
			)
	
		if 'henshin_trait' in data['special'] and 'henshin_stored_maxhp' in data['special']:
			htrait = data['special']['henshin_trait']
			if htrait is not None:
				hvalue = f"**{htrait['Name']}** ({htrait['Number']})\n{htrait['Effect']} ({htrait['Stat']})"
				if len(hvalue) > 1024:
					hvalue = hvalue[:1024-3] + "..."
				traits_embed.add_field(
					name=f"Henshin Trait ({'**__ACTIVE__**' if data['special']['henshin_stored_maxhp'] != 0 else 'INACTIVE'})",
					value=hvalue,
					inline=False
				)
			else:
				traits_embed.add_field(
					name="Henshin Trait",
					value=replace_commands_with_mentions(f"*Not set. Try out `/henshin`!*\n"),
					inline=False
				)
		if 'volatile_trait' in data['special']:
			vtrait = data['special']['volatile_trait']
			vvalue = f"**{vtrait['Name']}** ({vtrait['Number']})\n{vtrait['Effect']} ({vtrait['Stat']})"
			if len(vvalue) > 1024:
				vvalue = vvalue[:1024-3] + "..."
			traits_embed.add_field(
				name=f"Volatile Trait",
				value=vvalue,
				inline=False
			)

	else:
		traits_embed.description = replace_commands_with_mentions("This character doesn't have any traits yet.\n-# Add one with `/add_trait`!")
		
	output.append(traits_embed)
	
	items_embed = discord.Embed(title="ITEMS")

	if len(data['items']) > 0:
		items_block = ""

		for item in data['items']:
			items_block += f"\n- {item}"
			if item in data['counters']:
				counters = data['counters'][item]
				counter_strings = []
				for counter in counters:
					counter_strings.append(f"{counter.upper()}: {counters[counter]}")
				items_block += f" ({', '.join(counter_strings)})"
		
		items_block = items_block.strip()

		if len(items_block) > 4096:
			cutoff = items_block[:4096].rfind("\n")
			if cutoff != -1:
				items_embed.description = items_block[:cutoff]
				items_block = items_block[cutoff+1:]
			else:
				new_cutoff = items_block.find("\n")
				items_embed.description = items_block[:4093] + "..."
				if new_cutoff != -1:
					items_block = items_block[new_cutoff+1:]
				else:
					items_block = ""
		else:
			items_embed.description = items_block
			items_block = ""

		while len(items_block) > 1024:
			cutoff = items_block[:1024].rfind("\n")
			if cutoff != -1:
				items_embed.add_field(
					name='',
					value=items_block[:cutoff],
					inline=False
				)
				items_block = items_block[cutoff+1:]
			else:
				new_cutoff = items_block.find("\n")
				items_embed.add_field(
					name='',
					value=items_block[:1021] + "...",
					inline=False
				)
				if new_cutoff != -1:
					items_block = items_block[new_cutoff+1:]
				else:
					items_block = ""
		
		if len(items_block) > 0:
			items_embed.add_field(
				name = '',
				value = items_block,
				inline=False
			)
	else:
		items_embed.description = replace_commands_with_mentions("This character's inventory is empty.\n-# Get items with `/add_item`!")
	
	output.append(items_embed)

	if data.get('embed_color',None) is not None:
		col = data["embed_color"]
		col = discord.Color.from_rgb(col["r"],col["g"],col["b"])
		for emb in output:
			emb.color = col
	
	return output

def get_active_codename(ctx):
	uid = None
	cid = None
	try:
		uid = str(ctx.author.id)
		cid = str(ctx.channel_id)
	except:
		try:
			uid = str(ctx.interaction.user.id)
			cid = str(ctx.interaction.channel.id)
		except:
			uid = str(ctx.user.id)
			cid = str(ctx.channel_id)
	if uid in character_data:
		your_actives = character_data[uid]['active']
		if cid in your_actives:
			return your_actives[cid]
	return None

def get_active_char_object(ctx):
	codename = get_active_codename(ctx)
	if codename is None:
		return None
	else:
		uid = None
		try:
			uid = str(ctx.author.id)
		except:
			try:
				uid = str(ctx.interaction.user.id)
			except:
				uid = str(ctx.user.id)
		return character_data[uid]['chars'][codename]

async def roll_with_skill(ctx, extra_mod, superior_dice, inferior_dice, stat):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	modifier = character[stat.lower()] + extra_mod
	
	results = [d6(), d6()]
	if superior_dice ^ inferior_dice:
		results.append(d6())
	
	original_results = deepcopy(results)
	
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
		message += f"({dice_string}) {'+' if character[stat.lower()] >= 0 else '-'} {abs(character[stat.lower()])} ({stat.upper()}) {'+' if extra_mod >= 0 else '-'} {abs(extra_mod)} ({'bonus' if extra_mod >= 0 else 'penalty'}) = **{total}**: "
	else:
		message += f"({dice_string}) {'+' if character[stat.lower()] >= 0 else '-'} {abs(character[stat.lower()])} ({stat.upper()}) = **{total}**: "
	
	if results == [6,6]:
		message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
	elif total <= 6:
		message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
	elif total <= 9:
		message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
	else:
		message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."

	buttons = None
	if character_has_trait(character, 331): #hypnosis check
		class HypnosisReroll(discord.ui.View):
			orig_results = []
			def __init__(self,original_results,timeout,disable_on_timeout):
				super().__init__(timeout=timeout,disable_on_timeout=disable_on_timeout)
				self.orig_results = original_results
			@discord.ui.button(label="Reroll Lowest (Hypnosis)",emoji="🌀")
			async def hypnosis_reroll_callback(self,button,interaction):
				if interaction.user.id == ctx.author.id:
					log("Hypnosis reroll callback")
					self.disable_all_items()
					character = get_active_char_object(ctx)
					modifier = character[stat.lower()] + extra_mod
					old_lowest = min(self.orig_results)
					new_lowest = d6()
					oldlowindex = self.orig_results.index(old_lowest)
					self.orig_results[oldlowindex] = new_lowest
					
					dice_string = ""
					for d in self.orig_results:
						dice_string += " " + num_to_die[d]
					dice_string = dice_string.strip()
					
					full_results = sorted(self.orig_results)
					if superior_dice and not inferior_dice:
						self.orig_results = full_results[-2:]
					elif inferior_dice and not superior_dice:
						self.orig_results = full_results[:2]
					
					total = sum(self.orig_results) + modifier
					
					message = f"**{codename.upper()}** rolling +{stat.upper()}:\n> "
					
					if extra_mod != 0:
						message += f"({dice_string}) {'+' if character[stat.lower()] >= 0 else '-'} {abs(character[stat.lower()])} ({stat.upper()}) {'+' if extra_mod >= 0 else '-'} {abs(extra_mod)} ({'bonus' if extra_mod >= 0 else 'penalty'}) = **{total}**: "
					else:
						message += f"({dice_string}) {'+' if character[stat.lower()] >= 0 else '-'} {abs(character[stat.lower()])} ({stat.upper()}) = **{total}**: "
					
					if self.orig_results == [6,6]:
						message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
					elif total <= 6:
						message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
					elif total <= 9:
						message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
					else:
						message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."
					message += f"\n> - *A reroll was performed via HYPNOSIS: {old_lowest} -> {new_lowest}*"
					await interaction.response.edit_message(content=message,view=self)
				else:
					log("Denying invalid Hypnosis reroll response")
					await interaction.response.send_message("This is not your HYPNOSIS prompt.",ephemeral=True)
		buttons = HypnosisReroll(original_results,timeout=5*60,disable_on_timeout=True)
	
	await ctx.respond(message,view=buttons)

async def character_names_autocomplete(ctx: discord.AutocompleteContext):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		return list(character_data[uid]['chars'].keys())
	else:
		return []

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

trait_tips = {
	316: "You can manage switching forms with this trait using the `/henshin` command.", #henshin
	414: "You can generate monster statblocks for this trait using the `/monsters` command.", #monsters
	611: "You can deal damage with this trait using the `/sunder` command.", #sunder
	652: "You can roll or assign your additional random trait using the `/volatile` command." #volatile
}

async def image_autocomp(ctx):
	return ["REMOVE_IMAGE"]

@bot.command(description="Set the file image of your active character")
async def character_image(ctx: discord.ApplicationContext, image_url: discord.Option(str, "The link to the image.",autocomplete=discord.utils.basic_autocomplete(image_autocomp), required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if image_url == "REMOVE_IMAGE":
		character["image"] = None
		await ctx.respond(f"Removed the image for {codename.upper()}.",ephemeral=True)
		return
	else:
		image_advice = "\n-# If you are having trouble getting a link that works, try the following:\n-# 1. Upload your image to a Discord channel, such as this bot's DMs. (Don't delete it afterwards; it'll stop working!)\n-# 2. Right-click the image in chat and select 'Copy Link'.\n-# 3. Paste that link into this command.\n-# Alternatively, you can use an image hosting service such as [Imgur]( <https://imgur.com/> ) or [Postimages]( <https://postimages.org/> )."
		try:
			req = func_timeout(3, requests.head, args=[image_url])
			if not req.ok:
				await ctx.respond(f"Could not verify URL: remote server returned code {req.status_code} ({req.reason})." + image_advice,ephemeral=True)
				return
			ct = req.headers['Content-Type']
			if not ct in ['image/gif','image/jpeg','image/png']:
				await ctx.respond(f"Could not verify URL: expected image of PNG, JPEG or GIF format; remote server sent content type `{ct}`." + image_advice,ephemeral=True)
				return
		except Exception as e:
			await ctx.respond(f"Could not verify URL:\n```{e}```" + image_advice,ephemeral=True)
			return
		
		await ctx.defer()
		character["image"] = image_url
		emb = discord.Embed()
		emb.image = discord.EmbedMedia(image_url)
		emb.description = f"Set the character image for {codename.upper()}."

		await ctx.respond(embed=emb)
		await save_character_data(str(ctx.author.id))

@bot.command(description="Set the accent color of your active character's /sheet output")
async def clear_sheet_color(ctx: discord.ApplicationContext):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	character["embed_color"] = None

	emb = discord.Embed(description=f"The color of {codename.upper()}'s sheet has been cleared.")

	await ctx.respond(embed=emb)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Set the accent color of your active character's /sheet output")
async def set_sheet_color(ctx: discord.ApplicationContext,
		red: discord.Option(int,min_value=0,max_value=255,required=True),
		green: discord.Option(int,min_value=0,max_value=255,required=True),
		blue: discord.Option(int,min_value=0,max_value=255,required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	character["embed_color"] = {
		"r": red,
		"g": green,
		"b": blue
	}

	emb = discord.Embed(description=f"The color of {codename.upper()}'s sheet has been set.")
	emb.color = discord.Color.from_rgb(red,green,blue)

	await ctx.respond(embed=emb)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Add a core book trait to your active character")
async def add_trait(ctx, 
	trait: discord.Option(str, "The core book name or number of the trait to add.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=True),
	rename_item: discord.Option(str, "Renames the item this trait provides. Autocomplete displays the item's default name.",autocomplete=discord.utils.basic_autocomplete(current_trait_item_autocomp), required=False, default=None, max_length=100)):
	trait = trait.strip()
	if rename_item is not None:
		rename_item = rename_item.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if len(character['traits']) >= trait_limit:
		await ctx.respond(f"Characters cannot have more than {trait_limit} traits.",ephemeral=True)
		return
	
	if len(character['items']) >= ITEM_LIMIT:
		await ctx.respond(f"Adding this trait would cause {codename.upper()}'s inventory to exceed {ITEM_LIMIT} items, which is not allowed.",ephemeral=True)
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
	
	if character['special'].get('henshin_trait',None) is not None and my_new_trait['Name'] == character['special']['henshin_trait']['Name']:
		await ctx.respond(f'**{codename.upper()}** is already using **{my_new_trait["Name"]} ({my_new_trait["Number"]})** as their HENSHIN trait.',ephemeral=True)
		return
	
	for existing_trait in character['traits']:
		if existing_trait['Name'] == my_new_trait['Name']:
			await ctx.respond(f'**{codename.upper()}** already has the trait **{my_new_trait["Name"]} ({my_new_trait["Number"]})**.',ephemeral=True)
			return
	
	my_new_trait = deepcopy(my_new_trait)
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
	if my_new_trait['Number'] == 316: #henshin bookkeeping
		character['special']['henshin_trait'] = None
		character['special']['henshin_stored_hp'] = 0
		character['special']['henshin_stored_maxhp'] = 0
	
	if my_new_trait['Number'] == 652: #volatile bookkeeping
		vol_trait = select_random_novel_trait(character)
		character['special']['volatile_trait'] = vol_trait
		apply_stat_change(character,vol_trait['Stat'])
	
	old_max_hp = character['maxhp']
	
	apply_stat_change(character,my_new_trait["Stat"])

	volatile_dodge = None
	if character['special'].get('volatile_trait',None) is not None:
		if character['special']['volatile_trait']['Name'] == my_new_trait['Name']:
			volatile_dodge = reroll_volatile(character)
	
	out = f"**{codename.upper()}** has gained a trait!"
	if volatile_dodge is not None:
		out+= f"\n-# Their VOLATILE trait has changed to {volatile_dodge['Name']} ({volatile_dodge['Number']}) to prevent overlap."
	if old_max_hp > character['maxhp'] and character['maxhp'] <= 0:
		out += f"\n**This character now has a Max HP of {character['maxhp']}!!**"
	if my_new_trait['Number'] in trait_tips:
		out += replace_commands_with_mentions(f"\n-# 💡 {trait_tips[my_new_trait['Number']]}")
	out += f"\n>>> {trait_message_format(my_new_trait)}"
	if my_new_trait['Number'] == 652 and character['special'].get('volatile_trait',None) is not None:
		v = character['special']['volatile_trait']
		out += f"\n-# Your first Volatile trait is {v['Name']} ({v['Number']}):\n-# {v['Effect']} ({v['Stat']})"
	await ctx.respond(out)
	if 'add_trait' in ctx.command.qualified_name:
		await save_character_data(str(ctx.author.id))

@bot.command(description="Activate (or set) your active character's HENSHIN trait")
async def henshin(ctx, set_trait: discord.Option(str, "The core book name or number of the trait to set.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None)):
	if set_trait is not None:
		set_trait = set_trait.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if "henshin_trait" in character["special"]: #character does indeed have henshin
		if set_trait is None: #activating henshin
			if character['special']['henshin_trait'] == None: #henshin trait has not been set
				await ctx.respond(f"{codename.upper()} does not yet have a trait set for HENSHIN. To add one, specify the `set_trait` argument for this command.",ephemeral=True)
				return
			else: #successful activation
				if character['special']['henshin_stored_maxhp'] != 0: #henshin is already active; revert it
					revoke_stat_change(character,character['special']['henshin_trait']['Stat'])
					character['hp'] = character['special']['henshin_stored_hp']
					character['maxhp'] = character['special']['henshin_stored_maxhp']
					character['special']['henshin_stored_hp'] = 0
					character['special']['henshin_stored_maxhp'] = 0
					
					await ctx.respond(f"{codename.upper()} has deactivated HENSHIN.\n- They have lost the **{character['special']['henshin_trait']['Name']}** trait.\n- They have removed the {character['special']['henshin_trait']['Stat']} stat change.\n- Their HP has reverted to **{character['hp']}/{character['maxhp']}**.")
					await save_character_data(str(ctx.author.id))
					return
				else: #henshin is not active; activate it
					new_hp = d6()
					character['special']['henshin_stored_hp'] = character['hp']
					character['special']['henshin_stored_maxhp'] = character['maxhp']
					character['hp'] = new_hp
					character['maxhp'] = new_hp
					apply_stat_change(character,character['special']['henshin_trait']['Stat'])

					await ctx.respond(f"**{codename.upper()} has activated HENSHIN!**\n- They have gained the **{character['special']['henshin_trait']['Name']}** trait.\n- They have taken {character['special']['henshin_trait']['Stat']}.\n- This form has **{character['maxhp']} MAX HP**.")
					await save_character_data(str(ctx.author.id))
					return
		else: #setting the trait
			if character['special']['henshin_stored_maxhp'] != 0: #henshin is active; don't change anything!
				await ctx.respond(replace_commands_with_mentions(f"You cannot change your HENSHIN trait while the alternate form is active.\nTo disable the alternate form, perform `/henshin`, without additional arguments."),ephemeral=True)
				return
			else:
				set_trait = set_trait.upper()
				current_traits_by_name = traits_by_name | character_data[str(ctx.author.id)]['traits']
				
				my_new_trait = None
				if set_trait == "ABRACADABRA":
					my_new_trait = secret_trait
				elif set_trait in current_traits_by_name:
					my_new_trait = current_traits_by_name[set_trait]
				elif set_trait in traits_by_numstr:
					my_new_trait = traits_by_numstr[set_trait]
				
				if my_new_trait == None:
					await ctx.respond(f'No trait with the exact name or D666 number "{set_trait.upper()}" exists. Double-check your spelling.',ephemeral=True)
					return
				
				for t in character['traits']:
					if t['Name'] == my_new_trait['Name']:
						await ctx.respond(f"You cannot change your HENSHIN trait to a trait you already possess.",ephemeral=True)
						return

				volatile_dodge = None
				if character['special'].get('volatile_trait',None) is not None:
					if character['special']['volatile_trait']['Name'] == my_new_trait['Name']:
						volatile_dodge = reroll_volatile(character)
				
				character['special']['henshin_trait'] = deepcopy(my_new_trait)
				out = f"{codename.upper()} has set their HENSHIN trait to **{my_new_trait['Name'].upper()} ({my_new_trait['Number']})**."
				if volatile_dodge is not None:
					out+= f"\n-# Their VOLATILE trait has changed to {volatile_dodge['Name']} ({volatile_dodge['Number']}) to prevent overlap."
				await ctx.respond(out)
				await save_character_data(str(ctx.author.id))
				return
	else: #character does not have henshin
		await ctx.respond(f"**{codename.upper()}**" + replace_commands_with_mentions(" does not have the HENSHIN trait. You can add it with `/add_trait`."),ephemeral=True)
		return
	
def reroll_volatile(character: dict):
	if 'volatile_trait' not in character['special']:
		return None
	revoke_stat_change(character,character['special']['volatile_trait']['Stat'])
	new_roll = select_random_novel_trait(character)
	character['special']['volatile_trait'] = new_roll
	apply_stat_change(character,character['special']['volatile_trait']['Stat'])
	return new_roll

@bot.command(description="Reroll (or set) your active character's VOLATILE trait")
async def volatile(ctx: discord.ApplicationContext, force_trait: discord.Option(str, "The core book name or number of the trait to set.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None)=None):
	if force_trait is not None:
		force_trait = force_trait.strip().upper()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if not character_has_trait(character, 652):
		await ctx.respond(f"**{codename.upper()}**" + replace_commands_with_mentions(" does not have the VOLATILE trait. You can add it with `/add_trait`."),ephemeral=True)
		return
	
	my_new_trait = None
	if force_trait is None: # random reroll
		my_new_trait = reroll_volatile(character)
	else: # forced change
		current_traits_by_name = traits_by_name | character_data[str(ctx.author.id)]['traits']
		if force_trait == "ABRACADABRA":
			my_new_trait = secret_trait
		elif force_trait in current_traits_by_name:
			my_new_trait = current_traits_by_name[force_trait]
		elif force_trait in traits_by_numstr:
			my_new_trait = traits_by_numstr[force_trait]
		
		if my_new_trait == None:
			await ctx.respond(f'No trait with the exact name or D666 number "{force_trait.upper()}" exists. Double-check your spelling.',ephemeral=True)
			return
		
		for t in character['traits']:
			if t['Name'] == my_new_trait['Name']:
				await ctx.respond(f"You cannot change your VOLATILE trait to a trait you already possess.",ephemeral=True)
				return
		
		for item in list(character['special'].values()):
			if type(item) is dict and item.get('Name',None) == my_new_trait['Name']:
				await ctx.respond(f"You cannot change your VOLATILE trait to a trait you already possess.",ephemeral=True)
				return
		
		revoke_stat_change(character,character['special']['volatile_trait']['Stat'])
		character['special']['volatile_trait'] = deepcopy(my_new_trait)
		apply_stat_change(character,character['special']['volatile_trait']['Stat'])

	out = f"{codename.upper()} has shifted their VOLATILE trait to **{my_new_trait['Name'].upper()} ({my_new_trait['Number']})**."
	await ctx.respond(out)
	await save_character_data(str(ctx.author.id))
	return

valid_bonuses = ["+1D6 Max Hp","+1D6 War Dice","Random Standard Issue Item","Balaclava (hides identity)","Flashlight (can be used as a weapon attachment)","Knife (1D6 DAMAGE)","MRE field rations (+1D6 HP, one use)","Pistol (1D6 DAMAGE)","Riot shield (1 ARMOR, equip as weapon)"]

@bot.command(description="Create a new character to manage")
async def create_character(ctx, codename: discord.Option(str, "The character's codename, used for selecting them with other commands.",required=True, max_length=50),
	starter_trait_1: discord.Option(str, "The core book name or number of a trait to add to the character immediately.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None),
	starter_trait_2: discord.Option(str, "The core book name or number of a trait to add to the character immediately.",autocomplete=discord.utils.basic_autocomplete(traits_and_customs_autocomp), required=False, default=None),
	starter_bonus: discord.Option(str, "The extra starting bonus for your character.",choices=valid_bonuses, required=False, default=None)):
	
	codename = codename.strip()
	if starter_trait_1 is not None:
		starter_trait_1 = starter_trait_1.strip()
	if starter_trait_2 is not None:
		starter_trait_2 = starter_trait_2.strip()
	userid = str(ctx.author.id)
	
	if userid not in character_data:
		character_data[userid] = {
			"active": {},
			"chars": {},
			"traits": {}
		}
	
	premium_character = False
	if len(character_data[userid]["chars"]) >= STANDARD_CHARACTER_LIMIT:
		premium_user = await ext_character_management(ctx.author.id)
		if not premium_user:
			await ctx.respond(f"You may not create more than {STANDARD_CHARACTER_LIMIT} characters.\nYou can increase your character limit to {PREMIUM_CHARACTER_LIMIT} by enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
			return
		elif len(character_data[userid]["chars"]) >= PREMIUM_CHARACTER_LIMIT:
			await ctx.respond(f"You may not create more than {PREMIUM_CHARACTER_LIMIT} characters.",ephemeral=True)
			return
		else:
			premium_character = True
	
	codename = codename.lower()
	if codename in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the codename '{codename.upper()}'.",ephemeral=True)
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
		"creation_time": time(),
		"counters": {},
		"notes": "",
		"special": {},
		"pronouns": None,
		"image": None,
		"embed_color": None
	}
	
	msg = f"Created character with the codename **{codename.upper()}**."
	msg += f"\n-# You now have {len(character_data[userid]['chars'])} characters."
	if premium_character:
		msg += "\n-# *This character uses a premium slot!*"
	if starter_bonus is not None and starter_bonus not in valid_bonuses:
		msg += "\n-# *The provided `starter_bonus` is invalid. No starter bonus has been applied.*"
	await ctx.respond(msg)
	await switch_character(ctx, codename)
	if starter_trait_1 is not None:
		await add_trait(ctx, starter_trait_1, None)
	if starter_trait_2 is not None:
		await add_trait(ctx, starter_trait_2, None)
	if starter_bonus is not None:
		if starter_bonus == "+1D6 Max Hp":
			await adjust(ctx,"MAX HP","1D6")
		elif starter_bonus == "+1D6 War Dice":
			await adjust(ctx,"WAR DICE","1D6")
		else:
			standard_issue_items = ["Balaclava (hides identity)","Flashlight (can be used as a weapon attachment)","Knife (1D6 DAMAGE)","MRE field rations (+1D6 HP, one use)","Pistol (1D6 DAMAGE)","Riot shield (1 ARMOR, equip as weapon)"]
			if starter_bonus == "Random Standard Issue Item":
				starter_bonus = rnd.choice(standard_issue_items)
			elif starter_bonus in standard_issue_items:
				split_bonus = starter_bonus.split(" (")
				starting_item_name = split_bonus[0]
				starting_item_effect = split_bonus[1][:-1]
				await add_item(ctx,starting_item_name,starting_item_effect)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Rename an existing character")
async def rename(ctx,
	codename: discord.Option(str, "The codename of the character to rename.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	new_codename: discord.Option(str, "The new codename of the character.",required=True,max_length=50)):
	codename = codename.strip()
	new_codename = new_codename.strip()
	userid = str(ctx.author.id)

	codename = codename.lower()
	if userid not in character_data or codename not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'." + replace_commands_with_mentions("You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	if character_data[userid]['chars'][codename]['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	new_codename = new_codename.lower()
	if new_codename in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the codename '{new_codename}'.",ephemeral=True)
		return
	
	character_data[userid]['chars'][new_codename] = deepcopy(character_data[userid]['chars'][codename])
	del character_data[userid]['chars'][codename]
	
	msg = f"Renamed the character **{codename.upper()}** to **{new_codename.upper()}**."
	character_data[userid]
	for key in character_data[userid]['active']:
		if character_data[userid]['active'][key] == codename:
			character_data[userid]['active'][key] = new_codename
	await ctx.respond(msg)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Make a copy of an existing character")
async def clone(ctx,
	codename: discord.Option(str, "The codename of the character to duplicate.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	new_codename: discord.Option(str, "The new codename of the duplicated character.",required=True,max_length=50)):
	codename = codename.strip()
	new_codename = new_codename.strip()
	userid = str(ctx.author.id)
	
	codename = codename.lower()
	if userid not in character_data or codename not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	premium_character = False
	if len(character_data[userid]["chars"]) >= STANDARD_CHARACTER_LIMIT:
		premium_user = await ext_character_management(ctx.author.id)
		if not premium_user:
			await ctx.respond(f"You may not create more than {STANDARD_CHARACTER_LIMIT} characters.\nYou can increase your character limit to {PREMIUM_CHARACTER_LIMIT} by enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
			return
		elif len(character_data[userid]["chars"]) >= PREMIUM_CHARACTER_LIMIT:
			await ctx.respond(f"You may not create more than {PREMIUM_CHARACTER_LIMIT} characters.",ephemeral=True)
			return
		else:
			premium_character = True
	
	new_codename = new_codename.lower()
	if new_codename in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the codename '{new_codename}'.",ephemeral=True)
		return
	
	character_data[userid]['chars'][new_codename] = deepcopy(character_data[userid]['chars'][codename])
	character_data[userid]['chars'][new_codename]['premium'] = premium_character
	character_data[userid]['chars'][new_codename]['creation_time'] = time()
	
	msg = f"Cloned character with the codename **{codename.upper()}** with new codename **{new_codename.upper()}**."
	msg += f"\n-# You now have {len(character_data[userid]['chars'])} characters."
	if premium_character:
		msg += "\n-# *This character uses a premium slot!*"
	await ctx.respond(msg)
	await switch_character(ctx, new_codename)

@bot.command(description="Duplicate one character's items into another's inventory")
async def copy_inventory(ctx,
	source_character: discord.Option(str, "The codename of the character to copy items from.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	destination_character: discord.Option(str, "The codename of the character to recieve the copied items.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True),
	delete_original_items: discord.Option(bool, "If set to True, the items in the source character's inventory are deleted.", required=False, default=False)):

	# verify each character exists
	userid = str(ctx.author.id)
	source_character = source_character.lower().strip()
	if userid not in character_data or source_character not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{source_character}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	destination_character = destination_character.lower().strip()
	if userid not in character_data or destination_character not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{destination_character}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	# verify the duplication would not run past the item limit
	source_count = len(character_data[userid]['chars'][source_character]['items'])
	dest_count = len(character_data[userid]['chars'][destination_character]['items'])
	if source_count + dest_count > ITEM_LIMIT:
		msg = f"Adding {source_count} items to **{destination_character.upper()}**'s inventory would bring them over the item limit ({ITEM_LIMIT})."
		msg += f"\n{source_count + dest_count - ITEM_LIMIT} items must be removed from both inventories collectively before proceeding."
		msg += f"\n-# If you intend to overwrite **{destination_character.upper()}**'s inventory, " + replace_commands_with_mentions("use `/replace_inventory` instead.")
		await ctx.respond(msg)
		return
	
	# verify that no item name duplicates would arise
	source_items = set()
	dest_items = set()

	for item in character_data[userid]['chars'][source_character]['items']:
		source_items.add(get_item_name(item))
	
	for item in character_data[userid]['chars'][destination_character]['items']:
		dest_items.add(get_item_name(item))
	
	collisions = source_items.intersection(dest_items)
	if len(collisions) > 0:
		msg = f"There are {len(collisions)} items with the same name across both characters:"
		collisions = sorted(list(collisions))
		for item in collisions:
			msg += "\n- " + item
		msg += "\nThese items must be renamed before they can be copied over."
		msg += f"\n-# If you intend to overwrite **{destination_character}**'s inventory, " + replace_commands_with_mentions("use `/replace_inventory` instead.")
		return await response_with_file_fallback(ctx,msg,eph=True)
	
	# all checks pass; copy the inventory over
	character_data[userid]['chars'][destination_character]['items'] += deepcopy(character_data[userid]['chars'][source_character]['items'])
	msg = f"Copied all {source_count} items from **{source_character.upper()}**'s inventory to **{destination_character.upper()}**'s inventory."

	if delete_original_items:
		character_data[userid]['chars'][source_character]['items'] = []
		msg = msg.replace("Copied", "Moved")
		msg += f"\n-# All items in **{source_character.upper()}**'s inventory have been removed."
	
	await ctx.respond(msg)
	await save_character_data(userid)

@bot.command(description="Replace one character's inventory with another's")
async def replace_inventory(ctx,
	source_character: discord.Option(str, "The codename of the character to take items from.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	destination_character: discord.Option(str, "The codename of the character whose inventory will be overwritten.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True),
	delete_original_items: discord.Option(bool, "If set to True, the items in the source character's inventory are deleted.", required=False, default=False)):

	# verify each character exists
	userid = str(ctx.author.id)
	source_character = source_character.lower().strip()
	if userid not in character_data or source_character not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{source_character}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	destination_character = destination_character.lower().strip()
	if userid not in character_data or destination_character not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{destination_character}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	# copy the inventory over
	character_data[userid]['chars'][destination_character]['items'] = deepcopy(character_data[userid]['chars'][source_character]['items'])
	msg = f"Replaced **{destination_character.upper()}**'s inventory with a copy of **{source_character.upper()}**'s inventory."
	msg += f"\n-# All items originally held by **{destination_character.upper()}** have been removed."

	if delete_original_items:
		character_data[userid]['chars'][source_character]['items'] = []
		msg += f"\n-# All items in **{source_character.upper()}**'s inventory have been removed."
	
	await ctx.respond(msg)
	await save_character_data(userid)

@bot.command(description="Delete a character from your roster")
async def delete_character(ctx, codename: discord.Option(str, "The character's codename, used for selecting them with other commands.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True)):
	codename = codename.lower()
	yourid = str(ctx.author.id)
	if yourid not in character_data:
		await ctx.respond("You do not have any character data to delete.",ephemeral=True)
		return
	yourstuff = character_data[yourid]
	if codename not in yourstuff['chars']:
		await ctx.respond(f"You do not have a character named '{codename}' to delete.",ephemeral=True)
		return
	else:
		class DeleteConfirm(discord.ui.View):
			@discord.ui.button(label="Cancel deletion", style=discord.ButtonStyle.green, emoji="🔙")
			async def stop_deletion_callback(self, button, interaction):
				if interaction.user.id == ctx.author.id:
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					log(f"Cancelling deletion")
					await ctx.respond(f"Character deletion cancelled.")
				else:
					log("Denying invalid deletion response")
					await interaction.response.send_message("This is not your character deletion prompt.",ephemeral=True)
			@discord.ui.button(label=f"Confirm deletion of {codename.upper()}", style=discord.ButtonStyle.red, emoji="🗑️")
			async def accept_deletion_callback(self, button, interaction):
				if interaction.user.id == ctx.author.id:
					deletion_target = codename.lower()
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					log("Confirming deletion")
					message = f"<@{yourid}> Successfully deleted **{deletion_target.upper()}**."
					was_premium = yourstuff['chars'][deletion_target]['premium']
					del yourstuff['chars'][deletion_target]
					channel_unbinds = 0
					keys_to_purge = []
					for key in yourstuff['active']:
						if yourstuff['active'][key] == deletion_target:
							channel_unbinds += 1
							keys_to_purge.append(key)
					if channel_unbinds > 0:
						message += f"\n-# This action has cleared your active character across {channel_unbinds} channels:"
					for key in keys_to_purge:
						message += f" <#{key}>"
						del yourstuff['active'][key]
					
					earliest_time = math.inf
					earliest_premium_char = None
					earliest_prem_codename = None
					if not was_premium:
						for deletion_target in yourstuff['chars']:
							if yourstuff['chars'][deletion_target]['premium'] and yourstuff['chars'][deletion_target]['creation_time'] < earliest_time:
								earliest_time = yourstuff['chars'][deletion_target]['creation_time']
								earliest_premium_char = yourstuff['chars'][deletion_target]
								earliest_prem_codename = deletion_target
						if earliest_premium_char is not None:
							earliest_premium_char['premium'] = False
							message += f"\n-# You have freed up a non-premium slot. **{earliest_prem_codename.upper()}** is no longer a premium character."
					
					if len(yourstuff['chars']) <= 0 and len(yourstuff['traits']) <= 0:
						del character_data[yourid]
						message += "\n-# You no longer have any characters or traits. All data associated with your User ID has been deleted."
					else:
						message += f"\n-# You now have {len(yourstuff['chars'])} characters."
					await ctx.respond(message)
					await save_character_data(str(ctx.author.id))
				else:
					log("Denying invalid deletion response")
					await interaction.response.send_message("This is not your character deletion prompt.",ephemeral=True)
		
		await ctx.respond(f"⚠️ **This action will permanently delete your character {codename.upper()}, and all data associated with them.\nIt cannot be undone.\nContinue?**",view=DeleteConfirm(timeout=30,disable_on_timeout=True))

@bot.command(description="List all characters you've created")
async def my_characters(ctx):
	yourid = str(ctx.author.id)
	if yourid in character_data and len(character_data[yourid]['chars']) > 0:
		await ctx.defer()
		yourchars = character_data[yourid]['chars']
		msg_header = f"Characters created by <@{yourid}> ({len(yourchars)}/{PREMIUM_CHARACTER_LIMIT if await ext_character_management(yourid) else STANDARD_CHARACTER_LIMIT}):"
		
		def cretime(cd):
			return yourchars[cd]['creation_time']
		
		def divide_chunks(l:list, n:int):
			# looping till length l
			for i in range(0, len(l), n): 
				yield l[i:i + n]

		characters_per_page = 15

		sorted_chars = sorted(list(yourchars.keys()), key=cretime)
		char_pages = list(divide_chunks(sorted_chars,characters_per_page))
		pages = []
		pagenum = 0
		pagecount = len(char_pages)

		for sublist in char_pages:
			premiums = False
			page = msg_header
			if pagecount > 1:
				pagenum += 1
				page += f"\n-# Page {pagenum}/{pagecount}"
			for codename in sublist:
				char_traits = character_data[yourid]['chars'][codename]['traits']
				page += f"\n- **{codename.upper()}**"
				if character_data[yourid]['chars'][codename]['premium']:
					page += "\*"
				page += f" ({len(char_traits) if len(char_traits) > 0 else 'No'} traits)"
				premiums = premiums or character_data[yourid]['chars'][codename]['premium']
			if premiums:
				page += "\n-# \* *premium character*"
			pages.append(page)
		
		await paginated_response(ctx,pages)
	else:
		await ctx.respond("You haven't created any characters yet.",ephemeral=True)
	
@bot.command(description="Displays your current active character's sheet")
async def sheet(ctx: discord.ApplicationContext, codename: discord.Option(str, "The codename of a specific character to view instead.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=False, default=""), text_only: discord.Option(bool, "Sends a text-only version of the character sheet. May be sent as a file.", required=False, default=False)):
	codename = codename.lower().strip()
	yourid = str(ctx.author.id)
	if codename == "":
		codename = get_active_codename(ctx)
	if codename == None:
		await ctx.respond(replace_commands_with_mentions("You have not set an active character in this channel. Either set your active character with `/switch_character`, or specify which character's sheet you want to view using the optional `codename` argument for this command."),ephemeral=True)
		return
	if yourid not in character_data or codename not in character_data[yourid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	ch = character_data[yourid]['chars'][codename]
	blocks = output_character_embed(codename, ch, ctx.author)
	if text_only or any_embed_is_oversize(blocks):
		await response_with_file_fallback(ctx,output_character(codename, ch))
	else:
		first_embed_post = True
		while get_embed_group_length(blocks) > 6000:
			if first_embed_post:
				await ctx.respond(content=f"# {codename.upper()}", embed=blocks[0])
				first_embed_post = False
			else:
				await ctx.channel.send(embed=blocks[0])
			blocks = blocks[1:]
		if len(blocks) > 0:
			if first_embed_post:
				await ctx.respond(content=f"# {codename.upper()}", embeds=blocks)
				first_embed_post = False
			else:
				await ctx.channel.send(embeds=blocks)

@bot.command(description="Show your active character's inventory")
async def inventory(ctx, codename: discord.Option(str, "The codename of a specific character to view instead.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=False, default="")):
	codename = codename.lower().strip()
	yourid = str(ctx.author.id)
	if codename == "":
		codename = get_active_codename(ctx)
	if codename == None:
		await ctx.respond(replace_commands_with_mentions("You have not set an active character in this channel. Either set your active character with `/switch_character`, or specify which character's sheet you want to view using the optional `codename` argument for this command."),ephemeral=True)
		return
	if yourid not in character_data or codename not in character_data[yourid]['chars']:
		await ctx.respond(f"You have not created a character with the codename '{codename}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	
	character = character_data[yourid]['chars'][codename]

	message = f"**{codename.upper()}**'s inventory ({len(character['items'])}/{ITEM_LIMIT}):"
	if len(character['items']) <= 0:
		message = f"**{codename.upper()}** has no items in their inventory."
	else:
		for item in character['items']:
			message += f"\n- {item}"
			if item in character['counters']:
				counters = character['counters'][item]
				counter_strings = []
				for counter in counters:
					counter_strings.append(f"{counter.upper()}: {counters[counter]}")
				message += f" ({', '.join(counter_strings)})"
	await response_with_file_fallback(ctx,message)

sample_pronouns = ["they/them","she/her","he/him","it/its","any pronouns","unspecified pronouns","no pronouns","ae/aer","bun/buns","e/em","ey/em","fae/faer","liv/lir","mer/merm","nya/nyas","pup/pups","shi/hir","sie/hir","v/v","ve/ver","xe/xem","ze/zir"]

async def pronouns_autocomplete(ctx):
	return sample_pronouns

@bot.command(description="Set your active character's pronouns")
async def set_pronouns(ctx, pronouns: discord.Option(str, "The new pronouns for your active character.", autocomplete=discord.utils.basic_autocomplete(pronouns_autocomplete), required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	character['pronouns'] = pronouns

	out = f"**{codename.upper()}** now goes by the pronouns **{pronouns}**."
	await response_with_file_fallback(ctx,out)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Show the notes field for your active character")
async def view_notes(ctx, hide_output: discord.Option(bool, "Hides the output message from everyone else.", required=False, default=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	note = character['notes']
	if len(note) <= 0:
		await ctx.respond(f"You have not written any notes for **{codename.upper()}**.",ephemeral=True)
	else:
		message = f"Notes for **{codename.upper()}**:\n>>> {note}"
		await ctx.respond(message,ephemeral=hide_output)

@bot.command(description="Edit the notes field for your active character")
async def edit_notes(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	note = character['notes']

	class NotesModal(discord.ui.Modal):
		def __init__(self, *args, **kwargs) -> None:
			super().__init__(*args, **kwargs)

			self.add_item(discord.ui.InputText(label=f"Notes for '{codename.upper()}'",placeholder="Type your notes here.\nLeave this blank to clear notes.",style=discord.InputTextStyle.long,required=False,value=note,max_length=1900))

		async def callback(self, interaction: discord.Interaction):
			log("Updating character notes...")
			character['notes'] = value=self.children[0].value
			await save_character_data(str(ctx.author.id))
			await interaction.response.send_message(f"Notes for {codename.upper()} have been {'updated' if len(character['notes']) > 0 else '**cleared**'}.",ephemeral=True)
	
	modal = NotesModal(title=f"Notes editor")
	await ctx.send_modal(modal)

@bot.command(description="Switch which character is active in this channel")
async def switch_character(ctx, codename: discord.Option(str, "The codename of the character to switch to.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True)):
	codename = codename.strip()
	userid = str(ctx.author.id)
	if userid not in character_data or len(character_data[userid]['chars']) <= 0:
		await ctx.respond(replace_commands_with_mentions("You have no characters available. Use `/create_character` to make one."),ephemeral=True)
		return
		
	codename = codename.lower()
	if codename not in character_data[userid]["chars"]:
		await ctx.respond(f"You have not created a character with the codename '{codename}'." + replace_commands_with_mentions(" You can view what characters you've made with `/my_characters`. Check your spelling, or try creating a new one with `/create_character`."),ephemeral=True)
		return
	else:
		character_data[userid]['active'][str(ctx.channel_id)] = codename
		await ctx.respond(f"Your active character in this channel is now **{codename.upper()}**.")
		if 'switch_character' in ctx.command.qualified_name:
			await save_character_data(str(ctx.author.id))
	return

@bot.command(description="Check your current active character")
async def active_character(ctx, show_all: discord.Option(bool, "If TRUE, lists all channels you have active characters in. FALSE by default.", required=False, default=False)):
	if show_all:
		your_actives = None
		if str(ctx.author.id) in character_data:
			your_actives = character_data[str(ctx.author.id)]['active']
		else:
			await ctx.respond(f"You do not have active characters in any channels.",ephemeral=True)
			return
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
				filedata = BytesIO(message.encode('utf-8'))
				await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata,filename='response.md'),ephemeral=True)
		else:
			await ctx.respond(f"You do not have active characters in any channels.",ephemeral=True)
			return
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
	name: discord.Option(str,"The name of your role.",autocomplete=discord.utils.basic_autocomplete(role_autocomp),required=True,max_length=50),
	description: discord.Option(str,"The role's description.",required=True)):
	name = name.strip()
	description = description.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	name = name.upper()
	character['role'] = {
		"Name": name,
		"Text": description
	}
	
	out = f"**{codename.upper()}** has changed their role:"
	out += f"\n>>> **{name}**\n{description}"
	await ctx.respond(out)
	await save_character_data(str(ctx.author.id))

async def trait_autocomp(ctx):
	return trait_names

trait_limit = 15

async def stat_type_autocomp(ctx):
	return ["CREATIVE","FORCEFUL","TACTICAL","REFLEXIVE","MAX HP","to chosen attribute","WAR DIE per mission","ARMOR at all times","when you roll WAR DICE","DAMAGE with melee weapons","DAMAGE with ranged weapons"]

async def stat_amount_autocomp(ctx):
	return ["+1","-1","+2","-2","+1D6","-1D6"]

async def no_effect_autocomp(ctx):
	return ["NO_EFFECT"]

@bot.command(description="Create a custom trait")
async def create_custom_trait(ctx,	
		title: discord.Option(str, "The name of the trait", required=True,max_length=50), 
		description: discord.Option(str, "The trait's description", required=True),
		stat_type: discord.Option(str, "The stat this trait changes", autocomplete=discord.utils.basic_autocomplete(stat_type_autocomp), required=True),
		stat_amount: discord.Option(str, "The amount that the stat is changed (accepts dice syntax)", autocomplete=discord.utils.basic_autocomplete(stat_amount_autocomp), required=True),
		item_name: discord.Option(str, "The name of the item that this trait grants you", required=True,max_length=100),
		item_effect: discord.Option(str, "The effect of the item that this trait grants you",autocomplete=discord.utils.basic_autocomplete(no_effect_autocomp), required=True)):
	userid = str(ctx.author.id)
	title = title.strip()
	description = description.strip()
	stat_type = stat_type.strip()
	stat_amount = stat_amount.strip()
	item_name = item_name.strip()
	item_effect = item_effect.strip()
	
	if userid in character_data and len(character_data[userid]['traits']) >= standard_custrait_limit:
		premium_user = await ext_character_management(ctx.author.id)
		if not premium_user:
			await ctx.respond(f"You may not create more than {standard_custrait_limit} custom traits.\nYou can increase your custom trait limit to {premium_custrait_limit} by enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
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
		
	item_full = item_name
	if item_effect != "NO_EFFECT":
		item_full += f" ({item_effect})"
	
	new_trait = {
		"Number": "Custom",
		"Name": title,
		"Effect": description,
		"Item": item_full,
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
	out += f"\n-# You now have {len(character_data[userid]['traits'])} custom traits.\n>>> "
	out += trait_message_format(new_trait)
	await ctx.respond(out)
	await save_character_data(str(ctx.author.id))

async def custom_traits_list_autocomp(ctx):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		return list(character_data[uid]['traits'].keys())
	else:
		return []

@bot.command(description="Delete one of your custom traits")
async def delete_custom_trait(ctx,	
		name: discord.Option(str, "The name of the trait to delete",autocomplete=discord.utils.basic_autocomplete(custom_traits_list_autocomp), required=True)):
	uid = str(ctx.author.id)
	if uid not in character_data or len(character_data[uid]['traits']) <= 0:
		await ctx.respond("You do not have any custom traits on file.",ephemeral=True)
		return
	
	yourtraits = character_data[uid]['traits']
	name = name.upper()
	if name not in yourtraits:
		return await ctx.respond(f"You do not have a custom trait called {name}.",ephemeral=True)
	
	del yourtraits[name]

	message = f"Successfully deleted custom trait {name}."
	if len(character_data[uid]['chars']) <= 0 and len(character_data[uid]['traits']) <= 0:
		del character_data[uid]
		message += "\n-# You no longer have any characters or traits. All data associated with your User ID has been deleted."
	else:
		message += f"\n-# You now have {len(character_data[uid]['traits'])} custom traits."
	
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

@bot.command(description="View your custom traits")
async def my_traits(ctx, name: discord.Option(str, "The name of a specific trait to view",autocomplete=discord.utils.basic_autocomplete(custom_traits_list_autocomp), required=False, default=None)):
	if name is not None:
		name = name.strip()
	uid = str(ctx.author.id)
	if uid not in character_data or len(character_data[uid]['traits']) <= 0:
		await ctx.respond("You do not have any custom traits on file.",ephemeral=True)
		return
	
	def divide_chunks(l:list, n:int):
		# looping till length l
		for i in range(0, len(l), n): 
			yield l[i:i + n]
	
	yourtraits = character_data[uid]['traits']
	traits_per_page = 10
	trait_pages = list(divide_chunks(list(yourtraits.keys()),traits_per_page))
	pages = []
	pagenum = 0
	pagecount = len(trait_pages)

	if name is None:
		await ctx.defer()
		msg_header = f"Custom traits created by <@{uid}> ({len(yourtraits)}/{premium_custrait_limit if await ext_character_management(uid) else standard_custrait_limit}):"
		for sublist in trait_pages:
			page = msg_header
			if pagecount > 1:
				pagenum += 1
				page += f"\n-# Page {pagenum}/{pagecount}"
			for t in sublist:
				full_trait = yourtraits[t]
				page += f"\n- **{t.upper()}** ({full_trait['Stat']}, {get_item_name(full_trait['Item'])})"
			pages.append(page)
		await paginated_response(ctx,pages)
	else:
		name = name.upper()
		if name not in yourtraits:
			await ctx.respond(f"You do not have a custom trait called {name}.",ephemeral=True)
		else:
			await response_with_file_fallback(ctx,trait_message_format(yourtraits[name]))

@bot.command(description="Add an item your active character")
async def add_item(ctx,
	name: discord.Option(str, "The name of the item", required=True,max_length=100), 
	effect: discord.Option(str, "The effect of the item",autocomplete=discord.utils.basic_autocomplete(no_effect_autocomp), required=True)):
	name = name.strip()
	effect = effect.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return False
	codename = get_active_codename(ctx)

	uid = ctx.author.id if isinstance(ctx,discord.ApplicationContext) else ctx.user.id

	if character['premium'] and not await ext_character_management(uid):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return False
	
	if len(character['items']) >= ITEM_LIMIT:
		await ctx.respond(f"Characters cannot carry more than {ITEM_LIMIT} items.",ephemeral=True)
		return False
	
	concat = name+effect
	if "(" in concat or ")" in concat:
		await ctx.respond("For organizational reasons, please do not use parenthesis in the `name` or `effect` of your item.",ephemeral=True)
		return False
	
	for held_item in character['items']:
		held_name = held_item.split(" (")[0]
		if held_name.lower() == name.lower():
			await ctx.respond(f"You already have an item named '{held_name}'.\nFor organizational reasons, please do not add two items to your inventory with the same name. Instead, label them differently, or keep track of copies with an item counter" + replace_commands_with_mentions(" (via `/add_item_counter`)."),ephemeral=True)
			return False
	
	item_to_add = name
	if len(effect) > 0 and effect != "NO_EFFECT":
		item_to_add += f" ({effect})"
	
	character['items'].append(item_to_add)
	
	await ctx.respond(f"**{codename.upper()}** has added **{item_to_add}** to their inventory.")
	if isinstance(ctx,discord.ApplicationContext) and 'add_item' in ctx.command.qualified_name:
		await save_character_data(str(ctx.author.id))
	
	return True

@bot.command(description="(heal 1D6+TAC HP, one use)")
async def navy_medkit(ctx: discord.ApplicationContext):
	await spawn_item(ctx,"Navy Medkit <:navymedkit:1275300173689393182>","heal 1D6+TAC HP, one use",1)

async def item_name_autocomplete(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	output = []
	for item in current_char['items']:
		item_name = item.split(" (")[0]
		output.append(item_name)
	return output

def get_full_item_from_name(item_name, character):
	for full_item in character['items']:
		if full_item.split(" (")[0] == item_name:
			return full_item
	return item_name

async def orig_item_name_autocomp(ctx):
	return [ctx.options['original_item']]

async def orig_item_effect_autocomp(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	# get item here
	item = ctx.options['original_item']
	for inv_item in current_char['items']:
		if inv_item.split(" (")[0] == item:
			item = inv_item
			break
	item = item.split(" (")
	return [item[1][:-1],"REMOVE_EFFECT"] if len(item) > 1 else ["REMOVE_EFFECT"]

@bot.command(description="Edit an item in your inventory")
async def edit_item(ctx,
		original_item: discord.Option(str, "The name of the original item",autocomplete=discord.utils.basic_autocomplete(item_name_autocomplete), required=True),
		name: discord.Option(str, "The new name of the item",autocomplete=discord.utils.basic_autocomplete(orig_item_name_autocomp), required=True, max_length=100), 
		effect: discord.Option(str, "The new effect of the item",autocomplete=discord.utils.basic_autocomplete(orig_item_effect_autocomp), required=True)):
	name = name.strip()
	effect = effect.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	original_item = get_full_item_from_name(original_item, character)
	
	if original_item not in character['items']:
		await ctx.respond(f"The character **{codename.upper()}** is not carrying the item '{original_item}'. ",ephemeral=True)
		return

	concat = name+effect
	if "(" in concat or ")" in concat:
		await ctx.respond("For organizational reasons, please do not use parenthesis in the `name` or `effect` of your item.\nTo include an item's effect, use the optional `effect` argument for this command instead.",ephemeral=True)
		return
	
	item_index = character['items'].index(original_item)
	new_item = name if effect == "REMOVE_EFFECT" else f"{name} ({effect})"
	if new_item == original_item:
		await ctx.respond("The provided new and old items are identical. No change has been made.",ephemeral=True)
		return
	character['items'][item_index] = new_item
	
	message = f"**{codename.upper()}** has replaced the **{original_item}** in their inventory with **{new_item}**."
	
	# counter transfer
	if original_item in character['counters']:
		character['counters'][new_item] = character['counters'][original_item]
		del character['counters'][original_item]
		message += f"\n-# {len(character['counters'][new_item])} counters have been transferred to the new item."
	
	# trait item override
	for trait in character['traits']:
		if original_item == trait['Item']:
			trait['Item'] = new_item
			message += f"\n-# The trait item for {trait['Name']} has been updated accordingly."
			break
	
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Create an item in this channel for characters to pick up")
async def spawn_item(ctx,
					 item_name: discord.Option(str, "The name of the item", required=True,max_length=100), 
					 item_effect: discord.Option(str, "The effect of the item",autocomplete=discord.utils.basic_autocomplete(no_effect_autocomp), required=True),
					 count: discord.Option(int, "The number of times this item can be picked up.",required=False,default=1,min_value=1)):
	class ItemPickup(discord.ui.View):
		items_left = 1
		name = None
		effect = None
		expiry = 0
		def __init__(self,amount,item_name,item_effect,expiry,timeout,disable_on_timeout):
			super().__init__(timeout=timeout,disable_on_timeout=disable_on_timeout)
			self.items_left = amount
			self.name = item_name
			self.effect = item_effect
			self.expiry = expiry
		@discord.ui.button(label="Pick up",style=discord.ButtonStyle.green,emoji="🫳")
		async def item_pickup_callback(self,button,interaction):
			char = get_active_char_object(interaction)
			if char is None:
				log("Denying item pickup from user with no active character")
				await interaction.response.send_message(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
				return
			else:
				try:
					log("Performing item pickup")
					full_item = self.name
					if self.effect != "NO_EFFECT":
						full_item += f" ({self.effect})"

					if await add_item(interaction,self.name,self.effect or "NO_EFFECT"):
						self.items_left -= 1
						
					message = f"An item has spawned:\n**{full_item}**\nThere are {self.items_left} available to take.\n-# This prompt will expire <t:{self.expiry}:R>."
					if self.items_left <= 0:
						self.disable_all_items()
						message = message.replace(f"\n-# This prompt will expire <t:{self.expiry}:R>.","")
					await interaction.followup.edit_message(content=message,view=self,message_id=interaction.message.id)
				except Exception as e:
					await interaction.response.send_message(f"```{e}```")
		@discord.ui.button(label="Cancel",style=discord.ButtonStyle.red,emoji='✋')
		async def item_pickup_cancel_callback(self,button,interaction):
			if interaction.user.id == ctx.author.id:
				log("Cancelling item spawn")
				self.disable_all_items()
				full_item = self.name
				if self.effect != "NO_EFFECT":
					full_item += f" ({self.effect})"
				message = f"An item has spawned:\n**{full_item}**\n~~There are {self.items_left} available to take.~~ The remaining items have been revoked."
				await interaction.response.edit_message(content=message,view=self)
			else:
				log("Denying invalid item spawn cancellation")
				await interaction.response.send_message("This is not your item spawn.",ephemeral=True)
	
	concat = item_name+item_effect
	if "(" in concat or ")" in concat:
		await ctx.respond("For organizational reasons, please do not use parenthesis in the `name` or `effect` of your item.",ephemeral=True)
		return False

	full_item = item_name
	if item_effect != "NO_EFFECT":
		full_item += f" ({item_effect})"
	
	to = 5*60
	t = int(time())
	buttons = ItemPickup(count,item_name,item_effect,t+to,timeout=to,disable_on_timeout=True)

	message = f"An item has spawned:\n**{full_item}**\nThere are {count} available to take.\n-# This prompt will expire <t:{t+to}:R>."
	await ctx.respond(message,view=buttons)

@bot.command(description="Drop an item in this channel for other characters to pick up")
async def drop_item(ctx,
					 item: discord.Option(str, "The item to be dropped",autocomplete=discord.utils.basic_autocomplete(item_name_autocomplete), required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if len(character['items']) <= 0:
		await ctx.respond(f"**{codename.upper()}** does not have any items.",ephemeral=True)
		return
	
	item = get_full_item_from_name(item, character)
	item_name = get_item_name(item)
	item_effect = get_item_effect(item) or "NO_EFFECT"
	
	class ItemPickup(discord.ui.View):
		source_character = None
		source_codename = None
		name = None
		effect = None
		expiry = 0
		def __init__(self,source_char,source_name,item_name,item_effect,expiry,timeout,disable_on_timeout):
			super().__init__(timeout=timeout,disable_on_timeout=disable_on_timeout)
			self.source_character = source_char
			self.source_codename = source_name
			self.name = item_name
			self.effect = item_effect
			self.expiry = expiry
		@discord.ui.button(label=f"Pick up",style=discord.ButtonStyle.green,emoji="🫳")
		async def item_pickup_callback(self,button,interaction):
			char = get_active_char_object(interaction)
			nm = get_active_codename(interaction)
			if char is None:
				log("Denying item transfer to user with no active character")
				await interaction.response.send_message(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
				return
			else:
				if ctx.author.id == interaction.user.id and nm == self.source_codename:
					log("Denying self pickup")
					await interaction.response.send_message("You cannot pick up your own dropped item.\nTo cancel the item drop, use the Cancel button instead.",ephemeral=True)
					return
				log("Performing item transfer")
				full_item = self.name
				if self.effect != "NO_EFFECT":
					full_item += f" ({self.effect})"

				message = f"**{self.source_codename.upper()}** has dropped **{full_item}**.\n-# The item will only be removed from their inventory once it has been claimed.\n-# This prompt will expire <t:{self.expiry}:R>."
				
				if await add_item(interaction,self.name,self.effect or "NO_EFFECT"):
					counters = None
					if full_item in character['counters']:
						counters = deepcopy(character['counters'][full_item])
					
					try:
						self.source_character['items'].remove(full_item)
						if full_item in character['counters']:
							del character['counters'][full_item]
					except ValueError as e:
						log(f"Caught ValueError: {e}")
						out = "The item that you wanted to remove could not be found. Your current items are:"
						for i in self.source_character['items']:
							out += f"\n- {i}"
						await response_with_file_fallback(ctx,out)
					
					self.disable_all_items()
					message = f"**{self.source_codename.upper()}** has dropped **{full_item}**.\nIt was picked up by **{nm.upper()}**."
					if counters is not None:
						char['counters'][full_item] = counters
						await save_character_data(str(ctx.author.id))
				
				await interaction.followup.edit_message(content=message,view=self,message_id=interaction.message.id)
		@discord.ui.button(label="Cancel",style=discord.ButtonStyle.red,emoji='✋')
		async def item_pickup_cancel_callback(self,button,interaction):
			if interaction.user.id == ctx.author.id:
				log("Cancelling item drop")
				self.disable_all_items()
				full_item = self.name
				if self.effect != "NO_EFFECT":
					full_item += f" ({self.effect})"
				message = f"~~**{self.source_codename.upper()}** has dropped **{full_item}**.~~ The item has been picked back up.\n-# ~~The item will only be removed from their inventory once it has been claimed.~~"
				await interaction.response.edit_message(content=message,view=self)
			else:
				log("Denying invalid item drop cancellation")
				await interaction.response.send_message("This is not your item drop.",ephemeral=True)

	full_item = item_name
	if item_effect != "NO_EFFECT":
		full_item += f" ({item_effect})"
	
	to = 5*60
	t = int(time())
	buttons = ItemPickup(character,codename,item_name,item_effect,t+to,timeout=to,disable_on_timeout=True)

	message = f"**{codename.upper()}** has dropped **{full_item}**.\n-# The item will only be removed from their inventory once it has been claimed.\n-# This prompt will expire <t:{t+to}:R>."
	await ctx.respond(message,view=buttons)

async def example_counter_names(ctx):
	return ["Amount","Ammo","Uses remaining","Charges","Counter"]

@bot.command(description="Add a counter to an item on your character")
async def add_item_counter(ctx,
	item_name: discord.Option(str, "The item to attach a counter to",autocomplete=discord.utils.basic_autocomplete(item_name_autocomplete), required=True),
	counter_name: discord.Option(str, "The name of the counter",autocomplete=discord.utils.basic_autocomplete(example_counter_names), required=True, max_length=20),
	starting_value: discord.Option(int, "The value the counter should start at", required=True)
	):
	
	item_name = item_name.strip()
	counter_name = counter_name.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	item = None
	for stuff in character['items']:
		if stuff.split(" (")[0] == item_name:
			item = stuff
			break
	
	if item is None or item not in character['items']:
		await ctx.respond(f"**{codename.upper()}** is not carrying the item '{item}'.\n-# The item field is case- and formatting-sensitive; try using autofill suggestions.",ephemeral=True)
		return
	
	if item not in character['counters']:
		character['counters'][item] = {}
	
	counter_name = counter_name.lower()
	if counter_name in character['counters'][item]:
		await ctx.respond(f"The item **{item}** already has an associated counter called **'{counter_name}'**.",ephemeral=True)
		return
	
	character['counters'][item][counter_name] = starting_value
	
	await ctx.respond(f"{codename.upper()} has attached a counter to their **{item}**, called **'{counter_name}'**. It has a starting value of **{starting_value}**.")
	await save_character_data(str(ctx.author.id))

async def items_with_counters_autocomp(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	out = []
	for i in current_char['counters'].keys():
		out.append(i.split(" (")[0])
	return out

async def counters_on_the_item_autocomp(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	item = ctx.options['item']
	item = get_full_item_from_name(item,current_char)
	if item in current_char['counters']:
		return current_char['counters'][item].keys()

@bot.command(description="Adjust an item counter on your character")
async def adjust_item_counter(ctx,
	item: discord.Option(str, "The item with the associated counter",autocomplete=discord.utils.basic_autocomplete(items_with_counters_autocomp), required=True),
	counter_name: discord.Option(str, "The name of the counter",autocomplete=discord.utils.basic_autocomplete(counters_on_the_item_autocomp), required=True),
	amount: discord.Option(str, "The value to change the counter by; supports dice syntax.", required=True)
	):
	
	item = item.strip()
	counter_name = counter_name.strip()
	amount = amount.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	item = get_full_item_from_name(item,character)

	
	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if item not in character['items']:
		await ctx.respond(f"**{codename.upper()}** is not carrying the item '{item}'.\n-# The item field is case- and formatting-sensitive; try using autofill suggestions.",ephemeral=True)
		return
	
	counter_name = counter_name.lower()
	if (item not in character['counters']) or (counter_name.lower() not in character['counters'][item]):
		await ctx.respond(f"Your **{item}** does not have an associated counter called '{counter_name}'." + replace_commands_with_mentions("\n-# Add one with `/add_item_counter`."),ephemeral=True)
		return
	
	output = await roll_dice_with_context(ctx,amount,True)
	if output is None:
		return
	
	character['counters'][item][counter_name] += int(output[0])
	message = f"You have **{'in' if output[0] >= 0 else 'de'}creased** the {counter_name.upper()} counter on {codename.upper()}'s **{item}** by {abs(int(output[0]))}. The new value is **{character['counters'][item][counter_name]}**."
	if output[0] - int(output[0]) != 0:
		message += f"\n-# The dice result or provided number was not an integer; it has been rounded down from {output[0]}"
	if 'd' in amount or 'D' in amount:
		message += f"\n-# Dice results: `{output[1]}`"
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Performs an Ammo check on one of your item's counters")
async def ammo_check(ctx,
	item: discord.Option(str, "The item with the associated counter",autocomplete=discord.utils.basic_autocomplete(items_with_counters_autocomp), required=True),
	counter_name: discord.Option(str, "The name of the counter",autocomplete=discord.utils.basic_autocomplete(counters_on_the_item_autocomp), required=True)
	):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	item = get_full_item_from_name(item,character)
	if item not in character['items']:
		await ctx.respond(f"**{codename.upper()}** is not carrying the item '{item}'.\n-# The item field is case- and formatting-sensitive; try using autofill suggestions.",ephemeral=True)
		return
	
	counter_name = counter_name.lower()
	if (item not in character['counters']) or (counter_name.lower() not in character['counters'][item]):
		await ctx.respond(f"Your **{item}** does not have an associated counter called '{counter_name}'." + replace_commands_with_mentions("\n-# Add one with `/add_item_counter`."),ephemeral=True)
		return
	
	if character['counters'][item][counter_name] <= 0:
		await ctx.respond("The specified counter must have a value above zero to be used for an ammo check! If the AMMO score of a weapon is zero or less, it cannot be used.",ephemeral=True)
		return
	
	die = d6()
	current = character['counters'][item][counter_name]
	message = f"**{codename.upper()}** performs an AMMO check with their **{item}**'s {counter_name.upper()} counter."
	message += f"\n- Counter value: **{current}**"
	message += f"\n- Dice result: **{num_to_die[die]} ({die})**\n"
	
	if die > current:
		character['counters'][item][counter_name] = 0
		message += f"**Ammo has run dry!** The counter has been set to **zero**."
	elif die < current:
		character['counters'][item][counter_name] -= 1
		message += f"**Some ammo is consumed.** The counter has decreased to **{character['counters'][item][counter_name]}**."
	else:
		message += f"**Ammo is conserved.** The counter is **unchanged**."
	
	await ctx.respond(message)
	
	if character['counters'][item][counter_name] != current:
		await save_character_data(str(ctx.author.id))

@bot.command(description="Set an item counter on your character")
async def set_item_counter(ctx,
	item: discord.Option(str, "The item with the associated counter",autocomplete=discord.utils.basic_autocomplete(items_with_counters_autocomp), required=True),
	counter_name: discord.Option(str, "The name of the counter",autocomplete=discord.utils.basic_autocomplete(counters_on_the_item_autocomp), required=True),
	amount: discord.Option(str, "The value to set the counter to; supports dice syntax.", required=True)
	):
	
	item = item.strip()
	counter_name = counter_name.strip()
	amount = amount.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	
	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	item = get_full_item_from_name(item,character)
	if item not in character['items']:
		await ctx.respond(f"**{codename.upper()}** is not carrying the item '{item}'.\n-# The item field is case- and formatting-sensitive; try using autofill suggestions.",ephemeral=True)
		return
	
	counter_name = counter_name.lower()
	if (item not in character['counters']) or (counter_name.lower() not in character['counters'][item]):
		await ctx.respond(f"Your **{item}** does not have an associated counter called '{counter_name}'." + replace_commands_with_mentions("\n-# Add one with `/add_item_counter`."),ephemeral=True)
		return
	
	output = await roll_dice_with_context(ctx,amount,True)
	if output is None:
		return
	
	character['counters'][item][counter_name] = output[0]
	message = f"You have set the {counter_name.upper()} counter on {codename.upper()}'s **{item}** to {abs(output[0])}."
	if 'd' in amount or 'D' in amount:
		message += f"\n-# Dice results: `{output[1]}`"
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Remove a counter from one of your character's items")
async def remove_item_counter(ctx,
	item: discord.Option(str, "The item with the associated counter",autocomplete=discord.utils.basic_autocomplete(items_with_counters_autocomp), required=True),
	counter_name: discord.Option(str, "The name of the counter",autocomplete=discord.utils.basic_autocomplete(counters_on_the_item_autocomp), required=True)
	):
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	full_item = get_full_item_from_name(item,character)
	if full_item not in character['items']:
		await ctx.respond(f"**{codename.upper()}** is not carrying the item '{item}'.\n-# The item field is case- and formatting-sensitive; try using autofill suggestions.",ephemeral=True)
		return
	item = full_item
	
	counter_name = counter_name.lower()
	if (item not in character['counters']) or (counter_name.lower() not in character['counters'][item]):
		await ctx.respond(f"Your **{item}** does not have an associated counter called '{counter_name}'." + replace_commands_with_mentions("\n-# Add one with `/add_item_counter`."),ephemeral=True)
		return
	
	del character['counters'][item][counter_name]
	message = f"The {counter_name.upper()} counter on {codename.upper()}'s **{item}** has been removed."
	if len(character['counters'][item]) <= 0:
		del character['counters'][item]
		message += " It no longer has any associated counters."
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))
	
async def active_character_traits_autocomp(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	trait_list = current_char['traits']
	output = []
	for trait in trait_list:
		output.append(trait['Name'])
	return output

@bot.command(description="Remove a trait from your active character")
async def remove_trait(ctx, trait: discord.Option(str, "The name of the trait to remove.",autocomplete=discord.utils.basic_autocomplete(active_character_traits_autocomp), required=True),
	keep_item: discord.Option(bool, "If TRUE, the Trait's associated item will not be removed from your inventory.", required=False, default=False)):
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if len(character['traits']) <= 0:
		await ctx.respond(f"{codename.upper()} does not have any traits.",ephemeral=True)
		return
	
	target_trait = None
	target_trait_number = None
	for current in character['traits']:
		if current['Name'].lower() == trait.lower():
			target_trait = current
			target_trait_number = current['Number']
			break
	
	if target_trait == None:
		await ctx.respond(f"{codename.upper()} does not have a trait called '{trait}'.",ephemeral=True)
		return
	else:
		revoke_stat_change(character,target_trait["Stat"])
	
		character['traits'].remove(target_trait)
		await ctx.respond(f"{codename.upper()} has lost the trait **{trait.upper()}**.")
		
		if not keep_item:
			try:
				character['items'].remove(target_trait['Item'])
			except ValueError as e:
				log("Caught ValueError in attempt to remove trait item")
		
		if target_trait_number == 316: #henshin bookkeeping
			if 'henshin_trait' in character['special']:
				del character['special']['henshin_trait']
			if 'henshin_stored_hp' in character['special']:
				if character['special']['henshin_stored_maxhp'] != 0:
					character['hp'] = character['special']['henshin_stored_hp']
				del character['special']['henshin_stored_hp']
			if 'henshin_stored_maxhp' in character['special']:
				if character['special']['henshin_stored_maxhp'] != 0:
					character['maxhp'] = character['special']['henshin_stored_maxhp']
				del character['special']['henshin_stored_maxhp']
		
		if target_trait_number == 652: #volatile bookkeeping
			if 'volatile_trait' in character['special']:
				revoke_stat_change(character,character['special']['volatile_trait']['Stat'])
				del character['special']['volatile_trait']
		
		await save_character_data(str(ctx.author.id))
		return

@bot.command(description="Remove an item from your active character")
async def remove_item(ctx,
		item: discord.Option(str, "The item to be removed",autocomplete=discord.utils.basic_autocomplete(item_name_autocomplete), required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return False
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return False
	
	if len(character['items']) <= 0:
		await ctx.respond(f"**{codename.upper()}** does not have any items.",ephemeral=True)
		return False
	
	item = get_full_item_from_name(item, character)
	
	try:
		character['items'].remove(item)
	except ValueError as e:
		log(f"Caught ValueError: {e}")
		out = "The item that you wanted to remove could not be found. Your current items are:"
		for i in character['items']:
			out += f"\n- {i}"
		await response_with_file_fallback(ctx,out)
		return False
	
	if item in character['counters']:
		del character['counters'][item]
	
	await ctx.respond(f"**{codename.upper()}** has removed **{item}** from their inventory.")
	await save_character_data(str(ctx.author.id))
	return True

@bot.command(description="Display an item from your active character")
async def show_item(ctx,item: discord.Option(str, "The item to be removed",autocomplete=discord.utils.basic_autocomplete(item_name_autocomplete), required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if len(character['items']) <= 0:
		await ctx.respond(f"**{codename.upper()}** does not have any items.",ephemeral=True)
		return

	full_item = get_full_item_from_name(item, character)
	message = f"Displaying an item from {codename.upper()}'s inventory:"

	if full_item in character['items']:
		await ctx.defer()
		message += f"\n>>> ## {full_item}"
		if full_item in character['counters']:
			counters = character['counters'][full_item]
			counter_strings = []
			for counter in counters:
				counter_strings.append(f"\n- {counter.upper()}: {counters[counter]}")
			message += f"{', '.join(counter_strings)}"
		await ctx.respond(message)
		return
	else:
		await ctx.respond(f"**{codename.upper()}** does not have an item called '{item}'.",ephemeral=True)
		return

@bot.command(description="Show your active character's current Role")
async def show_role(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	r = character["role"]
	if r == {}:
		await ctx.respond(f"{codename.upper()} does not have a Role yet." + replace_commands_with_mentions(" You can set one with `/set_role`."),ephemeral=True)
		return
	else:
		await ctx.respond(f"{codename.upper()}'s Role:\n>>> **{r['Name']}**\n{r['Text']}")

@bot.command(description="Spend a War Die from your active character")
async def war_die(ctx, explode: discord.Option(bool, "If TRUE, this roll follows the 'Exploding WAR DICE' optional rule.", required=False, default=False)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if character['wd'] > 0:
		fated = False
		for trait in character['traits']:
			if trait['Number'] == 236:
				fated = True
				break
		
		if character['special'].get('volatile_trait',{}).get('Number',None) == 236:
			fated = True
		
		if character['special'].get('henshin_trait',{}).get('Number',None) == 236:
			if character['special']['henshin_stored_maxhp'] != 0:
				fated = True
		
		character['wd'] -= 1
		remaining = character['wd']
		if explode:
			if fated:
				first = [d6()]
				second = [d6()]
				if first[0] == second[0]:
					while first[-1] == 6:
						first.append(d6())
					while second[-1] == 6:
						second.append(d6())
					message = f"**{codename.upper()}** spends a **Fated** War Die. **They rolled doubles—both are used!**"
					message += f"\n-"
					for result in first:
						if result == 6:
							message += f" **{num_to_die[result]} ({result}💥)**"
						elif len(first) > 1 and result == 1:
							message += f" **{num_to_die[result]} ({result} - __collapse!__)**"
						else:
							message += f" **{num_to_die[result]} ({result})**"
					message += f"\n-"
					for result in second:
						if result == 6:
							message += f" **{num_to_die[result]} ({result}💥)**"
						elif len(second) > 1 and result == 1:
							message += f" **{num_to_die[result]} ({result} - __collapse!__)**"
						else:
							message += f" **{num_to_die[result]} ({result})**"
					message += f"\n- Total: **{0 if (1 in first and len(first) > 1) or (1 in second and len(second) > 1) else sum(first) + sum(second)}**"
					message += f"\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left."
					await ctx.respond(message)
				elif first[0] == 6 or second[0] == 6:
					nonsix = min([first[0],second[0]])
					class DiePicker(discord.ui.View):
						@discord.ui.button(label="Explode the 6", style=discord.ButtonStyle.red, emoji="💥")
						async def explode_callback(self, button, interaction):
							if interaction.user.id == ctx.author.id:
								self.disable_all_items()
								await interaction.response.edit_message(view=self)
								log("Sending Explode response")
								results = [6]
								while results[-1] == 6:
									results.append(d6())
								message = f"**{codename.upper()}** explodes the 6:"
								for result in results:
									if result == 6:
										message += f" **{num_to_die[result]} ({result}💥)**"
									elif len(results) > 1 and result == 1:
										message += f" **{num_to_die[result]} ({result} - __collapse!__)**"
									else:
										message += f" **{num_to_die[result]} ({result})**"
								if len(results) > 1 or (1 in results and len(results) > 1):
									message += f"\n- Total: **{0 if 1 in results else sum(results)}**"
								await ctx.respond(message)
							else:
								log("Denying invalid Explode response")
								await interaction.response.send_message("This is not your War Die roll.",ephemeral=True)
						@discord.ui.button(label="Keep the " + str(nonsix), style=discord.ButtonStyle.blurple, emoji="🎲")
						async def safety_callback(self, button, interaction):
							if interaction.user.id == ctx.author.id:
								log("Sending safe response")
								self.disable_all_items()
								await interaction.response.edit_message(view=self)
								await ctx.respond(f"**{codename.upper()}** keeps the **{num_to_die[nonsix]} ({nonsix})**.")
							else:
								log("Denying invalid safe response")
								await interaction.response.send_message("This is not your War Die roll.",ephemeral=True)
					await ctx.respond(f"**{codename.upper()}** spends a **Fated** War Die. **They must choose:**\n- **{num_to_die[6]} (6💥)**\n- **{num_to_die[nonsix]} ({nonsix})**\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left.",view=DiePicker(timeout=5*60,disable_on_timeout=True))
				else:
					results = [first[0],second[0]]
					winner = max(results)
					loser = min(results)
					await ctx.respond(f"**{codename.upper()}** spends a **Fated** War Die: **{num_to_die[results[0]]}/{num_to_die[results[1]]} ({winner})**\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left.")
			else:
				results = [d6()]
				while results[-1] == 6:
					results.append(d6())
				message = f"**{codename.upper()}** spends a War Die:"
				for result in results:
					if result == 6:
						message += f" **{num_to_die[result]} ({result}💥)**"
					elif len(results) > 1 and result == 1:
						message += f" **{num_to_die[result]} ({result} - __collapse!__)**"
					else:
						message += f" **{num_to_die[result]} ({result})**"
				if len(results) > 1 or (1 in results and len(results) > 1):
					message += f"\n- Total: **{0 if 1 in results and len(results) > 1 else sum(results)}**"
				message += f"\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left."
				await ctx.respond(message)
		else:
			if fated:
				results = [d6(),d6()]
				winner = max(results)
				loser = min(results)
				if winner == loser:
					winner = winner + loser
				await ctx.respond(f"**{codename.upper()}** spends a **Fated** War Die: **{num_to_die[results[0]]}{' + ' if results[0] == results[1] else '/'}{num_to_die[results[1]]} ({winner})**\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left.")
			else:
				result = d6()
				await ctx.respond(f"**{codename.upper()}** spends a War Die: **{num_to_die[result]} ({result})**\nThey have {remaining} War Di{'e' if remaining == 1 else 'ce'} left.")
		if character_has_trait(character,652):
			await volatile(ctx,None)
		else:
			await save_character_data(str(ctx.author.id))
	else:
		await ctx.respond(f"{codename.upper()} has no War Dice to spend!",ephemeral=True)

editable_stats = ["CURRENT HP","MAX HP","WAR DICE","FORCEFUL","TACTICAL","REFLEXIVE","CREATIVE","ARMOR"]

@bot.command(description="Increase one of your character's stats")
async def increase_stat(ctx,
	stat: discord.Option(str, "The stat to change.", choices=editable_stats, required=True),
	amount: discord.Option(str, "Amount to increase the stat by. Supports dice syntax. Negative values will decrease.", required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
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
	output = await roll_dice_with_context(ctx,amount,True)
	if output is None:
		return
	
	character[translated_stat] += output[0]
	if type(character[translated_stat]) is float and character[translated_stat] == int(character[translated_stat]):
		# if the number ends up as an integer, store it as an integer please
		character[translated_stat] = int(character[translated_stat])

	if translated_stat == "maxhp":
		if character['maxhp'] < 1:
			character['maxhp'] = 1
		if output[0] > 0:
			character['hp'] += output[0]
			if type(character['hp']) is float and character['hp'] == int(character['hp']):
				# store it as an integer please
				character['hp'] = int(character['hp'])
		elif character['hp'] > character['maxhp']:
			character['hp'] = character['maxhp']
	
	message = f"{codename.upper()} has **{'in' if output[0] >= 0 else 'de'}creased** their **{stat}** by {abs(output[0])}!"
	if 'hp' in translated_stat:
		message += f"\n- Their HP is now **{character['hp']}/{character['maxhp']}**."
	else:
		message += f"\n- The new value is **{character[translated_stat]}**."
	if character['hp'] <= 0 and 'henshin_stored_maxhp' in character['special'] and character['special']['henshin_stored_maxhp'] > 0:
		character['hp'] = character['special']['henshin_stored_hp']
		character['maxhp'] = character['special']['henshin_stored_maxhp']
		character['special']['henshin_stored_hp'] = 0
		character['special']['henshin_stored_maxhp'] = 0
		message += f"\n-# **This has deactivated HENSHIN.** HP has been reverted to **{character['hp']}/{character['maxhp']}**."

	if 'd' in amount or 'D' in amount:
		message += f"\n-# Dice results: `{output[1]}`"
	
	await ctx.respond(message)
	if 'adjust' in ctx.command.qualified_name:
		await save_character_data(str(ctx.author.id))

@bot.command(description="Decrease one of your character's stats")
async def decrease_stat(ctx,
	stat: discord.Option(str, "The stat to change.", choices=editable_stats, required=True),
	amount: discord.Option(str, "Amount to decrease the stat by. Supports dice syntax. Negative values will increase.", required=True)):
	
	return await increase_stat(ctx,stat,f"-({amount})")

@bot.command(description="Adjust one of your character's stats")
async def adjust(ctx,
	stat: discord.Option(str, "The stat to change.", choices=editable_stats, required=True),
	amount: discord.Option(str, "Amount to increase the stat by. Supports dice syntax. Negative values will decrease.", required=True)):
	
	return await increase_stat(ctx,stat,amount)

@bot.command(description="Reset your active character's stats and items to the trait defaults")
async def refresh(ctx, 
	reset_hp: discord.Option(bool, "If TRUE, sets your base HP to 6 and recalculates it. FALSE by default.", required=False, default=False), 
	reset_war_dice: discord.Option(bool, "If TRUE, sets your War Dice to 0 and recalculates it. FALSE by default.", required=False, default=False)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
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

	def refresh_handle_bonus(stat: str):
		bonus = stat.split(" ")
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
	
	for trait in character['traits']:
		if trait['Item'] not in character['items']:
			character['items'].append(trait['Item'])
		
		refresh_handle_bonus(trait['Stat'])
	
	if 'volatile_trait' in character['special']:
		refresh_handle_bonus(character['special']['volatile_trait']['Stat'])
	
	character['hp'] = character['maxhp']
	
	message = f"**{codename.upper()}**" + replace_commands_with_mentions(" has been reset to their default stats. Use `/sheet` to view updated information.")
	if weapon_reset:
		message += "\n-# This action has reset your equipped weapon to **Unarmed (2d6k1 DAMAGE)**."
	if armor_reset:
		message += "\n-# This action has reset your equipped weapon to **Nothing (0 ARMOR)**."
	if reset_hp:
		message += f"\n-# Your Max HP has been recalculated from the base 6, and is now **{character['maxhp']}**."
	if reset_war_dice:
		message += f"\n-# Your War Dice have been recalculated from the base 0, and is now **{character['wd']}**."
	if 'henshin_stored_maxhp' in character['special'] and character['special']['henshin_stored_maxhp'] != 0:
		character['special']['henshin_stored_hp'] = 0
		character['special']['henshin_stored_maxhp'] = 0
		message += f"\nYour active HENSHIN status has been cleared."
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

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
	
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	output = await roll_dice_with_context(ctx,amount,True)
	if output is None:
		return
	
	before_armor = output[0]
	if before_armor < 0:
		before_armor = 0
	damage_taken = output[0] - character['armor'] - bonus_armor
	if damage_taken < 0:
		damage_taken = 0
	dice_results = output[1]
	
	if armor_piercing:
		damage_taken = before_armor
	
	character['hp'] -= int(damage_taken)
	
	message = f"**{codename.upper()}** has taken **{int(before_armor)} damage!**"
	if (not armor_piercing and character['armor'] + bonus_armor > 0):
		message += f" (Reduced to **{int(damage_taken)}** by {character['armor']}{f' (+{bonus_armor} bonus)' if bonus_armor > 0 else ''} armor from {character['armor_name']}!)"
	elif (armor_piercing and character['armor'] + bonus_armor > 0):
		message += f" (Ignores {character['armor']}{f' (+{bonus_armor} bonus)' if bonus_armor > 0 else ''} armor from {character['armor_name']}!)"
	message += f"\nHP: {character['hp']}/{character['maxhp']}"
	
	if character['hp'] <= 0 and 'henshin_stored_maxhp' in character['special'] and character['special']['henshin_stored_maxhp'] > 0:
		revoke_stat_change(character,character['special']['henshin_trait']["Stat"])
		character['hp'] = character['special']['henshin_stored_hp']
		character['maxhp'] = character['special']['henshin_stored_maxhp']
		character['special']['henshin_stored_hp'] = 0
		character['special']['henshin_stored_maxhp'] = 0

		message += f"\n-# **This has deactivated HENSHIN.** HP has been reverted to **{character['hp']}/{character['maxhp']}**."
	
	if ('d' in amount or 'd' in amount):
		message += f"\n-# Dice results: `{dice_results}`"
		limit = 300
		if len(message) > limit:
			message = message[:limit-5]+"...]`"
	await ctx.respond(message)
	if character['hp'] > 0 and damage_taken >= 6 and character_has_trait(character,652):
		await volatile(ctx,None)
	else:
		await save_character_data(str(ctx.author.id))

@bot.command(description="Heal your active character")
async def heal(ctx, 
	amount: discord.Option(str, "Amount of healing to receive. Supports dice syntax.", required=True),
	):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	output = await roll_dice_with_context(ctx,amount,True)
	if output is None:
		return
	
	healing_taken = int(output[0])
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
	if ('d' in amount or 'D' in amount):
		message += f"\n-# Dice results: `{dice_results}`"
		limit = 300
		if len(message) > limit:
			message = message[:limit-5]+"...]`"
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Roll your active character's weapon damage")
async def attack(ctx,
	bonus_damage: discord.Option(str, "Amount of extra damage to deal; supports dice syntax.", required=False, default="0"),
	multiplier: discord.Option(int, "Amount to multiply the final damage by.", required=False, default=1)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	base_damage = character['damage']
	base_damage = await roll_dice_with_context(ctx,base_damage,True)
	if base_damage is None:
		return
	
	bonus_damage_result = await roll_dice_with_context(ctx,bonus_damage,True)
	if bonus_damage_result is None:
		return
	
	final_damage = (base_damage[0] + bonus_damage_result[0]) * multiplier
	
	message = f"**{codename.upper()}** has dealt **{final_damage} damage** using **{character['weapon_name']}**!\n-# Base damage: `{character['damage']}` -> `{base_damage[1]}`"
	if bonus_damage != "0":
		message += f"\n-# Bonus damage: `{bonus_damage}` -> `{bonus_damage_result[1]}`"
	if multiplier != 1:
		message += f"\n-# Final damage multiplier: `{multiplier}`"
	await ctx.respond(message)

async def get_all_acceptable_syntax(ctx, string):
	current_char = get_active_char_object(ctx)
	out = []
	words = string.split(" ")
	for word in words:
		diceout = await roll_dice_with_context(ctx,word,False)
		if len(word) > 0 and diceout is not None:
			out.append(word)
	return out

def get_item_effect(item):
	item_split = item.split(" (")
	if len(item_split) > 1:
		return item_split[1].replace(")","")
	else:
		return None

def get_item_name(item):
	item_split = item.split(" (")
	return item_split[0]

async def held_dice_autocomplete(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	item_list = current_char['items']
	dice_outs = set()
	current_item_selected = ctx.options["name"]
	if current_item_selected == 'Unarmed':
		dice_outs.add("2d6k1")
	full_current_item = get_full_item_from_name(current_item_selected,current_char)
	if full_current_item is None:
		for item in item_list:
			item_effect = get_item_effect(item)
			dice_outs = dice_outs.union(set(await get_all_acceptable_syntax(ctx,item_effect)))
	else:
		item_effect = get_item_effect(full_current_item)
		dice_outs = dice_outs.union(set(await get_all_acceptable_syntax(ctx,item_effect)))
	return list(dice_outs)

async def held_numbers_autocomplete(ctx):
	current_char = get_active_char_object(ctx)
	if current_char is None:
		return []
	item_list = current_char['items']
	num_outs = set()
	current_item_selected = ctx.options["name"]
	if current_item_selected == 'Nothing':
		num_outs.add(0)
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

async def weapon_name_autocomplete(ctx):
	items = await item_name_autocomplete(ctx)
	if items is None:
		return None
	else:
		return ["Unarmed"] + items

@bot.command(description="Set your equipped weapon")
async def equip_weapon(ctx, 
	name: discord.Option(str, "The weapon's name.", autocomplete=discord.utils.basic_autocomplete(weapon_name_autocomplete), required=True,max_length=100),
	damage: discord.Option(str, "Amount of damage to deal; supports dice syntax.", autocomplete=discord.utils.basic_autocomplete(held_dice_autocomplete), required=True)):
	
	character = get_active_char_object(ctx)
	
	name = name.strip()
	damage = damage.strip()
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	if await roll_dice_with_context(ctx,damage,True) is None:
		return
	
	character['weapon_name'] = name
	character['damage'] = damage
	
	await ctx.respond(f"**{codename.upper()}** has equipped **{name} ({damage} DAMAGE)**")
	
	await save_character_data(str(ctx.author.id))

async def armor_name_autocomplete(ctx):
	items = await item_name_autocomplete(ctx)
	if items is None:
		return None
	else:
		return ["Nothing"] + items

@bot.command(description="Set your equipped armor")
async def equip_armor(ctx, 
	name: discord.Option(str, "The armor's name.", autocomplete=discord.utils.basic_autocomplete(armor_name_autocomplete), required=True,max_length=100),
	damage: discord.Option(int, "Amount of damage it reduces.", autocomplete=discord.utils.basic_autocomplete(held_numbers_autocomplete), required=True)):
	
	name = name.strip()
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)

	if character['premium'] and not await ext_character_management(ctx.author.id):
		await ctx.respond(f"The character **{codename.upper()}** is in a premium slot, but you do not have an active subscription. You may not edit them directly.\nYou may edit them again if you clear out enough non-premium characters first, or re-enrolling in a [Ko-fi Subscription]( https://ko-fi.com/solarashlulu/tiers ), linking your Ko-fi account to Discord, and joining [Sonder's Garage]( https://discord.gg/VeedQmQc7k ).",ephemeral=True)
		return
	
	character['armor_name'] = name
	character['armor'] = damage
	
	await ctx.respond(f"**{codename.upper()}** has equipped **{name} ({damage} ARMOR)**")
	
	await save_character_data(str(ctx.author.id))

log("Creating trait commands")
trait_group = discord.SlashCommandGroup("trait", "Trait Commands")

@trait_group.command(description="Looks up a trait by name or d666 number")
async def lookup(ctx, trait: discord.Option(str,"The trait to search for",autocomplete=discord.utils.basic_autocomplete(trait_autocomp))):
	trait = trait.strip()
	message = search_for_trait(trait)
	hidden = message in ["No trait exists with the given number. Trait numbers must be possible d666 roll outputs.","Could not find a trait with an approximately similar name."]
	
	await ctx.respond(message,ephemeral=hidden)

@trait_group.command(description="Produces a random trait")
async def random(ctx):
	result = rnd.choice(trait_data)
	if (rnd.randint(1,10000) == 1):
		result = secret_trait
	message = trait_message_format(result)
	await ctx.respond(message)

@bot.command(description="Convert a barcode into a MONSTERS statblock")
async def monsters(ctx, barcode: discord.Option(str,"The barcode to input"), type: discord.Option(str,"A descriptor, usually the item the barcode was on",required=False,default=None,max_length=50)):
	try:
		barcode = [int(digit) for digit in barcode]
	except ValueError:
		await ctx.respond(f"Barcodes must consist of only integers.",ephemeral=True)
		return
	barcode = sorted(barcode)
	code_length = len(barcode)
	
	if code_length < 3:
		await ctx.respond(f"Barcodes must be at least 3 digits long.",ephemeral=True)
		return
	
	damage_bonus = barcode[0]
	health = barcode[-1]
	armor = None
	if code_length % 2 == 1:
		armor = barcode[code_length // 2]
	else:
		upper_middle_index = code_length // 2
		lower_middle_index = upper_middle_index - 1
		armor = (barcode[lower_middle_index] + barcode[upper_middle_index]) // 2
	
	await ctx.respond(f"Your summoned {type.upper() + ' ' if type is not None else ''}MONSTER has:\n- 💥 1D6{'+'+str(damage_bonus) if damage_bonus > 0 else ''} DAMAGE\n- ❤️ {health} HP\n- 🛡️ {armor} ARMOR")

@bot.command(description="Rolls a check for HARVEST")
async def harvest(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if not character_has_trait(character, 311):
		await ctx.respond(f"{codename.upper()} does not have the HARVEST trait.",ephemeral=True)
		return
	
	if d6() <= 3: #failure
		await ctx.respond(f"{codename.upper()}'s killing blow **fails to land!**")
	else:
		class HarvestChoice(discord.ui.View):
			@discord.ui.button(label=f"+1 WAR DIE (Current: {character['wd']})",style=discord.ButtonStyle.blurple,emoji="🎲")
			async def harvest_wd_callback(self,button,interaction):
				if interaction.user.id == ctx.author.id:
					log("Harvest +1WD callback")
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					await adjust(ctx,"WAR DICE","1")
				else:
					log("Denying invalid Harvest response")
					await interaction.response.send_message("This is not your HARVEST prompt.",ephemeral=True)
			@discord.ui.button(label=f"+1D6 HP (Current: {character['hp']}/{character['maxhp']})",style=discord.ButtonStyle.green,emoji="❤️‍🩹")
			async def harvest_hp_callback(self,button,interaction):
				if interaction.user.id == ctx.author.id:
					log("Harvest +1D6 HP callback")
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					await heal(ctx,"1D6")
				else:
					log("Denying invalid Harvest response")
					await interaction.response.send_message("This is not your HARVEST prompt.",ephemeral=True)
			@discord.ui.button(label="Cancel",emoji="🚫")
			async def harvest_cancel_callback(self, button, interaction):
				if interaction.user.id == ctx.author.id:
					log("Harvest cancel callback")
					self.disable_all_items()
					await interaction.response.edit_message(content=f"*HARVEST activation cancelled.*",view=self)
				else:
					log("Denying invalid Harvest response")
					await interaction.response.send_message("This is not your HARVEST prompt.",ephemeral=True)
		await ctx.respond(f"{codename.upper()}'s killing blow **strikes true!**\nThey may choose one of the following options.",view=HarvestChoice())

sunder_tracker = {}

@bot.command(description="Rolls damage for SUNDER, and then applies the damage to your active character")
async def sunder(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond(replace_commands_with_mentions("You do not have an active character in this channel. Select one with `/switch_character`."),ephemeral=True)
		return
	codename = get_active_codename(ctx)
	
	if not character_has_trait(character, 611):
		await ctx.respond(f"{codename.upper()} does not have the SUNDER trait.",ephemeral=True)
		return
	
	sunder_tracker[ctx.interaction.id] = d6()
	
	class SunderStacking(discord.ui.View):
		@discord.ui.button(label="+1D6",style=discord.ButtonStyle.blurple,emoji="🎲")
		async def sunder_stack_callback(self, button, interaction):
			if interaction.user.id == ctx.author.id:
				log("Sunder +1D6 callback")
				sunder_tracker[ctx.interaction.id] += d6()
				await interaction.response.edit_message(content=f"{codename.upper()} activates SUNDER...\n> - The target will take {sunder_tracker[ctx.interaction.id]} damage.\n> - {codename.upper()} will take {math.floor(sunder_tracker[ctx.interaction.id]/2)} damage.",view=self)
			else:
				log("Denying invalid Sunder response")
				await interaction.response.send_message("This is not your SUNDER prompt.",ephemeral=True)
		@discord.ui.button(label="Finish & take self-damage",style=discord.ButtonStyle.red,emoji="💥")
		async def sunder_finish_callback(self, button, interaction):
			if interaction.user.id == ctx.author.id:
				log("Sunder damage callback")
				self.disable_all_items()
				await interaction.response.edit_message(view=self)
				await damage(ctx,str(math.floor(sunder_tracker[ctx.interaction.id]/2)),True,0)
				del sunder_tracker[ctx.interaction.id]
			else:
				log("Denying invalid Sunder response")
				await interaction.response.send_message("This is not your SUNDER prompt.",ephemeral=True)
		@discord.ui.button(label="Cancel",emoji="🚫")
		async def sunder_cancel_callback(self, button, interaction):
			if interaction.user.id == ctx.author.id:
				log("Sunder cancel callback")
				del sunder_tracker[ctx.interaction.id]
				self.disable_all_items()
				await interaction.response.edit_message(content=f"{codename.upper()} activates SUNDER...\n> *Activation cancelled.*",view=self)
			else:
				log("Denying invalid Sunder response")
				await interaction.response.send_message("This is not your SUNDER prompt.",ephemeral=True)
	
	await ctx.respond(f"{codename.upper()} activates SUNDER...\n> - The target will take {sunder_tracker[ctx.interaction.id]} damage.\n> - {codename.upper()} will take {math.floor(sunder_tracker[ctx.interaction.id]/2)} damage.", view=SunderStacking(timeout=5*60,disable_on_timeout=True))

bot.add_application_command(trait_group)

log("Creating role commands")
role_group = discord.SlashCommandGroup("role", "Role Commands")

@role_group.command(description="Looks up a role by name or d66 number")
async def lookup(ctx, role: discord.Option(str,"The role to search for",autocomplete=discord.utils.basic_autocomplete(role_autocomp))):
	role = role.strip()
	message = search_for_role(role)
	hidden = message in ["No role exists with the given number. Role numbers must be possible d66 roll outputs.","Could not find a role with an approximately similar name."]
	await ctx.respond(message,ephemeral=hidden)

@role_group.command(description="Produces a random role")
async def random(ctx):
	result = rnd.choice(role_data)
	message = role_message_format(result)
	await ctx.respond(message)

bot.add_application_command(role_group)

log("Creating challenge commands")
challenge_group = discord.SlashCommandGroup("challenge", "Challenge Commands")
async def challenge(ctx, interval: int, interval_name: str):
	current_int = int(time() / interval)
	next_int = current_int + 1

	seeded_rnd = rnd.Random()
	seeded_rnd.seed(current_int)

	message = f"# {interval_name} CHALLENGE\n".upper()
	message += f"Began <t:{current_int * interval}:R>\n"
	message += f"Next challenge begins <t:{next_int * interval}:R>\n"

	# --- Generate Character ---

	message += f"## 👤 Character: {seeded_rnd.choice(merc_codenames).upper()}\n"
	traits = seeded_rnd.sample(trait_data, 2)
	role = seeded_rnd.choice(role_data)
	
	for i in range(len(traits)):
		if (seeded_rnd.randint(1,10000) == 1):
			traits[i] = secret_trait
			break
	
	traits.sort(key=trait_sort_key)
	
	extra_thing = seeded_rnd.randint(1,3)
	
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
	for trait in traits:
		message += f"- **{trait['Name']}** ({trait['Number']})\n"
	
	message += "\nITEMS:"
	for trait in traits:
		message += f"\n- {trait['Item']}"
	if extra_thing == 3:
		standard_issue_items = ["Balaclava (hides identity)", "Flashlight (can be used as a weapon attachment)", "Knife (1D6 DAMAGE)", "MRE field rations (+1D6 HP, one use)", "Pistol (1D6 DAMAGE)", "Riot shield (1 ARMOR, equip as weapon)"]
		message += f"\n- {seeded_rnd.choice(standard_issue_items)}"
	
	# --- Generate Mission ---
	
	name_A = roll_intelligence_matrix(intelligence['misc'][1],seeded_rnd).split(" ")
	name_B = roll_intelligence_matrix(intelligence['misc'][1],seeded_rnd).split(" ")
	mission_name = name_A[0] + " " + name_B[1]

	message += f"\n## 🗺️ Mission: {mission_name.upper()}\n"

	results = roll_all_matrices(intelligence["mission"],seeded_rnd)
	instigator = decap_first(results[0])
	activity = decap_first(results[1])
	effect = decap_first(results[2])
	twist = decap_first(results[3])
	reward = results[4]
	message += f"\nThe dossier says that **{instigator}** is trying to **{activity}**, which will **{effect}**. However, **{twist}**.\n- Reward: **{reward}**"
	
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

@challenge_group.command(description="Shows the current daily challenge")
async def daily(ctx):
	await challenge(ctx,60*60*24,"daily")

@challenge_group.command(description="Shows the current weekly challenge")
async def weekly(ctx):
	await challenge(ctx,7*60*60*24,"weekly")

bot.add_application_command(challenge_group)

log("Creating player commands")
player_group = discord.SlashCommandGroup("player", "Player Commands")

def trait_sort_key(trait):
	return trait["Name"]

log("Loading Codenames")
file = open('codenames.json')
merc_codenames = json.load(file)
file.close()

@player_group.command(description="Produces a random operative codename")
async def codename(ctx):
	await ctx.respond("# " + rnd.choice(merc_codenames))

@player_group.command(description="Produces a random character sheet")
async def character(ctx,
					traitcount: discord.Option(discord.SlashCommandOptionType.integer, "The number of traits this character should have. Defaults to 2.", required=False, default=2, min_value=1, max_value=40),
					include_custom_traits: discord.Option(bool, "Include your own custom traits in the list of possible traits.", required=False, default=False)):
	message = f"# {rnd.choice(merc_codenames)}\n"
	traits_to_use = trait_data

	if include_custom_traits:
		uid = str(ctx.author.id)
		if uid in character_data and len(character_data[uid]['traits']) > 0:
			traits_to_use = deepcopy(trait_data) + list(character_data[uid]['traits'].values())

	traits = rnd.sample(traits_to_use, traitcount)
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
	results = [d6(), d6()]
	if superior_dice ^ inferior_dice:
		results.append(d6())
		
	original_results = deepcopy(results)
	
	dice_string = ""
	for d in results:
		dice_string += " " + num_to_die[d]
	dice_string = dice_string.strip()
	
	full_results = sorted(results)
	if superior_dice and not inferior_dice:
		results = full_results[-2:]
	elif inferior_dice and not superior_dice:
		results = full_results[:2]
	
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
	
	buttons = None
	character = get_active_char_object(ctx)
	if character is not None and character_has_trait(character, 331): #hypnosis check
		class HypnosisReroll(discord.ui.View):
			orig_results = []
			def __init__(self,original_results,timeout,disable_on_timeout):
				super().__init__(timeout=timeout,disable_on_timeout=disable_on_timeout)
				self.orig_results = original_results
			@discord.ui.button(label="Reroll Lowest (Hypnosis)",emoji="🌀")
			async def hypnosis_reroll_callback(self,button,interaction):
				if interaction.user.id == ctx.author.id:
					log("Hypnosis reroll callback")
					self.disable_all_items()
					old_lowest = min(self.orig_results)
					new_lowest = d6()
					oldlowindex = self.orig_results.index(old_lowest)
					self.orig_results[oldlowindex] = new_lowest
					
					dice_string = ""
					for d in self.orig_results:
						dice_string += " " + num_to_die[d]
					dice_string = dice_string.strip()
					
					full_results = sorted(self.orig_results)
					if superior_dice and not inferior_dice:
						self.orig_results = full_results[-2:]
					elif inferior_dice and not superior_dice:
						self.orig_results = full_results[:2]
					
					total = sum(self.orig_results) + modifier
					
					message = ""
					
					if modifier != 0:
						message = f"({dice_string}) + {modifier} = **{total}**: "
					else:
						message = f"{dice_string} = **{total}**: "
					
					if self.orig_results == [6,6]:
						message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
					elif total <= 6:
						message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
					elif total <= 9:
						message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
					else:
						message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."
					message += f"\n- *A reroll was performed via HYPNOSIS: {old_lowest} -> {new_lowest}*"
					await interaction.response.edit_message(content=message,view=self)
				else:
					log("Denying invalid Hypnosis reroll response")
					await interaction.response.send_message("This is not your HYPNOSIS prompt.",ephemeral=True)
		buttons = HypnosisReroll(original_results,timeout=5*60,disable_on_timeout=True)
	
	await ctx.respond(message,view=buttons)

@player_group.command(description="Rolls dice using common dice syntax")
async def dice(ctx, syntax: discord.Option(str,"The dice syntax"),
	instances: discord.Option(discord.SlashCommandOptionType.integer, "The number of times to roll this dice formation", required=False, default=1, min_value=1),
	hidden: discord.Option(bool, "If TRUE, the output of this command is hidden to others", required=False, default=False)):
	syntax = syntax.strip()
	
	output = ()
	if instances > 1:
		output = []
		for i in range(instances):
			x = await roll_dice_with_context(ctx,syntax,True)
			if x is None:
				return
			else:
				output.append(x)
	else:
		output = await roll_dice_with_context(ctx,syntax,True)
		if output is None:
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
		message += f"\n-# It seems your input didn't actually roll any dice. Did you mean `1d{syntax}` or `{syntax}d6`?\n-# See [py-rolldice](<https://github.com/mundungus443/py-rolldice#dice-syntax>) for an explanation of dice syntax."
	
	await response_with_file_fallback(ctx,message,hidden)

bot.add_application_command(player_group)

log("Creating matrix commands")
matrix_group = discord.SlashCommandGroup("matrix", "Intelligence Matrix Rollers")

intelligence = {}

file = open('matrices/mission_generator.json')
intelligence["mission"] = json.load(file)
file.close()

@matrix_group.command(description="Provides a random Mission Dossier")
async def mission(ctx):
	results = roll_all_matrices(intelligence["mission"])
	instigator = decap_first(results[0])
	activity = decap_first(results[1])
	effect = decap_first(results[2])
	twist = decap_first(results[3])
	reward = results[4]
	message = f"The dossier says that **{instigator}** is trying to **{activity}**, which will **{effect}**. However, **{twist}**.\n- Reward: **{reward}**"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/mission_prompts.json')
intelligence["prompt"] = json.load(file)
file.close()

@matrix_group.command(description="Provides a random Mission Prompt")
async def prompt(ctx):
	message = roll_intelligence_matrix(intelligence["prompt"][0])
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/misc.json')
intelligence["misc"] = json.load(file)
file.close()

@matrix_group.command(description="Incants a Magical Word")
async def syllables(ctx, amount: discord.Option(int, "The amount of syllables the word will have.", required=False, default=None, min_value=1, max_value=100)=None):
	result = ""
	count = d6() if amount is None else amount
	for i in range(count):
		result += roll_intelligence_matrix(intelligence["misc"][0])
	if len(result) > 2000:
		await ctx.respond("The output for this command exceeds 2000 characters and cannot be sent.",ephemeral=True)
		return
	await ctx.respond(result)

@matrix_group.command(description="Gives a random Operation Codename")
async def operation_codename(ctx):
	result = roll_intelligence_matrix(intelligence["misc"][1])
	await ctx.respond("# " + result)

@matrix_group.command(description="Provokes a random Combat Behavior")
async def tactics(ctx):
	result = roll_intelligence_matrix(intelligence["misc"][2])
	await ctx.respond(result)

@matrix_group.command(description="Strikes a random Hit Location")
async def hit(ctx):
	result = [roll_intelligence_matrix(intelligence["misc"][3])]
	while "Compound injury (roll two hit locations)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.remove("Compound injury (roll two hit locations)")
	result = "You've been hit in the **" + "** __*and*__ **".join(result) + "**!"
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Faction Action")
async def factionaction(ctx):
	result = [roll_intelligence_matrix(intelligence["misc"][4])]
	while "Fake-out zig-zag (roll two actions)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.remove("Compound injury (roll two hit locations)")
	result = " __*and*__ ".join(result)
	result = f"A faction (any `/matrix faction`) makes the following move: **{result}**"
	await ctx.respond(result)

@matrix_group.command(description="Discloses a random Faction Mission")
async def factionmission(ctx):
	result = [roll_intelligence_matrix(intelligence["misc"][5])]
	while "Double mission (roll two objectives)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.remove("Double mission (roll two objectives)")
	result = " __*and*__ ".join(result)
	message = f"A faction (any `/matrix faction`) tasks you with this objective: **{result}**"
	await ctx.respond(message)

@matrix_group.command(description="Assigns a random CHOKE Score")
async def choke(ctx):
	result = roll_intelligence_matrix(intelligence["misc"][10])
	await ctx.respond(result)

@matrix_group.command(description="Causes random consequences for a Partial Success")
async def partial(ctx, type: discord.Option(str,"The type of consequence that should be inflicted",choices=["COMBAT","GENERAL","MENTAL","MOVEMENT","SOCIAL","WEIRD"],required=False,default=None)=None):
	if type is not None:
		type = type.upper()
	if type == None:
		await ctx.defer()
		message = roll_intelligence_matrix(intelligence["misc"][11])
		message = message.split(" ")
		message[0] = f"({message[0]})"
		message = " ".join(message)
		await ctx.respond(message)
	elif type in ["COMBAT","GENERAL","MENTAL","MOVEMENT","SOCIAL","WEIRD"]:
		await ctx.defer()
		all = intelligence["misc"][11]["Values"].values()
		outcomes = []
		for item in all:
			if item.startswith(type):
				split_point = len(type) + 1
				outcomes.append(item[split_point:])
		await ctx.respond(rnd.choice(outcomes))
	else:
		await ctx.respond("Valid partial success types are COMBAT, GENERAL, MOVEMENT, SOCIAL, and WEIRD.",ephemeral=True)

@matrix_group.command(description="Spawns a Random Encounter")
async def encounter(ctx):
	result = roll_intelligence_matrix(intelligence["misc"][12])
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Downtime Event")
async def downtime(ctx):
	result = roll_intelligence_matrix(intelligence["misc"][13])
	await ctx.respond(result)

file = open('matrices/cassettes.json')
intelligence["cassettes"] = json.load(file)
file.close()

file = open('matrices/cassette_links.json')
intelligence["cassette_links"] = json.load(file)
file.close()

@matrix_group.command(description="Plays a random Cassette Tape")
async def cassette(ctx, type: discord.Option(str,"The type of audio that should be on the cassette tape.",choices=["Music","Sounds"],required=False,default=None)=None):
	await ctx.defer()
	audio = rnd.choice(intelligence["cassettes"])
	if type is not None:
		while type[0] == "M" and ('[' in audio or ']' in audio):
			audio = rnd.choice(intelligence["cassettes"])
		while type[0] == "S" and not ('[' in audio or ']' in audio):
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

file = open('matrices/gear/GUARD.json')
intelligence["guard"] = json.load(file)
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
async def baseupgrade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific Base Upgrade instead",choices=bupgrade_names,required=False,default=None)=None):
	message = ""
	if lookup is None:
		result = rnd.choice(intelligence["gear_bupgrades"])
		message = f"**{result['Name']}:** {result['Effect']}"
	else:
		best_match = get_close_matches(lookup.upper(), bupgrade_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodbup = {}
			for bup in intelligence["gear_bupgrades"]:
				if best_match[0] == bup["Name"]:
					goodbup = bup
					break
			message = f"**{goodbup['Name']}:** {goodbup['Effect']}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

@gear_group.command(description="Divulges the contents of a random Crate")
async def crate(ctx):
	result = roll_intelligence_matrix(intelligence["gear_items"][1])
	message = f"You crack open a crate, revealing **{result}** inside."
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

@gear_group.command(description="Grants a random Common Item")
async def item(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of items to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

@gear_group.command(description="Grants a random piece of Armor")
async def armor(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of armor pieces to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
async def weapon(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of weapons to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
async def weapon_tag(ctx, lookup: discord.Option(str,"Including this argument searches for a specific tag instead",autocomplete=discord.utils.basic_autocomplete(tag_lookup_autocomp),required=False,default=None)=None):
	tags = intelligence["gear_weapons_and_armor"][2]["Values"]
	message = ""
	hidden = False
	if lookup is None:
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
			best_match = get_close_matches(lookup.upper(), wep_tag_names, n=1, cutoff=0.0)
			
			if len(best_match) > 0:
				for tag in tags.values():
					if tag["Name"] == best_match[0]:
						result = tag
						message = f"**{result['Name']}**: {result['Effect']}"
						break
			else:
				message = "Could not find a tag with an approximately similar name."
				hidden = True
	message = replace_commands_with_mentions(message)
	await ctx.respond(message,ephemeral=hidden)

armor_tag_names = []
for tag in intelligence["guard"]["Values"].values():
	armor_tag_names.append(tag['Name'])

async def armor_tag_lookup_autocomp(ctx):
	return armor_tag_names

@gear_group.command(description="Applies a random Weapon Tag")
async def armor_tag(ctx, lookup: discord.Option(str,"Including this argument searches for a specific tag instead",autocomplete=discord.utils.basic_autocomplete(armor_tag_lookup_autocomp),required=False,default=None)=None):
	tags = intelligence["guard"]["Values"]
	message = ""
	hidden = False
	if lookup is None:
		result = roll_intelligence_matrix(intelligence["guard"])
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
			best_match = get_close_matches(lookup.upper(), armor_tag_names, n=1, cutoff=0.0)
			
			if len(best_match) > 0:
				for tag in tags.values():
					if tag["Name"] == best_match[0]:
						result = tag
						message = f"**{result['Name']}**: {result['Effect']}"
						break
			else:
				message = "Could not find a tag with an approximately similar name."
				hidden = True
	message = replace_commands_with_mentions(message)
	message += "\n-# Armor tags are courtesy of Hevybot's [GUARD](<https://hevybot.itch.io/guard>) supplement."
	await ctx.respond(message,ephemeral=hidden)

@gear_group.command(description="Grants a random Vehicle")
async def vehicle(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of vehicles to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
async def vehicleweapon(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of vehicle weapons to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
async def skin(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of weapon skins to produce (allows duplicates)", required=False, default=1, min_value=1, max_value=50)=1):
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
async def weaponsmith(ctx,
		weapon_tags: discord.Option(discord.SlashCommandOptionType.integer, "The number of tags the weapon has", required=False, default=None, min_value=1, max_value=6)=None):
	model = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][1])
	
	tags = []
	amount = (d6() if d6() <= 1 else 1) if weapon_tags is None else weapon_tags
	tags = rnd.sample(list(intelligence["gear_weapons_and_armor"][2]["Values"].values()),amount)
	
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	
	output_embed = discord.Embed()
	output_embed.color = discord.Color.from_rgb(rnd.randint(0,255), rnd.randint(0,255), rnd.randint(0,255))
	output_embed.title = f"**{model}** (adorned with **{skin}**)"
	for tag in tags:
		output_embed.add_field(name=tag['Name'],value=replace_commands_with_mentions(tag['Effect']),inline=False)
	await ctx.respond(embed=output_embed)

@gear_group.command(description="Generates a fully unique Armor piece")
async def armorsmith(ctx,
		armor_tags: discord.Option(discord.SlashCommandOptionType.integer, "The number of tags the armor has", required=False, default=None, min_value=1, max_value=6)=None):
	model = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][0])
	
	tags = []
	amount = (d6() if d6() <= 1 else 1) if armor_tags is None else armor_tags
	tags = rnd.sample(list(intelligence["guard"]["Values"].values()),amount)

	if intelligence["guard"]["Values"]["66"] in tags:
		for i in range(2):
			extra_tag = rnd.choice(list(intelligence["guard"]["Values"].values()))
			while extra_tag in tags:
				extra_tag = rnd.choice(list(intelligence["guard"]["Values"].values()))
			tags.append(extra_tag)
	
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])

	output_embed = discord.Embed()
	output_embed.color = discord.Color.from_rgb(rnd.randint(0,255), rnd.randint(0,255), rnd.randint(0,255))
	output_embed.title = f"**{model}** (adorned with **{skin}**)"
	for tag in tags:
		output_embed.add_field(name=tag['Name'],value=tag['Effect'],inline=False)
	output_embed.set_footer(text="Armor tags are courtesy of Hevybot's GUARD supplement: https://hevybot.itch.io/guard")
	await ctx.respond(embed=output_embed)

@gear_group.command(description="Generates a fully unique Vehicle")
async def hangar(ctx):
	model = roll_intelligence_matrix(intelligence["gear_vehicles"][0])
	weapon = roll_intelligence_matrix(intelligence["gear_vehicles"][1])
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	message = f"**{model}**\n- Equipped with **{weapon}**\n- Adorned with **{skin}**"
	await ctx.respond(message)

cyclops_group = matrix_group.create_subgroup("cyclops", "CYCLOPS Intelligence Matrices")

file = open('matrices/cyclops/gadgets.json')
intelligence["cyclops_gadgets"] = json.load(file)
file.close()

gadgets_by_name = {}
for g in intelligence["cyclops_gadgets"][0]["Values"].values():
	gadgets_by_name[g["Name"].upper()] = g

async def gadget_lookup_autocomp(ctx):
	return list(gadgets_by_name.keys())

file = open('matrices/cyclops/rumors.json')
intelligence["cyclops_rumors"] = json.load(file)
file.close()

@cyclops_group.command(description="Grants a random CYCLOPS Gadget")
async def gadget(ctx, 
	lookup: discord.Option(str,"Including this argument searches for a specific gadget. Overrides other arguments!",autocomplete=discord.utils.basic_autocomplete(gadget_lookup_autocomp),required=False,default=None)=None,
	count: discord.Option(discord.SlashCommandOptionType.integer, "The number of CYCLOPS Gadgets to produce", required=False, default=1, min_value=1, max_value=250)=1,
	duplicates: discord.Option(bool, "Mark FALSE to prevent duplicate items being rolled if count > 1", required=False, default=True)=True
	):
	await ctx.defer()
	message = ""
	if lookup is None: #getting random gadgets
		if count <= 1:
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
	else: #performing lookup instead
		best_match = get_close_matches(lookup.upper(), list(gadgets_by_name.keys()), n=1, cutoff=0.0)
		result = gadgets_by_name[best_match[0]]
		message = f"**{result['Name']}**: {result['Effect']}"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges where CYCLOPS High Command is (allegedly) located")
async def location(ctx):
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][0])
	message = f"Rumored location of CYCLOPS High Command: **{result}**"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges the (alleged) origin of CYCLOPS")
async def origin(ctx):
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][1])
	message = f"Rumored origin of CYCLOPS: **{result}**"
	await ctx.respond(message)

world_group = matrix_group.create_subgroup("world", "World Intelligence Matrices")

file = open('matrices/world/hazards.json')
intelligence["world_hazards"] = json.load(file)
file.close()

@world_group.command(description="Spawns a random Hazard")
async def hazard(ctx):
	result = roll_intelligence_matrix(intelligence["world_hazards"][0])
	message = f"Tread carefully; the area ahead contains **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Reveals a random Trap")
async def trap(ctx):
	result = roll_intelligence_matrix(intelligence["world_hazards"][1])
	message = f"You've sprung a trap! You suffer the effects of **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Starts in a random Year")
async def year(ctx):
	start = int(roll_intelligence_matrix(intelligence["misc"][6]))
	modifier = int(roll_intelligence_matrix(intelligence["misc"][7]))
	year = start + modifier
	await ctx.respond(f"_The year is **{year}**..._")

@world_group.command(description="Randomly modifies the local Temperature and Precipitation")
async def weather(ctx):
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
async def premade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific NPC instead",autocomplete=discord.utils.basic_autocomplete(npc_lookup_autocomp),required=False,default=None)=None):
	message = ""
	if lookup is None:
		result = rnd.choice(intelligence["chars_premade"])
		message = format_premade(result)
	else:
		best_match = get_close_matches(lookup.upper(), premade_npc_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodchar = {}
			for char in intelligence["chars_premade"]:
				if best_match[0] in char["Head"]:
					goodchar = char
					break
			message = format_premade(goodchar)
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/celebrities.json')
intelligence["chars_celebs"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Celebrity")
async def celebrity(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/civilians.json')
intelligence["chars_civvies"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Civilian")
async def civilian(ctx):
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
	result = roll_all_matrices(intelligence["chars_politicians"])
	position = result[0]
	vice = result[1]
	name = result[2]
	feature = result[3]
	secret = result[4]
	message = f"Name: {name}\nPosition: {position}\nVice: {vice}\nFeature: {feature}\nSecret: {secret}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/scientists.json')
intelligence["chars_scientists"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Scientist")
async def scientist(ctx):
	result = roll_all_matrices(intelligence["chars_scientists"])
	alleg = result[0]
	career = result[1]
	name = result[2]
	feature = result[3]
	discovery = roll_extra_possibility(result[4])
	message = f"Name: {name}\nAllegiance: {alleg}\nCareer: {career}\nFeature: {feature}\nDiscovery: {discovery}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/soldiers.json')
intelligence["chars_soldiers"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Soldier")
async def soldier(ctx):
	result = roll_all_matrices(intelligence["chars_soldiers"])
	rank = result[0]
	name = result[1]
	feature = result[2]
	anecdote = result[3]
	message = f"Name: {name}\nRank: {rank}\nFeature: {feature}\nAnecdote: {anecdote}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)
	
file = open('matrices/characters/spies.json')
intelligence["chars_spies"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Spy")
async def spy(ctx):
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
async def premade(ctx, lookup: discord.Option(str,"Including this argument searches for a specific Enemy instead",autocomplete=discord.utils.basic_autocomplete(enemy_lookup_autocomp),required=False,default=None)=None):
	message = ""
	if lookup is None:
		result = rnd.choice(intelligence["chars_enemy_premade"])
		message = format_premade(result)
	else:
		best_match = get_close_matches(lookup.upper(), premade_enemy_names, n=1, cutoff=0.0)
		if len(best_match) > 0:
			goodchar = {}
			for char in intelligence["chars_enemy_premade"]:
				if best_match[0] in char["Head"]:
					goodchar = char
					break
			message = format_premade(goodchar)
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/animals.json')
intelligence["chars_animals"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Animal")
async def animal(ctx):
	result = roll_all_matrices(intelligence["chars_animals"])
	amount = result[0]
	desc = result[1]
	feature = result[2]
	mal = result[3]
	message = f"Description: {desc}\nAmount: {amount}\nFeature: {feature}\nMalady: {mal}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/anomalies.json')
intelligence["chars_anomalies"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Anomaly")
async def anomaly(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/monsters.json')
intelligence["chars_monsters"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Monster")
async def monster(ctx):
	result = roll_all_matrices(intelligence["chars_monsters"])
	amount = result[0]
	desc = result[1]
	feature = result[2]
	horror = result[3]
	if amount == "Dire (3-6 ARMOR, 6D6-10D6 HP, roll another horror)":
		horror += " __*and*__ " + roll_intelligence_matrix(intelligence["chars_monsters"][3])
	message = f"Description: {desc}\nAmount: {amount}\nFeature: {feature}\nHorror: {horror}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/characters/robots.json')
intelligence["chars_robots"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Robot")
async def robot(ctx):
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
	result = roll_all_matrices(intelligence["chars_squads"])
	rep = result[0]
	command = result[1]
	name = result[2]
	feature = result[3]
	if d6() <= 3:
		feature = f"{feature} __*and*__ {roll_intelligence_matrix(intelligence['chars_squads'][3])}"
	theme = result[4]
	message = f"Name: {name}\nReputation: {rep}\nFeature: {feature}\nTheme: {theme}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

fact_group = matrix_group.create_subgroup("faction", "Faction Intelligence Matrices")

file = open('matrices/factions/aliens.json')
intelligence["facs_aliens"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Alien faction")
async def aliens(ctx):
	result = roll_all_matrices(intelligence["facs_aliens"])
	origin = result[0]
	mission = result[1]
	desc = result[2]
	feature = result[3]
	truth = roll_extra_possibility(result[4])
	message = f"Description: {desc}\nFeature: {feature}\nMission: {mission}\nOrigin: {origin}\nTruth: {truth}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/factions/agencies.json')
intelligence["facs_agencies"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Agency")
async def agency(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/factions/criminals.json')
intelligence["facs_criminals"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Criminal organization")
async def criminals(ctx):
	result = roll_all_matrices(intelligence["facs_criminals"])
	honor = result[0]
	name = result[1]
	feature = result[2]
	racket = result[3]
	message = f"Name: {name}\nFeature: {feature}\nRacket: {racket}\nHonor: {honor}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/factions/cults.json')
intelligence["facs_cults"] = json.load(file)
file.close()

@fact_group.command(description="Establishes a random Cult")
async def cult(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

loc_group = matrix_group.create_subgroup("location", "Location Intelligence Matrices")

file = open('matrices/locations/battlefields.json')
intelligence["locs_battlefields"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Battlefield")
async def battlefield(ctx):
	result = roll_all_matrices(intelligence["locs_battlefields"])
	layout = result[0]
	desc = result[1]
	feature = result[2]
	grave = roll_extra_possibility(result[3])
	message = f"Layout: {layout}\nDescription: {desc}\nFeature: {feature}\nGrave: {grave}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/locations/cities.json')
intelligence["locs_cities"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random City")
async def city(ctx):
	result = roll_all_matrices(intelligence["locs_cities"])
	cyclops = result[0]
	name = result[1]
	feature = result[2]
	headline = result[3]
	message = f"Name: {name}\nFeature: {feature}\nCyclops Surveillance Level: {cyclops}\nHeadline: *{headline}*"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/locations/nature.json')
intelligence["locs_nature"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random location in Nature")
async def nature(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/locations/rooms.json')
intelligence["locs_rooms"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Room")
async def room(ctx):
	result = roll_all_matrices(intelligence["locs_rooms"])
	exits = result[0]
	doors = result[1]
	desc = result[2]
	feature = result[3]
	event = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nDoors: {doors}\nExits: {exits}\nEvent: {event}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/locations/structures.json')
intelligence["locs_structures"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Structure")
async def structure(ctx):
	result = roll_all_matrices(intelligence["locs_structures"])
	owner = result[0]
	security = result[1]
	desc = result[2]
	feature = result[3]
	history = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nOwner: {owner}\nSecurity: {security}\nHistory: {history}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/locations/zones.json')
intelligence["locs_zones"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Zone")
async def zone(ctx):
	result = roll_all_matrices(intelligence["locs_zones"])
	size = result[0]
	integrity = result[1]
	desc = result[2]
	feature = result[3]
	center = result[4]
	message = f"Size: {size}\nDescription: {desc}\nFeature: {feature}\nIntegrity: {integrity}\nCenter: {center}"
	message = replace_commands_with_mentions(message)
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/lore/coverups.json')
intelligence["lore_coverups"] = json.load(file)
file.close()

@lore_group.command(description="Uncovers a random Coverup")
async def coverup(ctx):
	result = roll_all_matrices(intelligence["lore_coverups"])
	suppression = result[0]
	witness = result[1]
	if witness == "1D6 witnesses":
		witness = f"{rnd.randint(2,6)} witnesses"
	desc = result[2]
	feature = result[3]
	hook = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nWitness: {witness}\nSuppression: {suppression}\nHook: {hook}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/lore/diplomacy.json')
intelligence["lore_diplomacy"] = json.load(file)
file.close()

@lore_group.command(description="Establishes a random Diplomacy")
async def diplomacy(ctx):
	result = roll_all_matrices(intelligence["lore_diplomacy"])
	coverage = result[0]
	desc = result[1]
	feature = result[2]
	drama = result[3]
	message = f"Description: {desc}\nFeature: {feature}\nCoverage: {coverage}\nDrama: {drama}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/lore/disasters.json')
intelligence["lore_disasters"] = json.load(file)
file.close()

@lore_group.command(description="Causes a random Disaster")
async def disaster(ctx):
	result = roll_all_matrices(intelligence["lore_disasters"])
	scale = result[0]
	response = result[1]
	desc = result[2]
	feature = result[3]
	impact = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nScale: {scale}\nResponse: {response}\nImpact: {impact}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/lore/legends.json')
intelligence["lore_legends"] = json.load(file)
file.close()

@lore_group.command(description="Tells a random Legend")
async def legend(ctx):
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
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

file = open('matrices/lore/spells.json')
intelligence["lore_spells"] = json.load(file)
file.close()

@lore_group.command(description="Casts a random Spell")
async def spell(ctx):
	result = roll_all_matrices(intelligence["lore_spells"])
	level = result[0]
	obscurity = result[1]
	name = result[2]
	if d6() <= 2:
		names = rnd.sample(list(intelligence["lore_spells"][2]["Values"].values()),2)
		names[0] = names[0].rsplit(" ", 1)
		names[1] = names[1].rsplit(" ", 1)
		name = names[0][0] + " " + names[1][1]
	
	number_of_features = 0
	if level == "Novice":
		number_of_features = 1
	elif level == "Apprentice":
		number_of_features = 2
	elif level == "Adept":
		number_of_features = 3
	elif level == "Expert":
		number_of_features = 4
	elif level == "Master":
		number_of_features = 5
	elif level == "Legendary":
		number_of_features = 6
	feature = ", ".join(rnd.sample(list(intelligence["lore_spells"][3]["Values"].values()),number_of_features))

	number_of_effects = 1
	if level == "Legendary":
		number_of_effects = d6()
	
	effect = ", ".join(rnd.sample(list(intelligence["lore_spells"][4]["Values"].values()),number_of_effects))
	message = f"Name: {name}\nLevel: {level}\nEffect{'s' if number_of_effects > 1 else ''}: {effect}\nFeature{'s' if number_of_features > 1 else ''}: {feature}\nObscurity: {obscurity}"
	message = replace_commands_with_mentions(message)
	await ctx.respond(message)

bot.add_application_command(matrix_group)

atrx_group = discord.SlashCommandGroup("ataraxia", "RATIONS #1: ATARAXIA Commands")

file = open('rations/ataraxia.json')
intelligence["ataraxia"] = json.load(file)
file.close()

@atrx_group.command(description="Listens to a rumor from Vizhay")
async def rumor(ctx):
	result = roll_intelligence_matrix(intelligence["ataraxia"][0])
	message = f"You pick up on a rumor in Vizhay: {result}"
	await ctx.respond(message)

@atrx_group.command(description="Encounter something in Dyatlov Pass")
async def encounter(ctx):
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
	result = roll_intelligence_matrix(intelligence["hazfunction"][0])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's hazard")
async def hazard(ctx):
	result = roll_intelligence_matrix(intelligence["hazfunction"][1])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a crucible animal")
async def animal(ctx):
	result = roll_intelligence_matrix(intelligence["hazfunction"][4])
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's encounter")
async def encounter(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True, min_value=0)):
	options = intelligence["hazfunction"][2]["Values"]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	result = options[str(roll)]
	await ctx.respond(result)

@hzfc_group.command(description="Spawn a chamber's item")
async def item(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True, min_value=0)):
	options = intelligence["hazfunction"][3]["Values"]
	roll = d6() + rooms_cleared
	if roll > 16:
		roll = 16
	result = options[str(roll)]
	await ctx.respond(result)

@hzfc_group.command(description="Enter a new chamber, and outfit it with an encounter, hazard, and item")
async def full_room(ctx, rooms_cleared: discord.Option(discord.SlashCommandOptionType.integer, "The number of rooms already cleared", required=True, min_value=0)):
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
async def canister(ctx, amount: discord.Option(str, "The number of canisters to provide", required=False, default="1")):
	original_syntax = amount
	syntax_results = None
	amount = await roll_dice_with_context(ctx,amount,True)
	if amount is None:
		return
	else:
		syntax_results = amount[1]
		amount = amount[0]

	msg = ""
	if amount == 1:
		msg = f"Colony offers you a Bacteria Canister that's labelled... **{strain()}**. Whatever that means."
	else:
		msg = "Colony offers you several Bacteria Canisters:"
		for i in range(amount):
			msg += f"\n- **{strain()}**"
	if 'd' in original_syntax.lower():
		msg += f"\nDice results: `{original_syntax}` -> `{syntax_results}` -> `{amount}`"
	
	await response_with_file_fallback(ctx,msg)

@ctsh_group.command(description="Roll to see if Colony will spawn.")
async def spawn(ctx):
	if d6() % 2 == 1:
		await ctx.respond("Colony **will** spawn in this region.")
	else:
		await ctx.respond("Colony **will not** spawn in this region.")

bot.add_application_command(ctsh_group)

log("Loading THE BOARD data...")
board_data = {}
if os.path.exists('the_board.json'):
	board_file = open('the_board.json')
	board_data = json.load(board_file)
	board_file.close()
else:
	board_data = {
		'time': None,
		'url': None
	}

@bot.command(description="Tracks THE BOARD.",guild_ids=[1101249440230154300,959600183186952232])
async def the_board(ctx, message_id_of_new_record: discord.Option(str, "The ID of the message to pin.", required=False, default=None, min_length=18, max_length=19)):
	if message_id_of_new_record is not None:
		if ctx.author.guild_permissions.manage_messages or ctx.author.id == ownerid:
			channel = ctx.channel
			message = None
			try:
				message = await channel.fetch_message(int(message_id_of_new_record))
			except (discord.NotFound,ValueError) as e:
				log(f"Caught: {e}")
				await ctx.respond(f"There was an error processing this command:\n```{e}```\nYou must provide a valid message ID. Check [this article](<https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->) for more details.",ephemeral=True)
				return
			
			t = int(message.created_at.timestamp())
			url = message.jump_url
			
			response = f"# THE BOARD HAS BEEN RESET\nTIME SINCE LAST INCIDENT: <t:{t}:R>"
			if board_data['time'] is not None and board_data['url'] is not None:
				response += f"\n## Previous Incident: <t:{board_data['time']}:R> ({board_data['url']})"
			
			board_data['time'] = t
			board_data['url'] = url
			with open('the_board.json','w') as outfile:
				outfile.write(json.dumps(board_data))
			
			await message.reply(response)
			await ctx.respond("Board updated.",ephemeral=True)
		else:
			await ctx.respond("You must have the MANAGE MESSAGES permission to use this command.",ephemeral=True)
	elif board_data['time'] is None or board_data['url'] is None:
		await ctx.respond("The board has not been set yet.",ephemeral=True)
	else:
		await ctx.respond(f"# TIME SINCE LAST INCIDENT: <t:{board_data['time']}:R>\nLast incident: {board_data['url']}")

log("Loading context menu reactions...")

async def generic_emoji_react(ctx: discord.ApplicationContext, message: discord.Message, emoji: str):
	await ctx.defer(ephemeral=True)

	for r in message.reactions:
		if not r.is_custom_emoji() and r.emoji == emoji:
			async for user in r.users():
				if user.id == bot.user.id:
					return await ctx.respond(f"I have already reacted to that message with {emoji}.",ephemeral=True)

	reaction_failure = None
	reply_failure = None

	try:
		await message.add_reaction(emoji)
	except Exception as e:
		reaction_failure = e
	
	try:
		await message.reply(content=emoji)
	except Exception as f:
		reply_failure = f

	if reaction_failure is None and reply_failure is None:
		# no errors encountered
		return await ctx.respond(f"Reacted with {emoji} for you.",ephemeral=True)
	elif reaction_failure is not None and reply_failure is not None:
		# both errors encountered
		msg = "This action could not be completed."
		msg += f"\n-# Reaction error: {reaction_failure}"
		msg += f"\n-# Reply error: {reply_failure}"
		return await ctx.respond(msg,ephemeral=True)
	elif reaction_failure is not None:
		# only reaction failure
		msg = f"Replied with {emoji} for you."
		msg = f"\n-# The reaction could not be completed: {reaction_failure}"
		return await ctx.respond(msg,ephemeral=True)
	elif reply_failure is not None:
		# only reply failure
		msg = f"Replied with {emoji} for you."
		msg = f"\n-# The reply could not be completed: {reply_failure}"
		return await ctx.respond(msg,ephemeral=True)

react_emojis = list("❌⭕🟢🟡🔴")

for emj in react_emojis:
	@bot.message_command(name=f"React with {emj}")
	async def react_cross(ctx: discord.ApplicationContext, message: discord.Message):
		return await generic_emoji_react(ctx,message,ctx.command.name.split(" ")[-1])

log("Starting bot session")
bot.run(token)

log("Bot session ended. Saving character data...")
asyncio.run(save_character_data())