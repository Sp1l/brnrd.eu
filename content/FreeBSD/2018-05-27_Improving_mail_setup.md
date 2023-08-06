Title: Improving my mail server setup
Tags: FreeBSD, jails
Modified: 2018-05-27
Author: Bernard Spil
Image: /img/OpenSMTPDrspamdDovecot.png
Summary: After switching from SpamAssassin to rspamd for spam classification I wasn't completely happy yet with the separation I had achieved. More and more I find myself splitting off functions on my server into jails and I wanted to achieve more separation of unauthenticated content processing with storage of data.
So OpenSMTPD and Dovecot had to separate into two jails (scanning and classification is already performed in a "scan" jail)

# History

Long ago I created a pag on FreeBSD's wiki [detailing my mail-server setup](https://wiki.freebsd.org/BernardSpil/MailServer). I have failed to keep that up-to-date, but I will try revise it shortly.
Notable changes between [that wiki page](https://wiki.freebsd.org/BernardSpil/MailServer) and my current setup are that I've replaced [dspam](http://dspam.sourceforge.net/) with [rspamd]() and [amavisd](https://www.ijs.si/software/amavisd/) has been replaced by the [ClamAV] filter and 'deliver to mda' in OpenSMTPD.
The mail processing pipeline is now:

    OpenSMTPD | clamav filter | rspamc | dovecot-lda

Which works nicely when you have Dovecot running in the same jail as where OpenSMTPD runs.

# Future

There are remnants of an [rspamc filter](https://github.com/OpenSMTPD/OpenSMTPD-extras/tree/filter-rspamd/extras/filters) in OpenSMTPD extras. Unfortunately the OpenSMTPD developers decided to drop support for filters in 6.0 and thus we're stuck with version 5.9 on FreeBSD so we have filters support.
OpenSMTPD intends to release another daemon 'smtpdf' for filtering purposes only. This would then chain with smtpd for the actual mail handling.

# Separation is good

Already the part that processes unauthenticated content was split off into a separate jail, which I've aptly named 'scan'. Processing email is an arduous thing. Nested parts, many types of compression and types of payload used. There's just too many places for an attacker to try and break in to run this anywhere near your users' data.

Not that I don't trust the OpenSMTPD devs to do a poor job at security, but I'd rather not have it run anywhere where there's access to the users' data either. So dovecot has to be split off into its own jail too.
For want of a working rspamc filter in OpenSMTPD, rspamc must be able to communicate with the Mail Delivery Agent (MDA or LDA) on another host. Unfortunately, rspamc is uncapable of doing anything other than piping the email payload (MIME message) through another program. Rspamc has no ability to use LMTP. Thus I had to build a bridge.

# Take it to the bridge

Neither pipes nor LMTP are very difficult protocols in their essence. I like to think I could probably code something in plain POSIX shell that would take `stdin`, connect to the LMTP socket, send the `LHLO`, `MAIL FROM` and `RCPT TO` commands and dump `stdin` to the `LMTP` socket.

As I'm currently interested in learning Python, I decided that this could be achieved easier with plain Python builtins. (Spoiler alert: yes it is). Scares me to bring in Python without experience in using it, but here we go!

(Following paragraphs appear in the order I discovered them for my python script)

## arguments

For LMTP to work, you need to know who the sender and receiver (local username!) are. These are not part of the email payload itself, but OpenSMTPD knows about them through the expansion it does via aliases, virtusers, etc. A bit of googling and prototyping later I settled on [`argparse`](https://docs.python.org/2.7/library/argparse.html). Most likely this isn't the lightest way of doing it, that would probably be `sys.argv`, but it comes with some helpful features.

    :::python
    import argparse
    
    parser = argparse.ArgumentParser(
                 description='Accept on stdin, forward to lmtp')
    parser.add_argument('-s',
                        '--sender',
                        help='Sender email address (required)',
                        required=True)
    parser.add_argument('-r',
                        '--receiver',
                         help='Receiving local user (required)',
                         required=True)
    args = parser.parse_args()
    
    sender = args.sender
    username = args.receiver

Now I have access to the sender and local username I need for LMTP

## stdin

Sure you can process the content of `stdin` in Python, it is part of the [`sys`](https://docs.python.org/2.7/library/sys.html) library. A bit of prototyping showed me that I would have full access to the email message via `sys.stdin`. Played a bit with `readline()` but ended up with a plain `read()` as I do not care for the mail body, I must assume it is already properly formatted.

The ultimate result shows up only as an argument to `smtplib.sendmail` where it is passed as `sys.stdin.read()`.

## LMTP

Python comes with a nice standard library [`smtplib`](https://docs.python.org/2.7/library/smtplib.html) that also knows how to handle `LMTP` (they're not that different). Instantiate an `smtplib.LMTP` object and use it to connect to the LMTP socket.

    :::python
    import smtplib
    lmtpconn = smtplib.LMTP(lmtpsock)

Then use that socket to deliver the mail

    :::python
    lmtpconn.sendmail(sender, username, sys.stdin.read())

Be a nice netizen and close the socket when done

    :::python
    lmtpconn.quit()

## Error handling, logging

The previous paragraphs are all that's needed for the python script, but only in a world where nothing goes wrong ever. We need to handle some errors and I wanted to add some logging too. As usual this becomes the bulk of the code.

The bits that I want are in the [`syslog`](https://docs.python.org/2.7/library/syslog.html) library. I want to make sure the logs tell me that lda2lmtp was to blame and provided some additional input on what went wrong in the system logs.

## lda2lmtp

Behold! My first Python script.

    #!python
    #!/usr/local/bin/python2.7
    
    # The only objective of this script is to receive a complete mail mime message
    # on stdin and deliver it using LMTP.
    # The usecase I have for this is using rspamc to classify the mail and then use
    # make it pipe it through a command.
    #
    #     deliver to mda "/usr/local/bin/rspamc -h scan --mime \
    #         -e \"/usr/local/bin/lda2lmtp
    #                  -s %{sender} -d %{user.username} \" "
    
    import sys
    import smtplib
    import argparse
    import syslog
    
    lmtpsock = '/var/run/dovecot-lmtp/lmtp'
    
    # Use fancy argument parsing
    parser = argparse.ArgumentParser(
                 description='Accept on stdin, forward to lmtp')
    parser.add_argument('-s', '--sender',
                        help='Sender email address (required)',
                        required=True)
    parser.add_argument('-r', '--receiver',
                         help='Receiving local user (required)',
                         required=True)
    args = parser.parse_args()
    
    sender = args.sender
    username = args.receiver
    
    syslog.openlog(ident='lda2lmtp',
                   logoption=syslog.LOG_PID,
                   facility=syslog.LOG_MAIL)
    
    def logerr(errmsg=""):
        syslog.syslog(syslog.LOG_ERR, errmsg)
        print(errmsg)
    
    # Connect to the LMTP socket
    try:
        lmtpconn = smtplib.LMTP(lmtpsock)
    except:
        errmsg = 'Failed to connect to ' + lmtpsock
        syslog.syslog(syslog.LOG_ERR, errmsg)
        print(errmsg)
        sys.exit(1)
    
    # Uncomment to get more debugging output on stdout
    #lmtpconn.set_debuglevel(True)
    
    # Try to dump all input to the LMTP socket
    # using sender and username from args
    try:
        lmtpconn.sendmail(sender, username, sys.stdin.read() )
    except smtplib.SMTPRecipientsRefused:
        errmsg = 'Receiver ' + username + ' invalid'
        syslog.syslog(syslog.LOG_ERR, errmsg)
        print(errmsg)
        sys.exit(1)
    except smtplib.SMTPException:
        errmsg = 'LMTP Exception, from: ' + sender + ', to: ' + username
        syslog.syslog(syslog.LOG_ERR, errmsg)
        print(errmsg)
        sys.exit(1)
    else:
        syslog.syslog(syslog.LOG_INFO,
            'Delivered mail using lmtp from: ' + sender + ', to: ' + username)
        print('Success')
    finally:
        lmtpconn.quit()


Even did some PEP8 style things here.

# Tying everything together

The original 'deliver locally to Dovecot' configuration in OpenSMTPD was

    accept from any \
           for domain <domains> alias <aliases> \
           deliver to mda "/usr/local/bin/rspamc -h scan --mime \
               -e \"/usr/local/libexec/dovecot/deliver -d %{user.username}\""

This needs adapting to include the sender address and use the `lda2lmtp.py` script

    accept from any \
           for domain <domains> alias <aliases> \
           deliver to mda "/usr/local/bin/rspamc -h scan --mime \
               -e \"/usr/local/bin/lda2lmtp -s %{sender}-r %{user.username}\""

# Testing and final words

This all seems to work flawlessly. I had a bit of doubt that there might be an edge-case when a mail is sent to two recipients on the same server. OpenSMTPD takes care of that by delivering the messages to each recipient in a separate call.
If the script returns an error, OpenSMTPD goes into retries

Now that I can connect to Dovecot over a socket, I can finally move it to its own jail. The (ez)jail is already prepared, but now it needs some plumbing. DNS changes, extra null-mounts...
