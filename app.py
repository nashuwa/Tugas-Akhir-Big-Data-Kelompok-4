import os
from flask import Flask, jsonify, render_template, request
# from pymongo import MongoClient
from dbconfig import collection_yfinance_5tahun, collection_idx, collection_market_news
from bson.json_util import dumps
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

@app.route("/")
def index():
    # return render_template("yfinance/5y.html")
    return render_template('idx/top_revenue.html', active_page='idx')

# @app.route('/idx')
# def idx():
#     return render_template('idx/index.html', active_page='idx')

# Route untuk halaman top revenue
@app.route('/idx/top-revenue')
def idx_top_revenue():
    return render_template('idx/top_revenue.html', active_page='idx')

# API untuk ambil data yang akan dipakai di grafik
@app.route("/api/emiten")
def get_emiten():
    data = collection_idx.find({}, {
        "_id": 0,
        "emiten": 1,
        "calculated_ratios.debt_to_equity": 1,
        "calculated_ratios.return_on_assets": 1,
        "calculated_ratios.return_on_equity": 1,
        "calculated_ratios.cash_to_assets_ratio": 1,
        "data_quality.financial_health_score": 1
    })
    return jsonify(list(data))

# API untuk mengambil 5 emiten dengan revenue tertinggi
@app.route("/api/top-revenue")
def get_top_revenue():
    # Ambil parameter tahun dari query string, default ke 2021 jika tidak ada
    year = int(request.args.get('year', 2021))
    
    # Ambil 5 emiten dengan revenue tertinggi berdasarkan current_year
    # Tambahkan pipeline aggregation untuk menghindari duplikasi
    pipeline = [
        {"$match": {
            "revenue.current_year": {"$exists": True, "$ne": None},
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"},
            "revenue": {"$first": "$revenue"},
            "reporting_year": {"$first": "$reporting_year"}
        }},
        {"$sort": {"revenue.current_year": -1}},
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1,
            "revenue.current_year": 1,
            "revenue.growth_rate_percent": 1,
            "reporting_year": 1
        }}
    ]
    
    top_emiten = list(collection_idx.aggregate(pipeline))
    
    # Mendapatkan daftar tahun unik untuk dropdown
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    
    return jsonify({
        "data": top_emiten,
        "years": distinct_years
    })

# API untuk mendapatkan top 5 emiten berdasarkan growth rate
@app.route("/api/top-growth")
def get_top_growth():
    # Ambil parameter tahun dari query string, default ke 2021 jika tidak ada
    year = int(request.args.get('year', 2021))
    
    # Ambil 5 emiten dengan growth rate tertinggi
    pipeline = [
        {"$match": {
            "revenue.growth_rate_percent": {"$exists": True, "$ne": None},
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"},
            "revenue": {"$first": "$revenue"},
            "reporting_year": {"$first": "$reporting_year"}
        }},
        {"$sort": {"revenue.growth_rate_percent": -1}},
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1,
            "revenue.current_year": 1,
            "revenue.prior_year": 1,
            "revenue.growth_rate_percent": 1,
            "reporting_year": 1
        }}
    ]
    
    top_growth = list(collection_idx.aggregate(pipeline))
    
    # Mendapatkan daftar tahun unik untuk dropdown
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    
    return jsonify({
        "data": top_growth,
        "years": distinct_years
    })

# API untuk mendapatkan top 5 emiten berdasarkan net profit
@app.route("/api/top-profit")
def get_top_profit():
    # Ambil parameter tahun dari query string, default ke 2021 jika tidak ada
    year = int(request.args.get('year', 2021))
    
    # Ambil 5 emiten dengan net profit tertinggi berdasarkan current_year
    pipeline = [
        {"$match": {
            "net_profit.current_year": {"$exists": True, "$ne": None},
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"},
            "net_profit": {"$first": "$net_profit"},
            "reporting_year": {"$first": "$reporting_year"}
        }},
        {"$sort": {"net_profit.current_year": -1}},
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1,
            "net_profit.current_year": 1,
            "net_profit.growth_rate_percent": 1,
            "reporting_year": 1
        }}
    ]
    
    top_profit = list(collection_idx.aggregate(pipeline))
    
    # Mendapatkan daftar tahun unik untuk dropdown
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    
    return jsonify({
        "data": top_profit,
        "years": distinct_years
    })

# API untuk mendapatkan daftar tahun yang tersedia
@app.route("/api/available-years")
def get_available_years():
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    return jsonify(distinct_years)

# API untuk mendapatkan daftar sektor
@app.route("/api/sectors")
def get_sectors():
    sectors = [
        'Agriculture',
        'Energy',
        'Basic Materials',
        'Industrials',
        'Consumer Non-Cyclicals',
        'Consumer Cyclicals',
        'Healthcare',
        'Financials',
        'Properties & Real Estate',
        'Technology',
        'Infrastructures',
        'Transportation & Logistic'
    ]
    return jsonify(sectors)

