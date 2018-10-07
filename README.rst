.. image:: https://img.shields.io/badge/chat-join%20now-blue.svg
   :target: https://gitter.im/python-trio/general
   :alt: Join chatroom

.. image:: https://img.shields.io/badge/docs-read%20now-blue.svg
   :target: https://trimeter.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/trimeter.svg
   :target: https://pypi.org/project/trimeter
   :alt: Latest PyPi version

.. image:: https://travis-ci.org/python-trio/trimeter.svg?branch=master
   :target: https://travis-ci.org/python-trio/trimeter
   :alt: Automated test status

.. image:: https://codecov.io/gh/python-trio/trimeter/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/python-trio/trimeter
   :alt: Test coverage

Warning
=======

This library isn't ready for release yet. (It even depends on an
unreleased version of trio!) Feedback welcome!


Trimeter
========

Trio is a friendly Python library for async concurrency and
networking. Trimeter is a simple but powerful job scheduler for
programs using Trio, released under your choice of the MIT or Apache 2
licenses.

Trimeter's core purpose is to make it easy to execute lots tasks
concurrently, with rich options to **control the degree of
concurrency** and to **collect the task results**.

Say you have 1000 urls that you want to fetch and process somehow:

.. code-block:: python3

   # Old slow way
   for url in urls:
       await fetch_and_process(url)

That's slow, so you want to do several at the same time... but to
avoid overloading the network, you want to limit it to at most 5 calls
at once. Oh, and there's a request quota, so we have to throttle it
down to 1 per second. No problem:

.. code-block:: python3

   # New and fancy way
   await trimeter.run_on_each(
       fetch_and_process, urls, max_at_once=5, max_per_second=1
   )

What if we don't know the whole list of urls up front? No worries,
just pass in an async iterable instead, and Trimeter will do the right
thing.

What if we want to get the result from each call as it finishes, so we
can do something further with it? Just use ``amap`` (= short for
"async `map
<https://docs.python.org/3/library/functions.html#map>`__"):

.. code-block:: python3

   async with trimeter.amap(fetch_and_process, urls, ...) as results:
       # Then iterate over the return values, as they become available
       # (i.e., not necessarily in the original order)
       async for result in results:
           ...

Of course ``amap`` also accepts throttling options like
``max_at_once``, ``max_per_second``, etc.

What if we want to use the `outcome library
<https://outcome.readthedocs.io/>`__ to capture exceptions, so one
call crashing doesn't terminate the whole program? And also, we want
to pass through the original url alongside each result, so we know
which result goes with which url?

.. code-block:: python3

   async with trimeter.amap(
       fetch_and_process,
       urls,
       capture_outcome=True,
       include_value=True,
   ) as outcomes:
       # Then iterate over the return values, as they become available
       # (i.e., not necessarily in the original order)
       async for url, outcome in outcomes:
           try:
               return_value = outcome.unwrap()
           except Exception as exc:
               print(f"error while processing {url}: {exc!r}")

What if we just want to call a few functions in parallel and then get
the results as a list, like `asyncio.gather
<https://docs.python.org/3/library/asyncio-task.html#asyncio.gather>`__
or `Promise.all
<https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all>`__?

.. code-block:: python3

   return_values = await trimeter.run_all([
       async_fn1,
       async_fn2,
       functools.partial(async_fn3, extra_arg, kwarg="yeah"),
   ])

Of course, this takes all the same options as the other functions, so
you can control the degree of parallelism, use ``capture_outcome`` to
capture exceptions, and so forth.

For more details, see `the fine manual
<https://trimeter.readthedocs.io>`__.


Can you summarize that in iambic trimeter?
------------------------------------------

`Iambic trimeter <https://en.wikipedia.org/wiki/Iambic_trimeter>`__?
No problem:

| Trimeter gives you tools
| for running lots of tasks
| to do your work real fast
| but not so fast you crash.


Code of conduct
---------------

Contributors are requested to follow our `code of conduct
<https://trio.readthedocs.io/en/latest/code-of-conduct.html>`__ in all
project spaces.
