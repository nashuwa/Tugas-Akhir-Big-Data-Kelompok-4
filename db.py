import os
from pymongo import MongoClient

#koneksi ke MongoDB
# client = MongoClient("mongodb+srv://bigdatakecil:bigdata04@xtrahera.m7x7qad.mongodb.net/?retryWrites=true&w=majority&appName=xtrahera")

# Koneksi ke MongoDB - pakai environment variable
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://bigdatakecil:bigdata04@xtrahera.m7x7qad.mongodb.net/?retryWrites=true&w=majority&appName=xtrahera')
client = MongoClient(MONGODB_URI)

# Akses database
db = client["tugas_bigdata"]

# Akses koleksi
# collection_idx = db["idx_raw"]
collection_idx = db["idx_transform"]
collection_yfinance = db["yfinance_data_lima_tahun"]
collection_market_news = db["market_news"]