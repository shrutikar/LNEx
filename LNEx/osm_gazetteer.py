"""#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################"""

from collections import defaultdict
import unicodedata

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections

import geo_calculations
import gaz_augmentation_and_filtering

################################################################################
################################################################################

__all__ = [ 'set_elasticindex_conn',
            'search_index',
            'extract_text',
            'build_bb_gazetteer']

################################################################################

Elasticsearch()
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

    if not geo_calculations.is_bb_acceptable(
            bb) or bb[0] > bb[2] or bb[1] > bb[3]:

        print "\n##########################################################"
        print "Global ERROR: Bounding Box is too big, choose a smaller one!"
        print "############################################################\n"
        exit()

    connections.create_connection(hosts=[connection_string], timeout=20)

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

    # to search with a scroll
    e_search = Search(index=index_name).query(Q('bool', must=phrase_search))

    try:
        res = e_search.scan()
    except BaseException:
        raise

    return res

################################################################################

def strip_non_ascii(s):
    if isinstance(s, unicode):
        nfkd = unicodedata.normalize('NFKD', s)
        return str(nfkd.encode('ASCII', 'ignore').decode('ASCII'))
    else:
        return s

################################################################################

def extract_names(obj):
    '''Extracts a location name from the different json fields in order
    giving the priority to (en) then (default), and so on.

    Acceptable keys for each json object -----------------------
        city	default	en
        state	default	en
        street	default	en
        name	alt	default	en	int	loc	old	reg
        country	default	en
        '''

    accepted_keys = ['default', 'en', 'alt', 'int', 'loc', 'old', 'reg']

    keys = dir(obj)
    result = list()

    # if there is only one key in the json object, return its value
    if len(keys) == 1:
        name = strip_non_ascii(obj[keys[0]])
        result.append(name)

    else:
        for key in keys:
            if key in accepted_keys:
                name = strip_non_ascii(obj[key])
                result.append(name)

    return result

################################################################################

def build_bb_gazetteer(bb, augment=True):
    '''Builds the gazetteer of a bounding box and agument it in case
    augmentation is activated. '''

    # accepted fields as location names
    location_fields = ["city", "country",
                       "name", "state", "street"]

    geo_info = defaultdict()
    geo_locations = defaultdict(list)

    _id = 0

    for match in search_index(bb):

        _id += 1

        keys = dir(match)

        geo_item = defaultdict()

        if "coordinate" in keys:
            geo_item["point"] = match["coordinate"]
        if "extent" in keys:
            geo_item["extent"] = match["extent"]["coordinates"]

        #######################################################################

        for key in dir(match):

            if key in location_fields:

                try:

                    for name in extract_names(match[key]):

                        if key == "name":

                            # mapping a location name to its geo-info
                            geo_locations[name].append(_id)

                            osm_value = match["osm_value"].lower()

                            geo_info[_id] = { "name": name,
                                              "geo_item": geo_item ,
                                              "osm_value": osm_value}

                        else:
                            geo_locations[name] = list()

                except BaseException:
                    print "extracting names is causing an error"
                    raise

    if augment:
        # 'pullapuram road': set([493])
        new_geo_locations, extended_words3 = \
            gaz_augmentation_and_filtering.augment(geo_locations, geo_info)

    else:
        # Augmentation will mean filtering and augmentation again to be
        #   consistent with the IJCAI paper.
        #new_geo_locations = \
        #    gaz_augmentation_and_filtering.filter_geo_locations(geo_locations)

        new_geo_locations =  {x.lower():set(geo_locations[x])
                                for x in geo_locations}

        extended_words3 = gaz_augmentation_and_filtering.get_extended_words3(
                            new_geo_locations.keys())

    return new_geo_locations, geo_info, extended_words3

################################################################################

if __name__ == "__main__":

    chennai_bb = [12.74, 80.066986084,
                  13.2823848224, 80.3464508057]

    connection_string = '130.108.85.186:9200'
    index_name = "photon_v1"

    set_elasticindex_conn(connection_string, index_name)

    geo_locations, geo_info, extended_words3 = build_bb_gazetteer(chennai_bb)
