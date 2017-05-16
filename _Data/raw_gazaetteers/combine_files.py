import json
from collections import defaultdict

gaz_names = ["chennai", "louisiana", "houston"]

for gaz_name in gaz_names:

    with open(gaz_name+"_geonames.json") as f:
        geonames = json.load(f)

    with open(gaz_name+"_osm.json") as f:
        osm = json.load(f)

    with open(gaz_name+"_dbpedia.json") as f:
        dbpedia = json.load(f)

    osm_geonames = list(geonames) + list(osm)
    dbpedia_geonames = list(geonames) + list(dbpedia)
    osm_dbpedia = list(osm) + list(dbpedia)
    all = list(geonames) + list(osm) + list(dbpedia)

    combinations = [("osm", osm), ("dbpedia", dbpedia), ("geonames", geonames),
                    ("osm+dbpedia", osm_dbpedia),
                    ("osm+geonames", osm_geonames),
                    ("dbpedia+geonames", dbpedia_geonames),
                    ("all", all)]

    
    for comb in combinations:

        final = defaultdict(int)

        for ln in comb[1]:

            final[ln] += 1

        with open("Combinations/"+gaz_name+"_"+comb[0]+".json", "w") as f:
            json.dump(final, f)
