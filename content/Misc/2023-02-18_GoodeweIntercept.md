Title: Recent issues with Goodwe's SEMSportal
Date: 2023-02-18
Tags: Solar, PV, IoT
Image: /img/PVOutput-Goodwe.png
Summary: Update on how I get the telemetry from my Goodwe Photovolaic inverter to [PVOutput](https://PVoutput.org)

Make sure to check the [earlier article](/misc/2019-03-23/killing-the-internet-of-shit.html) first. And perhaps the [original shell scripting](/misc/2016-03-13/goodwe-logging-to-pvoutput.html) article as well.

# Broken

## SEMSPortal broken

Recently noticed "gap"s on [PVoutput](https://pvoutput.org/list.jsp?id=41528&sid=37948). Seems SEMSPortal is having problems?

I was still pulling the data from Goodwe's SEMS portal, so this prompted me to revisit my code.

## My "intercept" code broken

The [code in my GitHub](https://github.com/Sp1l/PhotoVoltaic/tree/master/GoodweIntercept) was broken...

That's all updated now, and what I'm running on FreeBSD.

## Use the Shell script

PVOutput requires data in 5, 10 or 15 minute intervals. My inverter sends new data ca. every 8 minutes.

So there's a script that takes the last line from the CSV output of the intercept code, and posts that to PVoutput every 5 minutes.

## Configuring

Make sure you check the `config.sh` and `config.inc.php` documented files in the git repo.