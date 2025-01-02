from decimal import Decimal
    from functools import reduce

    class Calculator:
        def __init__(self):
            pass

        def divide(self, a: float | int | Decimal, b: float | int | Decimal) -> float | int | Decimal:
            if isinstance(a, (float, int)) and isinstance(b, (float, int)):
                return super().divide(a, b)
            elif isinstance(a, Decimal) and isinstance(b, Decimal):
                return a / b
            else:
                raise ValueError("Both inputs must be numbers of the same type")

        def add(self, *args: (float | int | Decimal)) -> float | int | Decimal:
            return reduce(lambda x, y: x + y, args, 0)

        def subtract(self, *args: (float | int | Decimal)) -> float | int | Decimal:
            result = self.add(*([-i for i in args]))
            return result if args else 0

        def multiply(self, *args: (float | int | Decimal)) -> float | int | Decimal:
            return reduce(lambda x, y: x * y, args, 1)

        def square_root(self, number: float | int | Decimal) -> float | Decimal:
            if isinstance(number, (float, int)):
                return number ** 0.5
            elif isinstance(number, Decimal):
                return number.sqrt()
            else:
                raise ValueError("Input must be a real number")

        def power(self, base: float | int | Decimal, exponent: int) -> float | Decimal:
            if isinstance(base, (float, int)):
                return base ** exponent
            elif isinstance(base, Decimal):
                return base ** Decimal(exponent)
            else:
                raise ValueError("Base must be a real number")

        def store_and_recall(self, key: str, value: float | int | Decimal) -> None:
            self._memory[key] = value

        def recall(self, key: str) -> float | int | Decimal:
            if key in self._memory:
                return self._memory[key]
            else:
                raise KeyError("No such memory key")

    calculator = Calculator()