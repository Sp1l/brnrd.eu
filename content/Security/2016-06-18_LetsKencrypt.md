Title: LetsKencrypt
Date: 2016-06-18
Modified: 2016-08-08
Tags: LetsEncrypt, SSL, FreeBSD, SysAdmin
Category: Security
Author: Bernard Spil
Image: /img/LETSkENCRYPT.png
Summary: This page describes a setup to renew LetsEncrypt certificates with the Lets<i>k</i>Encrypt client which has LibreSSL/libtls as its only dependency, uses chroots and drops privileges.

My [first guide](https://wiki.freebsd.org/BernardSpil/LetsEncrypt.py) used the official LetsEncrypt python client. I found that to be way too fat and had too many dependencies to be allowed to run as root.<BR>
My [second guide](https://https://brnrd.eu/security/2016-01-23/letsencrypt.html) used Lukas Schauer's LetsEncrypt.sh client which only required `openssl` and either `bash` or `zsh`. This is still a good method as it has separated privileged and un-privileged actions.

This latest guide uses [Lets<b><i>k</i></b>Encrypt](https://kristaps.bsd.lv/letskencrypt/) created by Kristaps Dzonsons. 

> LETS<i>k</i>ENCRYPT is a client for Let's Encrypt users, but one designed for <b>security</b>. No Python. No Ruby. No Bash. A straightforward, open source implementation in C that <b>isolates each step</b> of the sequence.

As a proponent of LibreSSL I can't let solutions that use libtls from LibreSSL pass by without trying to use them. I'm the creator and maintainer of the [`security/letskencrypt`](http://www.freshports.org/security/letskencrypt/) port in the [FreeBSD](https://freebsd.org) ports tree.

## Notes

Some notes on the configuration of my setup

1. All services accessible from the internet run in jails (all jails reside in `/usr/jails` by default on FreeBSD)
2. I use [LibreSSL](https://www.LibreSSL.org) as the provider of libcrypto, libssl and libtls on my FreeBSD system. The `security/letskencrypt` port depends on LibreSSL.

The `letskencrypt` process will be started by root but drops privileges to [`nobody`](https://en.wikipedia.org/wiki/Nobody_(username)) and [chroot](https://en.wikipedia.org/wiki/Chroot)'s any action that does not require root privileges. It must run as `root` to be able to drop privileges and run as an unprivileged user.

# Install Letsencrypt.sh

The port is available in the ports tree. Install it using the official pkg repository using

	:::sh
	pkg install letskencrypt

or alternatively build your own using [Poudriere](https://www.freebsd.org/doc/en_US.ISO8859-1/books/handbook/ports-poudriere.html) or any of the other building-from-source options and install it. The port works with either `security/libressl` or `security/libressl-devel`. If you want to use the newer 2.4 branch of LibreSSL you should add to

`/etc/make.conf`

	:::
	DEFAULT_VERSIONS+= ssl=libressl-devel

!!! warning
    The FreeBSD ports framework will detect that an OpenSSL/LibreSSL port is installed and then default to depend on the port rather than base. This will hit you if you use `portmaster`/`portupdate` or generally build 'in-situ'. You are encouraged to build using `poudriere` to avoid this.

Configuration will land in `/usr/local/etc/letsencrypt`. The keys, certificates and certificate-chains will be stored in `/usr/local/etc/ssl/letsencrypt` by default. You should want to check that the configuration directory is not world-writable.
The default directories in /usr/local/etc/ssl will be created with sane access restrictions when you install the port or package.

    /usr/local/etc/
        letsencrypt
        ssl/
        ssl/certs
        ssl/priv

# Prepare directories 

To make life easier all of the challenges (LetsEncrypt as well as keybase etc) will be hosted in a shared dir `/usr/local/www/.well-known` on the jail running my Apache server. 

    :::sh
    mkdir -pm750 /usr/jails/http/usr/local/www/.well-known

The LetsEncrypt and Lets<b><i>k</i></b>Encrypt bits will land in `/usr/local/etc/letsencrypt`, the private keys will land in `/usr/local/etc/ssl/priv` and certificates will land in domain-specific directories in `/usr/local/etc/ssl/letsencrypt` on the host system. These directories are created by the port/package upon installation apart from the domain-specific certificate directories.

## Migration from LetsEncrypt.sh

To migrate from the `LetsEncrypt.sh` method, copy/move your account key, the `domains.txt` file and all keys and certs to the new locations. Use the default filename, resolve symlinks to the actual timestamped file. Use the script as an example, yet it _should_ work for the default settings.

`migrate.sh`

	:::sh
	OLDDIR="/usr/local/etc/letsencrypt.sh"
	NEWDIR="/usr/local/etc/ssl"
	cp -p /usr/local/etc/letsencrypt{.sh,/domains.txt}
	cp -p /usr/local/etc/letsencrypt{.sh/private_key.pem,/privkey.pem}
	cat "${OLDDIR}/domains.txt" | while read domain line ; do
	   mkdir -pm755 "${NEWDIR}/${domain}"
	   cp -L "${OLDDIR}/certs/${domain}/privkey.pem" \
	         "${NEWDIR}/priv/${domain}.pem"
	   cp -L "${OLDDIR}/certs/${domain}/{cert,chain,fullchain}.pem" \
	         "${NEWDIR}/${domain}/"
	done

`LetsEncrypt.sh` uses a single account private key which we will reuse for the Lets<b><i>k</i></b>Encrypt setup (`/usr/local/etc/letsencrypt/privkey.pem`).

# Modify web-server configuration 

The acme validation will `GET` a uniquely named file from `http://<example.org>/.well-known/acme-challenge/`

### Apache

Access to the `.well-known` directory is granted in my main Apache config file `/usr/local/etc/apache24/httpd.conf`

`httpd.conf`

	:::apacheconf
	<Directory "/usr/local/www/.well-known/">
	   Options None
	   AllowOverride None
	   Require all granted
	   Header add Content-Type text/plain
	</Directory>

The Content-Type header was in my configs somewhere, shouldn't hurt.<<BR>>
If you want to only share the ACME challenges you can suffix `.well-known/` with `acme-challenge/`

Now every (non-ssl) Virtual Host that I have gets a on-line addition

`vhosts/domain.conf`

	:::apacheconf
	Alias /.well-known/ /usr/local/www/.well-known/

!!! caution
     You need to make sure that all (sub-)domains that you want to sign have access to this directory! That includes rewrites etc. The acme validation is done only using '''plain http''' and will not honour redirects etc.

### nginx

You'll need to add the following to the top of your ```location``` matches so requests from LetsEncrypt's acme servers get the correct responses.

    :::
	 # Letsencrypt needs http for acme challenges
	 location ^~ /.well-known/acme-challenge/ {
	     proxy_redirect off;
	     default_type "text/plain";
	     root /usr/local/www/.well-known/acme-challenge ;
	     allow all;
	 }

# Lets<i>k</i>encrypt configuration 

`Letskencrypt` works different from the other clients I've used as it does **not** use configuration files. Everything is handled passing parameters with values to the command. The intende use-case is a system that hosts a single domain.

I've tried to remain compatible with the `LetsEncrypt.sh` method using a file that lists domains and using the first (primary) hostname as prefix for the file and directory names. A filename-prefix handling is likely to be added in a future version. This could equally well be done with an inline HERE-document as documented below.

## Domains to sign 

The script requires a list of domain names you want to have a SAN cert for in the following format:

	example.com www.example.com
	example.net www.example.net wiki.example.net

Domains and sub-domains that are listed on the ''same line'' will result in SAN-certificates ([Subject-Alternative-Name](https://en.wikipedia.org/wiki/SubjectAltName)).<BR>
Store this as `/usr/local/etc/letsencrypt/domains.txt`

!!! caution 
    Make sure the first item in every line of `domains.txt` is unique or you'll end up in a real mess!

## The renew script

The script tries to make sure all things that need to exist actually do exist. Some of the statements are "on-off", after first run they can be deleted.

`/usr/local/etc/letsencrypt/letskencrypt.sh`

    #!sh
    #!/bin/sh -e
    
    # Define location of dirs and files
    DOMAINSFILE="/usr/local/etc/letsencrypt/domains.txt"
    CHALLENGEDIR="/usr/jails/http/usr/local/www/.well-known/acme-challenge"
    SSLDIR="/usr/local/etc/ssl"

    backupCertAndKey () {
       local CERTDIR=$1
       local DOMAINKEY=$2

       # Determine certificate expiry in ISO-8601 notation
       certExpiryOpenSSL=`openssl x509 -noout -enddate -in ${CERTDIR}/cert.pem`
       certExpiryISO8601=`date -j -f "notAfter=%b %d %H:%M:%S %Y %Z" "${certExpiryOpenSSL}" '+%Y-%m-%dT%H:%M:%S%z'`
       [ -d "${CERTDIR}/${certExpiryISO8601}" ] && return
       for file in cert chain fullchain ; do
          ln ${CERTDIR}/${file}.pem "${CERTDIR}/${certExpiryISO8601}/${file}.pem"
       done
       ln ${DOMAINKEY} "${DOMAINKEY%.pem}-${certExpiryISO8601}.pem"
    }

    # Check for account key and create dir and key (-n) if required
    if [ ! -f "/usr/local/etc/letsencrypt/privkey.pem" ] ; then
       [ ! -d "/usr/local/etc/letsencrypt" ] && \
           mkdir -m700 /usr/local/etc/letsencrypt 
       EXTRAARGS="${EXTRAARGS} -n"
    fi

    # Make sure we can store the private keys
    mkdir -pm700 "${SSLDIR}/priv" 2>/dev/null

    # Loop through the domains.txt file with lines like
    # example.org www.example.org img.example.org
    cat ${DOMAINSFILE} | while read domain subdomains ; do
       # Set the directory where cert.pem, fullchain.pem and chain.pem are saved
       CERTDIR="${SSLDIR}/certs/${domain}"
       # Define the name of the private key
       DOMAINKEY="${SSLDIR}/priv/${domain}.pem"
       # Make sure the certificates can be stored for this domain
       mkdir -pm755 "${CERTSDIR}" 2>/dev/null

       # create a hardlink for cert/chain/fullchain and domainkey if non-existent
       backupCertAndKey ${CERTDIR} ${DOMAINKEY}

       # letskencrypt returns RC=2 when certificates weren't changed
       set +e
       # Renew the key and certs if required
       letskencrypt -C "${CHALLENGEDIR}" \
                    -k "${DOMAINKEY}" \
                    -c "${CERTDIR}" \
                    ${EXTRAARGS} \
                    ${domain} ${subdomains}
       RC=$?
       set -e
       [ $RC -ne 2 ] && exit 1
    done

### In-line configuration

If you don't want to use a `domains.txt` configuration file you can use a different construct to include the list in your `/usr/local/etc/letsencrypt/letskencrypt.sh` script (changed lines only).

    :::sh
    ...
    while read domain line ; do
    ...
    done <<ENDOFLIST
    example.com www.example.com
    example.net www.example.net wiki.example.net
    ENDOFLIST

## Configure periodic job 

The FreeBSD port contains a [`periodic(8)`](https://www.freebsd.org/cgi/man.cgi?query=periodic) script for full automation of your certificate renewal. The periodic script allows using a script for renewals or periodic variables only for a single key/certifcate

To setup periodic to use the script

`/etc/periodic.conf`

    :::sh
    weekly_letskencrypt_enable="YES"
    weekly_letskencrypt_renewscript="/usr/local/etc/letsencrypt/letskencrypt.sh"
    weekly_letskencrypt_deployscript="/usr/local/etc/letsencrypt/deploy.sh"

Obviously you can also add your deployment to the renewal script if you would like to.

If you have only one certificate to renew on the machine, then you do so without a script by using periodic variables

`/etc/periodic.conf`

    :::sh
    weekly_letskencrypt_enable="YES"
    weekly_letskencrypt_domains="example.com www.example.com example.net www.example.net"
    weekly_letskencrypt_challengedir="/usr/jails/http/usr/local/www/.well-known/acme-challenge"
    weekly_letskencrypt_args="-c /usr/jails/http/usr/local/ssl/certs -p /usr/jails/http/usr/local/ssl/priv"

In stead of using the `weekly_letskencrypt_args` you can also use `weekly_letskencrypt_deployscript` for your single certificate deployment.

The remainder of this guide assumes you use the `weekly_letskencrypt_renewscript` method.

# First run 

You will probably want to run your LetsEncrypt manually the first time (as `root`) after you've setup periodic

    :::sh
    /usr/local/etc/periodic/weekly/000.letskencrypt.sh

You will end up with a sub-directory `certs` that contains your domains as directories with the Subject-Alternative-Names certs and the corresponding private keys in the `priv` sub-directory.

    /usr/local/etc/ssl/
       certs/example.com/
          cert.pem
          chain.pem
          fullchain.pem
       priv/example.com.pem
       certs/example.net/
          cert.pem
          chain.pem
          fullchain.pem
       priv/example.net.pem

# Deploy new certs 

The port contains a script (`/usr/local/etc/letsencrypt/deploy.sh`) that you can adapt to your needs.

Here you'll probably need to get creative with scripting. In the host environment, you now have

    /usr/local/etc/ssl/letsencrypt/priv/example.net.pem
    /usr/local/etc/ssl/letsencrypt/certs/example.net/fullchain.pem

## Example (jailed) applications 

Your Apache server may (should?) run in the `http` jail and you've setup an Apache Virtual Host with

    :::apacheconf
    SSLCertificateFile /etc/ssl/certs/example.net.pem
    SSLCertificateKeyFile /etc/ssl/priv/example.net.pem

and your OpenSMTPd mailserver for example.net in the `mail` jail

    pki example.net certificate "/etc/ssl/certs/example.net.pem"
    pki example.net key         "/etc/ssl/priv/example.net.pem"
    listen on $lan_addr port 587 tls-require \
           pki example.net hostname example.net auth

Seen from the host environment your certificates actually need to end up in 

    /usr/jails/http/etc/ssl
    /usr/jails/mail/etc/ssl

**NB:** Some applications want a private key, certificate and separate chain instead. If this is the case you'll need to copy `cert.pem` and `chain.pem` to the appropriate location in stead.

## Example deploy script

I've extended the default script. There's sufficient room to add your own domains.

Since `letskencrypt` runs as root you don't need to separate the renew and deploy scripts, you could make combine these.

`/usr/local/etc/letsencrypt/seploy.sh`
    :::sh
    #!/bin/sh -e
	 
    DOMAINSFILE="/usr/local/etc/letsencrypt/domains.txt"
    SSLDIR="/usr/local/etc/ssl"
    JAILSDIR="/usr/jails"
 	 
    cat ${DOMAINSFILE} | while read domain subdomains ; do
	
       case ${domain} in
          mta.example.net) targetjails=mail ;;
          *)               targetjails=http ;;
       esac
    
       for jail in ${targetjails}; do
          targetdir="${JAILSDIR}/${jail}/etc/ssl"
          # Skip to next if cert hasn't changed
          [ -z "`diff -rq ${SSLDIR}/certs/${domain}/fullchain.pem ${targetdir}/certs/${domain}.pem`" ] && continue
          cp "${SSLDIR}/private/${domain}.pem"   "${targetdir}/priv/${domain}.pem"
          cp "${SSLDIR}/${domain}/fullchain.pem" "${targetdir}/certs/${domain}.pem"
          chmod 400 "${targetdir}/priv/${domain}.pem"
          chmod 644 "${targetdir}/certs/${domain}.pem"
          # Mark jail/service for restart/-load
          eval restart${jail}=yes
       done
	
    done
	
    # Restart services when marked
    [ -n "${restarthttp}" ] && jexec http service apache24 restart
    [ -n "${restartmail}" ] && jexec mail service smtpd restart

## Example output of successful invocation with `-v`

	:::
	letskencrypt: https://acme-v01.api.letsencrypt.org/directory: directories
	letskencrypt: acme-v01.api.letsencrypt.org: DNS: 104.98.130.119
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/new-authz: req-auth: example.org
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/new-authz: req-auth: www.example.org
	letskencrypt: /jails/http/usr/local/www/.well-known/acme-challenge/<snip>: created
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: challenge
	letskencrypt: /jails/http/usr/local/www/.well-known/acme-challenge/<snip>: created
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: challenge
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: status
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: status
	letskencrypt: https://acme-v01.api.letsencrypt.org/acme/new-cert: certificate
	letskencrypt: http://cert.int-x3.letsencrypt.org/: full chain
	letskencrypt: cert.int-x3.letsencrypt.org: DNS: 185.27.16.17
	letskencrypt: /usr/local/etc/ssl/certs/example.org/chain.pem: created
	letskencrypt: /usr/local/etc/ssl/certs/example.org/cert.pem: created
	letskencrypt: /usr/local/etc/ssl/certs/example.org/fullchain.pem: created


### Changes

2016-07-16: Added nginx config and sample deploy script
2016-08-08: Fixed error in renew script, letskencrypt has exit status 2 when certs haven't changed