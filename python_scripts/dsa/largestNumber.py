nums = [10, 25, 5, 40, 15]



print(f"using max function finding largest number in list{nums} :{max(nums)}")

largest = nums[0]
for i in nums:
        if i > largest:
                largest = i

print(f"using the linear method to find largest number in list{nums} : {largest}")

largest = sorted(nums)

print(largest[::-1][0])
