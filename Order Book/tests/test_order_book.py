from order_book import Book, Trade


def test_crossing_limit_bid_fills_against_best_asks():

    book = Book()
    book.add_order("bid", "LimitBid1", 50, owner="jta", price=100)
    book.add_order("bid", "LimitBid2", 30, owner="icam", price=110)
    book.add_order("ask", "LimitAsk1", 40, owner="fes", price=130)
    book.add_order("ask", "LimitAsk2", 20, owner="mao", price=135)

    trades = book.add_order("bid", "LimitBid3", 80, owner="oxm", price=138)

    assert trades == [
        Trade(price=130, quantity=40, maker_id="LimitAsk1", maker_owner="fes",
            taker_id="LimitBid3", taker_owner="oxm", maker_side="ask"),
        Trade(price=135, quantity=20, maker_id="LimitAsk2", maker_owner="mao",
            taker_id="LimitBid3", taker_owner="oxm", maker_side="ask"),
    ]
    assert book.ask_prices == []
    assert book.orders_by_id["LimitBid3"].quantity == 20
    assert book.bid_prices == [100, 110, 138]


def test_non_crossing_orders_rest_without_trading():

    book = Book()

    assert book.add_order("bid", "LimitBid", 40, owner="jta", price=100) == []
    assert book.add_order("ask", "LimitAsk", 60, owner="fes", price=105) == []
    assert book.trade_log == []
    assert book.bid_prices == [100]
    assert book.ask_prices == [105]


def test_large_market_order_sweeps_whole_book():

    big_book = Book()
    for i in range(2000):
        assert big_book.add_order("ask", f"SmallAsk{i}", 1, owner="icam", price=100+i) == []
    trades = big_book.add_order("bid", "BigBid", 2000, owner="jta")

    assert len(big_book.trade_log) == 2000
    assert len(trades) == 2000
    assert big_book.orders_by_id == {}
    assert big_book.bid_prices == []
    assert big_book.ask_prices == []


def test_limit_order_partially_fills_then_rests():

    book = Book()
    for i in range(2000):
        book.add_order("ask", f"SmallAsk{i}", 1, owner="icam", price=100+i)

    trades = book.add_order("bid", "LimitBid", 2000, owner="jta", price=1100)

    assert len(trades) == 1001
    assert [t.price for t in trades] == list(range(100, 1101))
    assert book.bid_prices == [1100]
    assert book.orders_by_id["LimitBid"].quantity == 999
    assert len(book.ask_prices) == 999
    assert book.ask_prices[0] == 1101


def test_market_order_on_empty_book_returns_no_trades():

    book = Book()

    trades = book.add_order("bid", "MarketBid", 10, owner="jta")

    assert trades == []
    assert "MarketBid" not in book.orders_by_id
    assert book.bid_prices == []


def test_better_price_fills_first():

    book = Book()
    book.add_order("ask", "LimitAsk1", 1, owner="fes", price=105)
    book.add_order("ask", "LimitAsk2", 1, owner="mao", price=101)

    trades = book.add_order("bid", "MarketBid", 1, owner="jta")

    assert len(trades) == 1
    assert trades[0].price == 101
    assert trades[0].maker_id == "LimitAsk2"
    assert book.ask_prices == [105]


def test_same_price_fills_oldest_first():

    book = Book()
    book.add_order("bid", "LimitBid1", 20, owner="jta", price=100)
    book.add_order("bid", "LimitBid2", 20, owner="icam", price=100)
    assert book.add_order("ask", "LimitAsk", 20, owner="fes", price=95) == [
        Trade(price=100, quantity=20, maker_id="LimitBid1", maker_owner="jta",
            taker_id="LimitAsk", taker_owner="fes", maker_side="bid")
    ]

    assert book.trade_log == [
        Trade(price=100, quantity=20, maker_id="LimitBid1", maker_owner="jta",
                    taker_id="LimitAsk", taker_owner="fes", maker_side="bid")
    ]
    assert book.bid_prices == [100]
    assert book.ask_prices == []


def test_duplicate_id_rejected():

    book = Book()
    book.add_order("bid", "X", 10, owner="jta", price=100)

    trades = book.add_order("bid", "X", 50, owner="icam", price=105)

    assert trades == []
    assert book.orders_by_id["X"].quantity == 10
    assert book.orders_by_id["X"].owner == "jta"
    assert book.bid_prices == [100]


def test_invalid_orders_rejected():

    book = Book()

    assert book.add_order("bid", "ZeroPrice", 10, owner="jta", price=0) == []
    assert book.add_order("bid", "ZeroQty", 0, owner="jta", price=100) == []
    assert book.add_order("buy", "BadSide", 10, owner="jta", price=100) == []
    assert book.add_order("bid", "NoOwner", 10, owner="", price=100) == []

    assert book.orders_by_id == {}
    assert book.bid_prices == []
    assert book.ask_prices == []


def test_cancel_removes_order_and_empty_price_level():

    book = Book()
    book.add_order("bid", "LimitBid", 10, owner="jta", price=100)

    book.cancel_order("LimitBid", owner="jta")

    assert "LimitBid" not in book.orders_by_id
    assert 100 not in book.bid_levels
    assert book.bid_prices == []


def test_cancel_keeps_level_if_other_orders_remain():

    book = Book()
    book.add_order("bid", "LimitBid1", 10, owner="jta", price=100)
    book.add_order("bid", "LimitBid2", 20, owner="icam", price=100)

    book.cancel_order("LimitBid1", owner="jta")

    assert book.bid_prices == [100]
    assert [o.id for o in book.bid_levels[100]] == ["LimitBid2"]
    assert "LimitBid2" in book.orders_by_id


def test_cancel_by_wrong_owner_is_rejected():

    book = Book()
    book.add_order("bid", "LimitBid", 10, owner="jta", price=100)

    book.cancel_order("LimitBid", owner="icam")

    assert "LimitBid" in book.orders_by_id
    assert [o.id for o in book.bid_levels[100]] == ["LimitBid"]
    assert book.bid_prices == [100]


def test_best_bid_and_ask():

    book = Book()
    assert book.best_bid() is None
    assert book.best_ask() is None

    book.add_order("bid", "LimitBid1", 10, owner="jta", price=100)
    book.add_order("bid", "LimitBid2", 10, owner="jta", price=110)
    book.add_order("ask", "LimitAsk1", 10, owner="fes", price=120)
    book.add_order("ask", "LimitAsk2", 10, owner="fes", price=115)

    assert book.best_bid().price == 110
    assert book.best_ask().price == 115