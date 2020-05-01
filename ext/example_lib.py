"""mylib docstring.

This module is only here to show how config options look inside the documention,
when included from the doc-strings of actual python code.
"""



class A:
    """My A class.

    .. cfg:config :: A_config

        first : int
            Describe the `first` parameter, context ``allowed``.
        second : float
            Describe the `second` parameter, c.f. :class:`mylib.B`.

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

        .. cfg:configoptions :: A_config

            first: int
                A **different** description of the `first` parameter.
            third, fourth, fifth: str
                Multiple options documented at once.
                Works only if :cfg:option:`conf.py.cfg_options_parse_comma_sep_names` is enabled.
        """
        print(self.params.keys())


class Asub(A):
    """A subclass of A."""
    pass


class B:
    """Another class."""
    def run(self):
        """do nothing."""
        pass


def complicated_function(a, b, c, params):
    """A complicated function.

    .. cfg:config :: complicated_function

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
