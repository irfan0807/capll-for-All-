n = 153

numOfdigits = len(str(n))
sum_of_powers = 0

while n > 0:
        temp += n % 10
        sum_of_powers += temp**numOfdigits
        n = n // 10

print(sum_of_powers = n)
