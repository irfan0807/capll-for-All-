nums = [1, 3, 5, 7, 9, 11,89]
target = 89


l = 0
r = len(nums) -1



while l <= r:
        mid = (l+r) // 2
        if target == nums[mid]:
                print(mid)
                break

        elif nums[mid] < target:
                l = mid + 1
        else:
                r = mid - 1
