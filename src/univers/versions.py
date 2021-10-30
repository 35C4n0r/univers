#
# Copyright (c) nexB Inc. and others.
# SPDX-License-Identifier: Apache-2.0
#
# Visit https://aboutcode.org and https://github.com/nexB/univers for support and download.

import re
from functools import total_ordering

import attr
import semantic_version
from packaging import version as pypi_version

from univers import arch
from univers import debian
from univers import gentoo
from univers import maven
from univers import rpm
from univers.utils import remove_spaces


class InvalidVersion(ValueError):
    pass


class BaseVersion:
    """
    Base  version object to subclass for each version scheme.

    Each version value should be comparable e.g., implement
    functools.total_ordering
    """

    # the version scheme is a class attribute
    scheme = None
    value = attr.ib(type=str)

    def validate(self):
        """
        Validate that the version is valid for its scheme
        """
        raise NotImplementedError

    def __str__(self):
        return f"{self.scheme}:{self.value}"


@total_ordering
@attr.s(frozen=True, init=False, order=False, hash=True)
class PYPIVersion(BaseVersion):
    scheme = "pypi"

    def __init__(self, version_string):
        # TODO the `pypi_version.Version` class's constructor also does the same validation
        # but it has a fallback option by creating an object of pypi_version.LegacyVersion class.
        # Avoid the double validation and the fallback.

        self.validate(version_string)
        object.__setattr__(self, "value", pypi_version.Version(version_string))
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        match = pypi_version.Version._regex.search(version_string)  # NOQA
        if not match:
            raise InvalidVersion(f"Invalid version: '{version_string}'")

    def __eq__(self, other):
        # TBD: Should this verify the type of `other`
        return self.value.__eq__(other.value)

    def __lt__(self, other):
        return self.value.__lt__(other.value)


class GenericVersion:
    scheme = "generic"

    def validate(self):
        """
        Validate that the version is valid for its scheme
        """
        # generic implementation ...
        # TODO: Should use
        # https://github.com/repology/libversion/blob/master/doc/ALGORITHM.md#core-algorithm
        #  Version is split into separate all-alphabetic or all-numeric
        #  components.
        # All other characters are treated as separators. Empty components are
        # not generated.
        #   10.2alpha3..patch.4. → 10, 2, alpha, 3, patch, 4


@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
@total_ordering
class SemverVersion(BaseVersion):
    scheme = "semver"

    def __init__(self, version_string):
        version_string = version_string.lower()
        version_string = version_string.lstrip("v")
        object.__setattr__(self, "value", semantic_version.Version.coerce(version_string))
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        pass

    def __eq__(self, other):
        # TBD: Should this verify the type of `other`
        return self.value.__eq__(other.value)

    def __lt__(self, other):
        return self.value.__lt__(other.value)


@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
@total_ordering
class ArchVersion(BaseVersion):
    scheme = "arch"

    def __init__(self, version_string):
        version_string = version_string.lower()
        version_string = remove_spaces(version_string)
        object.__setattr__(self, "version_string", version_string)
        object.__setattr__(self, "value", version_string)

    @staticmethod
    def validate(version_string):
        pass

    def __eq__(self, other):
        # TBD: Should this verify the type of `other`
        return arch.vercmp(self.value, other.value) == 0

    def __lt__(self, other):
        return arch.vercmp(self.value, other.value) == -1


@total_ordering
@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
class DebianVersion(BaseVersion):
    scheme = "debian"

    def __init__(self, version_string):
        version_string = remove_spaces(version_string)
        object.__setattr__(self, "value", debian.Version.from_string(version_string))
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        pass

    def __eq__(self, other):
        return self.value.__eq__(other.value)

    def __lt__(self, other):
        return self.value.__lt__(other.value)


@total_ordering
@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
class MavenVersion(BaseVersion):
    scheme = "maven"

    def __init__(self, version_string):
        version_string = remove_spaces(version_string)
        object.__setattr__(self, "value", maven.Version(version_string))
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        # Defined for compatibility
        pass

    def __eq__(self, other):
        return self.value.__eq__(other.value)

    def __lt__(self, other):
        return self.value.__lt__(other.value)


# See https://docs.microsoft.com/en-us/nuget/concepts/package-versioning
@total_ordering
@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
class NugetVersion(SemverVersion):
    scheme = "nuget"
    pass


@total_ordering
@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
class RPMVersion(BaseVersion):
    scheme = "rpm"

    def __init__(self, version_string):
        version_string = remove_spaces(version_string)
        self.validate(version_string)
        object.__setattr__(self, "value", version_string)
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        pass

    def __eq__(self, other):
        result = rpm.vercmp(self.value, other.value)
        return result == 0

    def __lt__(self, other):
        result = rpm.vercmp(self.value, other.value)
        return result == -1


@total_ordering
@attr.s(frozen=True, init=False, order=False, eq=False, hash=True, repr=False)
class GentooVersion(BaseVersion):
    scheme = "ebuild"
    version_re = re.compile(r"^(?:\d+)(?:\.\d+)*[a-zA-Z]?(?:_(p(?:re)?|beta|alpha|rc)\d*)*$")

    def __init__(self, version_string):
        version_string = remove_spaces(version_string)
        self.validate(version_string)
        object.__setattr__(self, "value", version_string)
        object.__setattr__(self, "version_string", version_string)

    @staticmethod
    def validate(version_string):
        version, _ = gentoo.parse_version_and_revision(version_string)
        if not GentooVersion.version_re.match(version):
            raise InvalidVersion(f"Invalid version: '{version_string}'")

    def __eq__(self, other):
        result = gentoo.vercmp(self.value, other.value)
        return result == 0

    def __lt__(self, other):
        result = gentoo.vercmp(self.value, other.value)
        return result == -1


# TODO : Should these be upper case global constants ?


version_class_by_scheme = {
    "generic": GenericVersion,
    "semver": SemverVersion,
    "debian": DebianVersion,
    "pypi": PYPIVersion,
    "maven": MavenVersion,
    "nuget": NugetVersion,
    "rpm": RPMVersion,
    "ebuild": GentooVersion,
}


version_class_by_package_type = {
    "deb": DebianVersion,
    "pypi": PYPIVersion,
    "maven": MavenVersion,
    "nuget": NugetVersion,
    # TODO: composer may need its own scheme see https://github.com/nexB/univers/issues/5
    # and https://getcomposer.org/doc/articles/versions.md
    "composer": SemverVersion,
    # TODO: gem may need its own scheme see https://github.com/nexB/univers/issues/5
    # and https://snyk.io/blog/differences-in-version-handling-gems-and-npm/
    # https://semver.org/spec/v2.0.0.html#spec-item-11
    "gem": SemverVersion,
    "npm": SemverVersion,
    "rpm": RPMVersion,
    "golang": SemverVersion,
    "generic": SemverVersion,
    # apache is not semver at large. And in particular we may have schemes that
    # are package name-specific
    "apache": SemverVersion,
    "hex": SemverVersion,
    "cargo": SemverVersion,
    "mozilla": SemverVersion,
    "github": SemverVersion,
    "ebuild": GentooVersion,
}


def validate_scheme(scheme):
    if scheme not in version_class_by_scheme:
        raise ValueError(f"Invalid scheme {scheme}")


def parse_version(version):
    """
    Return a Version object from a scheme-prefixed string
    """
    if ":" in version:
        scheme, _, version = version.partition(":")
    else:
        scheme = "generic"

    cls = version_class_by_scheme[scheme]
    return cls(version)
