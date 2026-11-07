# Security

<sub><i>A Delgado &amp; Murphy restoration</i></sub>

Please **don't open a public issue** for a security problem. Use GitHub's
private reporting: **Security → Report a vulnerability** on this repository,
or on [hasler](https://github.com/Delgado-Murphy/hasler/security) when the
problem is in the radio rather than in the integration. We answer within a
week and say when a fix is out.

The radio trusts its home network by design: its API has no login, as its
key page has none, and it refuses requests that don't name the radio itself
as `Host` or come from a web page elsewhere. A way around those checks, or
the integration sending something to anywhere but the radio you added, is
worth a report.

<sub>Delgado &amp; Murphy</sub>
