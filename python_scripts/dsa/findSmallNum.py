nums = [10, 25, 5, 40, 15]



# print(sorted(nums)[0])

#linear method 
small = float("-inf")
secSmall = float("-inf")
for num in nums:
        if num > small:
                secSmall = small
                small = nums
        elif num > secSmall and num !=small:
                secSmall = num


print(secSmall)

#secound small number

