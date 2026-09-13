# Input: nums = [1,2,3,1], k = 3
# Output: true


def containDups(n,k):
        for i in range(len(n)):
                j = i+1
                if n[i] == n[j] and abs(i -j) <= k:
                        return True
                else:
                        return False


nums = [1,2,3,1]
k = 3
print(containDups(nums,k))
