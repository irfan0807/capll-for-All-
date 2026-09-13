nums = [10, 25, 5, 40, 15]


k = 12
# l = len(nums)-k
# print(nums)

# temp = nums[:-k]
# ftemp = nums[l:]
# print(ftemp)

# print(temp)
# # Above method effected with larger number , when rotation number > length of
# the list

# print(f"merging the :" ,ftemp+temp)

# # below method dont
# k = k % len(nums)

# nums = nums[-k:]+nums[:-k]

# print(f"another method" , nums)

for i in range(k):
        lst = nums.pop()
        nums.insert(0,lst)

print(nums)
