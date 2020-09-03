from functools import partial
import trio
from trimeter import run_on_each, amap, run_all


# Just the most basic smoke test of the three functions
async def test_basics():
    ran_on = []

    async def afn(value):
        ran_on.append(value)
        return value + 1

    await run_on_each(afn, [1, 2, 3])

    assert sorted(ran_on) == [1, 2, 3]

    async with amap(afn, [1, 2, 3]) as result_channel:
        results = []
        async for result in result_channel:
            results.append(result)
        assert sorted(results) == [2, 3, 4]

    results = await run_all(
        [
            partial(afn, 10),
            partial(afn, 11),
            partial(afn, 12),
        ]
    )
    assert results == [11, 12, 13]
