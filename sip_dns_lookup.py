#!/usr/bin/env python3
import sys
import argparse
import re
import logging
from typing import List, Tuple, Optional, Any
import dns.resolver
import dns.exception

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def query_naptr(domain: str, timeout: float = 5.0, resolver: Optional[dns.resolver.Resolver] = None) -> List[Any]:
    """Query NAPTR records for a domain.
    
    Args:
        domain: The domain to query
        timeout: Query timeout in seconds
        resolver: Optional DNS resolver instance to reuse
    
    Returns:
        List of NAPTR records or empty list on failure
    """
    if not validate_domain(domain):
        logger.warning(f"Invalid domain name for NAPTR query: {domain}")
        return []
    
    try:
        if resolver is None:
            resolver = dns.resolver.Resolver()
        resolver.timeout = min(timeout, 30.0)  # Cap timeout at 30 seconds
        resolver.lifetime = min(timeout * 2, 60.0)  # Allow slightly more time for retries
        answers = resolver.resolve(domain, 'NAPTR')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except dns.resolver.Timeout:
        logger.warning(f"NAPTR query for {domain} timed out after {timeout} seconds")
        return []
    except dns.exception.DNSException as e:
        logger.warning(f"NAPTR query for {domain} failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in NAPTR query for {domain}: {e}")
        return []

def query_srv(name: str, timeout: float = 5.0, resolver: Optional[dns.resolver.Resolver] = None) -> List[Any]:
    """Query SRV records for a service name.
    
    Args:
        name: The SRV name to query (e.g., _sip._tcp.example.com)
        timeout: Query timeout in seconds
        resolver: Optional DNS resolver instance to reuse
    
    Returns:
        List of SRV records or empty list on failure
    """
    # Extract just the domain part for validation
    # SRV names like _sip._tcp.example.com are valid
    domain_part = name
    if name.startswith('_'):
        # Skip service prefixes for validation
        parts = name.split('.')
        # Find where the actual domain starts (after service prefixes)
        domain_start = 0
        for i, part in enumerate(parts):
            if not part.startswith('_'):
                domain_start = i
                break
        domain_part = '.'.join(parts[domain_start:])
    
    if domain_part and not validate_domain(domain_part):
        logger.warning(f"Invalid domain in SRV query: {name}")
        return []
    
    try:
        if resolver is None:
            resolver = dns.resolver.Resolver()
        resolver.timeout = min(timeout, 30.0)  # Cap timeout at 30 seconds
        resolver.lifetime = min(timeout * 2, 60.0)  # Allow slightly more time for retries
        answers = resolver.resolve(name, 'SRV')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except dns.resolver.Timeout:
        logger.warning(f"SRV query for {name} timed out after {timeout} seconds")
        return []
    except dns.exception.DNSException as e:
        logger.warning(f"SRV query for {name} failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in SRV query for {name}: {e}")
        return []

def parse_naptr_for_sip(naptr_records: List[Any]) -> Tuple[List[str], List[str]]:
    """Parse NAPTR records to extract SIP services and SRV targets."""
    services: List[str] = []
    srv_targets: List[str] = []
    
    for r in naptr_records:
        # Check service field for SIP protocols
        if hasattr(r, 'service') and (b"SIP+D2U" in r.service or b"SIP+D2T" in r.service or b"SIP+D2S" in r.service):
            # Check if there's a replacement field pointing to an SRV record
            if hasattr(r, 'replacement') and str(r.replacement) != '.':
                srv_target = str(r.replacement)
                if srv_target.endswith('.'):
                    srv_target = srv_target[:-1]
                srv_targets.append(srv_target)
            else:
                # Standard service prefixes
                if b"SIP+D2U" in r.service:
                    services.append('_sip._udp.')
                if b"SIP+D2T" in r.service:
                    services.append('_sip._tcp.')
                if b"SIP+D2S" in r.service:  # SCTP
                    services.append('_sip._sctp.')
    
    return services, srv_targets

