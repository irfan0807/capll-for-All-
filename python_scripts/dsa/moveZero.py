nums = [0, 1, 0, 3, 12]

#linear solution
# temp = []
# # finalList = []
# for ele in nums:
#       if ele != 0:
#               temp.append(ele)

# temp += [0] * nums.count(0)

# print(temp)

write_index = 0
for ele in nums:
        if ele != 0:
                nums[write_index] = ele
                write_index +=1

for i in range(write_index,len(nums)):
        nums[i] = 0

print(nums)
