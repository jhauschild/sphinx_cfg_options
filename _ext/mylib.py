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

    .. cfg:config :: DMRG

        first : int
            Describe the `first` parameter, context ``alowed``.
        second : float
            Describe the `second` parameter, c.f. :py:class:`mylib.B`.

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

    def do_something(self):
        """Some function using `self.params`.

        .. cfg:config :: DMRG
            first: int
                Another description of the `first` parameter.
        """
        print(self.params.keys())


class Asub(A):
    """A subclass of A."""
    pass


def complicated_function(a, b, c, params):
    """A complicated function.

    .. cfg:config :: complicated_function.params
        :noindex:

        Na : int
           Number of repetitions for `a`.

    Parameters
    ----------
    a : int
        Parameter `a` description.
    b : :class:`mylib.B`
        Parameter `b` description.
    complicated_params : dict
        Parameters.


    Returns
    -------
    x : int
        The sum of `a` and `b`
    """
    pass
