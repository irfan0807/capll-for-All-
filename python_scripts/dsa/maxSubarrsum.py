nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]

#find the maximum of sub array sum

current  = nums[0]
maximum = nums[0]

for num in nums[1:]:
        current = max(num,current+num)
        maximum = max(maximum,current)

print(maximum)
