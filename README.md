# SIP DNS Lookup

This script queries SIP-related DNS records for a given domain.  
It attempts to find NAPTR and/or SRV records relevant for SIP.

Depends on `dnspython`

## Usage

```bash
pip install -r requirements.txt
python sip_dns_lookup.py sip.daily.co
```

## What it does

1. Queries NAPTR records for the domain.
  * If NAPTR records reference SIP SRV records, queries them.
  * If no NAPTR records exist, queries `_sip._tcp` and `_sip._udp` SRV records directly.
2. Queries and outputs SRV record details (priority, weight, port, target).


