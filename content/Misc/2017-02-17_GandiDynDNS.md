Title: Adding DynDNS to Gandi.net
Date: 2017-02-17
Tags: FreeBSD, DNS
Image: /img/PVOutput-Goodwe.png
Summary: [Gandi.net](https://gandi.net) doesn't support DynDNS but does have a [DNS API](http://doc.rpc.gandi.net/). Surely there must be a way to create a dyndns-like capability to my Gandi.net domain using the API?!? This also inluded an opportunity to learn a bit more about Python.

= Old solution(s) =

Having friends is a good thing. This allowed me to use a dynamic DNS service that operated very simply using a http GET call to update a sub-domain. It simply responds `No update needed` if the IP-address you're calling from hasn't changed. This is not a good solution if you want to host your own mail-server!

When I was doing my IPv6 certification with [Huricane Electric](https://he.net) I ran into the dynamic DNS service that they have. To get access to their DNS service, you have to do the [IPv6 certification](https://ipv6.he.net/certification/) but the service is pretty good! You can enable dynamic updates for specific DNS entries, each entry having its own `DDNS key` for authentication.

== Shell Scripts ==

To update your DNS records, you need to know the IP-address your ISP has allocated to you. For this I had created a shell script. Prety self-explanatory I hope...

    :::sh
    getMyWANIP () {
    local currentIP persistfile oldIP
    persistfile=/etc/currentWanIp
    oldIP=$(cat $persistfile)

    # Retrieve the page containing the IP-address from the router
    result=`fetch -q -o- http://username:password@192.0.2.1/cgi-bin/status-interfaces.sh`
    RC=$?

    if [ $RC -eq 0 ] ; then
       # Extract the IP-address from the web-page (crude!)
       currentIP=$(echo "${result}" | grep -A 1 -m 1 "IP Address" | tail -n 1 | tr -dc '[0-9.]')
       if [ ! "${currentIP}" = "${oldIP}" ] ; then
          echo -n ${currentIP} > ${persistfile}
       fi
    else
       currentIP=${oldIP}
    fi

    echo -n $currentIP
    }

In my DynDNS script I would use kind of a voting system to check if the IP-address updated or if the ISP link was down.

    #!/bin/sh
    . /home/root/bin/myWanIP.inc

    hostname=brnrd.eu
    DDNSKey=<myHEnetDDNSkey>
    HEnetAccount=<myHEnetAccount>
    CACert="--ca-cert=/etc/ssl/certs/cacert3.pem"
    HEurl="https://dyn.dns.he.net/nic/update"

    sendMail() {
       [ $# -gt 0 ] && mailSubject="$*"
       mail -s "$mailSubject" root@brnrd.eu <<- MAIL-BODY
       dyndns.myfriend.net result: $myfriendResult
       dyndns.myfriend.net     RC: $myfriendRC
       dyndns.myfriend.net  error: $myfriendError

       dyn.dns.he.net     result: $HEnetResult
       dyn.dns.he.net         RC: $HEnetRC
       dyn.dns.he.net      error: $henetError
       MAIL-BODY
    }

    updateHEnet () {
       local hostname errFile url fetchResult fetchRC
       hostname=$1
       errFile=$2
       url="${HEurl}?password=${DDNSKey}&hostname=${hostname}"
       fetchResult=`fetch -4qo- ${CACert} "${url}" 2>>${errFile}`
       fetchRC=$?
       [ $# -ge 3 ] && eval $3="${fetchResult%% *}"
       [ $# -ge 4 ] && eval $4="${fetchResult##* }"
       return ${fetchRC}
    }

    # Initialize Integer variables
    IPAddressChanged=0
    fetchRC=0

    rm -f /tmp/henetResult.err

    myfriendResult=`fetch -4qo- http://dyndns.myfriend.net:37/0.0.0.0/spil.myfriend.net/<DDNSkey>/ 2>/tmp/myfriendResult.err`
    myfriendRC=$?
    # RC !=0 -> fetch error # Result != "No update needed" -> IP address changed
    [ "X${myfriendResult}" != "XUpdate not needed" ] && IPAddressChanged=$((IPAddressChanged+1))
    [ "${myfriendRC}" -gt 0 ] && {
       fetchRC=$((fetchRC+1)) # set 1st bit
       myfriendError=`cat /tmp/myfriendResult.err`
    }

    updateHEnet brnrd.eu /tmp/henetResult.err HEnetResult HEnetIP
    HEnetRC=$?
    [ "${HEnetResult}" = "good" ] && {
       IPAddressChanged=$((IPAddressChanged+1))
       updateHEnet ${hostname} /tmp/henetResult.err
    }
    [ ${HEnetRC} -gt 0  ] && {
       fetchRC=$((fetchRC+2)) # set 2nd bit
       henetError=`cat /tmp/henetResult.err`
    }

    # No changes to IP-address so move on
    [ ${IPAddressChanged} -eq 0 ] && exit 0

    # Both fetches failed, no internet connection?
    [ ${fetchRC} -eq 3 ] && {
       sendMail "Updating Dynamic DNS Failed: No internet connection?"
       exit 2
    }

    # IP address seems to have changed
    # Single vote...
    [ ${IPAddressChanged}  -eq 1 ] && {
       # Inconclusive result
       [ ${HEnetRC} -eq 0 ] && {
       getIPaddress modemIP
       [ "X${HEnetIP}" = "X${modemIP}" ] && sendMail "IP Address changed"
          exit 1
       }
       [ ${HEnetRC} -ge 1 ] && sendMail "IP Address likely changed"
       exit 1
    }

= Python =

Since the examples of Gandi.net use Python, I thought this was a good opportunity to learn a bit more python-scripting. To replace the earlier shell script to retrieve the IP-address from the router

    :::py
    import httplib
    import re

    # Retrieve status page from CPE
    conn = httplib.HTTPConnection('192.0.2.1')
    
    # Create your Basic-auth string with \
    # echo -n "username:password" | b64encode -r auth
    req = conn.request("GET","/cgi-bin/status-interfaces.sh","",{"Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="})
    body = conn.getresponse().read()
    
    # Extract current IP-address from html body
    p1 = re.compile(r'<tr id="wan_ip_addr">.*?(\d*\.\d*\.\d*\.\d*).*?</tr>\n',re.DOTALL)
    s1 = p1.search(body)
    inetIP = s1.group(1)

