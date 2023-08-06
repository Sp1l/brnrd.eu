Title: History of hardware I used for FreeBSD
Tags: FreeBSD
Date: 2019-12-01
Modified: 2019-12-01 20:52
Author: Bernard Spil
Summary: As I was about to throw out the old laptop/servers I used before, I thought that I might as well document them!
Status: draft

My home-servers have always been named after the location they were in: the utilities cabinet. In Dutch that's the "meterkast" (meter closet). Oddly [meterkast](https://nl.wikipedia.org/wiki/Meterkast) has an article on Wikipedia, but there's no tranlations... Unlike in the US, the gas and electricity meter are located inside the house, hence the "meter".

Also, my home-servers have always been laptops. Already early on I was concerned about the powerdraw of the machine that's always powered-on. Nowadays you can get a < 10W idle system, but back in the day that was unheard of. Laptops have always been designed around limited battery power and have therefore been optimized to be frugal on my energy-bill.

# Dell Latitude LS

| Component | Model |
| :--- | :--- |
| CPU     | Intel Pentium III |
| Chipset | Intel BX433       |
| Memory  | 512MB |
| Disk | ??? PATA |
| Network | 3Com 3C920 100Mbps (internal) <BR> 3Com 3C575 100Mbps (CardBus) |

Bought from my work, probably 25€. It was pretty worn when I bought it
 Upgraded the disk and added the CardBus NIC so it would function as router.

# Dell D400

| Component | Model |
| :--- | :--- |
| CPU | Intel Centrino Mobile |
| Chipset | Intel 855GM |
| Memory  | 1GB DDR-266 |
| Disk | |
| Network | |


# Medion Akoya S5612

| Component | Model |
| :--- | :--- |
| CPU | [Intel Pentium SU4100](https://ark.intel.com/content/www/us/en/ark/products/43568/intel-pentium-processor-su4100-2m-cache-1-30-ghz-800-mhz-fsb.html) (2x1.3GHz) |
| Chipset | Intel 855GM |
| Memory | 4GB |
| Disk | |
| Network | |

This is when you find

# HP ProBook 8440p

| Component | Model |
| :--- | :--- |
| CPU | [Intel Core i5 520M](https://ark.intel.com/content/www/us/en/ark/products/47341/intel-core-i5-520m-processor-3m-cache-2-40-ghz.html) (2x2.4GHz) |
| Chipset | Intel QM57 |
| Memory  | 8GB (4+4) DDR3-1067 |
| Disk | 128GB 2.5" SSD <BR> 1863GB (2TiB) 2.5" <BR> 1630GB (1.75TB) 2.5" |
| Network | Intel 82577LM |

First server with an SSD. The DVD drive was replaced by a caddy containing the 2TB disk. The 1.75TB disk is connected using an eSATA-p cable.

# HP EliteBook 8570w

| Component | Model                                                                                                                                                     |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| CPU       | [Intel Core i7 3720QM](https://ark.intel.com/content/www/us/en/ark/products/64891/intel-core-i7-3720qm-processor-6m-cache-up-to-3-60-ghz.html) (4x2.6GHz) |
| Chipset   | Intel C216                                                                                                                                                |
| Memory    | 16GB (4+4+8) DDR3-1600                                                                                                                                    |
| Disk      | 512GB mSATA SSD <BR> 1863GB (2TiB) 2.5" <BR> 1630GB (1.75TiB) 2.5"                                                                                        |
| Network   | Intel 82579LM Gigabit                                                                                                                                     |

This laptop is from the "Intel Rapid Storage Technology" era. It came with a 24GB mSATA SLC Intel SSD that functions as a cache for the harddisk. I started building using a 256GB 2.5" SSD as boot-disk, but ended up buying a 512GB Samsung 860 EVO mSATA SSD. There's not a lot of choice any longer in mSATA SSDs!
The machine also has an eSATA-p connector but I'd rather have all disks inside the machine.