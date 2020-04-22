More tests
==========

Link to :cfg:config:`DMRG`.

Link to nonexistent :cfg:config:`ABCD`.
We can also document an empty config.

.. cfg:config:: empty_example

And we can document another example

.. cfg:config:: another_example

    x : asdf
        The `x` parameter
    y : :class:`mylib.B`    =   None
          Another parameter, called `y`, with a default value.
    z : :class:`mylib.B`   =   2
        Another parameter, called `y`, with a default value.

End of the config

.. cfg:option:: test
    :config: DMRG

    How does it handle adding references to other documents?
