'''#############################################################################
Copyright 2017 - anonymous authors of NAACL submission titled:
    "Location Name Extraction from Targeted Text Streams using Gazetteer-based
        Statistical Language Models"

LNEx code is available now for review purposes only. The tool will be made open
    after the review process.
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

if __name__ == "__main__":

    bbs = {
        "chennai": [12.74, 80.066986084, 13.2823848224, 80.3464508057],
        "louisiana":[29.4563,-93.3453,31.4521,-89.5276],
        "houston": [29.4778611958,-95.975189209,30.1463147381,-94.8889160156]}

    dataset = "chennai"

    response = ""
    try:
        response = requests.get("http://localhost:9200/_aliases?pretty=1").text
    except:
        pass

    # This will contain the geo information of location names from OSM
    geo_info = None
    if "photon" in response:
        # follow the instructions in README to setup photon elasitcsearch index
        geo_info = init_using_elasticindex(bbs[dataset], cache=True, dataset=dataset)
    else:
        # init the system using cached data which is the exact effect you would
        #   get by init using elasitcindex.
        geo_info = init_using_files(dataset)

    header = [ "Spotted_Location",
               "Location_Offsets",
               "Gaz-matched_Location",
               "Geo_Info_IDs" ]

    for tweet in read_tweets(dataset):
        rows = list()

        for ln in lnex.extract(tweet):

            row = ln[0], ln[1], ln[2].title(), ln[3]
            rows.append(row)

        print tweet
        print "-" * 120
        print tabulate(rows, headers=header)
        print
        print "_" * 120
        print
