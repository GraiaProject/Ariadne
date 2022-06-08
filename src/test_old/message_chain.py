import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain

if __name__ == "__main__":
    chain_1 = MessageChain(Plain("hello"), Plain("Hi"))
    chain_2 = chain_1.merge(copy=True)
    print(chain_1)
    print(chain_2)
    print(chain_2 * 5)
    chain_2 *= 3
    print(chain_2)
    print("hello" in chain_2)
    print(chain_2.find_sub_chain("Hi"))
    print(
        MessageChain.parse_obj(
            [{"type": "At", "target": 12345}, {"type": "Plain", "text": "hello"}, {"type": "Broken"}, 5]
        )
    )
