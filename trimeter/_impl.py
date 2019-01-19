from functools import partial
import operator
import abc

import trio
import outcome
from async_generator import async_generator, yield_, asynccontextmanager
import attr


@async_generator
async def iter2aiter(iterable):
    for value in iterable:
        await yield_(value)


class Meter(abc.ABC):
    @abc.abstractmethod
    def new_state(self):
        pass


class MeterState(abc.ABC):
    @abc.abstractmethod
    async def wait_task_can_start(self):
        pass

    @abc.abstractmethod
    def notify_task_started(self):
        pass

    @abc.abstractmethod
    def notify_task_finished(self):
        pass


def _check_positive(self, attribute, value):
    if not value > 0:
        raise ValueError("{} must be > 0".format(attribute.name))


@attr.s(frozen=True)
class MaxMeter:
    max_at_once = attr.ib(converter=operator.index, validator=_check_positive)

    def new_state(self):
        return MaxState(self)


# XX if we ever get deadlock tracking it might be nice to use a
# CapacityLimiter here and attribute the token ownership correctly
# maybe notify_task_started should get the task object? Or run inside the
# task? that would complicate startup slightly (can't call the next
# wait_task_can_start until after calling notify_task_started), but nothing
# nursery.start can't solve.
class MaxState:
    def __init__(self, max_meter):
        self.sem = trio.Semaphore(
            initial_value=max_meter.max_at_once, max_value=max_meter.max_at_once
        )

    async def wait_task_can_start(self):
        await self.sem.acquire()

    def notify_task_started(self):
        # Already acquired the semaphore in wait_task_can_start
        pass

    def notify_task_finished(self):
        self.sem.release()


@attr.s(frozen=True)
class TokenBucketMeter:
    max_per_second = attr.ib(converter=float, validator=_check_positive)
    max_burst = attr.ib(default=1, converter=operator.index, validator=_check_positive)

    def __attrs_post_init__(self):
        _check_positive(self, "max_per_second", self.max_per_second)
        _check_positive(self, "max_burst", self.max_burst)

    def new_state(self):
        return TokenBucketState(self)


class TokenBucketState:
    def __init__(self, token_bucket_meter):
        self._max_per_second = token_bucket_meter.max_per_second
        self._max_burst = token_bucket_meter.max_burst
        # In some cases it may make more sense to initialize to max_burst...?
        # We allow accumulating partial tokens, so this can be a float
        self._tokens = 1
        # maybe the start time should be passed in? that would let a keyed
        # token bucket meter
        self._last_update_time = trio.current_time()

    def _update(self):
        now = trio.current_time()
        elapsed = now - self._last_update_time
        self._tokens += elapsed * self._max_per_second
        self._tokens = max(self._tokens, self._max_burst)
        self._last_update_time = now

    async def wait_task_can_start(self):
        while True:
            self._update()
            if self._tokens >= 1:
                break
            next_token_after = (1 - self._tokens) / self._max_per_second
            await trio.sleep(next_token_after)

    def notify_task_started(self):
        # Have to make sure max_burst clipping is up to date before we take
        # our token
        self._update()
        assert self._tokens >= 1
        self._tokens -= 1

    def notify_task_finished(self):
        pass


# XX should we have a special-case to allow KeyboardInterrupt to pass through?
async def _worker(
        async_fn, value, index, config
):
    if config.capture_outcome:
        result = await outcome.acapture(async_fn, value)
    else:
        result = await async_fn(value)
    if config.send_to is not None:
        if config.include_index and not config.include_value:
            result = (index, result)
        elif not config.include_index and config.include_value:
            result = (value, result)
        elif config.include_index and config.include_value:
            result = (index, value, result)
        await config.send_to.send(result)
    for meter_state in config.meter_states:
        meter_state.notify_task_finished()


@attr.s(frozen=True)
class Config:
    capture_outcome = attr.ib(converter=bool)
    include_index = attr.ib(converter=bool)
    include_value = attr.ib(converter=bool)
    send_to = attr.ib()
    meter_states = attr.ib()


async def run_on_each(
        async_fn,
        iterable,
        *,
        max_at_once=None,
        max_per_second=None,
        max_burst=1,
        iterable_is_async="guess",
        send_to=None,
        capture_outcome=False,
        include_index=False,
        include_value=False,
):
    try:
        # XX: allow users to pass in their own custom meters
        meters = []
        if max_at_once is not None:
            meters.append(MaxMeter(max_at_once))
        if max_per_second is not None:
            meters.append(TokenBucketMeter(max_per_second, max_burst))
        meter_states = [meter.new_state() for meter in meters]

        if iterable_is_async not in [True, False, "guess"]:
            raise ValueError("iterable_is_async must be bool or 'guess'")
        if iterable_is_async == "guess":
            iterable_is_async = hasattr(iterable, "__aiter__")
        if not iterable_is_async:
            iterable = iter2aiter(iterable)

        config = Config(
            capture_outcome=capture_outcome,
            include_index=include_index,
            include_value=include_value,
            send_to=send_to,
            meter_states=meter_states,
        )

        if config.capture_outcome and config.send_to is None:
            raise ValueError("if capture_outcome=True, send_to cannot be None")

        async with trio.open_nursery() as nursery:
            index = 0
            async for value in iterable:
                for meter_state in meter_states:
                    await meter_state.wait_task_can_start()
                for meter_state in meter_states:
                    meter_state.notify_task_started()
                nursery.start_soon(_worker, async_fn, value, index, config)
                index += 1
    finally:
        if send_to is not None:
            await send_to.aclose()



@asynccontextmanager
@async_generator
async def amap(
        async_fn,
        iterable,
        *,
        max_at_once=None,
        max_per_second=None,
        max_burst=1,
        iterable_is_async="guess",
        capture_outcome=False,
        include_index=False,
        include_value=False,
        max_buffer_size=0
):
    send_channel, receive_channel = trio.open_memory_channel(max_buffer_size)
    async with receive_channel:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(
                partial(
                    run_on_each,
                    # Pass through:
                    async_fn,
                    iterable,
                    max_at_once=max_at_once,
                    max_per_second=max_per_second,
                    max_burst=max_burst,
                    iterable_is_async=iterable_is_async,
                    capture_outcome=capture_outcome,
                    include_index=include_index,
                    include_value=include_value,
                    # Not a simple pass-through:
                    send_to=send_channel,
                )
            )
            await yield_(receive_channel)


async def run_all(
        async_fns,
        *,
        max_at_once=None,
        max_per_second=None,
        max_burst=1,
        iterable_is_async="guess",
        capture_outcome=False,
):
    results = [None] * operator.length_hint(async_fns)
    results_len = 0
    async with amap(
            lambda fn: fn(),
            async_fns,
            max_at_once=max_at_once,
            max_per_second=max_per_second,
            iterable_is_async=iterable_is_async,
            capture_outcome=capture_outcome,
            include_index=True,
    ) as enum_results:
        async for index, result in enum_results:
            required_len = index + 1
            results_len = max(required_len, results_len)
            if required_len > len(results):
                results += [None] * (required_len - len(results))
            results[index] = result
    del results[results_len:]
    return results
