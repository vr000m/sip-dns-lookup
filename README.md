# SIP DNS Lookup

This script queries SIP-related DNS records for a given domain.  
It attempts to find NAPTR and/or SRV records relevant for SIP.

Depends on `dnspython`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Single domain lookup
```bash
python sip_dns_lookup.py sip.example.com
```

### Extract domain from SIP address
```bash
python sip_dns_lookup.py user@sip.example.com
```

### Batch mode (multiple domains)
```bash
python sip_dns_lookup.py domain1.com domain2.com domain3.com
```

### Read domains from file
```bash
# First, create your own domain list from the example
cp sample_domains.txt.example sample_domains.txt
# Edit sample_domains.txt with your domains

# Then run batch lookup
python sip_dns_lookup.py -f sample_domains.txt
```

### Testing
```bash
# Run test suite (uses sample_domains.txt by default)
python test_sip_domains.py

# Test with specific file
python test_sip_domains.py -f your_domains.txt
```

## What it does

1. Queries NAPTR records for the domain.
  * If NAPTR records reference SIP SRV records, queries them.
  * If no NAPTR records exist, queries `_sip._tcp` and `_sip._udp` SRV records directly.
2. Queries and outputs SRV record details (priority, weight, port, target).


