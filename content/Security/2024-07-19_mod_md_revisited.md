Title: Apache mod_md revisited, now with dns-01
Tags: SSL, LetsEncrypt
Category: Security
Author: Bernard Spil
Image: /img/mod_md.png
Summary: `mod_md` is still by far the simplest way to add LetsEncrypt signed certificates to your Apache httpd server. Just add one line of configuration and you're done!

Back in 2017, I was playing with all kind of ACME LetsEncrypt clients. For
a number of years now, I've been using [acme.sh](https://acme.sh) for
issueing (wildcard) certificates.

[mod_md](https://httpd.apache.org/docs/2.4/mod/mod_md.html) is now part of
most operating system's Apache httpd packages, and
the feature set has grown considerably. This blog post will focus on
dns-01 validation and wildcard certificates. I've switched to wildcard
certificates since I've noticed skiddies will be probing any domain name
that passes by on the Certificate Transparency logs.

## On dns-01 validation, wildcard certificates

Letsencrypt on [challenge-types](https://letsencrypt.org/docs/challenge-types/) notes that this has Pro's ***and*** Cons. Amongst the
pro's is that you can issue wildcard certificates, amongst the cons is that
you need a DNS service that has an API you can automate, and that this may
require storing DNS API credentials on the server.

To minimize this risk, the solution outlined here uses a gateway service to
add and remove only the type of DNS records that are required to make
`dns-01` validation work, no more, and no less.

## mod_md and dns-01 ACME validation

**A**utomated **C**ertificate **M**anagement **E**nvironment (ACME) relies
on Domain Validation for certificate issuance. The requestor must prove they
have control over the domain name before the issuer signs (issues) your
certificate. In the `http-01` mechanism, this is accomplished by putting a
file with an agreed name in a well known location on the webserver of the
domain that's requested. For the `dns-01` mechanism, this is accomplished by
adding a token to your domain's DNS records that the issuer can verify.
Technically the issuer will look for a DNS TXT record for the domain name
that's being validated, prefixed with `_acme-challenge`. For a domain
`subdomain.example.org`, you'd have a TXT record `_acme-challenge.subdomain.example.com`.

To get mod_md to work with `dns-01` validation, it needs to add DNS TXT
resource records to the domain's DNS server. mod_md simply executes a
command you configure in Apache with [MDChallengeDns01](https://httpd.apache.org/docs/2.4/mod/mod_md.html#mdchallengedns01). The command (or
script) gets the action, domain name and challenge token as arguments. Using
above example mod_md will pass `setup subdomain.example.com BoioGwWDRRrAaNnDdOoMmTtOoKkEeNnQ9JRjEqVZnDw` to your command.

## Security considerations

1. Jails (containers) have no direct outbound connectivity, outbound
   connections must pass through my squid forward proxy, which checks
   source, destination and port and defaults to "deny".
2. Services run isolated in jails, access is strictly controlled using a
   firewall where only specific access is allowed, defaults to "deny".
3. Least privilege for a process is applied. The ACME dns-01 gateway runs
   as a restricted, specific service user (i.e. not as root).
4. The "full control" DNS API credentials are isolated from the web-server.
   Compromise of the web-server would allow creation of certificates for
   your domains, but not provide full control over your DNS content.

## Implementation

We'll need 4 parts to make this work

1. Configuration of Apache
2. Command (script) for mod_md to call
3. ACME dns-01 gateway service
4. DNS API implementation

I've created a tiny Python web-service that does not require anything but
the base Python installation. No additional python packages, no `pip`.

### ACME dns-01 gateway

The gateway performs the following functions:

1. Is stand-alone, can run in a jail or container.
2. Expose a web-service, configurable by:
   1. Command-line arguments<br/>
      and/or
   2. Environment<br/>
      and/or
   3. Configuration file.
3. Authenticate the caller by:
   1. IP-address<br/>
      and/or
   2. Basic authentication.
4. Validate the request: is this a domain we manage?
5. Call a configurable DNS API implementation.

The project's home is [ACME-dns01-gateway](https://github.com/Sp1l/ACME-dns01-gateway)
which currently comes with a single DNS API implementation for
[OpenProvider](https://www.openprovider.com/). The API being pluggable
means you can bring or create your own DNS API service.

#### Gateway configuration

I start the gateway in a jail, that has a localhost-only IP-address, with
the following command:

```sh
daemon -u _acme -o /var/log/acme/daemon.log -p /var/run/acme/acmegw.pid /usr/local/bin/acmegw_server.py --dotenv /usr/local/etc/acmedns01gw/dotenv
``` 

With the `/usr/local/etc/acmedns01gw/dotenv` file containing:

```conf
DNSAPI_USERNAME = myapiuser
DNSAPI_PASSWORD = "YoureUsingAVeryLongPassphrasePleaseAmIRight?"
DNSAPI_MODULE = providers.openprovider
DNSAPI_CLASS = OpenProvider
DNSAPI_DOMAINS = example.com, example.org
ALLOWED_HOSTS = 127.0.0.1, 127.12.7.0/24
BASIC_AUTH = sufficient
ALL_PROXY = http://fwproxy.example.com:3128
```

It will be listining on `*:8000` in the default configuration. My internal
DNS has `acme.example.com` configured on the loopback address (127.0.0.0/8)
this jail has been provisioned with.

Logging will go to stdout, the "daemon" config logs that to a file.

#### Authentication

In `BASIC_AUTH` "sufficient" mode, either a matching source IP or a matching
username and password are sufficient as authentication. In "required" mode
both username/password **and** matching source IP are required.

Passwords are stored in the acmepasswd file, and are salted scrypt or
pbkdf2-sha3_512 protected.

You can use the `lib/passwd.py` script to create, change, delete users and
passwords.

### mod_md `MDChallengeDns01` script

There's an example script in the ACME-dns01-gateway git repository:
`apache-mod_md.sh`. Configuration is at the top of the file.

```sh
LOGFILE="/var/log/httpd/mod_md.log"
API_URI="https://acme.example.org:8000"
API_USER=""
API_PASSWD=""
DNS_DELAY=300
```

### Apache configuration

To make mod_md work with the script:

```apache
MDCAChallenges dns-01
MDChallengeDns01 /usr/local/etc/apache24/bin/apache-mod_md.sh
MDChallengeDns01Version 2
```

You may want a bit more elaborate configuration

```apache
# Managing domains across virtual hosts, certificate provisioning via the ACME protocol
#
# https://httpd.apache.org/docs/2.4/mod/mod_md.html

LoadModule md_module libexec/apache24/mod_md.so

<IfModule md_module>
    MDCertificateAuthority https://acme-v02.api.letsencrypt.org/directory
    MDCertificateAgreement accepted
    MDContactEmail letsencrypt.notify@example.com

    MDStapling on
    MDStapleOthers on
    MDHttpProxy http://fwproxy.example.com:3128
    # LogLevel md:debug

    MDPrivateKeys secp384r1 rsa4096
    MDCAChallenges dns-01

    MDStoreDir /usr/local/etc/apache24/md
    MDChallengeDns01 /usr/local/etc/apache24/bin/mdchallenge.sh
    MDChallengeDns01Version 2

    MDRequireHttps temporary
</IfModule>
```

Without `MDDomain` configurations, this will do nothing. The simplest
virtual host configuration would be something like

```apache
MDomain sub.example.com

<VirtualHost *:80>
   ServerName sub.example.com
   DocumentRoot /var/empty
</VirtualHost>

<VirtualHost *:443>
    ServerName sub.example.com
    SSLEngine On
    DocumentRoot /var/www/html/sub.example.com
</VirtualHost>
```

The `MDRequireHttps temporary` global configuration makes sure that any 
client is redirected to https.

To configure the key-type or https redirect separately for a domain, even use `http-01` if your web-server is exposed on the internet, replace
`MDomain sub.example.com` with

```apache
<MDomain sub.example.com>
   MDCAChallenges http-01
   MDPrivateKeys  rsa3072
   MDRequireHttps permanent
</MDomain>
```

To get a wildcard certificate for `example.com` that will be applied to
`sub.example.com` automatically, use

```apache
MDomain example.com *.example.com

<VirtualHost *:80>
   ServerName sub.example.com
   DocumentRoot /var/empty
</VirtualHost>

<VirtualHost *:443>
    ServerName sub.example.com
    SSLEngine On
    DocumentRoot /var/www/html/sub.example.com
</VirtualHost>
```

Adding `example.com` isn't strictly required, but is a best practice.