# API untuk mendapatkan data pertumbuhan sektor
@app.route("/api/sector-growth")
def get_sector_growth():
    # Ambil parameter sektor dari query string
    sector = request.args.get('sector')
    
    # Pipeline agregasi untuk menghitung rata-rata pertumbuhan revenue berdasarkan tahun untuk sektor tertentu
    pipeline = [
        {
            "$match": {
                "sector": {"$regex": sector, "$options": "i"},  # Case insensitive search
                "revenue.growth_rate_percent": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$reporting_year",
                "avg_growth": {"$avg": "$revenue.growth_rate_percent"},
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}  # Urutkan berdasarkan tahun
        }
    ]
    
    sector_data = list(collection_idx.aggregate(pipeline))
    
    # Format data untuk Chart.js
    result = {
        "labels": [str(item["_id"]) for item in sector_data],
        "data": [round(item["avg_growth"], 2) for item in sector_data],
        "counts": [item["count"] for item in sector_data]
    }
    
    return jsonify(result)

# Route untuk halaman tren pertumbuhan sektor
@app.route('/idx/sector-growth')
def idx_sector_growth():
    return render_template('idx/sector_growth.html', active_page='idx')

# Route untuk halaman top growth
@app.route('/idx/top-growth')
def idx_top_growth():
    return render_template('idx/top_growth.html', active_page='idx')

# Route untuk halaman top profit
@app.route('/idx/top-profit')
def idx_top_profit():
    return render_template('idx/top_profit.html', active_page='idx')

# Route untuk halaman revenue gabungan
@app.route('/idx/revenue')
def idx_revenue():
    return render_template('idx/revenue.html', active_page='idx')

# API untuk mendapatkan top 5 emiten dengan DER terendah per sektor
@app.route("/api/top-der")
def get_top_der():
    # Ambil parameter sektor dari query string
    sector = request.args.get('sector')
    year = int(request.args.get('year', 2021))
    
    if not sector:
        return jsonify({"error": "Sector parameter is required"}), 400
    
    # Pipeline aggregation untuk menghitung DER dan mengambil top 5 terendah
    pipeline = [
        {"$match": {
            "sector": {"$regex": sector, "$options": "i"},  # Case insensitive search
            "short_term_borrowing.current_year": {"$exists": True, "$ne": None},
            "long_term_borrowing.current_year": {"$exists": True, "$ne": None},
            "equity.current_year": {"$exists": True, "$ne": None, "$gt": 0}  # Pastikan equity positif untuk menghindari DER negatif
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"},
            "short_term_borrowing": {"$first": "$short_term_borrowing.current_year"},
            "long_term_borrowing": {"$first": "$long_term_borrowing.current_year"},
            "equity": {"$first": "$equity.current_year"},
            "reporting_year": {"$first": "$reporting_year"}
        }},
        # Tambahkan field DER dengan perhitungan
        {"$addFields": {
            "der": {
                "$divide": [
                    {"$add": ["$short_term_borrowing", "$long_term_borrowing"]},
                    "$equity"
                ]
            },
            "total_debt": {"$add": ["$short_term_borrowing", "$long_term_borrowing"]}
        }},
        {"$sort": {"der": 1}},  # Urutkan dari terendah (terbaik)
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1,
            "calculated_ratios": {
                "debt_to_equity": "$der"  # Agar kompatibel dengan template
            },
            "total_debt": 1, 
            "equity": {"current_year": "$equity"}  # Restruktur untuk kompatibilitas template
        }}
    ]
    
    top_der = list(collection_idx.aggregate(pipeline))
    
    return jsonify(top_der)

