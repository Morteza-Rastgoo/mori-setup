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
   ```