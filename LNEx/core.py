'''#############################################################################
Copyright 2017 Hussein S. Al-Olimat, hussein@knoesis.org

This software is released under the GNU Affero General Public License (AGPL)
v3.0 License.
#############################################################################'''

import re
import os
import json
import string
import itertools
import collections
from itertools import groupby
from wordsegment import segment
from operator import itemgetter
from collections import defaultdict

# importing local modules
import Language_Modeling
from tokenizer import Twokenize

################################################################################
################################################################################

__all__ = [ 'set_global_env',
            'Stack',
            'Tree',
            'preprocess_tweet',
            'flatten',
            'build_tree',
            'using_split2',
            'findall',
            'align_and_split',
            'extract',
            'do_they_overlap',
            'filterout_overlaps',
            'find_ngrams',
            'remove_non_full_mentions',
            'init_Env',
            'initialize']

################################################################################

printable = set(string.printable)
exclude = set(string.punctuation)

# LNEx global environment
env = None

def set_global_env(g_env):
    '''Sets the global environment at the time of initialization to be used
    module-wide'''

    global env
    env = g_env

################################################################################

class Stack(object):
    '''Stack data structure'''

    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop(0)

    def notEmpty(self):
        return self.items != []

################################################################################

class Tree(object):
    '''Tree data structure used for building the bottom up tree of n-grams'''

    def __init__(self, cargo, tokensIndexes, left=None, right=None, level=1):

        # the data of the node. i.e., the n-gram tokens
        self.cargo = cargo
        # n-gram tokens indexes from the original tweet text
        self.tokensIndexes = tokensIndexes
        # left child of tree node
        self.left = left
        # right child of tree node
        self.right = right
        # unigrams are level 1 -> bigrams are level 2
        self.level = level

    def __str__(self):
        return str(self.cargo)

################################################################################

def preprocess_tweet(tweet):
    '''Preprocesses the tweet text and break the hashtags'''

    # remove retweet handler
    if tweet[:2] == "rt":
        try:
            colon_idx = tweet.index(": ")
            tweet = tweet[colon_idx + 2:]
        except BaseException:
            pass

    # remove url from tweet
    tweet = re.sub(
        r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*',
        '',
        tweet)

    # remove non-ascii characters
    tweet = "".join([x for x in tweet if x in printable])

    # additional preprocessing
    tweet = tweet.replace("\n", " ").replace(" https", "").replace("http", "")

    # extract hashtags to break them -------------------------------------------
    hashtags = re.findall(r"#\w+", tweet)

    # This will contain all hashtags mapped to their broken segments
    # e.g., #ChennaiFlood : {chennai, flood}
    replacements = defaultdict()

    for hashtag in hashtags:

        # keep the hashtag with the # symbol
        _h = hashtag[1:]

        # remove any punctuations from the hashtag and mention
        # ex: Troll_Cinema => TrollCinema
        _h = _h.translate(None, ''.join(string.punctuation))

        # breaks the hashtag
        segments = segment(_h)
        # concatenate the tokens with spaces between them
        segments = ' '.join(segments)

        replacements[hashtag] = segments

    # replacement of hashtags in tweets
    # e.g., if #la & #laflood in the same tweet >> replace the longest first
    for k in sorted(
            replacements,
            key=lambda k: len(
                replacements[k]),
            reverse=True):
        tweet = tweet.replace(k, replacements[k])

    # --------------------------------------------------------------------------

    # padding punctuations
    tweet = re.sub('([,!?():])', r' \1 ', tweet)

    tweet = tweet.replace(". ", " . ").replace("-", " ")

    # shrink blank spaces in preprocessed tweet text to only one space
    tweet = re.sub('\s{2,}', ' ', tweet)

    # remove trailing spaces
    tweet = tweet.strip()

    return tweet

################################################################################

def flatten(l):
    '''Flattens a list of lists to a list.
    Based on Cristian answer @ http://stackoverflow.com/questions/2158395'''

    for el in l:
        if isinstance(el, collections.Iterable) and not \
           isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el

################################################################################

