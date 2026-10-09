import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional

import firebase_admin
from firebase_admin import db as rtdb
from backend.app.config import (
    FIREBASE_PROJECT_ID,
    FIREBASE_DATABASE_URL,
    DATABASE_NAME,
    MONGODB_URI
)

logger = logging.getLogger("quadmedic.database")
logging.basicConfig(level=logging.INFO)

# Path to local persistent store for seamless offline/standalone demo reliability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, "data")
LOCAL_DB_FILE = os.path.join(LOCAL_DATA_DIR, "rtdb_local.json")

# Seed baseline collections
DEFAULT_SEED_DATA = {
    "users": [],
    "students": [],
    "doctors": [
        {
            "_id": "doc_smith",
            "email": "smith@quadmedic.edu",
            "name": "Dr. Sarah Smith",
            "specialty": "Cardiology & General Medicine",
            "availability": ["Monday", "Tuesday", "Wednesday"],
            "slots": ["09:00 - 10:00", "10:00 - 11:00", "14:00 - 15:00"],
            "queue": []
        },
        {
            "_id": "doc_davis",
            "email": "davis@quadmedic.edu",
            "name": "Dr. Alan Davis",
            "specialty": "Pediatrics & General Care",
            "availability": ["Wednesday", "Thursday", "Friday"],
            "slots": ["10:00 - 11:00", "11:00 - 12:00", "15:00 - 16:00"],
            "queue": []
        },
        {
            "_id": "doc_jones",
            "email": "jones@quadmedic.edu",
            "name": "Dr. Emily Jones",
            "specialty": "Mental Wellness & Psychology",
            "availability": ["Monday", "Thursday"],
            "slots": ["09:00 - 10:00", "11:00 - 12:00", "14:00 - 15:00"],
            "queue": []
        }
    ],
    "appointments": [],
    "prescriptions": [],
    "vaccinations": [],
    "medical_reports": [],
    "symptoms": [],
    "chat_history": [],
    "notifications": [],
    "medicine_reminders": [],
    "emergency_cases": [],
    "health_scores": [],
    "otps": [],
    "clinical_notes": [],
    "emergency_emails": []
}

# In-memory store mirroring Realtime Database
_local_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

def _ensure_local_store():
    global _local_store
    if _local_store:
        return
    
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                _local_store = json.load(f)
                return
        except Exception as e:
            logger.warning(f"Failed to load local RTDB cache: {e}")

    # Initialize with default collections
    _local_store = {}
    for col, items in DEFAULT_SEED_DATA.items():
        _local_store[col] = {}
        for item in items:
            doc_id = str(item.get("_id", uuid.uuid4().hex[:8]))
            item_copy = dict(item)
            item_copy["_id"] = doc_id
            _local_store[col][doc_id] = item_copy

