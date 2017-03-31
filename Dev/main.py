"""#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################"""

import os
import json
import unicodedata
from tabulate import tabulate
from collections import defaultdict

import sys
sys.path.append('..')
import LNEx as lnex

################################################################################
################################################################################

with open("../LNEx/_Dictionaries/words.txt") as f:
    words3 = set(f.read().splitlines())

with open("../LNEx/_Dictionaries/world-universities.csv") as f:
    universities = set(f.read().splitlines())

with open("../LNEx/_Dictionaries/airports.json") as f:
    airports = json.load(f)

with open("../_Data/Brat_Annotations/chennai_annotations.json") as f:
    chennai_annotations = json.load(f)

with open("../_Data/Brat_Annotations/louisiana_annotations.json") as f:
    louisiana_annotations = json.load(f)

with open("../_Data/Brat_Annotations/houston_annotations.json") as f:
    houston_annotations = json.load(f)

################################################################################
airports_iata = set()

for airport in airports:
    airports_iata.add(airport['iata'])

################################################################################

for uni in universities:
    if "www" not in uni:
        print uni
