'''#############################################################################
Copyright 2017 anonymous authors of N-A-A-C-L submission titled:
    "Location Name Extraction from Targeted Text Streams using Gazetteer-based
        Statistical Language Models"

LNEx code is available online for N-A-A-C-L-2018 review purposes only. Users
    are not allowed to clone, share, or use in any way without permission
    from the authors after the double-blind period.
#############################################################################'''

import json
from tabulate import tabulate
import requests
import elasticsearch

import LNEx as lnex

################################################################################
################################################################################

def read_tweets(dataset):

    # read tweets from file to list
    with open("_Data/Brat_Annotations_Samples/"+dataset+"_50.json") as f:
        tweets = json.load(f)

    tweets = [tweets[id]["text"] for id in tweets]

    return tweets

################################################################################

def init_using_files(dataset):

    with open("_Data/Cached_Gazetteers/"+dataset+"_geo_locations.json") as f:
        geo_locations = json.load(f)

    with open("_Data/Cached_Gazetteers/"+dataset+"_extended_words3.json") as f:
        extended_words3 = json.load(f)

    with open("_Data/Cached_Gazetteers/"+dataset+"_geo_info.json") as f:
        geo_info = json.load(f)

    lnex.initialize_using_files(geo_locations, extended_words3)

    return geo_info

################################################################################

def init_using_elasticindex(bb, cache, dataset):
    lnex.elasticindex(conn_string='localhost:9200', index_name="photon")

    geo_info = None
    while geo_info is None:
        try:
            geo_info = lnex.initialize( bb,
                                        augment=True,
                                        cache=cache,
                                        dataset_name=dataset)
        except elasticsearch.exceptions.ConnectionTimeout:
            pass

    return geo_info

################################################################################

def slice_data(dataset):

    from collections import defaultdict
    from random import shuffle

    with open("_Data/Brat_Annotations/"+dataset.title()+"_annotations.json") as f:
        data = json.load(f)

    lns = set()
    tweets = set()
    for x in data:
        ll = set()
        for y in data[x].keys():
            if y != "text":

                ln = data[x][y]["text"].lower()

                ll.add(ln)

        # if dataset in ll:
        #     continue

        if ll-lns != set():
            lns |= ll
            tweets.add(x)

    keys = list(tweets)

    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)
    shuffle(keys)

    data2 = defaultdict()
    for key in keys[:50]:
        data2[key] = data[key]

    with open("_Data/Brat_Annotations_Samples/"+dataset+"_50.json", 'w') as f:
        json.dump(data2, f)

if __name__ == "__main__":

    bbs = {
        "chennai": [12.74, 80.066986084, 13.2823848224, 80.3464508057],
        "houston": [29.4778611958,-95.975189209,30.1463147381,-94.8889160156],
        "louisiana":[29.4563,-93.3453,31.4521,-89.5276]}

    dataset = "chennai"

    #slice_data(dataset)

    response = ""
    try:
        response = requests.get("http://localhost:9200/_aliases?pretty=1").text
    except:
        pass

    if "photon" in response:
        # follow the instructions in README to setup photon elasitcsearch index
        init_using_elasticindex(bbs[dataset], cache=True, dataset=dataset)
    else:
        # init the system using cached data which is the exact effect you would
        #   get by init using elasitcindex.
        init_using_files(dataset)

    header = [
        "Spotted_Location",
        "Location_Offsets",
        "Geo_Location"]

    for tweet in read_tweets(dataset):
        rows = list()

        for ln in lnex.extract(tweet):
            row = ln[0], ln[1], ln[2].title()
            rows.append(row)

        print tweet
        print "-" * 120
        print tabulate(rows, headers=header)
        print
        print "_" * 120
        print
