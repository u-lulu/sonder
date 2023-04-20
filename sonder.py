import discord
import json
import difflib
import re
import random as rnd
import os # default module

bot = discord.Bot(activity=discord.Game(name='FIST: Ultra Edition'))

token_file = open('token.json')
token_file_data = json.load(token_file)
ownerid = token_file_data["owner_id"]
token = token_file_data["token"]
token_file.close()

trait_file = open('traits.json')
trait_data = json.load(trait_file)
trait_file.close()

role_file = open('roles.json')
role_data = json.load(role_file)
role_file.close()

trait_names = []
for trait in trait_data:
	trait_names.append(trait["Name"])

role_names = []
for role in role_data:
	role_names.append(role["Name"])

num_to_die = {
	1: "<:revolver_dice_1:1029946656277405726>",
	2: "<:revolver_dice_2:1029946657439223858>",
	3: "<:revolver_dice_3:1029946659087601714>",
	4: "<:revolver_dice_4:1029946660341690368>",
	5: "<:revolver_dice_5:1029946661541269554>",
	6: "<:revolver_dice_6:1029946662531113011>"
}

def trait_message_format(trait):
	return f"{trait['Number']}. **{trait['Name']}**\n{trait['Effect']}\n- {trait['Item']}, {trait['Stat']}"

def role_message_format(role):
	return f"{role['Number']}. **{role['Name']}**\n{role['Text']}"

def search_for_trait(trait):
	message = ""
	if re.match("^\d+$", trait):
		number = int(trait)
		message = "No trait exists with the given number. Trait numbers must be possible d666 roll outputs."
		for trait in trait_data:
			if trait["Number"] == number:
				message = trait_message_format(trait)
				break
	else:
		best_match = difflib.get_close_matches(trait.upper(), trait_names, n=1, cutoff=0.0)

		if len(best_match) > 0:
			goodtrait = {}
			for trait in trait_data:
				if trait["Name"] == best_match[0]:
					goodtrait = trait
					break
			message = trait_message_format(trait)
		else:
			message = "Could not find a trait with an approximately similar name."
	return message

def search_for_role(role):
	message = ""
	if re.match("^\d+$", role):
		number = int(role)
		message = "No role exists with the given number. Role numbers must be possible d66 roll outputs."
		for role in role_data:
			if role["Number"] == number:
				message = role_message_format(role)
				break
	else:
		best_match = difflib.get_close_matches(role.upper(), role_names, n=1, cutoff=0.0)

		if len(best_match) > 0:
			goodtrait = {}
			for role in role_data:
				if role["Name"] == best_match[0]:
					goodtrait = role
					break
			message = role_message_format(role)
		else:
			message = "Could not find a role with an approximately similar name."
	return message

def roll_intelligence_matrix(table):
	roll_type = table["Roll"].upper()
	if roll_type == "2D6":
		roll_result = rnd.randint(1,6) + rnd.randint(1,6)
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
	unique_lst = []

	# Iterate through the elements in the original list
	for elem in lst:
		# If the element is not already in the unique list, add it
		if elem not in unique_lst:
			unique_lst.append(elem)

	# Return the resulting list
	return unique_lst

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

@bot.event
async def on_ready():
	print(f"{bot.user} is ready and online!")

@bot.command(description="Measure's this bot's latency")
async def ping(ctx):
	print("/ping")
	await ctx.respond(f"Pong! Latency is {bot.latency}")

@bot.command(description="Shuts down the bot. Will not work unless you own the bot.")
async def shutdown(ctx):
	print(f"/shutdown ({ctx.author.id})")
	if ctx.author.id == ownerid:
		await ctx.respond(f"Restarting.")
		await bot.close()
	else:
		await ctx.respond(f"Only <@{ownerid}> may use this command.",ephemeral=True)

