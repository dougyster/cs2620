from pymongo import MongoClient
from interfaces.db_interface import MongoDBInterface

class MongoOperation(MongoDBInterface):
    def __init__(self):
        self.client = MongoClient('mongodb+srv://dyang:tJwvDN1gD0Cqkjpq@chatapp.42cn2.mongodb.net/')
        self.db = self.client['ChatApp']  # Specify the database name

    def insert(self, collection_name, document):
        collection = self.db[collection_name]
        result = collection.insert_one(document)
        return result.inserted_id

    def read(self, collection_name, query):
        collection = self.db[collection_name]
        document = collection.find_one(query)
        return document

    def update(self, collection_name, query, update_values):
        collection = self.db[collection_name]
        result = collection.update_one(query, {'$set': update_values})
        return result.modified_count

    def delete(self, collection_name, query):
        collection = self.db[collection_name]
        result = collection.delete_one(query)
        return result.deleted_count
