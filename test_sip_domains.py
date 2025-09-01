#!/usr/bin/env python3
import sys
import os
import argparse
import logging
from typing import List, Dict, Any
from sip_dns_lookup import query_naptr, query_srv, parse_naptr_for_sip, parse_sip_address

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Use the parse_sip_address function from main module to avoid duplication
extract_domain_from_sip = parse_sip_address

def test_domain(domain: str) -> Dict[str, Any]:
    """Test a single domain for SIP DNS records."""
    print(f"\n{'='*60}")
    print(f"Testing: {domain}")
    print('='*60)
    
    results: Dict[str, Any] = {
        'domain': domain,
        'naptr': False,
        'srv_tcp': False,
        'srv_udp': False,
        'targets': []
    }
    
    # Query NAPTR records
    print(f"Querying NAPTR records...")
    naptr_records = query_naptr(domain)
    srv_names_to_query = []
    
    if naptr_records:
        results['naptr'] = True
        print(f"  ✓ Found {len(naptr_records)} NAPTR record(s)")
        naptr_services, srv_targets = parse_naptr_for_sip(naptr_records)
        
        # Add direct SRV targets from NAPTR replacement fields
        if srv_targets:
            print(f"  → Found {len(srv_targets)} SRV target(s) in NAPTR records")
            srv_names_to_query.extend(srv_targets)
        
        # Add service-based SRV names
        for service in naptr_services:
            srv_names_to_query.append(f"{service}{domain}")
        
        # If no SIP-related NAPTR records, fall back to standard SRV
        if not naptr_services and not srv_targets:
            srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]
    else:
        print(f"  ✗ No NAPTR records found")
        srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]
    
    # Query SRV records
    for srv_name in srv_names_to_query:
        service_type = "unknown"
        if "_tcp" in srv_name:
            service_type = "TCP"
        elif "_udp" in srv_name:
            service_type = "UDP"
        elif "_sctp" in srv_name:
            service_type = "SCTP"
        
        print(f"\nQuerying SRV records for {srv_name}...")
        srv_records = query_srv(srv_name)
        
        if srv_records:
            if "_tcp" in srv_name:
                results['srv_tcp'] = True
            elif "_udp" in srv_name:
                results['srv_udp'] = True
            
            print(f"  ✓ Found {len(srv_records)} SRV record(s):")
            for record in srv_records:
                target_info = f"    → {record.target}:{record.port} (Priority: {record.priority}, Weight: {record.weight})"
                print(target_info)
                results['targets'].append(str(record.target))
        else:
            print(f"  ✗ No SRV records found")
    
    return results

def load_test_addresses(filename: str) -> List[str]:
    """Load test addresses from file."""
    test_addresses: List[str] = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        test_addresses.append(line)
        except PermissionError:
            logger.error(f"Permission denied reading file '{filename}'")
        except UnicodeDecodeError:
            logger.error(f"File '{filename}' contains invalid UTF-8 characters")
        except IOError as e:
            logger.error(f"Error reading file '{filename}': {e}")
    return test_addresses

def main():
    parser = argparse.ArgumentParser(
        description='Test SIP DNS lookups for multiple domains',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-f', '--file', 
        default='sample_domains.txt',
        help='File containing domains/SIP addresses to test (default: sample_domains.txt)'
    )
    parser.add_argument(
        'addresses', 
        nargs='*', 
        help='Additional SIP addresses or domains to test'
    )
    
    args = parser.parse_args()
    
    # Load addresses from file
    test_addresses = []
    if args.file and os.path.exists(args.file):
        test_addresses.extend(load_test_addresses(args.file))
        print(f"Loaded addresses from: {args.file}")
    elif args.file and not os.path.exists(args.file):
        print(f"Warning: File '{args.file}' not found, using command-line arguments only")
    
    # Add command-line addresses
    test_addresses.extend(args.addresses)
    
    if not test_addresses:
        print("No addresses to test. Provide addresses via -f file or as arguments.")
        sys.exit(1)
    
    print("SIP DNS Lookup Test Suite")
    print("=" * 60)
    
    # Extract unique domains
    domains = []
    for addr in test_addresses:
        domain = extract_domain_from_sip(addr)
        if domain and domain not in domains:
            domains.append(domain)
    
    print(f"Found {len(domains)} unique domain(s) to test:")
    for i, domain in enumerate(domains, 1):
        print(f"  {i}. {domain}")
    
    # Test each domain
    all_results = []
    for domain in domains:
        try:
            result = test_domain(domain)
            all_results.append(result)
        except Exception as e:
            print(f"\n✗ Error testing {domain}: {e}")
            all_results.append({
                'domain': domain,
                'naptr': False,
                'srv_tcp': False,
                'srv_udp': False,
                'targets': [],
                'error': str(e)
            })
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    successful = 0
    for result in all_results:
        status = "✓" if (result['srv_tcp'] or result['srv_udp']) else "✗"
        record_types = []
        if result['naptr']:
            record_types.append("NAPTR")
        if result['srv_tcp']:
            record_types.append("SRV-TCP")
        if result['srv_udp']:
            record_types.append("SRV-UDP")
        
        if result['srv_tcp'] or result['srv_udp']:
            successful += 1
            
        records_str = ", ".join(record_types) if record_types else "None"
        print(f"{status} {result['domain']:<40} Records: {records_str}")
        
        if 'error' in result:
            print(f"    Error: {result['error']}")
    
    print(f"\nSuccessful lookups: {successful}/{len(all_results)}")

if __name__ == "__main__":
    main()