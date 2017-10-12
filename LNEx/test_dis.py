import osm_gazetteer_dis
import core_dis

bb = [12.74, 80.066986084, 13.2823848224, 80.3464508057]

connection_string = "localhost:9200"
index_name = "photon"

osm_gazetteer_dis.set_elasticindex_conn(connection_string, index_name)

geo_locations, extended_words3 = osm_gazetteer_dis.build_bb_gazetteer(bb)

core_dis.initialize(geo_locations, extended_words3)

print core_dis.extract("I am in new avadi road")
