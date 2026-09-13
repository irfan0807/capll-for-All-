s = "aabbcdde"

count = {}


for char in s:
        if char in count:
                count[char] += 1
        else:
                count[char] = 1

for i,v in count.items():
        if v == 1:
                print(i)
                break

#most freqent Char

s1 = "aabbbcccc"
cache = {}
for char in s1:
        if char in cache:
                cache[char] +=1
        else:
                cache[char] = 1

print(max(cache,key=cache.get))
