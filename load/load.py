import json
import os
import logging
import time
from datetime import datetime
from pymongo import MongoClient, errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection details via env (default fallback)
MONGO_URI = os.environ.get('MONGO_URI')
MONGO_DB = os.environ.get('MONGO_DB')
DEFAULT_COLLECTION = os.environ.get('MONGO_COLLECTION')
INPUT_FILE_PATH = os.environ.get('INPUT_PATH')

def load_to_mongodb(input_file_path=INPUT_FILE_PATH, mongo_collection=DEFAULT_COLLECTION):
    start_time = time.time()

    logger.info(f"Start MongoDB load at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Loading from: {input_file_path}")
    logger.info(f"Target MongoDB: {MONGO_DB}.{mongo_collection}")

    # Load the JSON data
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
        logger.info(f"Loaded {len(data_list)} records from file")
    except Exception as e:
        logger.error(f"Failed to read input file {input_file_path}: {str(e)}")
        raise

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        db = client[MONGO_DB]
        collection = db[mongo_collection]
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise

    insert_count = 0
    update_count = 0
    error_count = 0

    for idx, doc in enumerate(data_list, 1):
        try:
            doc_id = doc.get("_id")

            if doc_id:
                existing = collection.find_one({"_id": doc_id})
                if existing:
                    result = collection.replace_one({"_id": doc_id}, doc)
                    update_count += int(result.modified_count > 0)
                else:
                    collection.insert_one(doc)
                    insert_count += 1
            else:
                # No _id field, insert new document
                collection.insert_one(doc)
                insert_count += 1

            if idx % 10 == 0 or idx == len(data_list):
                logger.info(f"Progress: {idx}/{len(data_list)} documents processed")

        except Exception as e:
            error_count += 1
            logger.error(f"Error processing document {idx}: {str(e)}")

    elapsed = time.time() - start_time

    logger.info("\n" + "=" * 50)
    logger.info("MONGODB LOAD SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Execution time: {elapsed:.2f} seconds")
    logger.info(f"Total documents processed: {len(data_list)}")
    logger.info(f"Inserted: {insert_count}")
    logger.info(f"Updated: {update_count}")
    logger.info(f"Errors: {error_count}")

    client.close()
    logger.info("MongoDB connection closed")
    os.remove(input_file_path)
    logger.info(f"Deleted input file: {input_file_path}")

    return {
        "status": "success" if error_count == 0 else "partial_success" if error_count < len(data_list) else "failure",
        "total_processed": len(data_list),
        "inserted": insert_count,
        "updated": update_count,
        "errors": error_count,
        "execution_time_seconds": elapsed
    }

if __name__ == "__main__":
    load_to_mongodb()