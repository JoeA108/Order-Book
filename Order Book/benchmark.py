import time
import random
import statistics
import io
import contextlib
import order_book_v1 as v1
import order_book as v2


def v1_add(book, side, id, quantity, owner, price):
    book.add_order(side, id, quantity, price)


def v1_cancel(book, id, owner):
    book.cancel_order(id)


def v2_add(book, side, id, quantity, owner, price):
    book.add_order(side, id, quantity, owner=owner, price=price)


def v2_cancel(book, id, owner):
    book.cancel_order(id, owner)


def make_orders(depth) -> list[tuple]:
    random.seed(69)
    orders = []

    for i in range(depth):
        side = random.choice(["bid", "ask"])
        id = f"o{i}"
        quantity = random.randint(5,20)
        owner = random.choice(["joe", "itzi"]) if side == "bid" else random.choice(["fintan", "oli"])
        price = 1000 - random.randint(1,20) if side == "bid" else 1000 + random.randint(1,20)
        orders.append(("add", side, id, quantity, owner, price))

    random.shuffle(orders)
    return orders


def scenario_resting_adds(depth: int) -> tuple[list[tuple], list[tuple]]:
    setup = []
    timed = make_orders(depth)

    return setup, timed


def scenario_cancels(depth: int) -> tuple[list[tuple], list[tuple]]:
    setup = make_orders(depth)
    timed = []

    for order in setup:
        timed.append(("cancel", order[2], order[4]))
    random.shuffle(timed)

    return setup, timed


def scenario_crossing(depth: int) -> tuple[list[tuple], list[tuple]]:
    setup = make_orders(depth)
    timed = []
    n_id = 0

    for order in setup:
        side = "bid" if order[1] == "ask" else "ask"
        id = f"c{n_id}"
        quantity = order[3]
        owner = "sam" if order[1] == "ask" else "matt"
        price = order[5] + random.randint(1,5) if order[1] == "ask" else order[5] - random.randint(1,5)
        timed.append(("add", side, id, quantity, owner, price))

        refill = ("add", order[1], f"r{n_id}", quantity, "james", order[5])
        timed.append(refill)

        n_id += 1

    return setup, timed


def scenario_mixed(depth: int) -> tuple[list[tuple], list[tuple]]:
    setup = make_orders(depth)
    timed = []
    current_orders = []

    for order in setup:
        current_orders.append((order[2], order[4]))

    for i in range(len(setup)):
        n = random.randint(1, 10)

        if n <= 6:
            side = random.choice(["bid", "ask"])
            quantity = random.randint(5,20)
            owner = "kabelan" if side == "bid" else "finn"
            price = 980 + random.randint(0,40)
            timed.append(("add", side, f"m{i}", quantity, owner, price))
            current_orders.append((f"m{i}", owner))
        elif n != 10:
            id_owner = random.choice(current_orders)
            timed.append(("cancel", *id_owner))
            current_orders.remove(id_owner)
        else:
            side = random.choice(["bid", "ask"])
            quantity = random.randint(15,70)
            owner = "santi"
            price = None
            timed.append(("add", side, f"m{i}", quantity, owner, price))

    return setup, timed


def measure_throuput(Book, add, cancel, setup, timed) -> float:

    throughputs = []

    for _ in range(5):
        book = Book()
        for op in setup:
            add(book, *op[1:])

        with contextlib.redirect_stdout(io.StringIO()):

            start = time.perf_counter_ns()

            for op in timed:
                if op[0] == "add":
                    add(book, *op[1:])
                else:
                    cancel(book, *op[1:])

            end = time.perf_counter_ns()

        throughputs.append(len(timed) / ((end - start) / 1000000000))

    return max(throughputs)


def measure_latency(Book, add, cancel, setup, timed) -> tuple[float, float, float]:

    t_ops = []

    with contextlib.redirect_stdout(io.StringIO()):

        for _ in range(5):

            book = Book()
            for op in setup:
                add(book, *op[1:])

            for op in timed:

                start = time.perf_counter_ns()

                if op[0] == "add":
                    add(book, *op[1:])
                else:
                    cancel(book, *op[1:])  

                t = time.perf_counter_ns() - start  

                t_ops.append(t)   

    cuts = statistics.quantiles(t_ops, n=100)  

    p50 = cuts[49] / 1000
    p99 = cuts[98] / 1000
    max_t = max(t_ops) / 1000

    return p50, p99, max_t 


def same_trades(setup, timed) -> bool:
    v1_book = v1.Book()
    v2_book = v2.Book()

    with contextlib.redirect_stdout(io.StringIO()):

        for op in setup:
            v1_add(v1_book, *op[1:])
            v2_add(v2_book, *op[1:])

        for op in timed:
            if op[0] == "add":
                v1_add(v1_book, *op[1:])
                v2_add(v2_book, *op[1:])
            else:
                v1_cancel(v1_book, *op[1:])
                v2_cancel(v2_book, *op[1:])

    v1_trades = []
    v2_trades = []

    for trade in v1_book.trade_log:
        v1_trades.append((trade.quantity, trade.price, trade.maker_id, trade.taker_id))

    for trade in v2_book.trade_log:
        v2_trades.append((trade.quantity, trade.price, trade.maker_id, trade.taker_id))

    return v1_trades == v2_trades


if __name__ == "__main__":
    depths = [100, 1000, 10000]
    scenario_data = {}
    scenarios = [scenario_resting_adds, scenario_cancels, scenario_crossing, scenario_mixed]
    scenario_names = ["resting adds", "cancels", "crossing", "mixed"]

    for scenario, name in zip(scenarios, scenario_names):
        for d in depths:
            print(f"running {name} at depth {d}...")

            v1_tp = measure_throuput(v1.Book, v1_add, v1_cancel, *scenario(d))
            v2_tp = measure_throuput(v2.Book, v2_add, v2_cancel, *scenario(d))

            speedup = v2_tp / v1_tp

            v1_latencies = measure_latency(v1.Book, v1_add, v1_cancel, *scenario(d))
            v2_latencies = measure_latency(v2.Book, v2_add, v2_cancel, *scenario(d))

            p50s = (v1_latencies[0], v2_latencies[0])
            p99s = (v1_latencies[1], v2_latencies[1])

            s_trades = same_trades(*scenario(d))

            scenario_data[(name, d)] = [d, s_trades, (v1_tp, v2_tp), speedup, p50s, p99s]

    header = f"{'Scenario':<14} | {'Depth':^7} | {'v1 ops/s':^12} | {'v2 ops/s':^12} | {'Speedup':^8} | {'v1 p50':^8} | {'v2 p50':^8} | {'v1 p99':^8} | {'v2 p99':^8} | {'Same Trades':^11}"
    print(header)

    print('-' * len(header))

    for (name, d), value in scenario_data.items():
        v1_ops = value[2][0]
        v2_ops = value[2][1]
        speedup = value[3]
        v1_p50 = value[4][0]
        v2_p50 = value[4][1]
        v1_p99 = value[5][0]
        v2_p99 = value[5][1]

        if value[1]:
            s_t = "YES"
        else:
            s_t = "NO"

        print(f"{name:<14} | {d:^7,} | {v1_ops:^12,.0f} | {v2_ops:^12,.0f} | {speedup:^8.1f} | {v1_p50:^8.2f} | {v2_p50:^8.2f} | {v1_p99:^8.2f} | {v2_p99:^8.2f} | {s_t:^11}")