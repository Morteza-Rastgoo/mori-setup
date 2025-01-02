import math
import cmath
import unittest
from typing import Union, Dict, Any

class Calculator:
    def __init__(self):
        self._memory: Dict[str, Any] = {}

    def add(self, *numbers: Union[int, float, complex]) -> Union[int, float, complex]:
        """Add multiple numbers.
        
        Args:
            *numbers: Variable number of numeric values to add.
            
        Returns:
            The sum of all input numbers.
            
        Raises:
            TypeError: If any input is not a number.
        """
        if not all(isinstance(n, (int, float, complex)) for n in numbers):
            raise TypeError("All inputs must be numbers (int, float, or complex)")
        return sum(numbers)

    def subtract(self, a: Union[int, float, complex], b: Union[int, float, complex]) -> Union[int, float, complex]:
        """Subtract two numbers.
        
        Args:
            a: The first number (minuend).
            b: The second number (subtrahend).
            
        Returns:
            The difference between a and b (a - b).
            
        Raises:
            TypeError: If inputs are not numbers.
        """
        if not (isinstance(a, (int, float, complex)) and isinstance(b, (int, float, complex))):
            raise TypeError("Both inputs must be numbers (int, float, or complex)")
        return a - b

    def multiply(self, *numbers: Union[int, float, complex]) -> Union[int, float, complex]:
        """Multiply multiple numbers.
        
        Args:
            *numbers: Variable number of numeric values to multiply.
            
        Returns:
            The product of all input numbers.
            
        Raises:
            TypeError: If any input is not a number.
        """
        if not all(isinstance(n, (int, float, complex)) for n in numbers):
            raise TypeError("All inputs must be numbers (int, float, or complex)")
        result = 1
        for n in numbers:
            result *= n
        return result

    def divide(self, dividend: Union[int, float, complex], divisor: Union[int, float, complex]) -> Union[float, complex]:
        """Divide two numbers.
        
        Args:
            dividend: The number to be divided.
            divisor: The number to divide by.
            
        Returns:
            The quotient of the division.
            
        Raises:
            ValueError: If attempting to divide by zero.
            TypeError: If inputs are not numbers.
        """
        if not (isinstance(dividend, (int, float, complex)) and isinstance(divisor, (int, float, complex))):
            raise TypeError("Both inputs must be numbers (int, float, or complex)")
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return dividend / divisor

    def square_root(self, number: Union[int, float, complex]) -> Union[float, complex]:
        """Calculate the square root of a number.
        
        Args:
            number: The number to find the square root of.
            
        Returns:
            The square root of the input number.
            For negative real numbers, returns a complex number.
            
        Raises:
            TypeError: If input is not a number.
        """
        if not isinstance(number, (int, float, complex)):
            raise TypeError("Input must be a number (int, float, or complex)")
        if isinstance(number, (int, float)) and number < 0:
            return complex(0, math.sqrt(-number))
        return cmath.sqrt(number) if isinstance(number, complex) else math.sqrt(number)

    def power(self, base: Union[int, float, complex], exponent: Union[int, float]) -> Union[float, complex]:
        """Raise a number to a power.
        
        Args:
            base: The base number.
            exponent: The exponent to raise the base to.
            
        Returns:
            The result of base raised to the exponent.
            
        Raises:
            ValueError: If base is zero and exponent is non-positive.
            TypeError: If inputs are not numbers.
        """
        if not (isinstance(base, (int, float, complex)) and isinstance(exponent, (int, float))):
            raise TypeError("Base must be a number and exponent must be a real number")
        if base == 0 and exponent <= 0:
            raise ValueError("Cannot raise zero to a non-positive power")
        return pow(base, exponent)

    def store_and_recall(self, key: str, value: Union[int, float, complex]) -> None:
        """Store a value in memory.
        
        Args:
            key: The key to store the value under.
            value: The numeric value to store.
            
        Raises:
            TypeError: If value is not a number.
        """
        if not isinstance(value, (int, float, complex)):
            raise TypeError("Can only store numeric values")
        self._memory[key] = value

    def recall(self, key: str) -> Union[int, float, complex]:
        """Recall a value from memory.
        
        Args:
            key: The key of the value to recall.
            
        Returns:
            The stored value.
            
        Raises:
            KeyError: If the key doesn't exist in memory.
        """
        if key not in self._memory:
            raise KeyError(f"No value stored with key '{key}'")
        return self._memory[key]

class CalculatorTests(unittest.TestCase):
    """Unit tests for the Calculator class."""
    
    def setUp(self):
        self.calc = Calculator()
        
    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)
        self.assertEqual(self.calc.add(2.5, 3.7), 6.2)
        self.assertEqual(self.calc.add(1+2j, 3+4j), 4+6j)
        
    def test_subtract(self):
        self.assertEqual(self.calc.subtract(5, 3), 2)
        self.assertEqual(self.calc.subtract(2+3j, 1+1j), 1+2j)
        
    def test_multiply(self):
        self.assertEqual(self.calc.multiply(2, 3, 4), 24)
        self.assertEqual(self.calc.multiply(1+1j, 2+2j), 4j)
        
    def test_divide(self):
        self.assertEqual(self.calc.divide(10, 2), 5)
        with self.assertRaises(ValueError):
            self.calc.divide(1, 0)
            
    def test_square_root(self):
        self.assertEqual(self.calc.square_root(16), 4)
        self.assertEqual(self.calc.square_root(-1), 1j)
        
    def test_power(self):
        self.assertEqual(self.calc.power(2, 3), 8)
        with self.assertRaises(ValueError):
            self.calc.power(0, -1)
            
    def test_memory(self):
        self.calc.store_and_recall("test", 42)
        self.assertEqual(self.calc.recall("test"), 42)
        with self.assertRaises(KeyError):
            self.calc.recall("nonexistent")

if __name__ == "__main__":
    # Run unit tests
    unittest.main(argv=[''], exit=False)
    
    # Example usage
    calc = Calculator()
    
    print("\nBasic operations:")
    print(f"2 + 3 = {calc.add(2, 3)}")
    print(f"5 - 2 = {calc.subtract(5, 2)}")
    print(f"4 * 3 = {calc.multiply(4, 3)}")
    print(f"10 / 2 = {calc.divide(10, 2)}")
    
    print("\nComplex number operations:")
    print(f"(1+2j) + (3+4j) = {calc.add(1+2j, 3+4j)}")
    print(f"sqrt(-1) = {calc.square_root(-1)}")
    
    print("\nMemory functions:")
    calc.store_and_recall("result", 42)
    print(f"Stored value: {calc.recall('result')}")