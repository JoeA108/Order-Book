from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:

    side: str
    id: str
    quantity: int
    seq_number: int
    price: Optional[int] = None


@dataclass(frozen = True)
class Trade:

    price: int
    quantity: int
    maker_id: str
    taker_id: str
    maker_side: str


class Book:

    def __init__(self) -> None:
        self.trade_log: list = []
        self.bids : list = []
        self.asks : list = []
        self.seq_number : int = 0

    def __str__(self) -> str:
        return f"Book(bids={self.bids}, asks={self.asks}, seq_number={self.seq_number})"

    def __repr__(self) -> str:
        return f"Book(bids={self.bids}, asks={self.asks}, seq_number={self.seq_number})"

    def walk_side(self, incoming_order: Order, other_side: list) -> bool:
        if incoming_order.quantity < other_side[0].quantity:
            self.trade_log.append(Trade(price=other_side[0].price, quantity=incoming_order.quantity, maker_id=other_side[0].id, taker_id=incoming_order.id, maker_side=other_side[0].side))
            other_side[0].quantity -= incoming_order.quantity
            return False

        elif incoming_order.quantity == other_side[0].quantity:
            self.trade_log.append(Trade(price=other_side[0].price, quantity=incoming_order.quantity, maker_id=other_side[0].id, taker_id=incoming_order.id, maker_side=other_side[0].side))
            other_side.pop(0)
            return False
        else:
            self.trade_log.append(Trade(price=other_side[0].price, quantity=other_side[0].quantity, maker_id=other_side[0].id, taker_id=incoming_order.id, maker_side=other_side[0].side))
            incoming_order.quantity -= other_side[0].quantity
            other_side.pop(0)
            return True

    def market_order(self, incoming_order: Order, other_side: list) -> None:

        if not other_side:
            print("Rest of order cancelled.")
            return

        if self.walk_side(incoming_order, other_side):
            self.market_order(incoming_order, other_side)
        return

    def limit_order(self, incoming_order: Order, order_side: list, other_side: list) -> None:

        if not other_side or incoming_order.side == "bid" and incoming_order.price < other_side[0].price or incoming_order.side == "ask" and incoming_order.price > other_side[0].price:
            self.add_to_side(order_side, incoming_order)
            return
        
        if self.walk_side(incoming_order, other_side):
            self.limit_order(incoming_order, order_side, other_side)
        return            
        
    def add_to_side(self, side: list, new_order: Order) -> None:
        
        index: int = 0
                           
        for order in side:

            if new_order.side == "bid":
                if new_order.price > order.price:
                    side.insert(index, new_order)
                    return
                else:
                    index += 1
            
            elif new_order.side == "ask":
                if new_order.price < order.price:
                    side.insert(index, new_order)
                    return
                else:
                    index += 1
          
        side.append(new_order)
        return
        
    def add_order(self, side: str, id: str, quantity: int, price: Optional[int] = None) -> None:

        if any(order.id == id for order in self.bids) or any(order.id == id for order in self.asks):
            print(f"Order ID: {id} already exists. Order rejected.")
            return
                        
        if price is not None and price <=0 or quantity <= 0:
            print(f"Order: {id} rejected. Price and quantity must be greater than 0.")
            return

        if side not in ("bid", "ask"):
            print("Error in order entry, order type must be 'bid' or 'ask'.")
            return

        if price is None:

            if side == "bid":
                if not self.asks:
                    print("Market Order Cancelled.")
                    return None
                self.market_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number), self.asks)
                self.seq_number += 1

            elif side == "ask":
                if not self.bids:
                    print("Market Order Cancelled.")
                    return None
                self.market_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number), self.bids)
                self.seq_number += 1

        else:

            if side == "bid":
                self.limit_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, price=price), self.bids, self.asks)
                self.seq_number += 1

            if side == "ask":
                self.limit_order(Order(side=side, id=id, quantity=quantity, seq_number=self.seq_number, price=price), self. asks, self.bids)
                self.seq_number += 1

    def cancel_order(self, id: str) -> None:
         
        for order in self.bids:
             
            if order.id == id:
                self.bids.remove(order)
                print(f"Order: {id} successfully canceled.")
                return

        for order in self.asks:
                          
            if order.id == id:
                self.asks.remove(order)
                print(f"Order: {id} successfully canceled.")
                return
             
        print(f"Order: {id} not found.")

    def best_bid(self) -> Optional[Order]:

        if not self.bids:
            return None

        return self.bids[0]

    def best_ask(self) -> Optional[Order]:

        if not self.asks:
            return None
    
        return self.asks[0]

    def quantity_at_price(self, price: int, side: list) -> int:

        total_quantity = 0

        for order in side:
            if order.price == price:
                total_quantity += order.quantity

        return total_quantity


book: Book = Book()
book.add_order("bid", "LimitBid1", 50, 100)
book.add_order("bid", "LimitBid2", 30, 110)
book.add_order("ask", "LimitAsk1", 40, 130)
book.add_order("ask", "LimitAsk2", 20, 135)
book.add_order("bid", "LimitBid3", 80, 138)
print(book.trade_log)