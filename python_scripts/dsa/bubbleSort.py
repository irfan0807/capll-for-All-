nums = [5, 3, 8, 1, 2]


for ele in range(len(nums)):
        for j in range(len(nums) -ele -1):
                if nums[j] > nums[j+1]:
                        nums[j] ,nums[j+1] = nums[j+1],nums[j]

print(nums)
