import json
import os
import logging
import time
from datetime import datetime, timedelta
from pymongo import MongoClient, errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection details via env (default fallback)
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.environ.get('MONGO_DB', 'yfinance_data')
INPUT_FILE_PATH = os.environ.get('INPUT_PATH', '/app/output/tickers_data.json')

# 7 Collections to create with their period types
COLLECTIONS = {
    'data_harian': 'daily',
    'data_mingguan': 'weekly', 
    'data_bulanan': 'monthly',
    'data_tahunan': 'yearly',
    'data_lima_tahun': '5years',
    'data_satu_tahun': '1year',
    'data_tiga_tahun': '3years'
}

def group_data_by_period(history, period_type, symbol):
    """
    Group historical data by different periods
    """
    grouped_data = {}
    
    for entry in history:
        try:
            date_str = entry.get("Date", "")
            if not date_str:
                continue
                
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            if period_type == 'daily':
                # Each day is separate
                key = date_str  # "2020-04-16"
                bulan_value = date_str  # "2020-04-16"
            
            elif period_type == 'weekly':
                # Group by week (Monday as start)
                week_start = date_obj - timedelta(days=date_obj.weekday())
                key = week_start.strftime('%Y-W%U')
                bulan_value = f"{date_obj.year}-W{date_obj.isocalendar()[1]:02d}"  # "2020-W16"
            
            elif period_type == 'monthly':
                # Group by month
                key = date_str[:7]  # "2020-04"
                bulan_value = date_str[:7]  # "2020-04"
            
            elif period_type == 'yearly':
                # Group by year
                key = date_str[:4]  # "2020"
                bulan_value = date_str[:4]  # "2020"
            
            elif period_type in ['1year', '3years', '5years']:
                # For multi-year collections, group by month but label appropriately
                key = date_str[:7]  # "2020-04"
                if period_type == '1year':
                    bulan_value = f"{date_str[:7]}-1Y"  # "2020-04-1Y"
                elif period_type == '3years':
                    bulan_value = f"{date_str[:7]}-3Y"  # "2020-04-3Y"
                else:  # 5years
                    bulan_value = f"{date_str[:7]}-5Y"  # "2020-04-5Y"
            
            else:
                continue
            
            # Initialize group if not exists
            if key not in grouped_data:
                grouped_data[key] = {
                    'entries': [],
                    'bulan_value': bulan_value,
                    'start_date': date_str,
                    'end_date': date_str
                }
            
            # Add entry to group
            grouped_data[key]['entries'].append(entry)
            
            # Update end_date (keep the latest date)
            if date_str > grouped_data[key]['end_date']:
                grouped_data[key]['end_date'] = date_str
                
        except Exception as e:
            logger.warning(f"Error processing date {date_str} for {symbol}: {str(e)}")
            continue
    
    return grouped_data

def aggregate_entries(entries):
    """
    Aggregate multiple entries into one summary
    """
    try:
        if not entries:
            return None
            
        if len(entries) == 1:
            # Single entry, use as-is
            entry = entries[0]
            return {
                "Open": float(entry.get("Open", 0)) if entry.get("Open") and entry.get("Open") != 0 else 0.0,
                "Close": float(entry.get("Close", 0)) if entry.get("Close") and entry.get("Close") != 0 else 0.0,
                "Low": float(entry.get("Low", 0)) if entry.get("Low") and entry.get("Low") != 0 else 0.0,
                "High": float(entry.get("High", 0)) if entry.get("High") and entry.get("High") != 0 else 0.0,
                "AvgVolume": int(entry.get("Volume", 0)) if entry.get("Volume") and entry.get("Volume") != 0 else 0,
                "MaxVolume": int(entry.get("Volume", 0)) if entry.get("Volume") and entry.get("Volume") != 0 else 0,
            }
        
        # Multiple entries, aggregate them
        entries.sort(key=lambda x: x.get("Date", ""))
        
        # Filter out None, 0, and invalid values
        opens = [float(e.get("Open", 0)) for e in entries if e.get("Open") and float(e.get("Open", 0)) > 0]
        closes = [float(e.get("Close", 0)) for e in entries if e.get("Close") and float(e.get("Close", 0)) > 0]
        highs = [float(e.get("High", 0)) for e in entries if e.get("High") and float(e.get("High", 0)) > 0]
        lows = [float(e.get("Low", 0)) for e in entries if e.get("Low") and float(e.get("Low", 0)) > 0]
        volumes = [int(e.get("Volume", 0)) for e in entries if e.get("Volume") and int(e.get("Volume", 0)) > 0]
        
        # Calculate aggregated values with proper fallbacks
        open_price = opens[0] if opens else 0.0
        close_price = closes[-1] if closes else 0.0
        high_price = max(highs) if highs else 0.0
        low_price = min(lows) if lows else 0.0
        avg_volume = sum(volumes) // len(volumes) if volumes else 0
        max_volume = max(volumes) if volumes else 0
        
        return {
            "Open": open_price,
            "Close": close_price,
            "High": high_price,
            "Low": low_price,
            "AvgVolume": avg_volume,
            "MaxVolume": max_volume,
        }
        
    except Exception as e:
        logger.warning(f"Error aggregating entries: {str(e)}")
        return None

