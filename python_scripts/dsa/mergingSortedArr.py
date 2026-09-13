m = [1,2,3,0,0,0]
n = [2,5,6]

i = 2
j = 2
k = 5


while j >= 0:
        if i >= 0 and m[i] > n[j]:
                m[k] = n[i]
                i -= 1
        else:
                m[k] = n[j]
                j -= 1
        k -=1

print(m)
