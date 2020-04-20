More tests
==========

Link to :cfg:config:`DMRG`.

Link to nonexistent :cfg:config:`ABCD`.

.. currentmodule:: mylib

.. function:: myfunction

    :param x: Parameter `x` desription.
    :type x: int
    :param y: Parameter `y` desription.
    :type y: int

We can also document an empty config

.. cfg:config:: parsed

    x : asdf
        The `x` parameter
    y : :class:`mylib.B`    =   None
          Another parameter, called `y`, with a default value.
    z.a.sd.f : :class:`mylib.B`   =   2
        Another parameter, called `y`, with a default value.

End of the config