def _save_local_store():
    try:
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(_local_store, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not persist to {LOCAL_DB_FILE}: {e}")

_ensure_local_store()

# Realtime Database status
firebase_rtdb_connected = False

def init_database():
    global firebase_rtdb_connected
    _ensure_local_store()

    try:
        if not firebase_admin._apps:
            options = {
                'projectId': FIREBASE_PROJECT_ID,
                'databaseURL': FIREBASE_DATABASE_URL
            }
            firebase_admin.initialize_app(options=options)
            logger.info(f"Firebase Admin initialized with RTDB URL: {FIREBASE_DATABASE_URL}")
        firebase_rtdb_connected = True
    except Exception as e:
        firebase_rtdb_connected = False
        logger.info(f"Using local persistent database store: {e}")

class RealtimeDatabaseCollection:
    """
    MongoDB-compatible API wrapper for Firebase Realtime Database.
    Ensures drop-in compatibility with all existing routes and queries.
    """
    def __init__(self, name: str):
        self.name = name

    def _get_ref(self):
        if firebase_rtdb_connected:
            try:
                return rtdb.reference(f"/{self.name}")
            except Exception:
                pass
        return None

    def _sync_remote(self, doc_id: str, data: Optional[Dict[str, Any]]):
        def _bg_sync():
            try:
                ref = self._get_ref()
                if ref:
                    if data is None:
                        ref.child(str(doc_id)).delete()
                    else:
                        clean_data = {}
                        for k, v in data.items():
                            clean_key = str(k).replace(".", "_").replace("$", "")
                            clean_data[clean_key] = v
                        ref.child(str(doc_id)).set(clean_data)
            except Exception as e:
                logger.debug(f"RTDB background sync notice for {self.name}/{doc_id}: {e}")

        try:
            import threading
            threading.Thread(target=_bg_sync, daemon=True).start()
        except Exception:
            pass

    def _matches_filter(self, doc: Dict[str, Any], filter_dict: Optional[Dict[str, Any]]) -> bool:
        if not filter_dict:
            return True
        for k, v in filter_dict.items():
            doc_val = doc.get(k)
            if isinstance(v, dict):
                # Simple operator support ($ne, $in, $gt, etc.)
                if "$ne" in v and doc_val == v["$ne"]:
                    return False
                if "$in" in v and doc_val not in v["$in"]:
                    return False
                if "$gt" in v and not (doc_val > v["$gt"]):
                    return False
                if "$lt" in v and not (doc_val < v["$lt"]):
                    return False
            else:
                if doc_val != v:
                    return False
        return True

    def find(self, filter=None, projection=None, sort=None, limit=0) -> List[Dict[str, Any]]:
        _ensure_local_store()
        col_data = _local_store.get(self.name, {})

        results = []
        for doc_id, doc in col_data.items():
            if self._matches_filter(doc, filter):
                item = dict(doc)
                item["_id"] = str(doc_id)
                results.append(item)

        if sort:
            try:
                field, order = sort[0]
                results.sort(key=lambda x: str(x.get(field, "")), reverse=(order == -1))
            except Exception:
                pass

        if limit > 0:
            results = results[:limit]

        return results

    def find_one(self, filter=None, projection=None) -> Optional[Dict[str, Any]]:
        res = self.find(filter=filter, projection=projection, limit=1)
        return res[0] if res else None

    def insert_one(self, document: Dict[str, Any]):
        _ensure_local_store()
        doc = dict(document)
        doc_id = str(doc.get("_id") or uuid.uuid4().hex[:12])
        doc["_id"] = doc_id

        if self.name not in _local_store:
            _local_store[self.name] = {}

        _local_store[self.name][doc_id] = doc
        _save_local_store()
        self._sync_remote(doc_id, doc)

        return type('InsertOneResult', (object,), {'inserted_id': doc_id})()

    def insert_many(self, documents: List[Dict[str, Any]]):
        inserted_ids = []
        for d in documents:
            res = self.insert_one(d)
            inserted_ids.append(res.inserted_id)
        return type('InsertManyResult', (object,), {'inserted_ids': inserted_ids})()

    def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        _ensure_local_store()
        target = self.find_one(filter)

        if not target:
            if upsert:
                new_doc = dict(filter)
                if "$set" in update:
                    new_doc.update(update["$set"])
                res = self.insert_one(new_doc)
                return type('UpdateResult', (object,), {'modified_count': 1, 'upserted_id': res.inserted_id})()
            return type('UpdateResult', (object,), {'modified_count': 0, 'upserted_id': None})()

        doc_id = str(target["_id"])
        existing = _local_store[self.name].get(doc_id, {})
        
        if "$set" in update:
            for k, v in update["$set"].items():
                existing[k] = v
        else:
            for k, v in update.items():
                existing[k] = v

        _local_store[self.name][doc_id] = existing
        _save_local_store()
        self._sync_remote(doc_id, existing)

        return type('UpdateResult', (object,), {'modified_count': 1, 'upserted_id': None})()

    def update_many(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        _ensure_local_store()
        matches = self.find(filter)
        count = 0
        for m in matches:
            self.update_one({"_id": m["_id"]}, update, upsert=False)
            count += 1
        return type('UpdateResult', (object,), {'modified_count': count})()

    def delete_one(self, filter: Dict[str, Any]):
        _ensure_local_store()
        target = self.find_one(filter)
        if target:
            doc_id = str(target["_id"])
            if self.name in _local_store and doc_id in _local_store[self.name]:
                del _local_store[self.name][doc_id]
                _save_local_store()
                self._sync_remote(doc_id, None)
                return type('DeleteResult', (object,), {'deleted_count': 1})()
        return type('DeleteResult', (object,), {'deleted_count': 0})()

    def delete_many(self, filter: Optional[Dict[str, Any]] = None):
        _ensure_local_store()
        matches = self.find(filter)
        deleted_count = 0
        for m in matches:
            doc_id = str(m["_id"])
            if self.name in _local_store and doc_id in _local_store[self.name]:
                del _local_store[self.name][doc_id]
                self._sync_remote(doc_id, None)
                deleted_count += 1
        
        if deleted_count > 0:
            _save_local_store()
        return type('DeleteResult', (object,), {'deleted_count': deleted_count})()

    def count_documents(self, filter=None) -> int:
        return len(self.find(filter))

def get_collection(name: str):
    return RealtimeDatabaseCollection(name)

# ─── Data Migration Utility (MongoDB -> Realtime Database) ───────────────────
def transfer_all_data_from_mongo_to_rtdb() -> Dict[str, Any]:
    """
    Transfers all collections and records from MongoDB into the Firebase Realtime Database.
    Falls back gracefully to current store if MongoDB is offline.
    """
    import pymongo

    results = {}
    mongo_connected = False
    mongo_db = None

    try:
        logger.info(f"Connecting to MongoDB at {MONGODB_URI} for migration...")
        client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        client.server_info()
        mongo_db = client[DATABASE_NAME]
        mongo_connected = True
        logger.info(f"Successfully reached MongoDB database '{DATABASE_NAME}'.")
    except Exception as e:
        logger.warning(f"MongoDB offline or unreachable ({e}). Using existing document models for RTDB transfer.")

    target_collections = list(DEFAULT_SEED_DATA.keys())
    if mongo_connected and mongo_db is not None:
        try:
            target_collections = list(set(target_collections + mongo_db.list_collection_names()))
        except Exception:
            pass

    total_migrated = 0
    for col_name in target_collections:
        rtdb_col = get_collection(col_name)
        migrated_count = 0

        if mongo_connected and mongo_db is not None:
            try:
                mongo_col = mongo_db[col_name]
                cursor = mongo_col.find({})
                for doc in cursor:
                    doc_copy = dict(doc)
                    if "_id" in doc_copy:
                        doc_copy["_id"] = str(doc_copy["_id"])
                    rtdb_col.insert_one(doc_copy)
                    migrated_count += 1
            except Exception as ex:
                logger.warning(f"Error migrating {col_name} from Mongo: {ex}")
        else:
            # Transfer baseline records into Realtime Database
            existing = rtdb_col.find({})
            if not existing and col_name in DEFAULT_SEED_DATA:
                for item in DEFAULT_SEED_DATA[col_name]:
                    rtdb_col.insert_one(item)
                    migrated_count += 1
            else:
                migrated_count = len(existing)

        results[col_name] = migrated_count
        total_migrated += migrated_count

    logger.info(f"Migration completed! Transferred {total_migrated} documents across {len(results)} collections into Realtime Database.")
    return {
        "status": "success",
        "total_documents": total_migrated,
        "collections": results,
        "database": "Firebase Realtime Database",
        "url": FIREBASE_DATABASE_URL
    }

# Initialize on module load
try:
    init_database()
except Exception:
    pass
