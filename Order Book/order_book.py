from dataclasses import dataclass
from typing import Optional
from collections import deque
from bisect import insort


@dataclass
class Order:

    side: str
    id: str
    quantity: int
    seq_number: int
    owner: str
    price: Optional[int] = None


@dataclass(frozen = True)
class Trade:

    price: int
    quantity: int
    maker_id: str
    maker_owner: str
    taker_id: str
    taker_owner: str
    maker_side: str


class Book:

    def __init__(self) -> None:
        self.trade_log: list = []
        self.bid_levels: dict[int, deque[Order]] = {}
        self.bid_prices: list[int] = []
        self.ask_levels: dict[int, deque[Order]] = {}
        self.ask_prices: list[int] = []
        self.seq_number : int = 0
        self.orders_by_id: dict[str, Order] = {}

    def __str__(self) -> str:

        return f"Book(bid_levels={self.bid_levels}, ask_levels={self.ask_levels}, seq_number={self.seq_number})"

    def __repr__(self) -> str:

        return self.__str__()

    def walk_side(self, incoming_order: Order, levels: dict, prices: list, best_price: int) -> bool:

        level = levels[best_price]
        maker = level[0]

        if incoming_order.quantity < maker.quantity:
            self.trade_log.append(Trade(price=maker.price, quantity=incoming_order.quantity, maker_id=maker.id, maker_owner=maker.owner, taker_id=incoming_order.id, taker_owner=incoming_order.owner, maker_side=maker.side))
            maker.quantity -= incoming_order.quantity
            return False

        elif incoming_order.quantity == maker.quantity:
            del self.orders_by_id[maker.id]
            self.trade_log.append(Trade(price=maker.price, quantity=incoming_order.quantity, maker_id=maker.id, maker_owner=maker.owner, taker_id=incoming_order.id, taker_owner=incoming_order.owner, maker_side=maker.side))
            level.popleft()

            if not level:
                del levels[best_price]
                prices.remove(best_price)

            return False
        
        else:
            del self.orders_by_id[maker.id]
            self.trade_log.append(Trade(price=maker.price, quantity=maker.quantity, maker_id=maker.id, maker_owner=maker.owner, taker_id=incoming_order.id, taker_owner=incoming_order.owner, maker_side=maker.side))
            incoming_order.quantity -= maker.quantity
            level.popleft()

            if not level: 
                del levels[best_price]
                prices.remove(best_price)

            return True
        
    def market_order(self, incoming_order: Order, levels: dict, prices: list) -> None:

        while prices:

            best_price = prices[0] if incoming_order.side == "bid" else prices[-1]

            if not self.walk_side(incoming_order, levels, prices, best_price):

                return

        print("Rest of order cancelled.")

    def limit_order(self, incoming_order: Order, order_levels: dict, order_prices: list, other_levels: dict, other_prices: list) -> None:

        while True:

            if not other_prices or incoming_order.side == "bid" and incoming_order.price < other_prices[0] or incoming_order.side == "ask" and incoming_order.price > other_prices[-1]:
                self.add_to_side(order_levels, order_prices, incoming_order)
                return

            best_price = other_prices[0] if incoming_order.side == "bid" else other_prices[-1]

            if not self.walk_side(incoming_order, other_levels, other_prices, best_price):
                return

    def add_to_side(self, levels: dict, prices: list, new_order: Order) -> None:

        self.orders_by_id[new_order.id] = new_order

        if new_order.price not in levels:
            insort(prices, new_order.price)
            levels[new_order.price] = deque()

        levels[new_order.price].append(new_order)

        return
        
    def add_order(self, side: str, id: str, quantity: int, owner: str, price: Optional[int] = None) -> list[Trade]:

        if id in self.orders_by_id:
            print(f"Order ID: {id} already exists. Order rejected.")
            return []
                        
        if price is not None and price <=0 or quantity <= 0:
            print(f"Order: {id} rejected. Price and quantity must be greater than 0.")
            return []

        if side not in ("bid", "ask"):
            print("Error in order entry, order type must be 'bid' or 'ask'.")
            return []

        if not isinstance(owner, str) or not owner:
            print(f"Order: {id} rejected. Owner must be a non-empty string.")
            return []

        start = len(self.trade_log)

        if price is None:
            if side == "bid":
                if not self.ask_prices:
                    print("Market Order Cancelled.")
                    return self.trade_log[start:]
                
                self.market_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, owner=owner), self.ask_levels, self.ask_prices)
                self.seq_number += 1

            elif side == "ask":
                if not self.bid_prices:
                    print("Market Order Cancelled.")
                    return self.trade_log[start:]

                self.market_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, owner=owner), self.bid_levels, self.bid_prices)
                self.seq_number += 1

        else:
            if side == "bid":
                self.limit_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, owner=owner, price=price), self.bid_levels, self.bid_prices, self.ask_levels, self.ask_prices)
                self.seq_number += 1

            elif side == "ask":
                self.limit_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, owner=owner, price=price), self.ask_levels, self.ask_prices, self.bid_levels, self.bid_prices)
                self.seq_number += 1

        return self.trade_log[start:]

    def cancel_order(self, id: str, owner: str) -> None:

        order = self.orders_by_id.get(id)

        if order is None:
            print(f"Order: {id} not found.")
            return

        if order.owner != owner:
            print(f"Order: {id} rejected. Not owned by {owner}.")
            return

        del self.orders_by_id[id]

        levels = self.bid_levels if order.side == "bid" else self.ask_levels
        prices = self.bid_prices if order.side == "bid" else self.ask_prices
        level = levels[order.price]
        level.remove(order)

        if not level:
            del levels[order.price]
            prices.remove(order.price)

        print(f"Order: {id} cancelled successfully.")

    def best_bid(self) -> Optional[Order]:

        if not self.bid_prices:
            return None

        return self.bid_levels[self.bid_prices[-1]][0]

    def best_ask(self) -> Optional[Order]:

        if not self.ask_prices:
            return None

        return self.ask_levels[self.ask_prices[0]][0]

    def quantity_at_price(self, price: int, levels: dict) -> int:

        return sum(order.quantity for order in levels.get(price, []))

