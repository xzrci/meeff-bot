from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb+srv://itxcriminal:qureshihashmI1@cluster0.jyqy9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.meeff_tokens

# Insert or update token for a user
def set_token(user_id, token, meeff_user_id):
    db.tokens.update_one(
        {"user_id": user_id, "token": token},
        {"$set": {"user_id": user_id, "token": token, "name": meeff_user_id}},
        upsert=True
    )
    
# Get all tokens for a user
def get_tokens(user_id):
    return list(db.tokens.find({"user_id": user_id}, {"_id": 0, "token": 1, "name": 1}))

# Get all tokens in the database
def list_tokens():
    return list(db.tokens.find({}, {"_id": 0}))

def set_current_account(user_id, token):
    db.current_account.update_one({"user_id": user_id}, {"$set": {"token": token}}, upsert=True)

def get_current_account(user_id):
    record = db.current_account.find_one({"user_id": user_id})
    return record["token"] if record else None

# Delete a token for a user
def delete_token(user_id, token):
    db.tokens.delete_one({"user_id": user_id, "token": token})
