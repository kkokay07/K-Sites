"""
Organism Resolver for K-Sites

This module resolves organism identifiers (TaxID or scientific name) 
to standardized organism information using NCBI E-Utils.
"""

import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path
import time

# Set up logging
logger = logging.getLogger(__name__)

# Common organism mapping as fallback
COMMON_ORGANISMS = {
    "9606": {"taxid": "9606", "scientific_name": "Homo sapiens", "common_name": "human"},
    "human": {"taxid": "9606", "scientific_name": "Homo sapiens", "common_name": "human"},
    "Homo sapiens": {"taxid": "9606", "scientific_name": "Homo sapiens", "common_name": "human"},
    
    "10090": {"taxid": "10090", "scientific_name": "Mus musculus", "common_name": "mouse"},
    "mouse": {"taxid": "10090", "scientific_name": "Mus musculus", "common_name": "mouse"},
    "Mus musculus": {"taxid": "10090", "scientific_name": "Mus musculus", "common_name": "mouse"},
    
    "10116": {"taxid": "10116", "scientific_name": "Rattus norvegicus", "common_name": "rat"},
    "rat": {"taxid": "10116", "scientific_name": "Rattus norvegicus", "common_name": "rat"},
    "Rattus norvegicus": {"taxid": "10116", "scientific_name": "Rattus norvegicus", "common_name": "rat"},
    
    "7227": {"taxid": "7227", "scientific_name": "Drosophila melanogaster", "common_name": "fruit fly"},
    "fruit fly": {"taxid": "7227", "scientific_name": "Drosophila melanogaster", "common_name": "fruit fly"},
    "Drosophila melanogaster": {"taxid": "7227", "scientific_name": "Drosophila melanogaster", "common_name": "fruit fly"},
    
    "6239": {"taxid": "6239", "scientific_name": "Caenorhabditis elegans", "common_name": "worm"},
    "worm": {"taxid": "6239", "scientific_name": "Caenorhabditis elegans", "common_name": "worm"},
    "Caenorhabditis elegans": {"taxid": "6239", "scientific_name": "Caenorhabditis elegans", "common_name": "worm"},
    
    "7955": {"taxid": "7955", "scientific_name": "Danio rerio", "common_name": "zebrafish"},
    "zebrafish": {"taxid": "7955", "scientific_name": "Danio rerio", "common_name": "zebrafish"},
    "Danio rerio": {"taxid": "7955", "scientific_name": "Danio rerio", "common_name": "zebrafish"},
    
    "4932": {"taxid": "4932", "scientific_name": "Saccharomyces cerevisiae", "common_name": "yeast"},
    "yeast": {"taxid": "4932", "scientific_name": "Saccharomyces cerevisiae", "common_name": "yeast"},
    "Saccharomyces cerevisiae": {"taxid": "4932", "scientific_name": "Saccharomyces cerevisiae", "common_name": "yeast"},
    
    # KEGG organism codes
    "hsa": {"taxid": "9606", "scientific_name": "Homo sapiens", "common_name": "human"},
    "mmu": {"taxid": "10090", "scientific_name": "Mus musculus", "common_name": "mouse"},
    "rno": {"taxid": "10116", "scientific_name": "Rattus norvegicus", "common_name": "rat"},
    "dme": {"taxid": "7227", "scientific_name": "Drosophila melanogaster", "common_name": "fruit fly"},
    "cel": {"taxid": "6239", "scientific_name": "Caenorhabditis elegans", "common_name": "worm"},
    "dre": {"taxid": "7955", "scientific_name": "Danio rerio", "common_name": "zebrafish"},
    "sce": {"taxid": "4932", "scientific_name": "Saccharomyces cerevisiae", "common_name": "yeast"},
    
    # Plants
    "39947": {"taxid": "39947", "scientific_name": "Oryza sativa Japonica Group", "common_name": "rice"},
    "Oryza sativa Japonica Group": {"taxid": "39947", "scientific_name": "Oryza sativa Japonica Group", "common_name": "rice"},
    "Oryza sativa japonica": {"taxid": "39947", "scientific_name": "Oryza sativa Japonica Group", "common_name": "rice"},
    "rice": {"taxid": "39947", "scientific_name": "Oryza sativa Japonica Group", "common_name": "rice"},
    
    "3702": {"taxid": "3702", "scientific_name": "Arabidopsis thaliana", "common_name": "thale cress"},
    "Arabidopsis thaliana": {"taxid": "3702", "scientific_name": "Arabidopsis thaliana", "common_name": "thale cress"},
    "arabidopsis": {"taxid": "3702", "scientific_name": "Arabidopsis thaliana", "common_name": "thale cress"},
    
    "4577": {"taxid": "4577", "scientific_name": "Zea mays", "common_name": "maize"},
    "Zea mays": {"taxid": "4577", "scientific_name": "Zea mays", "common_name": "maize"},
    "maize": {"taxid": "4577", "scientific_name": "Zea mays", "common_name": "maize"},
    "corn": {"taxid": "4577", "scientific_name": "Zea mays", "common_name": "maize"},
    
    "3847": {"taxid": "3847", "scientific_name": "Glycine max", "common_name": "soybean"},
    "Glycine max": {"taxid": "3847", "scientific_name": "Glycine max", "common_name": "soybean"},
    "soybean": {"taxid": "3847", "scientific_name": "Glycine max", "common_name": "soybean"},
    
    # Bacteria
    "83333": {"taxid": "83333", "scientific_name": "Escherichia coli K-12", "common_name": "E. coli"},
    "Escherichia coli": {"taxid": "83333", "scientific_name": "Escherichia coli K-12", "common_name": "E. coli"},
    "E. coli": {"taxid": "83333", "scientific_name": "Escherichia coli K-12", "common_name": "E. coli"},
    "eco": {"taxid": "83333", "scientific_name": "Escherichia coli K-12", "common_name": "E. coli"},
    
    # Fungi
    "559292": {"taxid": "559292", "scientific_name": "Saccharomyces cerevisiae S288C", "common_name": "baker's yeast"},
    "Saccharomyces cerevisiae S288C": {"taxid": "559292", "scientific_name": "Saccharomyces cerevisiae S288C", "common_name": "baker's yeast"},
}


