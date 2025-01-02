def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        return a / b  # No error handling for division by zero

def main():
    # Test binary search
    arr = [1, 3, 5, 7, 9, 11, 13, 15]
    result = binary_search(arr, 7)
    print(f"Found 7 at index: {result}")
    
    # Test bubble sort
    unsorted = [64, 34, 25, 12, 22, 11, 90]
    sorted_arr = bubble_sort(unsorted)
    print(f"Sorted array: {sorted_arr}")
    
    # Test calculator
    calc = Calculator()
    print(f"Addition: {calc.add(5, 3)}")
    print(f"Division: {calc.divide(10, 2)}")

if __name__ == "__main__":
    main() 