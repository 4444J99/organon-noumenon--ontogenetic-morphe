"""
Regression and capacity tests for MessageBus bounded concurrency.
"""

import anyio
import pytest

from autogenrec.bus.message_bus import MessageBus
from autogenrec.core.signals import Message, MessageType


@pytest.mark.asyncio
async def test_all_matching_subscribers_invoked_exceeding_max_concurrent() -> None:
    """
    Test that when matching subscribers > max_concurrent_handlers,
    all subscribers are invoked exactly once and counted in total_messages_delivered.
    """
    bus = MessageBus(max_concurrent_handlers=2)
    invoked: list[int] = []

    def make_handler(index: int):  # type: ignore[no-untyped-def]
        async def handler(msg: Message) -> None:
            invoked.append(index)
        return handler

    # Register 5 subscribers for the same topic pattern
    for i in range(5):
        await bus.subscribe("events.test", make_handler(i))

    message = Message(
        type=MessageType.EVENT,
        topic="events.test",
        payload="data",
        source="test_source",
    )

    delivered = await bus.publish(message)

    assert delivered == 5
    assert len(invoked) == 5
    assert sorted(invoked) == [0, 1, 2, 3, 4]
    assert bus.stats.total_messages_delivered == 5


@pytest.mark.asyncio
async def test_peak_concurrency_bounded_by_max_concurrent() -> None:
    """
    Test that simultaneous handler executions never exceed max_concurrent_handlers.
    """
    max_concurrent = 3
    bus = MessageBus(max_concurrent_handlers=max_concurrent)

    current_concurrent = 0
    peak_concurrent = 0

    async def slow_handler(msg: Message) -> None:
        nonlocal current_concurrent, peak_concurrent
        current_concurrent += 1
        if current_concurrent > peak_concurrent:
            peak_concurrent = current_concurrent
        await anyio.sleep(0.05)
        current_concurrent -= 1

    # Register 10 subscribers
    for _ in range(10):
        await bus.subscribe("test.concurrent", slow_handler)

    message = Message.event("test.concurrent", "src", "payload")
    delivered = await bus.publish(message)

    assert delivered == 10
    assert peak_concurrent <= max_concurrent


@pytest.mark.asyncio
async def test_failing_handler_isolation_and_stats() -> None:
    """
    Test that a failing handler increments total_errors without stopping other handlers.
    """
    bus = MessageBus(max_concurrent_handlers=2)
    successful_invocations: list[str] = []

    async def ok_handler_1(msg: Message) -> None:
        successful_invocations.append("ok1")

    async def failing_handler(msg: Message) -> None:
        raise RuntimeError("Handler execution failed")

    async def ok_handler_2(msg: Message) -> None:
        successful_invocations.append("ok2")

    await bus.subscribe("topic.fail", ok_handler_1)
    await bus.subscribe("topic.fail", failing_handler)
    await bus.subscribe("topic.fail", ok_handler_2)

    msg = Message.event("topic.fail", "src", "payload")
    delivered = await bus.publish(msg)

    assert delivered == 2
    assert len(successful_invocations) == 2
    assert bus.stats.total_errors == 1
    assert bus.stats.total_messages_delivered == 2


@pytest.mark.asyncio
async def test_zero_matching_subscribers_returns_zero() -> None:
    """
    Test that publishing with zero matching subscribers returns 0 and does not error.
    """
    bus = MessageBus(max_concurrent_handlers=5)
    msg = Message.event("unmatched.topic", "src", "payload")
    delivered = await bus.publish(msg)

    assert delivered == 0
    assert bus.stats.total_messages_delivered == 0


def test_invalid_non_positive_concurrency_rejected() -> None:
    """
    Test that initializing MessageBus with non-positive concurrency limit raises ValueError.
    """
    with pytest.raises(ValueError, match="max_concurrent_handlers must be positive"):
        MessageBus(max_concurrent_handlers=0)

    with pytest.raises(ValueError, match="max_concurrent_handlers must be positive"):
        MessageBus(max_concurrent_handlers=-5)


@pytest.mark.asyncio
async def test_wildcard_routing_with_bounded_concurrency() -> None:
    """
    Test that wildcard routing works properly alongside bounded concurrency limit.
    """
    bus = MessageBus(max_concurrent_handlers=2)
    received: list[str] = []

    async def wildcard_handler(msg: Message) -> None:
        received.append(msg.topic)

    await bus.subscribe("sensor.#", wildcard_handler)
    await bus.subscribe("sensor.temperature.*", wildcard_handler)
    await bus.subscribe("sensor.temperature.room1", wildcard_handler)

    msg = Message.event("sensor.temperature.room1", "src", "22C")
    delivered = await bus.publish(msg)

    assert delivered == 3
    assert len(received) == 3
