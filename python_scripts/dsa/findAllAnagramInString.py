# "Given two strings s and p, return an array of all the start indices of p's anagrams in s. You may return the answer in any order.
# "
 


# Input: s = "cbaebabacd", p = "abc"
# Output: [0,6]


def findAnagrams(s, p):
        k = len(p)
        result = []
        for i in range(len(s) - k + 1):
                window = s[i:i+k]
                if sorted(window) == sorted(p):
                        result.append(i)
        return result



print(findAnagrams(s = "cbaebabacd",p = "abc"))