def build_tree(glm, ts):
    ''' Build a bottom-up tree of valid ngrams using the gazetteer langauge
    model (glm) and the tweet segment (ts)'''

    # dictionary of valid n-grams
    valid_n_grams = defaultdict(float)

    # store tree nodes in a stack
    nodes = Stack()

    # init leaf nodes from the unigrams
    for index, token in enumerate(ts):
        nodes.push(
            Tree( cargo=token,
                  tokensIndexes=set([index]),
                  left=None,
                  right=None,
                  level=1))

    node1 = None
    node2 = None

    while nodes.notEmpty():

        if node1 is None:
            node1 = nodes.pop()
            node2 = nodes.pop()

        else:
            node1 = node2
            node2 = nodes.pop()

        # process nodes of similar n-gram degree/level
        if node1.level == node2.level:

            _node2 = node2

            # if there is a common child take only the right child
            if node1.right == node2.left and node1.right is not None:
                _node2 = node2.right

            tokens_list = list()

            # find valid n-grams from the cartisian product of two tree nodes
            for i in itertools.product(node1.cargo, _node2.cargo):

                # flatten the list of lists
                flattened = list(flatten(i))

                # remove consecutive duplicates
                final_list = map(itemgetter(0), groupby(flattened))

                # prune based on the probability from the language model
                p = " ".join(final_list)
                p = p.strip()

                # the probability of a phrase p calculated by the language model
                score = glm.phrase_probability(p)

                # if an n-gram is valid then add it to the dictionary
                if score > 0:

                    # e.g., ('avadi', 'rd', (4, 5))
                    valid_n_gram = tuple(final_list) + \
                                    (tuple(set(node1.tokensIndexes | \
                                    _node2.tokensIndexes)),)

                    # e.g., ('avadi', 'rd', (4, 5)) 5.67800416892e-05
                    valid_n_grams[valid_n_gram] = score

                    # the cargo of the node
                    tokens_list.append(final_list)

            # create higher level nodes and store them in the stack
            nodes.push(
                Tree(
                    tokens_list,
                    (node1.tokensIndexes | node2.tokensIndexes),
                    node1,
                    node2,
                    (node1.level + node2.level)))

    return valid_n_grams

################################################################################

def using_split2(line, _len=len):
    '''Tokenizes the tweet and retain the offsets of each token
    Based on aquavitae answer @ http://stackoverflow.com/questions/9518806/'''

    words = Twokenize.tokenize(line)
    index = line.index
    offsets = []
    append = offsets.append
    running_offset = 0
    for word in words:
        word_offset = index(word, running_offset)
        word_len = _len(word)
        running_offset = word_offset + word_len
        append((word, word_offset, running_offset - 1))
    return offsets

################################################################################

#
def findall(p, s):
    '''Yields all the positions of the pattern p in the string s.
    Based on AkiRoss answer @ http://stackoverflow.com/questions/4664850'''

    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)

################################################################################

def align_and_split(raw_string, preprocessed_string):
    '''Aligns the offsets of the preprocessed tweet with the raw tweet to retain
    original offsets when outputing spotted location names'''

    tokens = list()

    last_index = 0

    for token in using_split2(preprocessed_string):

        matches = [(raw_string[i:len(token[0]) + i], i, len(token[0]) + i - 1)
                   for i in findall(token[0], raw_string)]

        for match in matches:
            if match[1] >= last_index:
                last_index = match[1]
                tokens.append(match)
                break

    return tokens

################################################################################
'''
NOTE: This is talking care of some of the errors caused by the aligment
      function. Example error: @chennairains #chennairainshelp
      > when extracting chennai from the hashtag the alignment function is
        getting the indexes of chennai from the mention that precedes it.

        tweet: 'Update:Water level in Sai Nagar,Thoraipakam is above the shoulder. Boats needed to rescue people from there @ChennaiRains #ChennaiRainsHelp'
'''
def remove_mentions(tweet):

    # remove all mentions
    mentions = re.findall(r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)", tweet)

    for mention in mentions:
        mention = "@"+mention
        tweet = tweet.replace(mention, "#"*len(mention))

    return tweet

################################################################################
################################################################################

