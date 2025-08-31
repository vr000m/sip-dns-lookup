# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python utility for querying SIP-related DNS records (NAPTR and SRV) for a given domain. The script attempts to find NAPTR records first, and if they reference SIP SRV records, queries them. If no NAPTR records exist, it falls back to querying `_sip._tcp` and `_sip._udp` SRV records directly.

## Commands

### Running the script
```bash
# Single domain
python sip_dns_lookup.py sip.example.com

# Parse SIP address and extract domain
python sip_dns_lookup.py user@sip.example.com

# Multiple domains (batch mode)
python sip_dns_lookup.py domain1.com domain2.com

# Read domains from file
python sip_dns_lookup.py -f domains.txt

# Custom timeout
python sip_dns_lookup.py -t 10 sip.example.com
```

### Testing
```bash
# First time setup: copy example file and add your domains
cp sample_domains.txt.example sample_domains.txt
# Edit sample_domains.txt with your test domains

# Run comprehensive test suite
python test_sip_domains.py

# Test with specific file
python test_sip_domains.py -f your_domains.txt
```

### Installing dependencies
```bash
# Using virtual environment (recommended)
source .venv/bin/activate
pip install -r requirements.txt
```

## Architecture

### Main script (`sip_dns_lookup.py`)
Key functions:
- `query_naptr(domain, timeout)`: Queries NAPTR records with timeout handling
- `query_srv(name, timeout)`: Queries SRV records with timeout handling
- `parse_naptr_for_sip(naptr_records)`: Parses NAPTR records to find SIP services and replacement SRV targets
- `parse_sip_address(address)`: Extracts domain from SIP addresses (user@domain format)
- `process_batch(domains)`: Handles multiple domain queries
- `main(domain)`: Orchestrates the DNS lookup process for a single domain

### Test suite (`test_sip_domains.py`)
Comprehensive testing utility that:
- Parses SIP addresses from various formats
- Tests multiple domains in sequence
- Provides detailed success/failure summary

### DNS lookup flow
1. First attempts NAPTR record lookup
2. Checks NAPTR replacement fields for direct SRV targets
3. If NAPTR records contain SIP services (SIP+D2U, SIP+D2T, SIP+D2S), queries the referenced SRV records
4. If no NAPTR records or no SIP services found, falls back to direct SRV queries for `_sip._tcp` and `_sip._udp`
5. All queries include configurable timeout handling to prevent hanging on slow DNS servers

## Dependencies

- Python 3.7+
- dnspython>=2.0.0 (DNS resolution library)