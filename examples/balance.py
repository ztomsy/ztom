import os
from dotenv import load_dotenv
import ztom

load_dotenv()

api_key = os.getenv("ZTOM_API_KEY")
secret = os.getenv("ZTOM_SECRET")

ew = ztom.ccxtExchangeWrapper("binance",
                            api_key=api_key,
                            secret = secret)

balance = ew.fetch_balance()

non_zero_balances = {}
for k,v in balance.items():
    if isinstance(v, dict) and v.get("total", 0) > 0: 
        non_zero_balances[k] = v

print(non_zero_balances)