def extract(tweet):
    '''Extracts all location names from a tweet.

        returns a list of the following 4 items tuple:
            tweet_mention, mention_offsets, geo_location, geo_info_id

            tweet_mention:   is the location mention in the tweet
                             (substring retrieved from the mention offsets)

            mention_offsets: a tuple of the start and end offsets of the LN

            geo_location:    the matched location name from the gazetteer.
                             e.g., new avadi rd > New Avadi Road

            geo_info_id:     contains the attached metadata of all the matched
                             location names from the gazetteer '''

    # --------------------------------------------------------------------------
    # check if environment was correctly initialized
    if env == None:
        print "\n##################################################"
        print "Global ERROR: LNEx environment must be initialized"
        print "##################################################\n"
        exit()

    # --------------------------------------------------------------------------

    #will contain for example: (0, 11): [(u'new avadi road', 3)]
    valid_ngrams = defaultdict(list)

    # we will call a tweet from now onwards a query
    query = str(tweet.lower())

    query = remove_mentions(query)

    preprocessed_query = preprocess_tweet(query)

    query_tokens = align_and_split(query, preprocessed_query)

    # --------------------------------------------------------------------------
    # prune the tree of locations based on the exisitence of stop words
    # by splitting the query into multiple queries
    query_splits = Twokenize.tokenize(query)
    stop_in_query = env.stopwords_notin_gazetteer & set(query_splits)

    # if tweet contains the following then remove them from the tweet and
    # split based on their presence:
    stop_in_query = stop_in_query | set(
        ["[", "]", ".", ",", "(", ")", "!", "?", ":", "<", ">", "newline"])

    # remove stops from query
    for index, token in enumerate(query_tokens):
        if token[0] in stop_in_query:
            query_tokens[index] = ()

    # combine consecutive tokens in a query as possible location names
    query_filtered = list()
    candidate_location = {"tokens": list(), "offsets": list()}

    for index, token in enumerate(query_tokens):

        if len(token) > 0:
            candidate_location["tokens"].append(token[0].strip())
            candidate_location["offsets"].append((token[1], token[2]))

        elif candidate_location != "":
            query_filtered.append(candidate_location)
            candidate_location = {"tokens": list(), "offsets": list()}

        # if I am at the last token in the list
        # ex: "new avadi road" then it wont be added unless I know that this is
        #        the last token then append whatever you have
        if index == len(query_tokens) - 1:
            query_filtered.append(candidate_location)

    ##########################################################################

    # start the core extraction procedure using the bottom up trees
    for sub_query in query_filtered: # ----------------------------------- for I

        sub_query_tokens = sub_query["tokens"]
        sub_query_offsets = sub_query["offsets"]

        # ignore splits of size 0
        if len(sub_query_tokens) == 0:
            continue

        # expand tokens in sub_query_tokens to vectors
        for idx, token in enumerate(sub_query_tokens): # ---------------- for II

            token_edited = ''.join(ch for ch in token if ch not in exclude)

            # if the token is for sure misspilled
            if  token not in env.extended_words3 and \
                token_edited not in env.extended_words3:

                sub_query_tokens[idx] = [token]

                # expand the token into the full name without abbreviations.
                # Ex=> rd to road
                token_exp = env.streets_suffixes_dict.get(token)
                if token_exp and token_exp not in sub_query_tokens[idx]:
                    sub_query_tokens[idx].append(token_exp)

            # do not expand the word if it is not misspilled
            else:

                loc_name = sub_query_tokens[idx]

                sub_query_tokens[idx] = [sub_query_tokens[idx]]

                # expand the token into the full name without abbreviations.
                # Ex=> rd to road
                token_exp = env.streets_suffixes_dict.get(loc_name)
                if token_exp and token_exp not in sub_query_tokens[idx]:
                    sub_query_tokens[idx].append(token_exp)

                sub_query_tokens[idx] = list(set(sub_query_tokens[idx]))


            # ------------------------------------------------------------------

            # Expand a token to its abbreviation and visa versa
            exp_words = list()
            for x in sub_query_tokens[idx]:
                if x in set(env.osm_abbreviations):
                    exp_words += env.osm_abbreviations[x]

            sub_query_tokens[idx] += exp_words

        # ----------------------------------------------------------- End for II

        valid_n_grams = defaultdict(float)

        # this would build the bottom up tree of valid n-grams
        # if the query contains more than one vector then build the tree
        if len(sub_query_tokens) > 1:

            valid_n_grams = build_tree(env.glm, sub_query_tokens)

            # imporoving recall by adding unigram location names ++++++++++++++

            already_assigned_locations_tokens = list()

            for valid_n_gram in valid_n_grams:
                for token_index in valid_n_gram[-1]:
                    already_assigned_locations_tokens.append(token_index)

            for idx, item in enumerate(sub_query_tokens):
                if idx not in already_assigned_locations_tokens:

                    for token_match in item:

                        if token_match in env.gazetteer_unique_names_set:
                            valid_n_grams[(token_match, (idx,))] = 1

        # when the size of the subquery is only one token
        elif len(sub_query_tokens) == 1:

            for token in sub_query_tokens[0]:
                valid_n_grams[(token, (0,))] = env.glm.phrase_probability(token)

        # ----------------------------------------------------------------------

        for valid_n_gram in valid_n_grams:

            # sort the offsets
            # e.g., valid_n_gram = ("token", "token", (index-1, index-2))
            offsets = sorted([sub_query_offsets[token_idx]
                              for token_idx in valid_n_gram[-1]])

            # the start index of the first token
            start_idx = offsets[0][0]
            # the end index of the last token
            end_idx = offsets[-1][1]

            # contains the matched location name from cartisian product
            mached_ln = " ".join(valid_n_gram[:-1])

            index_tub = (start_idx, end_idx + 1)

            number_of_tokens = len(valid_n_gram[:-1])

            valid_ngrams[index_tub].append(
                (mached_ln, number_of_tokens))

        # ----------------------------------------------------------------------

        # if length is zero means no more than unigrams were found in the query
        if len(valid_n_grams) == 0:

            for index, value in enumerate(sub_query_tokens):

                max_prob_reco = ("", 0)

                for y in value: # ----------------------------------------------

                    # if the unigram is an actual full location name
                    if y in env.gazetteer_unique_names_set:
                        if max_prob_reco[1] < len(
                                env.gazetteer_unique_names[y]):
                            max_prob_reco = (
                                y, len(env.gazetteer_unique_names[y]))

                # --------------------------------------------------------------

                # this is the solution for only one grams found in the sentence
                if max_prob_reco[1] > 0:

                    # here we add the unigram toponyms found in query

                    tub_1 = sub_query_offsets[index][0]
                    tub_2 = sub_query_offsets[index][1] + 1

                    # tuble would have: ((start_idx,end_idx),prob)

                    tub = (tub_1, tub_2)

                    mached_ln = max_prob_reco[0]

                    number_of_tokens = mached_ln.count(" ") + 1

                    valid_ngrams[tub].append(
                        (mached_ln, number_of_tokens))

    # ---------------------------------------------------------------- end for I

    filtered_n_grams = filterout_overlaps(valid_ngrams)

    # set of: ((offsets), probability), full_mention)
    location_names_in_query = remove_non_full_mentions( filtered_n_grams,
                                                        valid_ngrams,
                                                        query_tokens)

    # --------------------------------------------------------------------------

    result = list()

    for ln in location_names_in_query:

        mention_offsets = (ln[0][0], ln[0][1])

        tweet_mention = tweet[mention_offsets[0]:mention_offsets[1]]
        geo_location = ln[1]
        geo_info_ids = env.gazetteer_unique_names[ln[1]]

        result.append(( tweet_mention,
                        mention_offsets,
                        geo_location,
                        geo_info_ids))

    return result

