from . import ActionOrderManager
from . import ccxtExchangeWrapper

# for compatibility
class OwaManager(ActionOrderManager):

    def __init__(self, exchange: ccxtExchangeWrapper, max_order_update_attempts=20, max_cancel_attempts=10,
                 request_sleep=0.0):
        print("Please change OwaManager to ActionOrderManager")
        input("Press Enter to continue...")

        super().__init__(exchange, max_order_update_attempts, max_cancel_attempts,
                     request_sleep)

    pass

