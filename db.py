from pymongo import MongoClient

#koneksi ke MongoDB
client = MongoClient("mongodb+srv://bigdatakecil:bigdata04@xtrahera.m7x7qad.mongodb.net/?retryWrites=true&w=majority&appName=xtrahera")

# Akses database
db = client["tugas_bigdata"]

# Akses koleksi
# collection_idx = db["idx_raw"]
collection_idx = db["idx_transform"]
collection_yfinance = db["yfinance_data_lima_tahun"]
collection_market_news = db["market_news"]