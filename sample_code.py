```python
   class Calculator:
       """
       A simple calculator that performs basic arithmetic operations.
       """

       def divide(self, a: float, b: float) -> float:
           """
           Divides the given numbers. Raises ZeroDivisionError if b is zero.

           :param a: The dividend (float).
           :param b: The divisor (float).
           :return: The result of the division (float).
           :raises ZeroDivisionError: If the divisor is zero.
           """
           if b == 0:
               raise ZeroDivisionError("Cannot divide by zero")
           return a / b

       def add(self, a: float, b: float) -> float:
           """
           Adds two numbers together. Raises TypeError if either input is not a number.

           :param a: The first number (float).
           :param b: The second number (float).
           :return: The sum of the two numbers (float).
           :raises TypeError: If either input is not a number.
           """
           if not isinstance(a, float) or not isinstance(b, float):
               raise TypeError("Both inputs must be numbers")
           return a + b

       def subtract(self, a: float, b: float) -> float:
           """
           Subtracts the second number from the first. Raises TypeError if either input is not a number.

           :param a: The first number (float).
           :param b: The second number (float).
           :return: The result of the subtraction (float).
           :raises TypeError: If either input is not a number.
           """
           if not isinstance(a, float) or not isinstance(b, float):
               raise TypeError("Both inputs must be numbers")
           return a - b

       def multiply(self, a: float, b: float) -> float:
           """
           Multiplies two numbers together. Raises TypeError if either input is not a number.

           :param a: The first number (float).
           :param b: The second number (float).
           :return: The product of the two numbers (float).
           :raises TypeError: If either input is not a number.
           """
           if not isinstance(a, float) or not isinstance(b, float):
               raise TypeError("Both inputs must be numbers")
           return a * b
   ```