@bot.command(description="Links to the Help document for this bot")
async def help(ctx):
	print("/help")
	await ctx.respond("https://docs.google.com/document/d/15pm5o5cJuQF_J3l-NMpziPEuxDkcWJVE3TNT7_IerbQ/edit?usp=sharing",ephemeral=True)

@bot.command(description="Links to the invite page for this bot")
async def invite(ctx):
	print("/invite")
	await ctx.respond("https://discord.com/api/oauth2/authorize?client_id=1096635021395251352&permissions=274877908992&scope=bot%20applications.commands",ephemeral=True)

@bot.command(description="spin")
async def spin(ctx):
	print("/spin")
	await ctx.respond("https://cdn.discordapp.com/attachments/1098474379383423018/1098475477116669952/spin_lq.mp4",ephemeral=True)

trait_group = discord.SlashCommandGroup("trait", "Trait Commands")

async def role_autocomp(ctx):
	return trait_names

@trait_group.command(description="Looks up a trait by name or d666 number")
async def lookup(ctx, trait: discord.Option(str,"The trait to search for",autocomplete=discord.utils.basic_autocomplete(role_autocomp))):
	print(f"/trait lookup {trait}")
	message = search_for_trait(trait)
	hidden = message in ["No trait exists with the given number. Trait numbers must be possible d666 roll outputs.","Could not find a trait with an approximately similar name."]
	
	await ctx.respond(message,ephemeral=hidden)

@trait_group.command(description="Produces a random trait")
async def random(ctx):
	print("/trait random")
	result = rnd.choice(trait_data)
	message = trait_message_format(result)
	await ctx.respond(message)

bot.add_application_command(trait_group)

role_group = discord.SlashCommandGroup("role", "Role Commands")

async def role_autocomp(ctx):
	return role_names

@role_group.command(description="Looks up a role by name or d66 number")
async def lookup(ctx, role: discord.Option(str,"The role to search for",autocomplete=discord.utils.basic_autocomplete(role_autocomp))):
	print(f"/role lookup {role}")
	message = search_for_role(role)
	hidden = message in ["No role exists with the given number. Role numbers must be possible d66 roll outputs.","Could not find a role with an approximately similar name."]
	await ctx.respond(message,ephemeral=hidden)

@role_group.command(description="Produces a random role")
async def random(ctx):
	print("/role random")
	result = rnd.choice(role_data)
	message = role_message_format(result)
	await ctx.respond(message)

bot.add_application_command(role_group)

player_group = discord.SlashCommandGroup("player", "Player Commands")

@player_group.command(description="Produces a random character sheet")
async def character(ctx):
	print("/player character")
	message = "ROLE: "
	
	traits = rnd.sample(trait_data, 2)
	role = rnd.choice(role_data)
	
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
		stats["MAX"] += rnd.randint(1,6)
	elif extra_thing == 2:
		stats["WAR"] += rnd.randint(1,6)
	
	for trait in traits:
		bonus = trait["Stat"].split(" ")
		num = 0
		if bonus[1] in stats:
			if bonus[0] == "+1D6":
				num = rnd.randint(1,6)
			else:	
				num = 0
				numerical = bonus[0]
				if numerical[0] in ('+', '-'):
					num = int(numerical[1:])
					if numerical[0] == '-':
						num = -num
				else:
					num = int(numerical)
			
			stats[bonus[1]] += num
	
	message += f"MAX HP: {stats['MAX']}\n"
	message += f"WAR DICE: {stats['WAR']}\n\n"
	message += f"FORCEFUL: {stats['FORCEFUL']}\n"
	message += f"TACTICAL: {stats['TACTICAL']}\n"
	message += f"CREATIVE: {stats['CREATIVE']}\n"
	message += f"REFLEXIVE: {stats['REFLEXIVE']}\n\n"
	
	message += "TRAITS:\n"
	for trait in traits:
		message += f"{trait['Number']}. **{trait['Name']}**\n{trait['Effect']} ({trait['Stat']})\n"
	
	message += "\nITEMS:"
	for trait in traits:
		message += f"\n- {trait['Item']}"
	if extra_thing == 3:
		standard_issue_items = ["Balaclava (hides identity)", "Flashlight (can be used as a weapon attachment)", "Knife (1D6 DAMAGE)", "MRE field rations (+1D6 HP, one use)", "Pistol (1D6 DAMAGE)", "Riot shield (1 ARMOR, equip as weapon)"]
		message += f"\n- {rnd.choice(standard_issue_items)}"
	await ctx.respond(message)

