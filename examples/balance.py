import ztom
ew = ztom.ccxtExchangeWrapper("binance",
                            api_key="J9L7pjFOnVJUpNrMVCxZaT8gSomtkBpll6MESONxxnapnR7V7qXfmru6WLheP5MB",
                            secret = "vciAExtP7LTQoAUE6LCtF4MFLVzhW8GOrAH0GTetC9Axttm3Mcdkmkm6MV2E5yFE")

balance = ew.fetch_balance()

non_zero_balances = {}
for k,v in balance.items():
    if isinstance(v, dict) and v.get("total", 0) > 0: 
        non_zero_balances[k] = v

print(non_zero_balances)

