class Codec:

        def __init__(self):
                self.cache = {}

        def encode(self,longUrl:str) -> str:

                shortUrl = "https:tinyUrl/"+str(len(longUrl))

                self.cache[shortUrl] = longUrl

                return shortUrl



        def decode(self,shortUrl:str) -> str:
                if shortUrl in self.cache:
                        return self.cache[shortUrl]



url = "https://leetcode.com/problems/design-problem"

obj = Codec()
print(f"OriginalURl {url}")
encoded = obj.encode(url)
print(f"encodedURL + {encoded}")
decode = obj.decode(encoded)
print(f"decoded URL +{decode}")