# API untuk mendapatkan DER emiten dan rata-rata sektor
@app.route("/api/emiten-der")
def get_emiten_der():
    # Ambil parameter emiten dari query string
    emiten_code = request.args.get('emiten')
    year = int(request.args.get('year', 2021))
    
    if not emiten_code:
        return jsonify({"error": "Emiten parameter is required"}), 400
    
    # Dapatkan data emiten termasuk sektor
    emiten_data = collection_idx.find_one({"company_code": emiten_code, "reporting_year": year})
    
    if not emiten_data:
        return jsonify({"error": "Emiten not found"}), 404
    
    sector = emiten_data.get("sector")
    
    # Hitung DER untuk emiten yang dipilih
    short_term = emiten_data.get("short_term_borrowing", {}).get("current_year", 0) or 0
    long_term = emiten_data.get("long_term_borrowing", {}).get("current_year", 0) or 0
    equity = emiten_data.get("equity", {}).get("current_year", 0) or 0
    
    emiten_der = None
    if equity > 0:
        emiten_der = (short_term + long_term) / equity
    
    # Pipeline aggregation untuk menghitung rata-rata DER sektor
    pipeline = [
        {"$match": {
            "sector": sector,
            "short_term_borrowing.current_year": {"$ne": None},
            "long_term_borrowing.current_year": {"$ne": None},
            "equity.current_year": {"$ne": None, "$gt": 0},  # Pastikan equity positif
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "short_term_borrowing": {"$first": "$short_term_borrowing.current_year"},
            "long_term_borrowing": {"$first": "$long_term_borrowing.current_year"},
            "equity": {"$first": "$equity.current_year"}
        }},
        # Tambahkan field DER dengan perhitungan
        {"$addFields": {
            "der": {
                "$divide": [
                    {"$add": ["$short_term_borrowing", "$long_term_borrowing"]},
                    "$equity"
                ]
            }
        }},
        # Hitung rata-rata DER
        {"$group": {
            "_id": None,
            "avg_der": {"$avg": "$der"},
            "count": {"$sum": 1}
        }}
    ]
    
    sector_result = list(collection_idx.aggregate(pipeline))
    sector_avg_der = sector_result[0]["avg_der"] if sector_result else None
    count_emiten = sector_result[0]["count"] if sector_result else 0
    
    # Mendapatkan daftar tahun unik untuk dropdown
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    
    # Mendapatkan daftar semua emiten untuk dropdown
    all_emitens = list(collection_idx.find(
        {"company_code": {"$exists": True, "$ne": ""}},
        {"_id": 0, "company_code": 1, "emiten": 1}
    ).distinct("company_code"))
    
    return jsonify({
        "emiten": emiten_code,
        "emiten_name": emiten_data.get("emiten"),
        "sector": sector,
        "emiten_der": emiten_der,
        "sector_avg_der": sector_avg_der,
        "count_emiten_in_sector": count_emiten,
        "years": distinct_years,
        "emitens": all_emitens
    })

# Route untuk halaman DER (Debt to Equity Ratio)
@app.route('/idx/der')
def idx_der():
    return render_template('idx/der.html', active_page='idx')

# API endpoint untuk mengambil semua sektor yang tersedia
@app.route('/api/all-sectors')
def get_all_sectors():
    sectors = collection_idx.distinct("sector")
    # Filter out None values and sort
    sectors = sorted([sector for sector in sectors if sector])
    return jsonify(sectors)

# API endpoint untuk mengambil daftar emiten (untuk dropdown)
@app.route('/api/emiten-list')
def get_emiten_list():
    pipeline = [
        {"$match": {"company_code": {"$exists": True, "$ne": None}}},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"}
        }},
        {"$sort": {"company_code": 1}},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1
        }}
    ]
    
    emiten_list = list(collection_idx.aggregate(pipeline))
    return jsonify(emiten_list)

# API endpoint untuk membandingkan DER emiten dengan rata-rata sektornya
@app.route('/api/compare-der')
def compare_der():
    emiten_code = request.args.get('emiten')
    year = int(request.args.get('year', 2021))
    
    if not emiten_code:
        return jsonify({})
    
    # Ambil data emiten yang dipilih
    emiten_data = collection_idx.find_one({
        "company_code": emiten_code,
        "reporting_year": year,
        "short_term_borrowing.current_year": {"$exists": True},
        "long_term_borrowing.current_year": {"$exists": True},
        "equity.current_year": {"$exists": True, "$gt": 0}
    })
    
    if not emiten_data:
        return jsonify({})
    
    # Ambil sektor dari emiten yang dipilih
    sector = emiten_data.get("sector")
    
    # Hitung DER untuk emiten yang dipilih
    short_term = emiten_data.get("short_term_borrowing", {}).get("current_year", 0) or 0
    long_term = emiten_data.get("long_term_borrowing", {}).get("current_year", 0) or 0
    equity = emiten_data.get("equity", {}).get("current_year", 0) or 0
    
    emiten_der = None
    if equity > 0:
        emiten_der = (short_term + long_term) / equity
    
    # Pipeline aggregation untuk menghitung rata-rata DER sektor
    pipeline = [
        {"$match": {
            "sector": sector,
            "short_term_borrowing.current_year": {"$ne": None},
            "long_term_borrowing.current_year": {"$ne": None},
            "equity.current_year": {"$ne": None, "$gt": 0},  # Pastikan equity positif
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "short_term_borrowing": {"$first": "$short_term_borrowing.current_year"},
            "long_term_borrowing": {"$first": "$long_term_borrowing.current_year"},
            "equity": {"$first": "$equity.current_year"}
        }},
        # Tambahkan field DER dengan perhitungan
        {"$addFields": {
            "der": {
                "$divide": [
                    {"$add": ["$short_term_borrowing", "$long_term_borrowing"]},
                    "$equity"
                ]
            }
        }},
        # Hitung rata-rata DER
        {"$group": {
            "_id": None,
            "avg_der": {"$avg": "$der"},
            "count": {"$sum": 1}
        }}
    ]
    
    sector_der_data = list(collection_idx.aggregate(pipeline))
    
    if not sector_der_data:
        return jsonify({})
    
    sector_avg_der = sector_der_data[0].get("avg_der", 0)
    total_emiten = sector_der_data[0].get("count", 0)
    
    result = {
        "company_code": emiten_code,
        "emiten_name": emiten_data.get("emiten"),
        "sector": sector,
        "emiten_der": emiten_der,
        "sector_avg_der": sector_avg_der,
        "total_emiten": total_emiten
    }
    
    return jsonify(result)

