Title: Using your jails easier
Tags: FreeBSD, jails
Modified: 2016-12-11
Author: Bernard Spil
Image: /img/BeastieJailed.jpg
Summary: Recently on Twitter I said I was using `jx` to run programs in my FreeBSD jails and there were requests to create a port for them. As I think these are so basic, I decided to just create a short blogpost and host the scripts myself. Whilst doing so I discovered that over the years my scripts grew stale even though they still worked!

# History

The reason I have the scripts is mostly historical. In the old days, there were no jail names. Checking old versions of man-pages I can see that `-n <jailname>` was added to  the [`jexec(8)`](https://www.freebsd.org/cgi/man.cgi?query=jexec&sektion=8) command and that [`jls`](https://www.freebsd.org/cgi/man.cgi?query=jls&sektion=8) added the `-N` option to output jail names in stead of jail IDs.

The original scripts mostly dealt with being able to execute commands in a jail referring to it by its name. This was accomplished by looking at the hostname set for the jail and some `sed`.

My jails don't have OpenSSH or cron running.

# Update

Now that jail has added support for names, the scripts are now a lot simpler. No more regular expressions to look for the jail by its name. The 'name' capability of `jls` and `jexec` reduced the size of the scripts by over a third.

There are 2 scripts that I use regularly, namely `jx` (run a command in a jail) and `jsh` (start a shell in a jail)

## `jx`

There is (was?) a [port named `jx`](https://www.freshports.org/sysutils/jx) which requires perl which I found to be overkill for what I wanted. My private `jx` is a simple shell script that just does what I want and doesn't want to be too smart.

The main usage now is to cycle over all started jails to run a command. You'll easily find uses for this in periodic scripts etc. You may run into trouble when you're using elaborate quoting in the command you're passing. For these usage types I create shell scripts inside the jail that I then call using `jx`.

    :::sh
    #!/bin/sh -e
    
    [ `id -u` -ne 0 ] && { echo Not root... exiting... ; exit 1 ; }
   
    usage () {
       cat <<-USAGE
        Execute a command in a jail by name or in all jails
        Usage: ${0##*/} [-s] <jailname>|all <command>
                         -s : silent
        USAGE
    }
    
    # Need at least a jail name and a command
    [ $# -lt 2 ] && { usage ; exit ; }
    
    if [ "$1" = "-s" ] ; then
       silent=YES
       shift
    fi
    
    # Still need at least a jail name and a command
    [ $# -lt 2 ] && { usage ; exit ; }
     
    if [ "$1" = "all" ] ; then
       shift
       rcall=0
       for jname in `jls name` ; do
          [ -n "$silent" ] && echo Jail: $jname
          set +e
          jexec $jname "$@"
          set -e
          rc=$?
          [ $rc -gt $rcall ] && rcall=$rc
       done
       exit $rcall
    else
       jname=$1
       shift
       # Test if jail exists
       set +e
       jls -j ${jname} jid 1>/dev/null 2>&1
       RC=$?
       set -e
       if [ $RC -gt 0 ] ; then
          echo -e "\e[31mJail \e[1m""${jname}""\e[0;31m not started or unknown\e[0m"
          usage; exit 1
       fi
       jexec $jname "$@"
       exit $?
    fi

See? Simple.

## `jsh`

The `jsh` script was started because I found typing `jexec <jid> csh` too cumbersome and for some of my jails I wanted non-standard things to happen.

    :::sh
    #!/bin/sh -e
    
    [ `id -u` -ne 0 ] && { echo Not root... exiting... ; exit 1 ; }
      
    usage () {
       cat <<-USAGE
            Execute a shell in a jail by name
            Usage: ${0##*/} <jailname>
            USAGE
    }
     
    set +e
    jls -j $1 jid 1>/dev/null 2>&1
    RC=$?
    set -e
    if [ $RC -gt 0 ] ; then
       echo "Jail ""${jname}"" not started or unknown" >2
       usage; exit 1
    fi
    
    # This is where you fiddle with parameters or set
    # non-default shells for jails
    case $1 in
       build) jshell=zsh; jopts="-U brnrd";;
    esac
    jexec ${jopts} $1 ${jshell:-csh}
    
    echo -e "\e[32mLeft jail $1"

My "build" jail is where I do porting. In stead of jumping into the jail and then switching to the regular user, I can now just run `jsh build`.

# Usage tips

These scripts I use heavily for maintaining jails.

## periodic

One of the uses of the `jx` script is in my periodic scripts. If you run cron in your jails you will, in the default configuration, start all hourly, daily, weekly and monthly scripts in parallel. Depending on what you do in the jails this could result in a very busy system and potentially resource exhaustion. This happens because all cron daemons will start the periodic script at exactly the same time (give or take a second).

If you don't need cron for other purposes in your jails you can  disable cron in all your jails:

    :::sh
    jx all sysrc cron_enable=NO
    jx all service cron onestop

Or alternatively disable the periodic entries in the jails 

    :::sh
    jx all sed -e 's/^\(.*periodic\)/#\1/' /etc/crontab

and add to your periodic conf files

    :::sh
    for interval in daily weekly monthly ; do
       echo jx all periodic ${interval} >> /etc/${interval}.conf
    done

In e.g. daily, `periodic` runs whatever is in /etc/daily.conf in addition to the regular entries it runs for the host. This causes the periodic jobs to now run in sequence, and no longer in parallel.

If you don't need to be able to modify crontab entries from within the jail, you can add regular crontab entries from the jails in the host's crontab

    :::sh
    # Purge stale entries from dspam database (daily, 09:31)
    31 9 * * *      jx database /root/bin/dspam-purge.sh
    # Update SpamAssassin rules (daily 00:32)
    32 0 * * *      jx amavisd /root/bin/sa-update.sh
    # Process reported spam / ham (hourly :57)
    57 * * * *      jx amavisd /root/bin/dspam-learn.sh
    # Update ClamAV virus databases (hourly :53)
    53 * * * *      jx amavisd /root/bin/freshclam.sh

You can also run cron jobs in the jails as different users if you use something like

    :::sh
    23 * * * *      jexec -U www webserver /usr/local/www/webapp/cron.php

Check the [`jexec` manpage](https://www.freebsd.org/cgi/man.cgi?query=jexec) for the possibilities.