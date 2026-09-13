nums = [1, 2, 3, 2, 4, 1]

seen = {}

for num in nums:
        if num in seen:
                seen[num] +=1
        else:
                seen[num] = 1

for i in seen:
        if seen[i] > 1:
                print(i)