def transform_for_collection(original_data, collection_name, period_type):
    """
    Transform data specifically for each collection type with balanced sizing
    """
    simplified_data = []
    
    # DYNAMIC STOCK LIMITATION BASED ON COLLECTION TYPE
    if collection_name == 'data_harian':
        # Most documents - limit to 70 stocks (70 * 1040 days = ~73k docs)
        limited_data = original_data[:70]
        logger.info(f"🔄 Limited to {len(limited_data)} stocks for {collection_name} (largest collection)")
    elif collection_name in ['data_mingguan']:
        # Medium-high documents - limit to 280 stocks (280 * 260 weeks = ~73k docs)  
        limited_data = original_data[:280]
        logger.info(f"🔄 Limited to {len(limited_data)} stocks for {collection_name}")
    elif collection_name in ['data_bulanan', 'data_lima_tahun']:
        # Medium documents - limit to 950 stocks (all data - 950 * 60 months = ~57k docs)
        limited_data = original_data[:950]
        logger.info(f"🔄 Using all {len(limited_data)} stocks for {collection_name}")
    elif collection_name in ['data_tiga_tahun']:
        # Medium-low documents - limit to 950 stocks (950 * 36 months = ~34k docs)
        limited_data = original_data[:950]
        logger.info(f"🔄 Using all {len(limited_data)} stocks for {collection_name}")
    elif collection_name in ['data_satu_tahun']:
        # Low documents - use all stocks (950 * 12 months = ~11k docs)
        limited_data = original_data[:950]
        logger.info(f"🔄 Using all {len(limited_data)} stocks for {collection_name}")
    else:  # data_tahunan
        # Very low documents - use all stocks (950 * 5 years = ~5k docs)
        limited_data = original_data[:950]
        logger.info(f"🔄 Using all {len(limited_data)} stocks for {collection_name}")
    
    logger.info(f"🔄 Transforming data for {collection_name} ({period_type} periods)")
    
    for stock_data in limited_data:
        try:
            info = stock_data.get("info", {})
            history = stock_data.get("history", [])
            symbol = info.get("symbol", "UNKNOWN")
            
            if not history:
                continue
            
            # Group data by period
            grouped_data = group_data_by_period(history, period_type, symbol)
            
            # Create documents for each period
            for period_key, period_data in grouped_data.items():
                try:
                    # Aggregate the entries for this period
                    aggregated = aggregate_entries(period_data['entries'])
                    if not aggregated:
                        continue
                    
                    # Create document structure
                    document = {
                        "Bulan": period_data['bulan_value'],
                        "StartDate": period_data['start_date'] + "T00:00:00.000+00:00",
                        "EndDate": period_data['end_date'] + "T00:00:00.000+00:00",
                        "Open": aggregated["Open"],
                        "Close": aggregated["Close"],
                        "Low": aggregated["Low"],
                        "High": aggregated["High"],
                        "AvgVolume": aggregated["AvgVolume"],
                        "MaxVolume": aggregated["MaxVolume"],
                        "ticker": symbol
                    }
                    
                    simplified_data.append(document)
                    
                except Exception as e:
                    logger.warning(f"Error creating document for {symbol}, period {period_key}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing stock data for {symbol}: {str(e)}")
            continue
    
    logger.info(f"✅ Created {len(simplified_data):,} documents for {collection_name}")
    return simplified_data

