from ztom import ActionOrder


# compatibility
class OrderWithAim(ActionOrder):

    def __init__(self, symbol, amount: float, price: float, side: str,
                 cancel_threshold: float=0.000001, max_order_updates: int=10):

        print("Please change OrderWithAim to ActionOrder")
        input("Press Enter to continue...")
        super().__init__(symbol, amount, price, side, cancel_threshold, max_order_updates)

    pass