# API untuk mendapatkan top 5 emiten dengan aset terbesar per sektor
@app.route("/api/top-assets")
def get_top_assets():
    # Ambil parameter sektor dari query string
    sector = request.args.get('sector')
    year = int(request.args.get('year', 2021))
    
    if not sector:
        return jsonify({"error": "Sector parameter is required"}), 400
    
    # Pipeline aggregation untuk mendapatkan top 5 dengan aset terbesar berdasarkan sektor
    pipeline = [
        {"$match": {
            "sector": {"$regex": sector, "$options": "i"},  # Case insensitive search
            "assets.current_year": {"$exists": True, "$ne": None},
            "reporting_year": year
        }},
        # Group berdasarkan company_code untuk menghindari duplikasi
        {"$group": {
            "_id": "$company_code",
            "emiten": {"$first": "$emiten"},
            "company_code": {"$first": "$company_code"},
            "sector": {"$first": "$sector"},
            "assets": {"$first": "$assets"},
            "reporting_year": {"$first": "$reporting_year"}
        }},
        {"$sort": {"assets.current_year": -1}},  # Urutkan dari terbesar
        {"$limit": 5},
        {"$project": {
            "_id": 0,
            "emiten": 1,
            "company_code": 1,
            "sector": 1,
            "assets": 1,
            "reporting_year": 1
        }}
    ]
    
    top_assets = list(collection_idx.aggregate(pipeline))
    
    # Mendapatkan daftar tahun unik untuk dropdown
    distinct_years = sorted(collection_idx.distinct("reporting_year"))
    
    return jsonify({
        "data": top_assets,
        "years": distinct_years
    })

@app.route('/yfinance/5tahun')
def yfinance_lima_tahun():
    return render_template('yfinance/5y.html', active_page='yfinance')

@app.route("/api/tickers/5tahun")
def get_tickers_lima_tahun():
    tickers = collection_yfinance_5tahun.distinct("ticker")
    return jsonify(tickers)

@app.route("/api/stock/5tahun/<ticker>")
def get_stock_data_lima_tahun(ticker):
    data = collection_yfinance_5tahun.find(
        {"ticker": ticker},
        {
            "_id": 0,
            "StartDate": 1,
            "Open": 1,
            "Close": 1,
            "Low": 1,
            "High": 1,
            "AvgVolume": 1,
            "MaxVolume": 1
        }
    ).sort("StartDate", 1)

    result = []
    for d in data:
        start_date = d.get("StartDate", "")
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        elif isinstance(start_date, str) and "T" in start_date:
            start_date = start_date.split("T")[0]

        result.append({
            "StartDate": start_date,
            "open": d.get("Open", 0),
            "close": d.get("Close", 0),
            "high": d.get("High", 0),
            "low": d.get("Low", 0),
            "avgVolume": d.get("AvgVolume", 0),
            "maxVolume": d.get("MaxVolume", 0)
        })

    return jsonify(result)

# Route untuk halaman top assets
@app.route('/idx/top-assets')
def idx_top_assets():
    return render_template('idx/top_assets.html', active_page='idx')

@app.route('/market_news')
def market_news():
    return render_template('iqplus/market.html', active_page='market_news')

@app.route("/api/market_news")
def get_market_news():
    # Ambil data dari MongoDB, tanpa _id, diurutkan dari tanggal terbaru
    data = collection_market_news.find(
        {
            "_id": 0,
            "judul": 1,
            "tanggal_artikel": 1,
            "link": 1,
            "ringkasan": 1
        }
    ).sort("tanggal_artikel", -1)

    # Ubah ke list dan return sebagai JSON
    return jsonify({
        "data": dumps(data)  # Menggunakan dumps untuk mengubah BSON ke JSON
    })

@app.route("/api/test")
def test_data():
    data = list(collection_market_news.find())
    print(data)  # buat debug di terminal
    return jsonify(data)

# Jalankan Flask
if __name__ == "__main__":
    # app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