class OrganismNotFoundError(Exception):
    """Raised when an organism cannot be resolved."""
    pass


def resolve_organism(input_str: str) -> Dict[str, str]:
    """
    Resolve an organism identifier to standardized organism information.
    
    Args:
        input_str: Either NCBI TaxID (e.g., "9606") or scientific name (e.g., "Homo sapiens")
        
    Returns:
        Dictionary with taxid, scientific_name, and common_name
        
    Raises:
        OrganismNotFoundError: If the organism cannot be resolved
    """
    input_clean = input_str.strip()
    
    # First check cache
    cached_result = _get_cached_result(input_clean)
    if cached_result:
        logger.debug(f"Found cached result for {input_clean}")
        return cached_result
    
    # Check common organisms mapping first
    if input_clean in COMMON_ORGANISMS:
        result = COMMON_ORGANISMS[input_clean]
        _cache_result(input_clean, result)
        logger.debug(f"Resolved {input_clean} using common organisms mapping")
        return result
    
    # Try to determine if input is a taxid or scientific name
    is_numeric = input_clean.isdigit()
    
    try:
        # Use NCBI E-Utils via requests
        import requests
        
        if is_numeric:
            # Input is likely a TaxID, fetch organism info
            taxid = input_clean
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                "db": "taxonomy",
                "id": taxid,
                "retmode": "json"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "taxonomy" in data and len(data["taxonomy"]) > 0:
                tax_data = data["taxonomy"][0]
                
                result = {
                    "taxid": tax_data.get("TaxId", taxid),
                    "scientific_name": tax_data.get("ScientificName", ""),
                    "common_name": tax_data.get("OtherNames", {}).get("GenbankCommonName", "")
                }
                
                _cache_result(input_clean, result)
                logger.info(f"Resolved taxid {taxid} to {result['scientific_name']}")
                return result
        else:
            # Input is likely a scientific name, search for TaxID
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "taxonomy",
                "term": f"{input_clean}[Organism]",
                "retmode": "json"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "esearchresult" in data and "idlist" in data["esearchresult"]:
                id_list = data["esearchresult"]["idlist"]
                
                if id_list:
                    taxid = id_list[0]
                    
                    # Now fetch the detailed info
                    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                    params = {
                        "db": "taxonomy",
                        "id": taxid,
                        "retmode": "json"
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    detail_data = response.json()
                    
                    if "taxonomy" in detail_data and len(detail_data["taxonomy"]) > 0:
                        tax_data = detail_data["taxonomy"][0]
                        
                        result = {
                            "taxid": tax_data.get("TaxId", taxid),
                            "scientific_name": tax_data.get("ScientificName", input_clean),
                            "common_name": tax_data.get("OtherNames", {}).get("GenbankCommonName", "")
                        }
                        
                        # Cache with both the original input and the taxid
                        _cache_result(input_clean, result)
                        _cache_result(taxid, result)
                        
                        logger.info(f"Resolved {input_clean} to taxid {taxid}")
                        return result
    
    except Exception as e:
        logger.warning(f"NCBI lookup failed for {input_clean}: {str(e)}. Using fallback mapping.")
        # If NCBI fails, try the common organisms mapping again with variations
        for key, value in COMMON_ORGANISMS.items():
            if input_clean.lower() in key.lower() or key.lower() in input_clean.lower():
                result = value
                _cache_result(input_clean, result)
                logger.debug(f"Resolved {input_clean} using fuzzy match to {key}")
                return result
    
    # If we get here, the organism couldn't be resolved
    raise OrganismNotFoundError(f"Could not resolve organism: {input_clean}")


def _get_cached_result(input_str: str) -> Optional[Dict[str, str]]:
    """Retrieve cached organism resolution result."""
    cache_file = _get_cache_file_path()
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if input_str exists in cache
        if input_str in cache_data:
            return cache_data[input_str]
        
        # Also check if input_str is a taxid that matches any cached taxid
        if input_str.isdigit():
            for cached_key, cached_value in cache_data.items():
                if cached_value.get("taxid") == input_str:
                    return cached_value
    
    except Exception as e:
        logger.warning(f"Could not read cache file: {str(e)}")
    
    return None


def _cache_result(input_str: str, result: Dict[str, str]):
    """Cache organism resolution result."""
    cache_file = _get_cache_file_path()
    
    # Create cache directory if it doesn't exist
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing cache
    cache_data = {}
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load existing cache: {str(e)}")
    
    # Add new result
    cache_data[input_str] = result
    
    # Write back to cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write to cache file: {str(e)}")


def _get_cache_file_path() -> Path:
    """Get the path to the organism cache file."""
    cache_dir = Path.home() / ".openclaw" / "workspace" / "k-sites" / ".cache"
    return cache_dir / "organism_cache.json"


def search_organisms(query: str, limit: int = 20) -> list:
    """
    Search for organisms by name or taxid.
    
    Args:
        query: Search string (scientific name, common name, or taxid)
        limit: Maximum number of results to return
        
    Returns:
        List of organism dictionaries matching the query
    """
    query_lower = query.lower().strip()
    results = []
    
    # Search in common organisms
    seen_taxids = set()
    for key, org in COMMON_ORGANISMS.items():
        taxid = org['taxid']
        if taxid in seen_taxids:
            continue
            
        # Check if query matches any field
        if (query_lower in key.lower() or 
            query_lower in org['scientific_name'].lower() or
            query_lower in org.get('common_name', '').lower() or
            query_lower == taxid):
            
            results.append({
                'name': org['scientific_name'],
                'taxid': taxid,
                'common_name': org.get('common_name', '')
            })
            seen_taxids.add(taxid)
            
        if len(results) >= limit:
            break
    
    # If query is numeric, try exact taxid match via NCBI
    if query.isdigit() and len(results) == 0:
        try:
            result = resolve_organism(query)
            if result:
                results.append({
                    'name': result['scientific_name'],
                    'taxid': result['taxid'],
                    'common_name': result.get('common_name', '')
                })
        except OrganismNotFoundError:
            pass
    
    return results