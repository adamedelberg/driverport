# -*- coding: utf-8 -*-
"""
MongoDB Database Driver

    This class contains all the accessor methods for manipulating MongoDB databases.

    For a single server, the default host is assigned to: localhost, port 27017. For further adjustments to the
    database connector please see config.py.
"""

import json
import time
import logging
import pymongo
from pymongo import MongoClient
from pymongo import errors
import os
import config

logger = logging.getLogger(__name__)

# set defaults
DATABASE = config.database
DATABASE_INDEXED = config.indexed_database
COLLECTION = config.collection
DOCUMENT = config.document
DOCUMENT_SINGLE = config.single
DATABASE_COLLECTION = config.collection_database
HOST = config.host_mongo
PORT = config.port_mongo


def connect(host, port):
    """
    Connect to the MongoDB Server on <host>:<port>

    :param host: see configs - [default = 'localhost']
    :param port: see configs - [default = 27017]
    :return: MongoClient object
    """

    global client
    try:
        client = MongoClient(host, port)
        logger.debug("CONNECTED ON: {}:{}".format(client.HOST, client.PORT))
    except pymongo.errors.ConnectionFailure as code:
        logger.warning("PyMongo Error: {}".format(code))
    except pymongo.errors.PyMongoError as code:
        logger.warning("PyMongo Error: {}".format(code))
    return client


def drop_database(database):
    """
    Safe drop database using remove

    :param database:
    :return:
    """
    try:
        client = MongoClient(HOST, PORT)
        db = client.get_database(database)
        coll = db.get_collection(COLLECTION)
        coll.remove({})

        # connect(HOST, PORT).drop_database(database)
        # client.drop_database(database)
        logger.debug("DROPPED {}!".format(database))

    except pymongo.errors as e:
        logger.warning("DROP ERROR: " + e)


def create_indexes(database):
    """
    Create indexes in given database

    :param database: the database where indexes will be created
    :return:
    """


    try:
        coll = database.get_collection(COLLECTION)
        coll.create_index([("id", pymongo.ASCENDING)], name='tweet_id_index')
        coll.create_index([("user.id", pymongo.ASCENDING)], name='user.id_index')
        coll.create_index([("user.followers_count", pymongo.ASCENDING)], name='user.follower_count_index')
        coll.create_index([("user.friends_count", pymongo.ASCENDING)], name='user.friends_count_index')
        coll.create_index([("location", pymongo.ASCENDING)], name='location_index')
    except pymongo.errors.CollectionInvalid as code:
        logger.warning("PyMongo Error: {}".format(code))
    except pymongo.errors.PyMongoError as code:
        logger.warning("PyMongo Error: {}".format(code))


def bulk_insert(path, indexed, drop_on_start, drop_on_exit=False, write_concern=1):
    """
    Bulk insert into MongoDB database

    :param path:
    :param indexed: insert into benchmark_db_indexed [default = False]
    :param drop_on_start:
    :param drop_on_exit:
    :param write_concern:
    :return:
    """


    # check drop flag
    if drop_on_start: drop_database(DATABASE)

    # connect to correct database:
    db = connect(HOST, PORT).get_database(DATABASE)
    coll = db.get_collection(COLLECTION, write_concern=pymongo.WriteConcern(w=write_concern))

    document = open(path, 'r')

    docs = []

    for doc in document:
        docs.append(json.loads(doc))

    start = time.time()
    coll.insert_many(docs)
    run = time.time() - start

    if indexed:
        db2 = connect(HOST, PORT).get_database(DATABASE_INDEXED)
        coll2 = db2.get_collection(COLLECTION)
        drop_database(DATABASE_INDEXED)
        create_indexes(db2)
        coll2.insert_many(docs)

    size = "{}MB".format(round(os.path.getsize(path) / 1024 / 1024, 2))
    logger.info("{} seconds to bulk insert {}, indexed={}".format(run, size, indexed))

    # check drop flag on exit
    if drop_on_exit: drop_database(DATABASE)

    return run, size


