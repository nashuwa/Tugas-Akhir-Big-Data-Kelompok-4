# pip install pandas yfinance
import os
import pandas as pd
import yfinance as yf
import time
import logging
import json
import gc
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yfinance_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
EXCEL_FILE_PATH = os.getenv('EXCEL_FILE_PATH', 'tickers.xlsx')
JSON_OUTPUT_PATH = os.getenv('YFINANCE_OUTPUT_PATH', 'tickers_data.json')
YEARS_BACK = 5

def calculate_date_range():
    """Calculate start and end dates for the last 5 years"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=YEARS_BACK * 365)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def read_tickers_from_excel(file_path):
    """Read ticker symbols from Excel file"""
    try:
        df = pd.read_excel(file_path)
        
        # Handle different possible column names
        ticker_column = None
        for col in df.columns:
            if col.lower() in ['ticker', 'symbol', 'code', 'stock']:
                ticker_column = col
                break
        
        if ticker_column is None:
            raise ValueError("No ticker column found. Expected columns: 'Ticker', 'Symbol', 'Code', or 'Stock'")
        
        tickers = df[ticker_column].astype(str).tolist()
        
        # Add .JK suffix for Indonesian stocks if not present
        tickers = [ticker + ".JK" if not ticker.endswith(".JK") else ticker for ticker in tickers]
        
        logger.info(f"Successfully loaded {len(tickers)} tickers from {file_path}")
        return tickers
    
    except Exception as e:
        logger.error(f"Failed to read Excel file {file_path}: {str(e)}")
        raise

def fetch_ticker_data(ticker, start_date, end_date):
    """Fetch data for a single ticker with 5 years history"""
    try:
        stock = yf.Ticker(ticker)
        
        # Get stock info
        info = stock.info
        
        # Get historical data for 5 years
        hist_data = stock.history(start=start_date, end=end_date)
        
        if hist_data.empty:
            logger.warning(f"{ticker} has no historical data for the specified period")
            return None
        
        # Convert historical data to the format expected by MongoDB script
        history_records = []
        for date, row in hist_data.iterrows():
            history_records.append({
                "Date": date.strftime('%Y-%m-%d'),
                "Open": float(row['Open']) if pd.notna(row['Open']) else None,
                "High": float(row['High']) if pd.notna(row['High']) else None,
                "Low": float(row['Low']) if pd.notna(row['Low']) else None,
                "Close": float(row['Close']) if pd.notna(row['Close']) else None,
                "Volume": int(row['Volume']) if pd.notna(row['Volume']) else None,
                "Dividends": float(row['Dividends']) if 'Dividends' in row and pd.notna(row['Dividends']) else 0,
                "Stock Splits": float(row['Stock Splits']) if 'Stock Splits' in row and pd.notna(row['Stock Splits']) else 0
            })
        
        # Structure data to match MongoDB script expectations
        return {
            "info": info,
            "history": history_records,
            "fetch_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_period": f"{start_date} to {end_date}",
            "total_records": len(history_records)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
        return None

def fetch_all_data(tickers, start_date, end_date):
    """Memory-optimized version - process in smaller batches"""
    all_data = []
    total_tickers = len(tickers)
    successful_fetches = 0
    failed_fetches = 0
    
    # Process in smaller batches to manage memory
    batch_size = 10  # Process 10 tickers at a time
    
    for batch_start in range(0, total_tickers, batch_size):
        batch_end = min(batch_start + batch_size, total_tickers)
        batch_tickers = tickers[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_start//batch_size + 1}: tickers {batch_start+1}-{batch_end}")
        
        for idx, ticker in enumerate(batch_tickers):
            retries = 3
            success = False
            
            logger.info(f"Processing {idx}/{total_tickers}: {ticker}")
            
            while retries > 0 and not success:
                try:
                    data = fetch_ticker_data(ticker, start_date, end_date)
                    
                    if data:
                        all_data.append(data)
                        successful_fetches += 1
                        logger.info(f"✅ Successfully fetched {len(data['history'])} records for {ticker}")
                        success = True
                    else:
                        logger.warning(f"❌ No data available for {ticker}")
                        failed_fetches += 1
                        break
                        
                except Exception as e:
                    retries -= 1
                    logger.error(f"❌ Error fetching {ticker} (retries left: {retries}): {str(e)}")
                    
                    if retries > 0:
                        logger.info("Waiting 5 seconds before retry...")
                        time.sleep(5)
                    else:
                        failed_fetches += 1
                
                # Rate limiting - wait between requests
                time.sleep(1)
            
            # Progress update every 10 tickers
            if idx % 10 == 0 or idx == total_tickers:
                logger.info(f"Progress: {idx}/{total_tickers} processed | Success: {successful_fetches} | Failed: {failed_fetches}")
        
        # Force garbage collection after each batch
        gc.collect()
        
        # Save intermediate results every 50 tickers
        if len(all_data) % 50 == 0 and all_data:
            logger.info(f"Intermediate save - {len(all_data)} tickers processed")
    
    return all_data, successful_fetches, failed_fetches

def save_to_json(data, file_path):
    """Save data to JSON file"""
    try:
        # Custom JSON encoder to handle datetime and other objects
        def json_serializer(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            elif pd.isna(obj):
                return None
            return str(obj)
        
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2, default=json_serializer)
        
        logger.info(f"✅ Data successfully saved to {file_path}")
        
        # Log file size
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        logger.info(f"📁 File size: {file_size:.2f} MB")
        
    except Exception as e:
        logger.error(f"Failed to save data to {file_path}: {str(e)}")
        raise

def main():
    """Main execution function"""
    start_time = time.time()
    
    logger.info("=" * 50)
    logger.info("YFINANCE DATA FETCHER - 5 YEARS HISTORICAL DATA")
    logger.info("=" * 50)
    
    try:
        # Calculate date range
        start_date, end_date = calculate_date_range()
        logger.info(f"Fetching data from {start_date} to {end_date}")
        
        # Read tickers from Excel
        tickers = read_tickers_from_excel(EXCEL_FILE_PATH)
        
        # Fetch all data
        all_data, successful, failed = fetch_all_data(tickers, start_date, end_date)
        
        # Save to JSON
        if all_data:
            save_to_json(all_data, JSON_OUTPUT_PATH)
        else:
            logger.error("No data to save!")
            return
        
        # Summary
        execution_time = time.time() - start_time
        
        logger.info("\n" + "=" * 50)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total tickers processed: {len(tickers)}")
        logger.info(f"Successful fetches: {successful}")
        logger.info(f"Failed fetches: {failed}")
        logger.info(f"Success rate: {(successful/len(tickers)*100):.1f}%")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info(f"Output file: {JSON_OUTPUT_PATH}")
        
        # Calculate total records
        total_records = sum(len(item.get('history', [])) for item in all_data)
        logger.info(f"Total historical records: {total_records:,}")
        
        logger.info("\n🎉 Data fetching completed successfully!")
        logger.info(f"You can now run your MongoDB loader script with INPUT_PATH={JSON_OUTPUT_PATH}")
        
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()