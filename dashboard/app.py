from flask import Flask, jsonify, render_template
# from pymongo import MongoClient
from db import collection_yfinance, collection_idx
from bson.json_util import dumps

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/tickers")
def get_tickers():
    tickers = collection_yfinance.distinct("ticker")
    return jsonify(tickers)

@app.route('/idx')
def idx():
    return render_template('idx/index.html', active_page='idx')

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

@app.route('/yfinance')
def yfinance():
    return render_template('yfinance/3y.html', active_page='yfinance')

@app.route("/api/stock/<ticker>")
def get_stock_data(ticker):
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    # Ambil 3 tahun terakhir
    three_years_ago = datetime.now() - relativedelta(years=5)
    
    data = collection_yfinance.find(
        {"ticker": ticker, "Bulan": {"$gte": three_years_ago}},
        {"_id": 0, "Bulan": 1, "Open": 1, "High": 1, "Low": 1, "Close": 1, "Volume": 1}
    ).sort("Bulan", 1)

    # Format Bulan jadi string
    result = [
        {
            "Bulan": d["Bulan"].strftime("%Y-%m-%d"),
            "close": d["Close"],
            "volume": d["Volume"],
            "open" : d["Open"],
            "high" : d["High"],
            "low" : d["Low"]
        } for d in data
    ]
    return jsonify(result)

@app.route("/api/stock/latest/<ticker>")
def get_latest_stock(ticker):
    latest_data = collection_yfinance.find_one(
        {"ticker": ticker},
        {"_id": 0, "Bulan": 1, "Open": 1, "High": 1, "Low": 1, "Close": 1},
        sort=[("Bulan", -1)]
    )

    if latest_data:
        latest_data["Bulan"] = latest_data["Bulan"].strftime("%Y-%m-%d")
        return jsonify(latest_data)
    else:
        return jsonify({"error": "Data not found"}), 404

# Jalankan Flask
if __name__ == "__main__":
    app.run(debug=True)