################################################################################

def do_they_overlap(tub1, tub2):
    '''Checks whether two substrings of the tweet overlaps based on their start
    and end offsets.'''

    if tub2[1] >= tub1[0] and tub1[1] >= tub2[0]:
        return True

################################################################################

def filterout_overlaps(valid_ngrams):
    '''Filters the overlapping ngrams from the tree of valid ngrams'''

    full_location_names = list()
    lengths = list()

    # this will keep a list of full location names and their lengths
    for ngram_offsets in valid_ngrams:
        ngram = valid_ngrams[ngram_offsets]

        for ngram_tuple in ngram:
            if ngram_tuple[0] in env.gazetteer_unique_names_set:
                full_location_names.append(ngram_offsets)
                lengths.append(ngram_tuple[1])
                break

    ############################################################################
    # remove the overlapping full location names preferring the longest and
    #   will keep both if they have the same length

    original_set = set(valid_ngrams.keys())

    for idx, item in enumerate(full_location_names):
        for y in range(idx + 1, len(full_location_names)):

            offsets_1 = item
            offsets_2 = full_location_names[y]

            try:
                # if they overlap then the shorter is removed
                if do_they_overlap(offsets_1, offsets_2):

                    if lengths[idx] > lengths[y]:
                        original_set.remove(full_location_names[y])

                    # NOTE: this was changed since the IJCAI submission to leave
                    #       the ones of equal length
                    elif lengths[idx] < lengths[y]:
                        original_set.remove(item)

            except BaseException:
                pass

    ############################################################################
    # Now, we will remove all the ngrams that overlaps with the longest location
    #   names and leaving the rest to be decided in the next step of extracting
    #   only full location names from non-overlapping ngrams (including the
    #   ones we already know are full location names).

    longest_full_location_names = original_set & set(full_location_names)

    final_set = set(original_set)

    for ln in longest_full_location_names:
        for ngram in original_set:

            if ln != ngram:

                if do_they_overlap(ln, ngram):

                    try:
                        final_set.remove(ngram)
                    except BaseException:
                        pass

    return final_set

