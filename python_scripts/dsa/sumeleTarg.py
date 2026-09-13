nums = [i for i in range(1, 101)]
target = 99

pair = {}

# # this solves the problem but
# j = len(nums) - 1
# for i in range(len(nums)):
#       for k in range(j,0,-1):
#               if nums[i] + nums[k] == target:
#                               pair[i] = [i,k]

# for i,j in pair.items():
#       print(j)

cache = {}
for index ,num in enumerate(nums):
        # print(index)

        req = target - num

        if req in cache:
                print(cache[req],index)
                break

        cache[num] = index
