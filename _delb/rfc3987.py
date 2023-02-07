# Copyright (c) 2011 Daniel Gerber.
# Copyright (C) 2023 Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Parsing and validation of IRIs (RFC 3987).

This module provides a regular expression object according to `RFC 3987
"Internationalized Resource Identifiers (IRIs)" <http://tools.ietf.org/html/rfc3987>`_.

Copied and trimmed down for usage with delb from:
https://files.pythonhosted.org/packages/14/bb/f1395c4b62f251a1cb503ff884500ebd248eed593f41b469f89caa3547bd/rfc3987-1.3.8.tar.gz

"""

from __future__ import annotations

import re

from _delb.typing import Final  # noqa: TC001


_patterns: dict[str, str] = {}
for name, pattern in reversed(
    (
        # http://tools.ietf.org/html/rfc3987
        # January 2005
        #
        # REFERENCES
        ("IRI_reference", r"(?:{IRI}|{irelative_ref})"),
        ("IRI", r"{absolute_IRI}(?:\#{ifragment})?"),
        ("absolute_IRI", r"{scheme}:{ihier_part}(?:\?{iquery})?"),
        (
            "irelative_ref",
            (r"(?:{irelative_part}" r"(?:\?{iquery})?(?:\#{ifragment})?)"),
        ),
        (
            "ihier_part",
            r"(?://{iauthority}{ipath_abempty}|{ipath_absolute}"
            r"|{ipath_rootless}|{ipath_empty})",
        ),
        (
            "irelative_part",
            r"(?://{iauthority}{ipath_abempty}|{ipath_absolute}"
            r"|{ipath_noscheme}|{ipath_empty})",
        ),
        # AUTHORITY
        ("iauthority", r"(?:{iuserinfo}@)?{ihost}(?::{port})?"),
        ("iuserinfo", r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|:)*"),
        ("ihost", r"(?:{IP_literal}|{IPv4address}|{ireg_name})"),
        ("ireg_name", r"(?:{iunreserved}|{pct_encoded}|{sub_delims})*"),
        # PATH
        (
            "ipath",
            r"(?:{ipath_abempty}|{ipath_absolute}|{ipath_noscheme}"
            r"|{ipath_rootless}|{ipath_empty})",
        ),
        ("ipath_empty", r""),
        ("ipath_rootless", r"{isegment_nz}(?:/{isegment})*"),
        ("ipath_noscheme", r"{isegment_nz_nc}(?:/{isegment})*"),
        ("ipath_absolute", r"/(?:{isegment_nz}(?:/{isegment})*)?"),
        ("ipath_abempty", r"(?:/{isegment})*"),
        ("isegment_nz_nc", r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|@)+"),
        ("isegment_nz", r"{ipchar}+"),
        ("isegment", r"{ipchar}*"),
        # QUERY
        ("iquery", r"(?:{ipchar}|{iprivate}|/|\?)*"),
        # FRAGMENT
        ("ifragment", r"(?:{ipchar}|/|\?)*"),
        # CHARACTER CLASSES
        ("ipchar", r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|:|@)"),
        ("iunreserved", r"(?:[a-zA-Z0-9._~-]|{ucschar})"),
        ("iprivate", r"[\uE000-\uF8FF\U000F0000-\U000FFFFD\U00100000-\U0010FFFD]"),
        (
            "ucschar",
            r"["
            r"\xA0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF"
            r"\U00010000-\U0001FFFD\U00020000-\U0002FFFD\U00030000-\U0003FFFD"
            r"\U00040000-\U0004FFFD\U00050000-\U0005FFFD\U00060000-\U0006FFFD"
            r"\U00070000-\U0007FFFD\U00080000-\U0008FFFD\U00090000-\U0009FFFD"
            r"\U000A0000-\U000AFFFD\U000B0000-\U000BFFFD\U000C0000-\U000CFFFD"
            r"\U000D0000-\U000DFFFD\U000E1000-\U000EFFFD"
            r"]",
        ),
        # SCHEME
        ("scheme", r"[a-zA-Z][a-zA-Z0-9+.-]*"),
        # PORT
        ("port", r"[0-9]*"),
        # IP ADDRESSES
        ("IP_literal", r"\[(?:{IPv6address}|{IPvFuture})\]"),
        (
            "IPv6address",
            (
                r"(?:                             (?:{h16}:){{6}} {ls32}"
                r"|                            :: (?:{h16}:){{5}} {ls32}"
                r"| (?:                {h16})? :: (?:{h16}:){{4}} {ls32}"
                r"| (?:(?:{h16}:)?     {h16})? :: (?:{h16}:){{3}} {ls32}"
                r"| (?:(?:{h16}:){{,2}}{h16})? :: (?:{h16}:){{2}} {ls32}"
                r"| (?:(?:{h16}:){{,3}}{h16})? :: (?:{h16}:)      {ls32}"
                r"| (?:(?:{h16}:){{,4}}{h16})? ::                 {ls32}"
                r"| (?:(?:{h16}:){{,5}}{h16})? ::                 {h16} "
                r"| (?:(?:{h16}:){{,6}}{h16})? ::                      )"
            ).replace(" ", ""),
        ),
        ("ls32", r"(?:{h16}:{h16}|{IPv4address})"),
        ("h16", r"{hexdig}{{1,4}}"),
        ("IPv4address", r"(?:{dec_octet}\.){{3}}{dec_octet}"),
        ("dec_octet", r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"),
        ("IPvFuture", r"v{hexdig}+\.(?:{unreserved}|{sub_delims}|:)+"),
        # CHARACTER CLASSES
        ("unreserved", r"[a-zA-Z0-9_.~-]"),
        ("reserved", r"(?:{gen_delims}|{sub_delims})"),
        ("pct_encoded", r"%{hexdig}{{2}}"),
        ("gen_delims", r"[:/?#[\]@]"),
        ("sub_delims", r"[!$&'()*+,;=]"),
        ("hexdig", r"[0-9A-Fa-f]"),
    )
):
    _patterns[name] = pattern.format(**_patterns)

iri_reference_re: Final = re.compile(f"^{_patterns['IRI_reference']}$")
del _patterns


def is_iri_compliant(string: str) -> bool:
    return iri_reference_re.match(string) is not None


__all__ = (is_iri_compliant.__name__,)