@player_group.command(description="Rolls against the Emergency Insertion table")
async def emergencyinsertion(ctx):
	print("/player emergencyinsertion")
	results = [rnd.randint(1,6), rnd.randint(1,6)]
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
async def roll(ctx, modifier: discord.Option(discord.SlashCommandOptionType.integer, "The skill modifier for the roll", required=False, default=0)):
	print(f"/player roll {modifier}")
	results = [rnd.randint(1,6), rnd.randint(1,6)]
	sum = results[0] + results[1] + modifier
	
	message = ""
	
	if modifier != 0:
		message = f"{num_to_die[results[0]]} {num_to_die[results[1]]} + {modifier} = **{sum}**: "
	else:
		message = f"{num_to_die[results[0]]} {num_to_die[results[1]]} = **{sum}**: "
	
	if results == [6,6]:
		message += "Your roll is an **ultra success!** You do exactly what you wanted to do, with some spectacular added bonus."
	elif sum <= 6:
		message += "Your roll is a **failure.** You don’t do what you wanted to do, and things go wrong somehow."
	elif sum <= 9:
		message += "Your roll is a **partial success.** You do what you wanted to, but with a cost, compromise, or complication."
	else:
		message += "Your roll is a **success.** You do exactly what you wanted to do, without any additional headaches."
	await ctx.respond(message)

@player_group.command(description="Rolls any amount of six-sided dice")
async def d6(ctx, count: discord.Option(discord.SlashCommandOptionType.integer, "The number of dice to roll", required=False, default=1)):
	print(f"/player d6 {count}")
	max = 30
	if count < 1:
		await ctx.respond("Invalid parameters. You must provide a positive whole number of dice to roll.", ephemeral=True)
	elif count > max:
		await ctx.respond(f"Invalid parameters. You may roll a maximum of {max} dice at a time.", ephemeral=True)
	else:
		results = ""
		numerical_results = []
		individual = {
			1: 0,
			2: 0,
			3: 0,
			4: 0,
			5: 0,
			6: 0
		}
		sum = 0
		for i in range(count):
			x = rnd.randint(1,6)
			numerical_results.append(str(x))
			individual[x] = individual[x] + 1
			sum += x
			results += num_to_die[x] + " "
			
		results += "\n[" + ", ".join(numerical_results) + "]"
		if count > 1:
			results += f"\n> **Total: {sum}**\n> Average: {sum/count}\n > Counts:"
			for i in range(1,7):
				if individual[i] > 0:
					results += f"\n> - **{i}:** {individual[i]}"
		else:
			results += f"({sum})"
		await ctx.respond(results)

bot.add_application_command(player_group)

matrix_group = discord.SlashCommandGroup("matrix", "Intelligence Matrix Rollers")

intelligence = {}

file = open('matrices/mission_generator.json')
intelligence["mission"] = json.load(file)
file.close()

@matrix_group.command(description="Provides a random Mission Dossier")
async def mission(ctx):
	print("/matrix mission")
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
	print("/matrix prompt")
	result = roll_intelligence_matrix(intelligence["prompt"][0])
	await ctx.respond(result)

file = open('matrices/misc.json')
intelligence["misc"] = json.load(file)
file.close()

@matrix_group.command(description="Incants a Magical Word")
async def syllables(ctx):
	print("/matrix syllables")
	result = ""
	count = rnd.randint(1,6)
	for i in range(count):
		result += roll_intelligence_matrix(intelligence["misc"][0])
	await ctx.respond(result)

