import json
from youtubesearchpython import * #pip install youtube-search-python

file = open("matrices/cassettes.json")
cassettes = json.load(file)
file.close()

cassette_links = {}
print("Fetching cassette links...")
for song in cassettes:
	if not '[' in song:
		search = VideosSearch(song,limit=1)
		result = search.result()['result'][0]
		cassette_links[song] = result['link']
		print(f"{song}: {cassette_links[song]}")

print(cassette_links)

with open("matrices/cassette_links.json", "w") as outfile:
	outfile.write(json.dumps(cassette_links,indent=2))