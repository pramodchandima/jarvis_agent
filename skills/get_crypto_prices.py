import urllib.request
import json

def run():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,solana,ripple,dogecoin&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = json.loads(response.read().decode('utf-8'))
            
        btc = raw.get("bitcoin", {}).get("usd")
        eth = raw.get("ethereum", {}).get("usd")
        bnb = raw.get("binancecoin", {}).get("usd")
        sol = raw.get("solana", {}).get("usd")
        xrp = raw.get("ripple", {}).get("usd")
        doge = raw.get("dogecoin", {}).get("usd")
        
        return f"Cryptocurrency Prices (USD): BTC: ${btc:,}, ETH: ${eth:,}, BNB: ${bnb:,}, SOL: ${sol:,}, XRP: ${xrp}, DOGE: ${doge}."
    except Exception as e:
        return f"Failed to retrieve cryptocurrency prices: {e}"
