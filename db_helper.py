from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb+srv://itxcriminal:qureshihashmI1@cluster0.jyqy9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.meeff_tokens

# Insert or update token for a user
def set_token(user_id, token):
    db.tokens.update_one({"user_id": user_id, "token": token}, {"$set": {"user_id": user_id, "token": token}}, upsert=True)

# Get all tokens for a user
def get_tokens(user_id):
    return list(db.tokens.find({"user_id": user_id}, {"_id": 0, "token": 1}))

# Get all tokens in the database
def list_tokens():
    return list(db.tokens.find({}, {"_id": 0}))