################################################################################

def find_ngrams(input_list, n):
    '''Generates grams of length (n) from the list of unigrams (input_list)'''

    return zip(*[input_list[i:] for i in range(n)])

################################################################################

def remove_non_full_mentions(filtered_n_grams, valid_ngrams, query_tokens):
    '''Removes all valid ngrams but non full mention location names as the final
    step in this system'''

    final_set = set()

    for ngram_offsets in filtered_n_grams:
        ngram = valid_ngrams[ngram_offsets]

        # add ngrams to the final set of location names if they are full
        # location names.
        full_ln = False

        for ngram_tuple in ngram:
            if ngram_tuple[0] in env.gazetteer_unique_names_set:
                final_set.add((ngram_offsets, ngram_tuple[0]))
                full_ln = True
                break

        # if the ngram is not a full location name then search inside it for
        # a full location name. e.g., The Louisiana > Louisiana
        if not full_ln:

            # keep track of the token offsets
            ngram_min_range = ngram_offsets[0]
            ngram_max_range = (ngram_offsets[1]) - 1

            for ngram_tuple in ngram:

                unigrams = ngram_tuple[0].split()

                # generate all possible grams from the list of unigrams
                for new_ngram_len in range(len(unigrams) - 1, -1, -1):

                    # search the new ngram for a possible full location name
                    for new_ngram in find_ngrams(unigrams, new_ngram_len + 1):

                        candidate_ln = " ".join(new_ngram)

                        # if it is a full mention then get the offsets from the
                        # query_tokens list
                        if candidate_ln in env.gazetteer_unique_names_set:

                            # get the indecies from the original query tokens
                            for query_token in query_tokens:

                                # TODO: check in the old code why empty tuples
                                #   are not removed
                                # if it is an empty tuple.. skip
                                if query_token == tuple():
                                    continue

                                # NOTE: apparently at the time of development
                                # and testing I had a good reason for having the
                                # first two conditions. They can be removed
                                # in the future.
                                if ngram_min_range <= query_token[1] and \
                                   ngram_max_range >= query_token[2] and \
                                   candidate_ln == query_token[0]:

                                    t = ((query_token[1], query_token[2]+1),
                                        candidate_ln)

                                    final_set.add(t)

    return final_set

################################################################################

class init_Env(object):
    '''Where all the gazetteer data, dictionaries and language model resides'''

    def __init__(self, geo_locations, extended_words3):
        '''Initialized the system using the location names and list of english
        words (words3)'''

        ###################################################
        # OSM abbr dictionary
        ###################################################

        dicts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        "_Dictionaries/")

        fname = dicts_dir + "osm_abbreviations.csv"

        # read lines to list
        with open(fname) as f:
            lines = f.read().splitlines()

        self.osm_abbreviations = defaultdict(list)

        for x in lines:
            line = x.split(",")

            # apartments > apts
            self.osm_abbreviations[line[0]].append(line[1])
            # apartments > apts.
            self.osm_abbreviations[line[0]].append(line[1] + ".")

            # apts > apartments
            self.osm_abbreviations[line[1]].append(line[0])
            # apts. > apartments
            self.osm_abbreviations[line[1] + "."].append(line[0])

        ########################################################################

        self.gazetteer_unique_names = geo_locations

        self.gazetteer_unique_names_set = \
                    set(self.gazetteer_unique_names.keys())

        # NOTE BLACKLIST CODE GOES HERE

        # this list has all the english words in addition to the names
        # from the combined gazetteer, any word not in the list is
        # considered misspilled.

        self.extended_words3 = extended_words3
        self.extended_words3 = set(self.extended_words3)

        ########################################################################

        streets_suffixes_dict_file = dicts_dir + "streets_suffixes_dict.json"

        with open(streets_suffixes_dict_file) as f:

            self.streets_suffixes_dict = json.load(f)

        ########################################################################

        # gazetteer-based language model
        self.glm = Language_Modeling.GazBasedModel(geo_locations)

        ########################################################################

        # list of unigrams
        unigrams = self.glm.unigrams["words"].keys()

        self.stopwords_notin_gazetteer = set(
            self.extended_words3) - set(unigrams)

