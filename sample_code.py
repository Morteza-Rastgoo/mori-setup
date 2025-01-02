import math

    class Calculator:
        def __init__(self):
            pass

        def add(self, *numbers):
            return sum(numbers)

        def subtract(self, *args):
            return self.add([x for x in args if isinstance(x, (int, float))]) - self.add([y for y in args if not isinstance(y, (int, float))])

        def multiply(self, *args):
            return math.copysign(1, args[0]) * self.add([x*y for x, y in zip(args, reversed(args))])

        def divide(self, dividend, divisor):
            if divisor == 0:
                raise ValueError("Cannot divide by zero")
            return dividend / divisor

        def square_root(self, number):
            if number < 0:
                raise ValueError("Square root of negative numbers is not defined.")
            return math.sqrt(number)

        def power(self, base, exponent):
            return base ** exponent

        def store_and_recall(self, key, value):
            self._memory[key] = value

        def recall(self, key):
            if key not in self._memory:
                raise KeyError("No such memory key")
            return self._memory[key]

    if __name__ == "__main__":
        calc = Calculator()

        # Test basic operations
        print("Basic operations:")
        print(f"2 + 3 = {calc.add(2, 3)}")
        print(f"5 - 2 = {calc.subtract(5, 2)}")
        print(f"4 * 3 = {calc.multiply(4, 3)}")
        print(f"10 / 2 = {calc.divide(10, 2)}")

        # Test advanced operations
        print("\nAdvanced operations:")
        print(f"Square root of 16 = {calc.square_root(16)}")
        print(f"2 to the power of 3 = {calc.power(2, 3)}")

        # Test memory functions
        print("\nMemory functions:")
        calc.store_and_recall("result", 42)
        print(f"Stored value: {calc.recall('result')}")