@matrix_group.command(description="Gives a random Operation Codename")
async def codename(ctx):
	print("/matrix codename")
	result = roll_intelligence_matrix(intelligence["misc"][1])
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Combat Behavior")
async def tactics(ctx):
	print("/matrix tactics")
	result = roll_intelligence_matrix(intelligence["misc"][2])
	await ctx.respond(result)

@matrix_group.command(description="Strikes a random Hit Location")
async def hit(ctx):
	print("/matrix hit")
	result = [roll_intelligence_matrix(intelligence["misc"][3])]
	while "Compound injury (roll two hit locations)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.append(roll_intelligence_matrix(intelligence["misc"][3]))
		result.remove("Compound injury (roll two hit locations)")
	result = "You've been hit in the **" + "** __*and*__ **".join(result) + "**!"
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Faction Action")
async def factionaction(ctx):
	print("/matrix factionaction")
	result = [roll_intelligence_matrix(intelligence["misc"][4])]
	while "Fake-out zig-zag (roll two actions)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.append(roll_intelligence_matrix(intelligence["misc"][4]))
		result.remove("Compound injury (roll two hit locations)")
	result = " __*and*__ ".join(result)
	await ctx.respond(result)

@matrix_group.command(description="Discloses a random Faction Mission")
async def factionmission(ctx):
	print("/matrix factionmission")
	result = [roll_intelligence_matrix(intelligence["misc"][5])]
	while "Double mission (roll two objectives)" in result:
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.append(roll_intelligence_matrix(intelligence["misc"][5]))
		result.remove("Compound injury (roll two hit locations)")
	result = " __*and*__ ".join(result)
	await ctx.respond(result)

@matrix_group.command(description="Assigns a random CHOKE Score")
async def choke(ctx):
	print("/matrix choke")
	result = roll_intelligence_matrix(intelligence["misc"][10])
	await ctx.respond(result)

async def part_success_autocomplete(ctx: discord.AutocompleteContext):
	return ["COMBAT","GENERAL","MENTAL","MOVEMENT","SOCIAL","WEIRD"]

@matrix_group.command(description="Causes random consequences for a Partial Success")
async def partial(ctx, type: discord.Option(str,"The type of consequence that should be inflicted",autocomplete=discord.utils.basic_autocomplete(part_success_autocomplete),required=False,default="")):
	print(f"/matrix partial {type}")
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
	print("/matrix encounter")
	result = roll_intelligence_matrix(intelligence["misc"][12])
	await ctx.respond(result)

@matrix_group.command(description="Provokes a random Downtime Event")
async def downtime(ctx):
	print("/matrix downtime")
	result = roll_intelligence_matrix(intelligence["misc"][13])
	await ctx.respond(result)

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

@gear_group.command(description="Divulges the contents of a random Crate")
async def crate(ctx):
	print("/matrix gear crate")
	result = roll_intelligence_matrix(intelligence["gear_items"][1])
	message = f"You crack open a crate, revealing **{result}** inside."
	await ctx.respond(message)

@gear_group.command(description="Grants a random Common Item")
async def item(ctx):
	print("/matrix gear item")
	result = roll_intelligence_matrix(intelligence["gear_items"][0])
	await ctx.respond(result)

@gear_group.command(description="Grants a random piece of Armor")
async def armor(ctx):
	print("/matrix gear armor")
	result = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][0])
	await ctx.respond(result)

@gear_group.command(description="Grants a random Weapon")
async def weapon(ctx):
	print("/matrix gear weapon")
	result = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][1])
	await ctx.respond(result)

@gear_group.command(description="Applies a random Weapon Tag")
async def tag(ctx):
	print("/matrix gear tag")
	result = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][2])
	message = f"**{result['Name']}**: {result['Effect']}"
	await ctx.respond(message)

