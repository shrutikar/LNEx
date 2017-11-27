"""#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################"""

import json, os
import unicodedata
import numpy as np
import datetime

import LNEx as lnex

from LNEx import geo_calculations

from collections import defaultdict

################################################################################
################################################################################

def strip_non_ascii(s):
    if isinstance(s, unicode):
        nfkd = unicodedata.normalize('NFKD', s)
        return str(nfkd.encode('ASCII', 'ignore').decode('ASCII'))
    else:
        return s

################################################################################

def init_using_elasticindex(bb):
    lnex.elasticindex(conn_string='localhost:9200', index_name="photon")
    return lnex.initialize(bb, augment=True)

################################################################################

def get_all_tweets_and_annotations(gaz_name):

    with open("_Data/Brat_Annotations/"+gaz_name+'_annotations.json') as f:
        data = json.load(f)

    all_tweets_and_annotations = list()

    for key, x in data.iteritems():

        toponyms_and_indexes = list()

        text = x["text"]

        for key, y in x.iteritems():

            # ignore the field which has the tweet text
            if key != "text":

                start_idx = int(y["start_idx"])
                end_idx = int(y["end_idx"])

                toponyms_and_indexes.append((y["type"], (start_idx,end_idx)))

        all_tweets_and_annotations.append((text, toponyms_and_indexes))

    return all_tweets_and_annotations

################################################################################

def absoluteFilePaths(directory):
   for dirpath,_,filenames in os.walk(directory):
       for f in filenames:
           if f.endswith(".json"):
               yield os.path.abspath(os.path.join(dirpath, f))


if __name__ == "__main__":

    #for fname in absoluteFilePaths("_Data/tweets/"):
    #    print fname

    #dataset = "houston"
    #dataset = "chennai"
    #dataset = "lousiana"

    config = {
        "chennai":[ "_Data/tweets/ChennaiFloodRelief_C.json",
                    [12.74, 80.066986084, 13.2823848224, 80.3464508057]],
        "houston":[ "_Data/tweets/Houston_Floods_2016_Twitris_HazardSEES_Knoesis.json",
                    [29.4778611958,-95.975189209,30.1463147381,-94.8889160156]],
        "lousiana":[ "_Data/tweets/Louisiana_Flooding_2016_Twitris_HazardSEES_Knoesis.json",
                     [29.4563,-93.3453,31.4521,-89.5276]]}


    for dataset in config:

        # keep trying if elasticsearch times out!
        geo_info = None
        while geo_info is None:
            try:
                geo_info = init_using_elasticindex(config[dataset][1])
            except elasticsearch.exceptions.ConnectionTimeout:
                pass

        with open(config[dataset][0]) as f:
            tweets = f.readlines()

        tweets_dict = defaultdict()

        for tweet in tweets:
            tweet = json.loads(tweet)

            if(dataset!="chennai"):
                tweet = tweet["_source"]

            created_at = datetime.datetime.fromtimestamp(tweet["date"]/1000.0)
            text = strip_non_ascii(tweet["text"])

            if text not in tweets_dict:

                for x in lnex.extract(text):

                    for geo_point in x[3]:
                        geo_point = geo_info[geo_point]['geo_item']['point']

                        tweets_dict[text] = [created_at, geo_point]


        # spatiotemporal mapping

        distance_threshold = 5# km
        time_interval = 1# hour

        tweet_tweet_spatiotemporal_mapping = defaultdict(lambda: defaultdict(list))

        keys = tweets_dict.keys()
        for i, k1 in enumerate(keys):

            latlong1 = tweets_dict[k1][1]
            latlong1 = (latlong1["lat"], latlong1["lon"])

            for j, k2 in enumerate(keys):
                if i < j:
                    latlong2 = tweets_dict[k2][1]
                    latlong2 = (latlong2["lat"], latlong2["lon"])

                    # in km
                    distance = geo_calculations.get_distance_between_latlon_points(latlong1, latlong2)

                    if distance <= distance_threshold:

                        # temporal bucketing
                        diff = tweets_dict[k1][0] - tweets_dict[k2][0]
                        hours = (diff.seconds) / 3600

                        tweet_tweet_spatiotemporal_mapping[k1][hours].append(k2)
                        tweet_tweet_spatiotemporal_mapping[k2][hours].append(k1)

        tweet_tweet_spatiotemporal_mapping = dict(tweet_tweet_spatiotemporal_mapping)

        with open("_Data/Spatiotemporal/"+dataset+".json", "w") as f:
            json.dump(tweet_tweet_spatiotemporal_mapping, f)

        print "Done!"
