"""mylib docstring.

This module is only here to show how config options look inside the documention,
when included from the doc-strings of actual python code.
"""



class BaseA:
    """Example parent or base class.

    .. cfg:config :: A_config

        first : int
            Describe the `first` parameter, context ``allowed``.
        second : float
            Describe the `second` parameter.
            You can reference other objects, e.g., :class:`OtherC`.

    Parameters
    ----------
    params : dict
        Parameters to be used as :attr:`BaseA.params`.
        See above :cfg:config:`A_config` for details.

    Attributes
    ----------
    x : int
        Usually equal ``1+1``.
    params : dict
        Parameters. See above
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


class ChildB(BaseA):
    """A subclass of BaseA.


    .. cfg:config :: B_config
        :include: A_config

        third : str
            Another different description of of the `third` parameter,
            see :cfg:option:`A_config.third` for the one in the base class.

    """

    def do_something_else(self):
        """Another method using self.params.

        .. cfg:configoptions :: B_config

            fourth : str
                Yet another parameter that changes in `ChildB` compared to `BaseA`.
        """
        pass


class OtherC:
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
