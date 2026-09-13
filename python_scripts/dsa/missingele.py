nums = [1, 2, 3, 5, 6]


for i in nums:
        if nums.index(i)+1 != i:
                print(nums.index(i)+1)
                break


for i,v in enumerate(nums):
        if i+1 != v:
                print(i+1)
                break


n = 6

expected = n*(n+1) // 2

actual = sum(nums)

print(expected - actual)
