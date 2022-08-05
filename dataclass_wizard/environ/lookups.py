from os import environ, name
from typing import ClassVar, Dict, Optional, Set

from ..decorators import cached_class_property
from ..lazy_imports import dotenv
from ..utils.string_conv import to_snake_case


# Type of `os.environ` or `DotEnv` dict
Environ = Dict[str, Optional[str]]

# Type of (unique) environment variable names
EnvVars = Set[str]


# noinspection PyMethodParameters
class Env:

    __slots__ = ()

    _accessed_cleaned_to_env: ClassVar[bool] = False

    @cached_class_property
    def var_names(cls) -> EnvVars:
        """
        Cached mapping of `os.environ` key names. This can be refreshed with
        :meth:`reload` as needed.
        """
        return set(environ.keys())

    @classmethod
    def reload(cls, env: dict = environ):
        """Refresh cached environment variable names."""
        env_vars: EnvVars = cls.var_names
        new_vars = env.keys() - env_vars

        # update names of environment variables
        env_vars.update(new_vars)

        # update mapping of cleaned environment variables (if needed)
        if cls._accessed_cleaned_to_env:
            cls.cleaned_to_env.update(
                (clean(var), var) for var in new_vars
            )

    @classmethod
    def update_with_dotenv_file(cls, filename='.env'):
        dotenv_path = dotenv.find_dotenv(filename)
        # take environment variables from `.env` file
        env: Environ = dotenv.dotenv_values(dotenv_path)
        # reload cached mapping of environment variables
        cls.reload(env)
        # update `os.environ` with new environment variables
        environ.update(env)

    # noinspection PyDunderSlots,PyUnresolvedReferences
    @cached_class_property
    def cleaned_to_env(cls) -> Environ:
        cls._accessed_cleaned_to_env = True
        return {clean(var): var for var in cls.var_names}


def clean(s: str) -> str:
    """
    TODO:
        see https://stackoverflow.com/questions/1276764/stripping-everything-but-alphanumeric-chars-from-a-string-in-python
        also, see if we can refactor to use something like Rust and `pyo3` for a slight performance improvement.
    """
    return s.replace('-', '').replace('_', '').lower()


def try_cleaned(key: str) -> Optional[str]:
    key = Env.cleaned_to_env.get(clean(key))

    if key is not None:
        return environ[key]

    return None


if name == 'nt':
    # Where Env Var Names Must Be UPPERCASE
    def lookup_exact(var: str):
        """
        Lookup by variable name with *exact* letter casing, and return `None`
        if not found in the environment.
        """
        var = var.upper()

        if var in Env.var_names:
            return environ[var]

        return None

else:
    # Where Env Var Names Can Be Mixed Case
    def lookup_exact(var: str):
        """
        Lookup by variable name with *exact* letter casing, and return `None`
        if not found in the environment.
        """
        if var in Env.var_names:
            return environ[var]

        return None


def with_screaming_snake_case(field_name: str) -> Optional[str]:
    """
    Lookup with `SCREAMING_SNAKE_CASE` letter casing first - this is the
    default lookup.

    This function assumes the dataclass field name is lower-cased.

    For a field named 'my_env_var', this tries the following lookups in order:
        - MY_ENV_VAR (screaming snake-case)
        - my_env_var (snake-case)
        - Any other variations - i.e. MyEnvVar, myEnvVar, myenvvar, my-env-var

    :param field_name: The dataclass field name to lookup in the environment.
    :return: The value of the matched environment variable, if one is found in
      the environment.
    """
    upper_key = field_name.upper()

    if upper_key in Env.var_names:
        return environ[upper_key]

    if field_name in Env.var_names:
        return environ[field_name]

    return try_cleaned(field_name)


def with_snake_case(field_name: str) -> Optional[str]:
    """Lookup with `snake_case` letter casing first.

    This function assumes the dataclass field name is lower-cased.

    For a field named 'my_env_var', this tries the following lookups in order:
        - my_env_var (snake-case)
        - MY_ENV_VAR (screaming snake-case)
        - Any other variations - i.e. MyEnvVar, myEnvVar, myenvvar, my-env-var

    :param field_name: The dataclass field name to lookup in the environment.
    :return: The value of the matched environment variable, if one is found in
      the environment.
    """
    if field_name in Env.var_names:
        return environ[field_name]

    upper_key = field_name.upper()

    if upper_key in Env.var_names:
        return environ[upper_key]

    return try_cleaned(field_name)


def with_pascal_or_camel_case(field_name: str) -> Optional[str]:
    """Lookup with `PascalCase` or `camelCase` letter casing first.

    This function assumes the dataclass field name is either pascal- or camel-
    cased.

    For a field named 'myEnvVar', this tries the following lookups in order:
        - myEnvVar, MyEnvVar (camel-case, or pascal-case)
        - MY_ENV_VAR (screaming snake-case)
        - my_env_var (snake-case)
        - Any other variations - i.e. my-env-var, myenvvar

    :param field_name: The dataclass field name to lookup in the environment.
    :return: The value of the matched environment variable, if one is found in
      the environment.
    """
    if field_name in Env.var_names:
        return environ[field_name]

    snake_key = to_snake_case(field_name)
    upper_key = snake_key.upper()

    if upper_key in Env.var_names:
        return environ[upper_key]

    if snake_key in Env.var_names:
        return environ[snake_key]

    return try_cleaned(field_name)
