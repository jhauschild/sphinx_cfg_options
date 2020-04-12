"""mylib docstring.

This is only for debugging
"""


class B:
    """Another class."""
    def run(self):
        """do nothing."""
        pass


class A:
    """My A class.

    .. prm:definition :: params

        :param first: Describe the `first` parameter, context ``alowed``.
        :type first: int
        :param second: Describe the `second` parameter, c.f. :class:`mylib.B`.
        :type second: float


    Parameters
    ----------
    params : dict
        Parameters to be used as :attr:`A.params`.

    Attributes
    ----------
    x : int
        Usually equal ``1+1``.
    params : dict
        Parameters.
    """
    def __init__(self, params):
        self.params = params
        self.x = 2

    def show_params(self):
        """Print keys of :attr:`params`."""
        print(self.params.keys())


class Asub(A):
    """A subclass of A."""
    pass


def complicated_function(a, b, c, params):
    """A complicated function.


    Parameters
    ----------
    a : int
        Parameter `a` description.
    b : :class:`mylib.B`
        Parameter `b` description.
    params : dict
        Parameters.

    Returns
    -------
    x : int
        The sum of `a` and `b`
    """
