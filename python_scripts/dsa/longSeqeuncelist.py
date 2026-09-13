nums = [100,4,200,1,3,2]

seen = set()
count = 0
for i in range(1,len(nums)-1):
        seen.add(i)

for i in nums:
        if i in seen:
                count +=1

print(count)
