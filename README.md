<!-- ###########################################################################
Copyright 2017 - anonymous authors of NAACL submission titled:
    "Location Name Extraction from Targeted Text Streams using Gazetteer-based
        Statistical Language Models"

LNEx code is available now for review purposes only. The tool will be made open
    after the review process.
#############################################################################-->

[![GitHub release](https://img.shields.io/badge/release-V1.1-orange.svg)]() [![Build Status](https://travis-ci.com/halolimat/LNEx.svg?token=Gg8N5fqoMjLGd4ehzd72&branch=master)](https://travis-ci.com/halolimat/LNEx)
# LNEx: Location Name Extractor #

LNEx extracts location names from targeted text streams.

---

Following are the steps which allows you to setup and start using LNEx.

## For reviewers ##

- Install the requirements in the file ```requirements```
- Change the ```dataset``` name in ```pytest.py``` and run the script to extract Locations from 50 randomly selected tweets from each of our three datasets.
- The output is going to be a list of tuples of the following items:
   - Spotted_Location: a substring of the tweet
   - Location_Offsets: the start and end offsets of the Spotted_Location
   - Gaz-matched_Location: the matched location name from the gazetteer
   - Geo_Info_IDs: the ids of the geo information of the matched Geo_Locations

### Important Files and Directory layout
    .
    ├── _Data                           # where all the cached data resides for testing purposes
    │   ├── Brat_Annotations_Samples    # Contains 50 samples of annotated tweets for the three 
    |   |                                datasets. Tweets will be read from here to test LNEx.
    │   └── Cached_Gazetteers           # Contains 3 cached files for each dataset (to replace 
    |       |                               using elastic index of OSM, if you still want to use 
    |       |                               elastic index please refer to "Querying OpenStreetMap 
    |       |                               Gazetteers" section below)
    |       ├── *_extended_words3.json      # contains the custom stopwords list for each dataset
    |       ├── *_geo_info.json             # contains the geo information (i.e., metadata) from OSM
    │       └── *_geo_locations.json        # contains all augmented and filtered gazetteer locations
    ├── LNEx                # contains the core code-base of LNEx
    │   ├── _Dictionaries   # contains the dictionaries used by LNEx. For more info read the README file
    │   └── tokenizer       # Twokenier code. For more info read the LICENSE file in the folder
    └── pytest.py           # python script to test LNEx


## Querying OpenStreetMap Gazetteers ##

To use the system beyond testing, we will be using a ready to go elastic index of the whole [OpenStreetMap](http://www.osm.org) data provided by [komoot](http://www.komoot.de) as part of their [photon](https://photon.komoot.de/) open source geocoder ([project repo](https://github.com/komoot/photon)). If you don't want to have the full index of OpenStreetMap then you might look for alternative options such as [Pelias OpenStreetMap importer](https://github.com/pelias/openstreetmap) provided by [Mapzen](https://www.mapzen.com/).

Nevertheless, using Photon might be a good idea for users if they have enough space (~ 72 GB) and if they want to use LNEx for many streams along the way (not only for testing). If that sound like something you want to do, follow the steps below:

 - Download the full photon elastic index which is going to allow us to query OSM using a bounding box

   ```sh
   wget -O - http://download1.graphhopper.com/public/photon-db-latest.tar.bz2 | bzip2 -cd | tar x
   ```

 - Now, start photon which starts the elastic index in the background as a service

   ```sh
   wget http://photon.komoot.de/data/photon-0.2.7.jar
   java -jar photon-0.2.7.jar
   ```

 - You should get the Port number information from the log of running the jar, similar to the following:

   ```
   [main] INFO org.elasticsearch.http - [Amelia Voght] bound_address {inet[/127.0.0.1:9201]},
   publish_address {inet[/127.0.0.1:9201]}
   ```

   - this means that elasticsearch is running correctly and listening on:

   ```
   localhost:9201
   ```
   - You can test the index by running the following command:
   ```sh
       curl -XGET 'http://localhost:9201/photon/place/_search/?size=5&pretty=1' -d '{
         "query": {
           "filtered": {
             "filter": {
               "geo_bounding_box" : {
                 "coordinate" : {
                   "top_right" : {
                     "lat" : 13.7940725231,
                     "lon" : 80.4034423828
                   },
                   "bottom_left" : {
                     "lat" : 12.2205755634,
                     "lon" : 79.0548706055
                   }
                 }
               }
             }
           }
         }
      }'
    `
