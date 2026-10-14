import gridfs
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient

from config import Config

# One shared MongoDB client for the whole app. MongoClient already manages a
# connection pool, so creating many clients would only waste connections.
# MongoClient connects lazily, so importing this file does not need a live DB.
mongo_client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)

# The "invexa" database handle. Every module imports this instead of
# building its own, so tests can swap it in one place.
db = mongo_client[Config.DB_NAME]

# GridFS stores uploaded bills and chat files inside the same database.
fs = gridfs.GridFS(db)

# Rate limiter that tracks requests per IP address.
# In-memory storage is fine for one dev server; production would need Redis.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[Config.DEFAULT_RATE_LIMIT],
    storage_uri="memory://",
)
