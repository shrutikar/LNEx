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

def do_they_overlap(tub1, tub2):
    '''Checks whether two substrings of the tweet overlaps based on their start
    and end offsets.'''

    if tub2[1] >= tub1[0] and tub1[1] >= tub2[0]:
        return True

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

def init_using_files():

    data_folder = os.path.join("..", "_Data")

    with open(data_folder+"/chennai_geo_locations.json") as f:
        geo_locations = json.load(f)

    with open(data_folder+"/chennai_geo_info.json") as f:
        geo_info = json.load(f)

    with open(data_folder+"/chennai_extended_words3.json") as f:
        extended_words3 = json.load(f)

    lnex.initialize_using_files(geo_locations, extended_words3)

    return geo_info

def init_using_elasticindex(bb):

    lnex.elasticindex(conn_string='130.108.85.186:9200', index_name="photon_v1")

    return lnex.initialize(bb, augment=True)

################################################################################

if __name__ == "__main__":

    # chennai flood bounding box
    chennai_bb = [12.74, 80.066986084, 13.2823848224, 80.3464508057]

    #init_using_elasticindex(chennai_bb)

    init_using_files()

    ############################################################################

    filename = "Chennai_annotations.json"

    anns = read_annotations(filename)

    TPs_count = .0
    FPs_count = .0
    FNs_count = .0
    overlaps_count = 0

    for key in anns:

        tweet_lns = set()
        lnex_lns = set()
        tweet_text = ""

        for ann in anns[key]:
            if ann != "text":
                ln = anns[key][ann]

                tweet_lns.add(((int(ln['start_idx']), int(ln['end_idx'])),
                                    ln['type']))
            else:
                tweet_text = anns[key][ann]
                #print tweet_text
                lnex_lns = set([x[1] for x in lnex.extract(tweet_text)])

        #print tweet_lns, [tweet_text[x[0]:x[1]] for x in tweet_lns]
        #print lnex_lns, [tweet_text[x[0]:x[1]] for x in lnex_lns]

        # The location names of type outLoc and ambLoc that the tools should've
        #   not extracted them
        tweet_lns_not_inLocs = set([x[0] for x in tweet_lns if x[1] != 'inLoc'])

        # remove lns that are not inLoc as we already calculated their effect+++
        tweet_lns = set([x[0] for x in tweet_lns]) - tweet_lns_not_inLocs

        # True Positives +++++++++++++++++++++++++++++++++++++++++++++++++++++++
        TPs = tweet_lns & lnex_lns

        TPs_count += len(TPs)

        # Left in both sets ++++++++++++++++++++++++++++++++++++++++++++++++++++
        tweet_lns = tweet_lns - TPs
        lnex_lns = lnex_lns - TPs

        # Find Overlapping Location Names to be counted as 1/2 FPs and 1/2 FNs++
        overlaps = set()
        for x in tweet_lns:
            for y in lnex_lns:
                if do_they_overlap(x, y):
                    overlaps.add(x)
                    overlaps.add(y)

        # add all non-inLoc even if only overlaps as FPs
        FPs_count += len(lnex_lns & tweet_lns_not_inLocs) + \
                     len(overlaps & tweet_lns_not_inLocs)

        # count the number of overlaps that are of type inLoc as 1/2s
        overlaps = overlaps - tweet_lns_not_inLocs
        overlaps_count += len(overlaps)

        # remove the overlapping lns and of type not inLoc from lnex_lns
        lnex_lns = lnex_lns - (tweet_lns_not_inLocs | overlaps)
        # before this line. tweet_lns contains all but the TPs and !inLoc
        tweet_lns = tweet_lns - overlaps

        # False Positives ++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # lnex_lns = all - (TPs and overlaps and !inLoc)
        FPs = lnex_lns - tweet_lns
        FPs_count += len(FPs)

        # False Negatives ++++++++++++++++++++++++++++++++++++++++++++++++++++++
        FNs = tweet_lns - lnex_lns
        FNs_count += len(FNs)

    Precision = TPs_count/(TPs_count + FPs_count + .5 * overlaps_count)
    Recall = TPs_count/(TPs_count + FNs_count + .5 * overlaps_count)

    print Precision
    print Recall
