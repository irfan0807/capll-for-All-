nums = [1, 2, 2, 3, 4, 4, 5]

print(list(set(nums)))


seen = {}

for num in nums:
        if num in seen:
                seen[num] +=1
        else:
                seen[num] = 1
print(list(seen.keys()))


# count the freq of numbers in list
count = {}
for num in nums:
                count[num] = count.get(num,0)+1
for i,v in count.items():
        print(f"{i} repeated {v} times")