@gear_group.command(description="Grants a random Vehicle")
async def vehicle(ctx):
	print("/matrix gear vehicle")
	result = roll_intelligence_matrix(intelligence["gear_vehicles"][0])
	await ctx.respond(result)

@gear_group.command(description="Grants a random Vehicle Weapon")
async def vehicleweapon(ctx):
	print("/matrix gear vehicleweapon")
	result = roll_intelligence_matrix(intelligence["gear_vehicles"][1])
	await ctx.respond(result)

@gear_group.command(description="Applies a random Weapon Skin")
async def skin(ctx):
	print("/matrix gear skin")
	result = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	await ctx.respond(result)

@gear_group.command(description="Generates a fully unique Weapon")
async def weaponsmith(ctx):
	print("/matrix gear weaponsmith")
	model = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][1])
	tag = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][2])
	tag = f"**{tag['Name']}**: {tag['Effect']}"
	skin = roll_intelligence_matrix(intelligence["gear_weapons_and_armor"][3])
	message = f"**{model}** (adorned with **{skin}**)\n- {tag}"
	await ctx.respond(message)

@gear_group.command(description="Generates a fully unique Vehicle")
async def hangar(ctx):
	print("/matrix gear weaponsmith")
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
async def gadget(ctx):
	print("/matrix cyclops gadget")
	result = roll_intelligence_matrix(intelligence["cyclops_gadgets"][0])
	message = f"**{result['Name']}**: {result['Effect']}"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges where CYCLOPS High Command is (allegedly) located")
async def location(ctx):
	print("/matrix cyclops location")
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][0])
	message = f"Rumored location of CYCLOPS High Command: **{result}**"
	await ctx.respond(message)

@cyclops_group.command(description="Divulges the (alleged) origin of CYCLOPS")
async def origin(ctx):
	print("/matrix cyclops origin")
	result = roll_intelligence_matrix(intelligence["cyclops_rumors"][1])
	message = f"Rumored origin of CYCLOPS: **{result}**"
	await ctx.respond(message)

world_group = matrix_group.create_subgroup("world", "World Intelligence Matrices")

file = open('matrices/world/hazards.json')
intelligence["world_hazards"] = json.load(file)
file.close()

@world_group.command(description="Spawns a random Hazard")
async def hazard(ctx):
	print("/matrix world hazard")
	result = roll_intelligence_matrix(intelligence["world_hazards"][0])
	message = f"Tread carefully; the area ahead contains **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Reveals a random Trap")
async def trap(ctx):
	print("/matrix world trap")
	result = roll_intelligence_matrix(intelligence["world_hazards"][1])
	message = f"You've sprung a trap! You suffer the effects of **{result.lower()}**."
	await ctx.respond(message)

@world_group.command(description="Starts in a random Year")
async def year(ctx):
	print("/matrix world year")
	start = int(roll_intelligence_matrix(intelligence["misc"][6]))
	modifier = int(roll_intelligence_matrix(intelligence["misc"][7]))
	await ctx.respond(str(start + modifier))

@world_group.command(description="Randomly modifies the local Temperature and Precipitation")
async def weather(ctx):
	print("/matrix world weather")
	temp = roll_intelligence_matrix(intelligence["misc"][8])
	precip = roll_intelligence_matrix(intelligence["misc"][9])
	result = f"**Temperature:** {temp}\n**Precipitation:** {precip}"
	await ctx.respond(result)

chars_group = matrix_group.create_subgroup("character", "Character Intelligence Matrices")

file = open('matrices/characters/celebrities.json')
intelligence["chars_celebs"] = json.load(file)
file.close()

@chars_group.command(description="Spawns a random Celebrity")
async def celebrity(ctx):
	print("/matrix character celebrity")
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
	print("/matrix character civilian")
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
	print("/matrix character politician")
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
	print("/matrix character scientist")
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
	print("/matrix character soldier")
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
	print("/matrix character spy")
	result = roll_all_matrices(intelligence["chars_spies"])
	code = result[0]
	clearance = result[1]
	name = result[2]
	feature = result[3]
	modus = result[4]
	message = f"Name: {name}\nCodename: {code}\nClearance: {clearance}\nFeature: {feature}\nModus: {modus}"
	await ctx.respond(message)