def main(domain: str, timeout: float = 5.0) -> None:
    """Main function to query SIP DNS records for a domain."""
    # Create a single resolver instance to reuse
    resolver = dns.resolver.Resolver()
    
    print(f"Querying NAPTR records for {domain}...")
    naptr_records = query_naptr(domain, timeout, resolver)
    
    srv_names_to_query: List[str] = []
    
    if naptr_records:
        naptr_services, srv_targets = parse_naptr_for_sip(naptr_records)
        
        # Add direct SRV targets from NAPTR replacement fields
        if srv_targets:
            print(f"Found {len(srv_targets)} SRV target(s) in NAPTR records")
            srv_names_to_query.extend(srv_targets)
        
        # Add service-based SRV names
        if naptr_services:
            for service in naptr_services:
                srv_names_to_query.append(f"{service}{domain}")
        
        # If no SIP-related NAPTR records, fall back to standard SRV
        if not naptr_services and not srv_targets:
            print("No SIP NAPTR records found. Trying SRV records directly.")
            srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]
    else:
        print("No NAPTR records found. Trying SRV records directly.")
        srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]

    # Query all SRV records
    for srv_name in srv_names_to_query:
        print(f"\nQuerying SRV records for {srv_name}...")
        srv_records = query_srv(srv_name, timeout, resolver)
        if srv_records:
            for record in srv_records:
                print(f"Priority: {record.priority}, Weight: {record.weight}, Port: {record.port}, Target: {record.target}")
        else:
            print("No SRV records found.")

def process_batch(domains: List[str], timeout: float = 5.0) -> None:
    """Process multiple domains."""
    print(f"Processing {len(domains)} domain(s)...\n")
    for i, domain in enumerate(domains, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(domains)}] Domain: {domain}")
        print('='*60)
        main(domain.strip(), timeout)

def validate_domain(domain: str) -> bool:
    """Validate domain name for DNS query safety."""
    if not domain or len(domain) > 253:  # Max DNS name length
        return False
    
    # Check for valid characters
    # Domain regex: alphanumeric, dots, hyphens
    if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
        return False
    
    # Check label lengths (max 63 chars per label)
    labels = domain.split('.')
    for label in labels:
        if not label or len(label) > 63:
            return False
        # Labels can't start or end with hyphen
        if label.startswith('-') or label.endswith('-'):
            return False
    
    return True

def parse_sip_address(address: str) -> Optional[str]:
    """Extract domain from SIP address (e.g., user@domain)."""
    if not address:
        return None
    address = address.replace("sip:", "").replace("sips:", "").strip()
    if not address:
        return None
    
    # Remove angle brackets if present
    address = address.strip('<>')
    
    if "@" in address:
        domain = address.split("@")[1]
        domain = domain.split(":")[0].split(";")[0].split(">")[0].strip()
    else:
        domain = address
    
    # Validate domain before returning
    if domain and validate_domain(domain):
        return domain
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Query SIP-related DNS records (NAPTR, SRV) for domains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sip.example.com                    # Query single domain
  %(prog)s user@sip.example.com               # Extract domain from SIP address
  %(prog)s -f domains.txt                     # Read domains from file
  %(prog)s domain1.com domain2.com            # Query multiple domains
        """)
    
    parser.add_argument('domains', nargs='*', help='Domain(s) to query (can be SIP addresses)')
    parser.add_argument('-f', '--file', help='File containing domains/SIP addresses (one per line)')
    parser.add_argument('-t', '--timeout', type=float, default=5.0, 
                       help='DNS query timeout in seconds (default: 5.0, min: 0.1, max: 30)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output (show warnings and debug info)')
    
    args = parser.parse_args()
    
    # Configure logging based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
    
    # Validate timeout
    if args.timeout < 0.1 or args.timeout > 30:
        print(f"Error: Timeout must be between 0.1 and 30 seconds (got {args.timeout})")
        sys.exit(1)
    
    # Collect domains to process
    domains_to_process: List[str] = []
    
    # Add domains from file if specified
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        domain = parse_sip_address(line)
                        if domain:
                            domains_to_process.append(domain)
                        else:
                            logger.warning(f"Invalid address on line {line_num} of {args.file}: '{line}'")
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found")
            sys.exit(1)
        except PermissionError:
            print(f"Error: Permission denied reading file '{args.file}'")
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Error: File '{args.file}' contains invalid UTF-8 characters")
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file '{args.file}': {e}")
            sys.exit(1)
    
    # Add domains from command line
    for arg_domain in args.domains:
        domain = parse_sip_address(arg_domain)
        if domain:
            domains_to_process.append(domain)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_domains: List[str] = []
    for domain in domains_to_process:
        if domain not in seen:
            seen.add(domain)
            unique_domains.append(domain)
    
    # Process domains
    if not unique_domains:
        parser.print_help()
        sys.exit(1)
    elif len(unique_domains) == 1:
        main(unique_domains[0], args.timeout)
    else:
        process_batch(unique_domains, args.timeout)