def bulk_insert_collections(path, indexed, drop_on_start, drop_on_exit=False, write_concern=1):
    """

    :param path:
    :param indexed:
    :param drop_on_start:
    :param drop_on_exit:
    :param write_concern:
    :return:
    """
    if drop_on_start: drop_database(DATABASE_COLLECTION)

    db = connect(HOST, PORT).get_database(DATABASE_COLLECTION)
    user_collection = db.get_collection('users', write_concern=pymongo.WriteConcern(w=write_concern))
    tweet_collection = db.get_collection('tweets', write_concern=pymongo.WriteConcern(w=write_concern))

    if indexed:
        tweet_collection.create_index([("id", pymongo.ASCENDING)], name='tweet.id index', unique=True)
        user_collection.create_index([("id", pymongo.ASCENDING)], name='user.id index', unique=True)

    execution_time = 0

    document = open(path, 'r')

    users = []
    tweets = []

    for doc in document:
        d = json.loads(doc)
        users.append(d['user'])
        # add the user id to the tweet collection
        d['user_id'] = d['user']['id']
        del d['user']
        tweets.append(d)

    start_time = time.time()

    user_collection.insert_many(users)
    tweet_collection.insert_many(tweets)

    execution_time += time.time() - start_time

    size = "{}MB".format(round(os.path.getsize(DOCUMENT) / 1024 / 1024, 2))
    logger.info("{} seconds to bulk insert into collections {}".format(execution_time, size))

    if drop_on_exit: drop_database(DATABASE)

    return execution_time, size


def bulk_insert_one(path, drop_on_start, drop_on_exit=False, write_concern=1):
    """

    :param path:
    :param drop_on_start:
    :param drop_on_exit:
    :param write_concern:
    :return:
    """

    # drop database
    if drop_on_start: drop_database(DATABASE)

    db = connect(HOST, PORT).get_database(DATABASE)
    coll = db.get_collection(COLLECTION, write_concern=pymongo.WriteConcern(w=write_concern))

    document = open(path, 'r')

    start = time.time()
    for doc in document:
        coll.insert_one(json.loads(doc))
    run = time.time() - start

    size = "{}MB".format(round(os.path.getsize(DOCUMENT) / 1024 / 1024, 2))
    logger.info("{} seconds to bulk insert one {}".format(run, size))

    if drop_on_exit: drop_database(DATABASE)

    return run, size


def insert_one(path, indexed, drop_on_start, drop_on_exit=False, write_concern=1):
    """
    Inserts a single document to the benchmark_db database

    :param path:
    :param indexed:
    :param drop_on_start:
    :param drop_on_exit:
    :param write_concern:
    :return:

       Parameters:
           indexed          - insert with indexes
           doc_path         - database document path
           drop_on_start    - drop database before query
           drop_on_exit     - drop database after query

       Returns:
           insert_one_time  - execution time for one insert
           bulk_insert_time - execution time for bulk insert
           doc_size         - size of the inserted document
           db_size          - size of the database"""

    if indexed:
        database = DATABASE_INDEXED
    else:
        database = DATABASE

    if drop_on_start: drop_database(database)

    db = connect(HOST, PORT).get_database(DATABASE)
    coll = db.get_collection(COLLECTION, write_concern=pymongo.WriteConcern(w=write_concern))

    d1 = open(path, 'r')
    docs = []

    for doc in d1:
        docs.append(json.loads(doc))


    d2 = open(DOCUMENT_SINGLE, 'r')
    single_doc = json.load(d2)

    start = time.time()
    coll.insert_many(docs)
    bulk_insert_time = time.time() - start

    start = time.time()
    coll.insert_one(single_doc)
    insert_one_time = time.time() - start

    doc_size = "{}MB".format(round(os.path.getsize(DOCUMENT_SINGLE) / 1024 / 1024, 2))
    db_size = "{}MB".format(round(os.path.getsize(DOCUMENT) / 1024 / 1024, 2))

    logger.info("{} seconds to insert one indexed={} db_size={} doc_size={}".format(insert_one_time, indexed, db_size,
                                                                                    doc_size))

    if drop_on_exit: drop_database(database)

    return insert_one_time, doc_size, db_size, bulk_insert_time


def find(indexed):
    """

    :param indexed:
    :return:
    """

    if indexed:
        db = connect(HOST, PORT).get_database(DATABASE)
    else:
        db = connect(HOST, PORT).get_database(DATABASE_INDEXED)

    collection = db.get_collection(COLLECTION)

    execution_time = 0

    for i in range(5):
        count = 0

        start_time = time.time()

        count += collection.find({'user.location': 'London'}).count()
        count += collection.find({'user.friends_count': {'$gt': 1000}}).count()
        count += collection.find({'user.followers_count': {'$gt': 1000}}).count()

        execution_time += time.time() - start_time

    logger.info("{} seconds to find {} with indexed={}".format(execution_time, count, indexed))

    return execution_time, count


def scan():
    """

    :return:
    """
    db = connect(HOST, PORT).get_database(DATABASE)

    collection = db.get_collection(COLLECTION)

    start_time = time.time()

    collection.find({}).count()

    execution_time = time.time() - start_time

    scanned = collection.count()

    logger.info("{} seconds to scan {} objects".format(execution_time, scanned))

    return execution_time, scanned