def load_to_collection(client, db_name, collection_name, data):
    """
    Load data to specific collection
    """
    try:
        db = client[db_name]
        collection = db[collection_name]
        
        logger.info(f"📊 Loading data to {db_name}.{collection_name}")
        
        if not data:
            logger.warning(f"No data to load for {collection_name}")
            return 0
        
        # Process data in batches for better performance
        batch_size = 1000
        total_batches = (len(data) + batch_size - 1) // batch_size
        insert_count = 0
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(data))
            batch_data = data[start_idx:end_idx]
            
            try:
                # Insert batch data
                result = collection.insert_many(batch_data, ordered=False)
                insert_count += len(result.inserted_ids)
                
                if batch_idx % 10 == 0 or batch_idx == total_batches - 1:
                    logger.info(f"  Batch {batch_idx + 1}/{total_batches}: {len(result.inserted_ids)} docs inserted")
                
            except Exception as e:
                logger.error(f"  Error inserting batch {batch_idx + 1}: {str(e)}")
        
        logger.info(f"✅ {collection_name}: {insert_count:,} documents inserted")
        return insert_count
        
    except Exception as e:
        logger.error(f"❌ Error loading to {collection_name}: {str(e)}")
        return 0

def load_to_all_collections():
    """
    Load yFinance data to all 7 collections automatically with proper periods
    """
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("🚀 YFINANCE AUTO-LOAD TO 7 COLLECTIONS WITH DIFFERENT PERIODS")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Loading from: {INPUT_FILE_PATH}")
    logger.info(f"Target database: {MONGO_DB}")
    logger.info(f"Target collections: {list(COLLECTIONS.keys())}")

    # Load JSON data
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        logger.info(f"📁 Loaded {len(original_data)} stock records from file")
        
        # REDUCE DATA SIZE FOR FREE TIER - Use only 100 stocks for testing
        original_data = original_data[:100]
        logger.info(f"🔄 Reduced to {len(original_data)} stocks for testing (avoiding quota limit)")
        
    except Exception as e:
        logger.error(f"Failed to read input file {INPUT_FILE_PATH}: {str(e)}")
        raise

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        logger.info(f"🔗 MongoDB connection successful")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise

    # Load data to all collections
    total_inserted = 0
    successful_collections = 0
    
    for collection_name, period_type in COLLECTIONS.items():
        try:
            logger.info(f"\n🔄 Processing {collection_name} with {period_type} aggregation...")
            
            # Transform data for this specific collection
            transformed_data = transform_for_collection(original_data, collection_name, period_type)
            
            # Load to collection
            inserted_count = load_to_collection(client, MONGO_DB, collection_name, transformed_data)
            total_inserted += inserted_count
            
            if inserted_count > 0:
                successful_collections += 1
                
        except Exception as e:
            logger.error(f"❌ Failed to process {collection_name}: {str(e)}")

    elapsed = time.time() - start_time

    # Summary logging
    logger.info("\n" + "=" * 70)
    logger.info("📊 FINAL SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Database: {MONGO_DB}")
    logger.info(f"Total collections processed: {len(COLLECTIONS)}")
    logger.info(f"Successful collections: {successful_collections}")
    logger.info(f"Total documents inserted: {total_inserted:,}")
    logger.info(f"Execution time: {elapsed:.2f} seconds")
    
    if successful_collections == len(COLLECTIONS):
        logger.info("🎉 ALL 7 COLLECTIONS CREATED SUCCESSFULLY!")
    else:
        logger.warning(f"⚠️  {successful_collections}/{len(COLLECTIONS)} collections created successfully")

    # Close connection
    client.close()
    logger.info("🔌 MongoDB connection closed")

    # Optional: Remove input file after successful load
    if successful_collections == len(COLLECTIONS):
        try:
            os.remove(INPUT_FILE_PATH)
            logger.info(f"🗑️ Deleted input file: {INPUT_FILE_PATH}")
        except Exception as e:
            logger.warning(f"Could not delete input file: {str(e)}")

    return {
        "status": "success" if successful_collections == len(COLLECTIONS) else "partial_success",
        "total_collections": len(COLLECTIONS),
        "successful_collections": successful_collections,
        "total_documents": total_inserted,
        "execution_time_seconds": elapsed,
        "database": MONGO_DB,
        "collections": list(COLLECTIONS.keys())
    }

if __name__ == "__main__":
    result = load_to_all_collections()
    
    logger.info(f"\n🏁 Final Status: {result['status']}")
    logger.info(f"📈 Created {result['successful_collections']}/{result['total_collections']} collections")
    logger.info(f"📊 Total documents: {result['total_documents']:,}")
    
    # List collections created with their period types
    logger.info(f"\n📋 Collections created in database '{MONGO_DB}':")
    for collection, period_type in COLLECTIONS.items():
        logger.info(f"  ✅ {MONGO_DB}.{collection} ({period_type} aggregation)")