################################################################################

class init_Env_Files(object):
    '''Where all the gazetteer data, dictionaries and language model resides'''

    def __init__(self, gaz_name, gaz_comb_name):
        '''Initialized the system using the location names and list of english
        words (words3)'''

        data_dir = '/home/hussein/code/github/LNEx/_Data/CombinedAugmentedGazetteers/'

        ###################################################
        # OSM abbr dictionary
        ###################################################

        dicts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        "_Dictionaries/")

        fname = dicts_dir + "osm_abbreviations.csv"

        # read lines to list
        with open(fname) as f:
            lines = f.read().splitlines()

        self.osm_abbreviations = defaultdict(list)

        for x in lines:
            line = x.split(",")

            # apartments > apts
            self.osm_abbreviations[line[0]].append(line[1])
            # apartments > apts.
            self.osm_abbreviations[line[0]].append(line[1] + ".")

            # apts > apartments
            self.osm_abbreviations[line[1]].append(line[0])
            # apts. > apartments
            self.osm_abbreviations[line[1] + "."].append(line[0])

        ########################################################################

        combined_unique_names_file = data_dir + gaz_name + "_language_model_"+ \
                                    gaz_comb_name+"_unique_names_augmented.json"

        with open(combined_unique_names_file) as data_file:
            self.gazetteer_unique_names = json.load(data_file)

        if "" in self.gazetteer_unique_names:
            self.gazetteer_unique_names.pop("", None)

        # since geo_loc has the geo_info in an array and in this old code we
        #   don't have geo_info, I am adding dummy values in an array for the
        #   same length of the geo_info
        self.gazetteer_unique_names = {x:[1]*self.gazetteer_unique_names[x]
                                        for x in self.gazetteer_unique_names}

        self.gazetteer_unique_names_set = \
                    set(self.gazetteer_unique_names.keys())

        # NOTE BLACKLIST CODE GOES HERE

        # this list has all the english words in addition to the names
        # from the combined gazetteer, any word not in the list is
        # considered misspilled.

        fname = data_dir+gaz_name+"_"+gaz_comb_name+"_words3_extended.txt"
        with open(fname) as f:

            self.extended_words3 = f.read().splitlines()
            self.extended_words3 = set(self.extended_words3)

        ########################################################################

        streets_suffixes_dict_file = dicts_dir + "streets_suffixes_dict.json"

        with open(streets_suffixes_dict_file) as f:

            self.streets_suffixes_dict = json.load(f)

        ########################################################################

        # gazetteer-based language model
        self.glm = Language_Modeling.GazBasedModel(self.gazetteer_unique_names)

        ########################################################################

        # list of unigrams
        unigrams = self.glm.unigrams["words"].keys()

        self.stopwords_notin_gazetteer = set(
            self.extended_words3) - set(unigrams)

################################################################################

def initialize(geo_locations, extended_words3):
    '''Initializing the system here'''

    #print "Initializing LNEx ..."
    g_env = init_Env(geo_locations, extended_words3)
    set_global_env(g_env)
    #print "Done Initialization ..."

################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
# Multi combination evaluation code below
################################################################################
################################################################################

def findOccurences(s, ch):
    return [i for i, letter in enumerate(s) if letter == ch]

def get_gaz_combinations():

    data_dir = '/home/hussein/code/github/LNEx/_Data/CombinedAugmentedGazetteers/'

    gaz_combs = set()

    for root, dirs,files in os.walk(data_dir, topdown=True):
        for name in files:

            if "words3_extended" in name or "foursquare" in name:
                continue

            filename = os.path.join(root, name)

            indexes = findOccurences(filename, "_")

            gaz_comb = filename[indexes[3]+1:indexes[4]]

            gaz_combs.add(gaz_comb)

    return gaz_combs

