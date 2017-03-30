"""#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################"""

import os
import json
import unicodedata
from tabulate import tabulate

import sys
sys.path.append('..')
import LNEx as lnex

################################################################################
################################################################################

def read_annotations(filename):

    filename = os.path.join("..", "_Data/Brat_Annotations", filename)

    # read tweets from file to list
    with open(filename) as f:
        data = json.load(f)

    return data

def write_to_file(filename, data):

    filename = os.path.join("..", "_Data/Brat_Annotations", filename)

    with open(filename, "w") as f:
        json.dump(data, f)

def fix_ann_names(filename):

    anns = read_annotations(filename)

    counter = 0

    for key in anns:
        for ann in anns[key]:
            if ann != "text":

                if anns[key][ann]['type'] == 'Toponym':
                    anns[key][ann]['type'] = 'inLoc'
                elif anns[key][ann]['type'] == 'Imp-Top':
                    anns[key][ann]['type'] = 'ambLoc'
                elif anns[key][ann]['type'] == 'Out-Top':
                    anns[key][ann]['type'] = 'outLoc'
                else:
                    if anns[key][ann]['type'] not in ['inLoc', 'outLoc', 'ambLoc']:
                        print anns[key][ann]['type']
        #counter += 1
        #print counter

    write_to_file(filename, anns)

################################################################################

def init_using_elasticindex(bb):

    lnex.elasticindex(conn_string='130.108.85.186:9200', index_name="photon_v1")

    return lnex.initialize(bb, augment=True)

################################################################################

if __name__ == "__main__":

    # chennai flood bounding box
    chennai_bb = [12.74, 80.066986084, 13.2823848224, 80.3464508057]

    init_using_elasticindex(chennai_bb)

    ############################################################################

    filename = "Chennai_annotations.json"

    anns = read_annotations(filename)

    for key in anns:
        for ann in anns[key]:
            if ann != "text":
                print anns[key][ann]
            else:
                tweet_text = anns[key][ann]
                print tweet_text
                print lnex.extract(tweet_text)
