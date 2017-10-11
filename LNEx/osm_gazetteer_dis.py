
"""#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################"""

from collections import defaultdict

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections

import geo_calculations
import gaz_augmentation_and_filtering_dis

import json

################################################################################
################################################################################

__all__ = [ 'set_elasticindex_conn',
            'search_index',
            'extract_text',
            'build_bb_gazetteer']

################################################################################
connection_string = ""
index_name = ""
################################################################################

def set_elasticindex_conn(cs, inn):
    '''Sets the connection string and index name for the elastic index

    connection_string: (e.g, localhost:9200)
    index_name: (e.g., photon) '''


    global connection_string
    global index_name

    connection_string = cs
    index_name = inn

################################################################################

def search_index(bb):
    '''Retrieves the location names from the elastic index using the given
    bounding box'''


    if connection_string == '' or index_name == '':

        print "\n###########################################################"
        print "Global ERROR: Elastic host and port or index name not defined"
        print "#############################################################\n"
        exit()

    if not geo_calculations.is_bb_acceptable(bb) or bb[0] > bb[2] or bb[1] > bb[3]:

        print "\n##########################################################"
        print "Global ERROR: Bounding Box is too big, choose a smaller one!"
        print "############################################################\n"
        exit()

    connections.create_connection(hosts=[connection_string], timeout=20)
    client = Elasticsearch(timeout=60)#, http_auth=('elastic', 'knoesis'))

    phrase_search = [Q({"filtered": {
        "filter": {
            "geo_bounding_box": {
                        "coordinate": {
                            "bottom_left": {
                                "lat": bb[0],
                                "lon": bb[1]
                            },
                            "top_right": {
                                "lat": bb[2],
                                "lon": bb[3]
                            }
                        }
                        }
        },
        "query": {
            "match_all": {}
        }
    }
    })]

    #to search with a scroll
    e_search = Search(using=client, index=index_name).query(Q('bool', must=phrase_search))

    try:
        res = e_search.scan()
    except BaseException:
        raise

    return res

    # Do not work correctly
    # s = Search(using=client, index=index_name) \
    #     .filter("geo_bounding_box", location={
    #         "top_right": {
    #             "lat": bb[2],
    #             "lon": bb[3]
    #         },
    #         "bottom_left": {
    #             "lat": bb[0],
    #             "lon": bb[1]
    #         }
    #     })
    #
    # return s.execute()

################################################################################

def extract_text(obj):
    '''Extracts a location name from the different json fields in order
    giving the priority to (en) then (default), and so on. '''


    keys = dir(obj)

    if len(keys) == 1:
        return obj[keys[0]]

    else:
        if "en" in keys:
            return obj["en"]
        elif "default" in keys:
            return obj["default"]
        elif "reg" in keys:
            return obj["reg"]
        elif "old" in keys:
            return obj["old"]
        elif "alt" in keys:
            return obj["alt"]
        elif "loc" in keys:
            return obj["loc"]
        elif "int" in keys:
            return obj["int"]
        else:
            try:
                return obj[keys[0]]
            except BaseException:
                return obj

################################################################################

def build_bb_gazetteer(bb, augment=True):
    '''Builds the gazetteer of a bounding box and agument it in case
    augmentation is activated. '''

    # accepted fields as location names
    location_fields = ["city", "country",
                       "name", "state", "street"]
    meta_fields = ["osm_key", "osm_value", "postcode"]

    new_geolocations = list()

    # ln > id
    all_geolocations = defaultdict()
    # id > ln
    all_geolocations_invert = defaultdict()

    for match in search_index(bb):

        new_geolocation = { "name": None,
                            "coordinate": None,
                            "extent": None,
                            "country": None,
                            "state": None,
                            "city": None,
                            "street": None,
                            "osm_key": None,
                            "osm_value": None,
                            "postcode": None}

        keys = dir(match)

        if "coordinate" in keys:
            # [lat, lon]
            new_geolocation["coordinate"] = [ match["coordinate"]["lat"],
                                              match["coordinate"]["lon"]]

        if "extent" in keys:
            # [ upper_left_lat, upper_left_lon,
            #   bottom_right_lat, bottom_right_lon ]
            new_geolocation["extent"] = [ match["extent"]["coordinates"][0][1],
                                            match["extent"]["coordinates"][0][0],
                                            match["extent"]["coordinates"][1][1],
                                            match["extent"]["coordinates"][1][0]]

        for meta_field in meta_fields:
            if meta_field in keys:
                new_geolocation[meta_field] = match[meta_field]

        #######################################################################

        for key in keys:

            if key in location_fields:

                try:
                    txt = extract_text(match[key])
                    new_geolocation[key] = txt

                    if txt not in all_geolocations and txt is not None:
                        all_geolocations[txt] = len(all_geolocations.keys())
                        all_geolocations_invert[len(all_geolocations.keys())] = txt

                except BaseException:
                    raise

        # add new geolocation
        new_geolocations.append(new_geolocation)

    ############################################################################

    if augment:
        # 'pullapuram road': set([493])
        new_geo_locations, extended_words3 = \
            gaz_augmentation_and_filtering_dis.augment(all_geolocations)

    else:
        new_geo_locations = \
            gaz_augmentation_and_filtering_dis.filter_geo_locations(all_geolocations)
        extended_words3 = \
            gaz_augmentation_and_filtering_dis.get_extended_words3(
                new_geo_locations.keys())

    return new_geo_locations, geo_info, extended_words3

################################################################################

if __name__ == "__main__":

    #bb = [41.6187434973, -83.7106928844, 41.6245055116, -83.7017216664]
    bb = [41.6210542639,-83.7086427212,41.623699501,-83.7079453468]
    # Chennai
    bb = [12.74, 80.066986084, 13.2823848224, 80.3464508057]

    # connection_string = '130.108.85.186:9200'
    # index_name = "photon_v1"

    connection_string = "localhost:9200"
    index_name = "photon"

    set_elasticindex_conn(connection_string, index_name)

    geo_locations, geo_info, extended_words3 = build_bb_gazetteer(bb)

    print geo_info
