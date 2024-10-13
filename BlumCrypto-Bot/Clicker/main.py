import math

# Function to divide a number by 50
def divide_by_50(num):
    return num / 50

# Function to add 3 to a number
def add_3(num):
    return num + 3

# Function to calculate the power of 3 for a number
def power_of_3(num):
    return num ** 3

# Function to subtract 100 from a number
def subtract_100(num):
    return num - 100

# Function to calculate the square root of a number
def calculate_square_root(num):
    return math.sqrt(num)

# Function to add 85 to a number
def add_85(num):
    return num + 85

# Function to multiply a number by PI
def multiply_by_pi(num):
    return num * math.pi

# Function to divide a number by 180
def divide_by_180(num):
    return num / 180

# Function to calculate the sine of a number
def calculate_sin(num):
    return math.sin(num)

# Main function
def main():
    # Starting with 100
    num = 100
    
    # Perform the operations step by step
    num = divide_by_50(num)
    num = add_3(num)
    num = power_of_3(num)
    num = subtract_100(num)
    num = calculate_square_root(num)
    num = add_85(num)
    num = multiply_by_pi(num)
    num = divide_by_180(num)
    
    # Calculate the sine and convert the result to an integer
    result = int(calculate_sin(num))
    
    # Display the final result
    print("The answer is xd: ", result)

main()
