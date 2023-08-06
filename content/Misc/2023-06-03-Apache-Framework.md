Title: Templated Apache httpd config
Date: 2023-06-03
Tags: Apache, httpd, website
Image: /img/httpd-feather.png
Summary: Part 1 of a series demonstrating building a templated Apache httpd configuration to host multiple websites: the basics. The template uses a `Define`/`Include` structure to achieve the goal.

# Templated Apache config

Can your expose an intranet site on the internet with as little as 2 lines of config (and an include)? This blog post aims to show how to build such a setup. Part 1 of a multi-part series, the basics.

## History

Since ca. 2006 "Best viewed in Internet Explorer 5", I've been creating
[Apache httpd](https://httpd.apache.org) configurations where I work. As seems natural for a novice, I started out with one large `httpd.conf` file.

Incidently, the Apache httpd project showed me the power of Open Source. We were having some weird unexplained issue with SSL. A contributor working at Vodafone Deutschland helped me fix the issue (race condition in keep-alive timeouts).

The first hints of what ultimately resulted in an extensible framework popped up when I was working on the unexplainable SSL issues. We had a load-balancing solution in front of the 2 Apache reverse proxies so we needed to know which node served the failing requests. This lazy admin doesn't want to do dual maintenance, I needed to be able to just copy the config between the nodes. I ended up with a separate file for the node name.

```
# 01-LocalDefines.conf
Define NodeName node1
```

```
# httpd.conf
Include 01-LocalDefines.conf
Header set X-Via ${NodeName}
```

This construct is the basis for the framework I'm going to build here. Later on, I learned about [`mod_macro`](https://httpd.apache.org/docs/2.4/mod/mod_macro.html#protocol) that can do similar things for vhosts, but this `Define`/`Include` framework serves me very well!

Other things I've learned:

1. Split your Virtual Hosts into separate conf files in a `vhosts.d` or `sites-enabled` directory and use `Include vhosts/*.conf`.
2. Name your config files with the complete virtual hostname.
3. Make a separate log directory for every virtual host and set `CustomLog` and `ErrorLog` in every virtual host. Note that the highest level errors still end up in the default error log.

## The deliverable

I want to end up with a framework that can host your static blog. It should look like this:

```
Define vhost blog.personal.me
Define DocRoot /home/brnrd/blog
Include templates/StaticSite.conf
```

Naturally, other types of Apache config can be done similarly, like

```
Define vhost www.corpsite.example.com
Define NextHop http://webserver.site.local:8080
Include templates/ProxyAll.conf
```

## The Static Site template

The [default Apache config](https://github.com/apache/httpd/blob/trunk/docs/conf/httpd.conf.in#L133) has the elements that we need to make this work. New to me: The latest version of the default config already uses defines!

```
DocumentRoot "${DOCROOT}"
<Directory "${DOCROOT}">
    Options Indexes FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
```

From this we can formulate the simplest possible static site template. I put these in a `templates` directory in the apache config dir.

```
# templates/StaticSite.conf
<VirtualHost *:*>
    ServerName "${vhost}"
    DocumentRoot "${DocRoot}"
    <Directory "${DocRoot}">
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>
</VirtualHost>
Undefine vhost
Undefine DocRoot
```

**NOTE:** `Undefine` all directives at the end of your template, or get hit with unexpected behavior when multiple virtual hosts use the same template!

Voilá, there's your blog.personal.me site!

## Extending the template

Let's implement my earlier learnings in the template, and add SSL (using [`mod_md`](https://httpd.apache.org/docs/2.4/mod/mod_md.html), make sure you have `MDContactEmail` and `MDCertificateAgreement` configured)

```
# templates/StaticSite.conf
<VirtualHost *:80>
    ServerName "${vhost}"
    # Assumes you have mod_alias loaded
    RedirectPermanent "https://${vhost}/"
</VirtualHost>
MDomain "${vhost}" 
<VirtualHost *:443>
    ServerName "${vhost}"
    CustomLog "/var/log/httpd/${vhost}/access.log" combined
    ErrorLog "/var/log/httpd/${vhost}/error.log"
    SSLEngine On
    DocumentRoot "${DocRoot}"
    <Directory "${DocRoot}">
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>
</VirtualHost>
Undefine vhost
Undefine DocRoot
```

**NOTE:** The log directory for the vhost must exist, or Apache won't start. 

## Automate creation of a new Static site

Adding a static site as easy as 

```
create-static.sh blog.personal.me /home/brnrd
apachectl -k graceful
```

```
#!/bin/sh -u

usage () {
    cat <<EOF
Usage: $0 hostname directory
EOF
}

[ $# -lt 2 ] && { usage; exit 1; }
[ -f "/etc/httpd/vhosts/$1.conf" ] && { echo "vhost $1 already exists; exit 1; }
[ -d $2 ] || { echo "No such dir $2"; usage; exit 1; }
host $1 || { echo "$1 does not resolve"; usage; exit 1; }

mkdir "/var/log/httpd/$1"

echo "Define vhost $1" > "/etc/httpd/vhosts/$1.conf"
echo "Define DocRoot $1" >> "/etc/httpd/vhosts/$1.conf"
echo "Include templates/StaticSite.conf" >> "/etc/httpd/vhosts/$1.conf"
```

## Operations

Extend your log-rotation to include

`/var/log/httpd/*/access.log`
`/var/log/httpd/*/error.log`

or you'll end up with huge logfiles.