def read_annotations(gaz_name):
    gaz_name += "_annotations.json"
    filename = "/home/hussein/code/github/LNEx/_Data/Brat_Annotations/"+gaz_name

    # read tweets from file to list
    with open(filename) as f:
        data = json.load(f)

    return data

def run_multicomb_evaluations():

    gaz_names = ["louisiana"]
    gaz_combs = get_gaz_combinations()#["wikipedia"]

    for gaz_name in gaz_names:

        anns = read_annotations(gaz_name)

        for gaz_comb in gaz_combs:

            # init environment using gaz combination ###########################
            g_env = init_Env_Files(gaz_name, gaz_comb)
            set_global_env(g_env)
            ####################################################################

            TPs_count = .0
            FPs_count = .0
            FNs_count = .0
            overlaps_count = 0

            fns = defaultdict(int)

            for key in anns:

                tweet_lns = set()
                lnex_lns = set()
                tweet_text = ""

                for ann in anns[key]:
                    if ann != "text":
                        ln = anns[key][ann]

                        tweet_lns.add(((int(ln['start_idx']),
                                        int(ln['end_idx'])),
                                        ln['type']))
                    else:
                        tweet_text = anns[key][ann]
                        #print tweet_text
                        lnex_lns = set([x[1] for x in extract(tweet_text)])

                # The location names of type outLoc and ambLoc that the tools
                #   should've not extracted them
                tweet_lns_not_inLocs = set([x[0] for x in tweet_lns
                                                if x[1] != 'inLoc'])
                # add all lns than are of types other than inLoc as FPs
                FPs_count += len(lnex_lns & tweet_lns_not_inLocs)

                # remove LNs that are not inLoc
                tweet_lns = set([x[0] for x in tweet_lns]) - tweet_lns_not_inLocs
                lnex_lns -= tweet_lns_not_inLocs

                # True Positives +++++++++++++++++++++++++++++++++++++++++++++++
                TPs = tweet_lns & lnex_lns

                TPs_count += len(TPs)

                # Left in both sets ++++++++++++++++++++++++++++++++++++++++++++
                tweet_lns -= TPs
                lnex_lns -= TPs

                # Find Overlapping LNs to be counted as 1/2 FPs and 1/2 FNs++
                overlaps = set()
                for x in tweet_lns:
                    for y in lnex_lns:
                        if do_they_overlap(x, y):
                            overlaps.add(x)
                            overlaps.add(y)

                # count all overlapping extractions with non-inLoc as FPs
                FPs_count += len(overlaps & tweet_lns_not_inLocs)

                # count the number of overlaps that are of type inLoc as 1/2s
                overlaps = overlaps - tweet_lns_not_inLocs
                overlaps_count += len(overlaps)

                # remove the overlapping lns from lnex_lns and tweet_lns
                lnex_lns -= overlaps
                tweet_lns -= overlaps

                # False Positives ++++++++++++++++++++++++++++++++++++++++++++++
                # lnex_lns = all - (TPs and overlaps and !inLoc)
                FPs = lnex_lns - tweet_lns
                FPs_count += len(FPs)

                # False Negatives ++++++++++++++++++++++++++++++++++++++++++++++
                FNs = tweet_lns - lnex_lns
                FNs_count += len(FNs)

                '''if len(FNs) > 0:
                    for x in [tweet_text[x[0]:x[1]] for x in FNs]:
                        fns[x.lower()] += 1'''

                ################################################################
                #print TPs_count, FPs_count, FNs_count, overlaps_count
                #print "#"*100

            '''
            since we add 2 lns one from lnex_lns and one from tweet_lns if they
            overlap the equation of counting those as 1/2 FPs and 1/2 FNs is
            going to be:
                overlaps_count x
                    1/2 (since we count twice) x
                        1/2 (since we want 1/2 of all the errors made)
            '''
            Precision = TPs_count/(TPs_count + FPs_count + \
                            .5 * .5 * overlaps_count)
            Recall = TPs_count/(TPs_count + FNs_count + \
                            .5 * .5 * overlaps_count)
            F_Score = (2 * Precision * Recall)/(Precision + Recall)

            print "\t".join([gaz_comb, str(Precision),
                                str(Recall), str(F_Score)])

if __name__ == "__main__":
    run_multicomb_evaluations()
