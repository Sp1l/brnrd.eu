Title: acme-client
Date: 2016-12-30
Modified: 2017-12-15
Tags: LetsEncrypt, SSL, FreeBSD, SysAdmin
Category: Security
Author: Bernard Spil
Image: /img/LetsEncryptLogo.jpg
Summary: This should be the final and my definitive guide on using Let's Encrypt and acme-client on FreeBSD. I've written multiple posts about this but things have changed again. I believe that the LetsEncrypt service is now stable and the acme-client seems to be stable as well.

If you just want to dig in, jump to the [Install acme-client](#install-acme-client) chapter.

 1. My [first guide](https://wiki.freebsd.org/BernardSpil/LetsEncrypt.py) used the official Let's Encrypt python client (now known as [CertBot](https://certbot.eff.org/)). I found that to be way too fat and had too many dependencies to be allowed to run as root.<BR>
 1. My [second guide](/security/2016-01-23/letsencrypt.html) used Lukas Schauer's LetsEncrypt.sh client (now known as [Dehydrated](https://github.com/lukas2511/dehydrated)) which only required `openssl` and either `bash` or `zsh`. This is still a good method as it has separated privileged and un-privileged actions.<BR>
 1. My [third guide](https://brnrd.eu/security/2016-06-18/letskencrypt.html) used Kristaps Dzonsons' Lets<b><i>k</i></b>Encrypt client (now known as [acme-client](https://kristaps.bsd.lv/acme-client/)).<BR>
 1. This latest guide uses acme-client which is the new name for Lets<b><i>k</i></b>Encrypt.

 > acme-client is a client for Let's Encrypt users, but one designed for <b>security</b>. No Python. No Ruby. No Bash. A straightforward, open source implementation in C that <b>isolates each step</b> of the sequence.

The `acme-client` process will be started by root but drops privileges to [`nobody`](https://en.wikipedia.org/wiki/Nobody_(username)) and [chroot](https://en.wikipedia.org/wiki/Chroot)'s any action that does not require root privileges. It must run as `root` to be able to drop privileges and run as an unprivileged user.

As a proponent of LibreSSL I can't let solutions that use libtls from LibreSSL pass by without trying to use them. I'm the creator and maintainer of the [`security/acme-client`](http://www.freshports.org/security/acme-client/) port in the [FreeBSD](https://freebsd.org) ports tree.

# Recent changes

The acme-client is now a part of the OpenBSD base system in addition to being a portable project for other operating systems.

## Trademark & name change

In June 2016, the LetsEncrypt project noticed that [Comodo](https://www.comodo.com/), a provider of SSL certificates, was [trying to hijack](https://letsencrypt.org/2016/06/23/defending-our-brand.html) the "Let's Encrypt" trademark. After the LetsEncrypt project managed to establish its rightful ownership of the trademark, Comodo dropped the trademark claims. As a side-effect the official LetsEncrypt client was renamed to CertBot and all other projects using the LetsEncrypt name had to be renamed.

The Lets<b><i>k</i></b>Encrypt process was quick off the bat and snapped the acme-client name.

Instructions to migrate from the old LetskEncrypt to the new acme-client directory-structure is documented in `/usr/ports/UPDATING` and the pkg-message.

## acme-client changes

A new feature `-b` was added which makes a backup of the old key when it is renewed.

## Port changes

The port as of version 0.1.15 no longer requires the user to switch to LibreSSL completely. By default it will check if LibreSSL is the default provider for libcrypto and libssl (SSL_DEFAULT=libressl). The port will build LibreSSL but not install it and statically link the not-installed libraries.

For users that have fully switched to LibreSSL there's no difference.

# Install acme-client

The port is available in the ports tree. Install it using the official pkg repository using

	:::sh
	pkg install acme-client

or alternatively build your own using [Poudriere](https://www.freebsd.org/doc/en_US.ISO8859-1/books/handbook/ports-poudriere.html) or any of the other building-from-source options and install it.

Configuration will land in `/usr/local/etc/acme`. The keys, certificates and certificate-chains will be stored in `/usr/local/etc/ssl/acme` by default. You should want to check that the configuration directory is not world-writable.
The default directories in /usr/local/etc/ssl will be created with sane access restrictions when you install the port or package.

    /usr/local/etc/
        acme/
        ssl/
        ssl/certs
        ssl/private

# Prepare directories 

To make life easier all of the challenges (LetsEncrypt as well as keybase etc) will be hosted in a shared dir `/usr/local/www/.well-known` on the jail running my Apache server. 

    :::sh
    mkdir -pm750 /usr/jails/http/usr/local/www/.well-known

The LetsEncrypt and acme-client bits will land in `/usr/local/etc/acme`, the private keys will land in `/usr/local/etc/ssl/private` and certificates will land in domain-specific directories in `/usr/local/etc/ssl/acme` on the host system. These directories are created by the port/package upon installation apart from the domain-specific certificate directories.

# Modify web-server configuration 

The acme validation will `GET` a uniquely named file from `http://<example.org>/.well-known/acme-challenge/` directory.

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

If you want to only share the ACME challenges you can suffix `.well-known/` with `acme-challenge/`

Now every (non-ssl) Virtual Host that I have gets a on-line addition

`vhosts/domain.conf`

	:::apacheconf
	Alias /.well-known/ /usr/local/www/.well-known/

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

# acme-client configuration 

`acme-client` works different from the other clients I've used as it does **not** use configuration files. Everything is handled passing parameters with values to the command. The intended use-case is a system that hosts a single domain. As I want to use acme-client to issue multiple certificates, I had to come up with some scripting.

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

`/usr/local/etc/acme/acme-client.sh`

    :::sh
    #!/bin/sh -e
    
    # Define location of dirs and files
    DOMAINSFILE="/usr/local/etc/acme/domains.txt"
    CHALLENGEDIR="/usr/jails/http/usr/local/www/.well-known/acme-challenge"
    SSLDIR="/usr/local/etc/ssl"

    # Check for account key and create dir and key (-n) if required
    if [ ! -f "/usr/local/etc/acme/privkey.pem" ] ; then
       EXTRAARGS="${EXTRAARGS} -n"
    fi

    # Loop through the domains.txt file with lines like
    # example.org www.example.org img.example.org
    cat ${DOMAINSFILE} | while read domain subdomains ; do
       # Set the directory where cert.pem, fullchain.pem and chain.pem are saved
       CERTDIR="${SSLDIR}/${domain}"
       # Define the name of the private key
       DOMAINKEY="${SSLDIR}/priv/${domain}.pem"
       # Make sure the certificates can be stored for this domain
       mkdir -pm755 "${CERTDIR}" 2>/dev/null

       # acme-client returns RC=2 when certificates weren't changed
       set +e
       # Renew the key and certs if required
       acme-client -b -C "${CHALLENGEDIR}" \
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

### Using the domains.txt file

To setup periodic to use the script

`/etc/periodic.conf`

    :::sh
    weekly_acme_client_enable="YES"
    weekly_acme_client_renewscript="/usr/local/etc/acme/acme-client.sh"
    weekly_acme_client_deployscript="/usr/local/etc/acme/deploy.sh"

Obviously you can also add your deployment to the renewal script if you would like to.

### Using periodic.conf for a single cert 

If you have only one certificate to renew on the machine, then you do so without a script by using periodic variables

`/etc/periodic.conf`

    :::sh
    weekly_acme_client_enable="YES"
    weekly_acme_client_domains="example.com www.example.com example.net www.example.net"
    weekly_acme_client_challengedir="/usr/jails/http/usr/local/www/.well-known/acme-challenge"
    weekly_acme_client_args="-c /usr/jails/http/usr/local/ssl/certs -p /usr/jails/http/usr/local/ssl/priv"

In stead of using the `weekly_acme_client_args` you can also use `weekly_acme_client_deployscript` for your single certificate deployment.

You will have to take care of creating the Account Key first time yourself!

The remainder of this guide assumes you use the `weekly_acme_client_renewscript` method.

# First run

You will probably want to run your LetsEncrypt manually the first time (as `root`) after you've setup periodic

    :::sh
    /usr/local/etc/periodic/weekly/000.acme-client.sh

You will end up with a sub-directory `certs` that contains your domains as directories with the Subject-Alternative-Names certs and the corresponding private keys in the `priv` sub-directory.

    /usr/local/etc/ssl/
       example.com/
          cert.pem
          chain.pem
          fullchain.pem
       priv/example.com.pem
       example.net/
          cert.pem
          chain.pem
          fullchain.pem
       priv/example.net.pem

# Deploy new certs

The port contains a script (`/usr/local/etc/acme/deploy.sh`) that you can adapt to your needs.

Here you'll probably need to get creative with scripting. In the host environment, you now have

    /usr/local/etc/ssl/priv/example.net.pem
    /usr/local/etc/ssl/example.net/fullchain.pem

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

**NB:** Some applications want the certificate and chain as separate files. If this is the case you'll need to copy `cert.pem` and `chain.pem` to the appropriate location in stead.

## Example deploy script

I've extended the default script. There's sufficient room to add your own domains.

Since `acme-client` runs as root you don't need to separate the renew and deploy scripts, you could make combine these.

`/usr/local/etc/acme/deploy.sh`

    :::sh
    #!/bin/sh -e
     
    DOMAINSFILE="/usr/local/etc/acme/domains.txt"
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
          cmp -s ${SSLDIR}/certs/${domain}/fullchain.pem ${targetdir}/certs/${domain}.pem && continue
          cp "${SSLDIR}/private/${domain}.pem"   "${targetdir}/priv/${domain}.pem"
          cp "${SSLDIR}/${domain}/fullchain.pem" "${targetdir}/certs/${domain}.pem"
          chmod 400 "${targetdir}/priv/${domain}.pem"
          chmod 644 "${targetdir}/certs/${domain}.pem"
          # Mark jail/service for restart/-load (no duplicate)
          [ -z "${restart}" ] && restart=${jail}
          [ "${restart%${jail}*}" == "$restart" ] && restart="${restart} ${jail}"
       done
     
    done
     
    # Restart services when marked
    [ -z "${restart}" ] && exit 0
    for jail in ${restart} ; do
       # Restart services when marked
       case ${jail} in
          http) jexec http service -v apache24 reload  ;;
          mail) jexec mail service -v smtpd    restart ;
                jexec mail service -v dovecot  reload  ;;
    done

## Example output of successful invocation with `-v`

	:::
	acme-client: https://acme-v01.api.letsencrypt.org/directory: directories
	acme-client: acme-v01.api.letsencrypt.org: DNS: 104.98.130.119
	acme-client: https://acme-v01.api.letsencrypt.org/acme/new-authz: req-auth: example.org
	acme-client: https://acme-v01.api.letsencrypt.org/acme/new-authz: req-auth: www.example.org
	acme-client: /jails/http/usr/local/www/.well-known/acme-challenge/<snip>: created
	acme-client: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: challenge
	acme-client: /jails/http/usr/local/www/.well-known/acme-challenge/<snip>: created
	acme-client: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: challenge
	acme-client: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: status
	acme-client: https://acme-v01.api.letsencrypt.org/acme/challenge/<snip>/<snip>: status
	acme-client: https://acme-v01.api.letsencrypt.org/acme/new-cert: certificate
	acme-client: http://cert.int-x3.letsencrypt.org/: full chain
	acme-client: cert.int-x3.letsencrypt.org: DNS: 185.27.16.17
	acme-client: /usr/local/etc/ssl/certs/example.org/chain.pem: created
	acme-client: /usr/local/etc/ssl/certs/example.org/cert.pem: created
	acme-client: /usr/local/etc/ssl/certs/example.org/fullchain.pem: created
