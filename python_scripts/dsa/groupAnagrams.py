# Given an array of strings strs, group the anagrams together. You can return the answer in any order.

 

# Example 1:

# Input: strs = ["eat","tea","tan","ate","nat","bat"]

# Output: [["bat"],["nat","tan"],["ate","eat","tea"]]

# Explanation:

# There is no string in strs that can be rearranged to form "bat".
# The strings "nat" and "tan" are anagrams as they can be rearranged to form each other.
# The strings "ate", "eat", and "tea" are anagrams as they can be rearranged to form each other.
# Example 2:

# Input: strs = [""]

# Output: [[""]]

# Example 3:

# Input: strs = ["a"]

# Output: [["a"]]




def groupAnagram(strs):
        groupList = []
        seen = {}
        for word in strs:
                key = "".join(sorted(word))
                if key in seen:
                        seen[key].append(word)
                else:
                        seen[key] = [word]
        print(list(seen.values()))



strs = ["eat","tea","tan","ate","nat","bat"]
print(groupAnagram(strs))