enemy_group = matrix_group.create_subgroup("enemy", "Enemy Intelligence Matrices")

file = open('matrices/characters/animals.json')
intelligence["chars_animals"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Animal")
async def animal(ctx):
	print("/matrix enemy animal")
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
	print("/matrix enemy anomaly")
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
	print("/matrix enemy experiment")
	result = roll_all_matrices(intelligence["chars_experiments"])
	creation = result[0]
	desc = result[1]
	feature = result[2]
	mistake = result[3]
	if creation == "Uncontrolled\u2014Roll 1D6 extra features.":
		feature = [feature]
		more = rnd.randint(1,6)
		for i in range(more):
			feature.append(roll_intelligence_matrix(intelligence["chars_experiments"][2]))
		feature = ", ".join(feature)
	elif creation == "Accidental\u2014Roll 1D6 extra mistakes":
		mistake = [mistake]
		more = rnd.randint(1,6)
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
	print("/matrix enemy monster")
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
	print("/matrix enemy robot")
	result = roll_all_matrices(intelligence["chars_robots"])
	budget = result[0]
	desc = result[1]
	feature = result[2]
	prog = result[3]
	
	if budget == "Federal\u2014roll again for conflicting programming":
		prog_conflict = roll_intelligence_matrix(intelligence["chars_robots"][3])
		while prog_conflict == prog:
			prog_conflict = roll_intelligence_matrix(intelligence["chars_robots"][3])
		prog = f"{prog} (conflicts with {prog_conflict})"
	elif budget == "CYCLOPS\u2014add 1D6 additional features":
		possible_features = list(intelligence["chars_robots"][2]["Values"].values())
		feature = rnd.sample(possible_features,rnd.randint(2,7))
		feature = ", ".join(feature)
	elif budget == "Corporate\u2014mash together 1D6 descriptions":
		possible_descs = list(intelligence["chars_robots"][1]["Values"].values())
		desc = rnd.sample(possible_descs,rnd.randint(1,6))
		desc = ", ".join(desc)
	
	message = f"Description: {desc}\nBudget: {budget}\nFeature: {feature}\nProgramming: {prog}"
	await ctx.respond(message)

file = open('matrices/characters/squads.json')
intelligence["chars_squads"] = json.load(file)
file.close()

@enemy_group.command(description="Spawns a random Squad")
async def squad(ctx):
	print("/matrix enemy squad")
	result = roll_all_matrices(intelligence["chars_squads"])
	rep = result[0]
	command = result[1]
	name = result[2]
	feature = result[3]
	if rnd.randint(1,6) <= 3:
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
	print("/matrix faction aliens")
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
	print("/matrix faction agency")
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
	print("/matrix faction corporation")
	result = roll_all_matrices(intelligence["facs_corporations"])
	sector = result[0]
	if sector == "Megacorp (roll 1D6 sectors)":
		possible_sectors = list(intelligence["facs_corporations"][0]["Values"].values())
		possible_sectors.remove("Megacorp (roll 1D6 sectors)")
		subsectors = rnd.sample(possible_sectors, rnd.randint(1,6))
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
	print("/matrix faction criminals")
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
	print("/matrix faction cult")
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
	print("/matrix faction insurgents")
	result = roll_all_matrices(intelligence["facs_insurgents"])
	foothold = result[0]
	desc = result[1]
	feature = result[2]
	strategy = result[3]
	message = f"Description: {desc}\nFeature: {feature}\nFoothold: {foothold}\nStrategy: {strategy}"
	await ctx.respond(message)

loc_group = matrix_group.create_subgroup("location", "Location Intelligence Matrices")

file = open('matrices/locations/battlefields.json')
intelligence["locs_battlefields"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Battlefield")
async def battlefield(ctx):
	print("/matrix location battlefield")
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
	print("/matrix location city")
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
	print("/matrix location nature")
	result = roll_all_matrices(intelligence["locs_nature"])
	situation = result[0]
	desc = result[1]
	feature = result[2]
	claim = result[3]
	if situation == "Shaky\u2014roll two claims, situation deteriorating":
		claim += " __*and*__ " + roll_intelligence_matrix(intelligence["locs_nature"][3])
	elif situation in ["Powder keg\u2014roll 1D6 claims, tensions are high","War\u2014roll 1D6 claims, active conflict in the area"]:
		possible_claims = list(intelligence["locs_nature"][3]["Values"].values())
		subclaims = rnd.sample(possible_claims, rnd.randint(1,6))
		claim = '\n- ' + '\n- '.join(subclaims)
	message = f"Description: {desc}\nFeature: {feature}\nSituation: {situation}\nClaim: {claim}"
	await ctx.respond(message)

file = open('matrices/locations/rooms.json')
intelligence["locs_rooms"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Room")
async def room(ctx):
	print("/matrix location room")
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
	print("/matrix location structure")
	result = roll_all_matrices(intelligence["locs_structures"])
	owner = result[0]
	security = result[1]
	desc = result[2]
	feature = result[3]
	history = result[4]
	message = f"Description: {desc}\nFeature: {feature}\nOwner: {owner} (`/matrix character {owner.lower()}`)\nSecurity: {security}\nHistory: {history}"
	await ctx.respond(message)


file = open('matrices/locations/zones.json')
intelligence["locs_zones"] = json.load(file)
file.close()

@loc_group.command(description="Locates a random Zone")
async def zone(ctx):
	print("/matrix location zone")
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

@lore_group.command(description="Forges a random Artifact")
async def artifact(ctx):
	print("/matrix lore artifact")
	result = roll_all_matrices(intelligence["lore_artifacts"])
	interest = result[0]
	desc = result[1]
	feature = result[2]
	rumor = result[3]
	message = f"Description: {desc}\nFeature: {feature}\nRumor: {rumor}\nInterest: {interest}"
	await ctx.respond(message)

file = open('matrices/lore/coverups.json')
intelligence["lore_coverups"] = json.load(file)
file.close()

@lore_group.command(description="Uncovers a random Coverup")
async def coverup(ctx):
	print("/matrix lore coverup")
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
	print("/matrix lore diplomacy")
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
	print("/matrix lore disaster")
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
	print("/matrix lore legend")
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
	while rnd.randint(1,6) <= 2:
		possible_achieves = list(intelligence["lore_legends"][3]["Values"].values())
		achieve += f" (or maybe {rnd.choice(possible_achieves)})"
	message = f"Description: {desc}\nFeature: {feature}\nAchievement: {achieve}\nUltimate Fate: {fate}"
	await ctx.respond(message)

file = open('matrices/lore/spells.json')
intelligence["lore_spells"] = json.load(file)
file.close()

@lore_group.command(description="Casts a random Spell")
async def spell(ctx):
	print("/matrix lore spell")
	result = roll_all_matrices(intelligence["lore_spells"])
	level = result[0]
	obscurity = result[1]
	name = result[2]
	if rnd.randint(1,6) <= 2:
		names = rnd.sample(list(intelligence["lore_spells"][2]["Values"].values()),2)
		names[0] = names[0].rsplit(" ", 1)
		names[1] = names[1].rsplit(" ", 1)
		name = names[0][0] + " " + names[1][1]
	feature = result[3]
	effect = result[4]
	message = f"Name: {name}\nEffect: {effect}\nFeature: {feature}\nLevel: {level}\nObscurity: {obscurity}"
	await ctx.respond(message)

bot.add_application_command(matrix_group)

bot.run(token)