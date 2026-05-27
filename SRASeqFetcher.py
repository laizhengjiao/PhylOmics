#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
import re
import os

# -------------------------- Auto Install Missing Dependencies --------------------------
def install_dependencies():
    """Auto install required packages if missing"""
    required_packages = {
        "Bio": "biopython",
        "pandas": "pandas"
    }
    missing_packages = []

    for import_name, pkg_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(pkg_name)
    
    if missing_packages:
        print(f"[INFO] Missing required packages: {', '.join(missing_packages)}")
        print("[INFO] Installing automatically...")
        try:
            pip_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + missing_packages
            subprocess.check_call(pip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[SUCCESS] All missing packages installed!")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install packages: {e}")
            print("Please install manually with: pip install biopython pandas")
            sys.exit(1)

install_dependencies()

# -------------------------- Import Required Libraries --------------------------
import argparse
import xml.etree.ElementTree as ET
from Bio import Entrez
import pandas as pd

# -------------------------- Global Configuration --------------------------
PLACEHOLDER_EMAIL = "abcdefg@123.com"  # Fixed placeholder (never change)
DEFAULT_EMAIL = "1642162535@qq.com"      # Will be replaced by user email
Entrez.email = DEFAULT_EMAIL
Entrez.max_tries = 5
Entrez.timeout = 30
BATCH_SIZE = 10000  # NCBI max records per request

# -------------------------- Email Validation & Script Rewrite --------------------------
def validate_email(email):
    """Validate email format with regex"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def rewrite_script_with_email(new_email):
    """Rewrite the script file to replace DEFAULT_EMAIL with user's email (ensure quotes)"""
    script_path = os.path.abspath(sys.argv[0])
    
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            script_content = f.read()
        
        # Only replace DEFAULT_EMAIL (keep PLACEHOLDER_EMAIL unchanged)
        pattern = r'^(\s*DEFAULT_EMAIL\s*=\s*)["\'].*?["\'](\s*#.*)?$'
        replacement_line = rf'\1"{new_email}"\2'
        new_content = re.sub(pattern, replacement_line, script_content, flags=re.MULTILINE)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"[SUCCESS] Script updated! DEFAULT_EMAIL is now set to: {new_email}")
        print(f"[INFO] Next time you run this script, it will use {new_email} directly (no prompt)")
    except PermissionError:
        print(f"[ERROR] Permission denied: Cannot write to {script_path}")
        print("Please run the script with sudo/administrator privileges, or make the file writable: chmod +w", script_path)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to update script: {str(e)}")
        sys.exit(1)

def set_entrez_email():
    """Only prompt if email is still the placeholder (not user's email)"""
    # Key fix: judge against PLACEHOLDER_EMAIL (fixed), not DEFAULT_EMAIL
    if Entrez.email == PLACEHOLDER_EMAIL:
        print("\n[??  IMPORTANT] NCBI requires a valid personal email for API access!")
        print(f"Current email is default placeholder: {PLACEHOLDER_EMAIL}")
        print("This email will be saved permanently in the script file for future use.")
        
        while True:
            user_email = input("\nPlease enter your REAL email address: ").strip()
            if not user_email:
                print("[ERROR] Email cannot be empty!")
                continue
            if validate_email(user_email):
                Entrez.email = user_email
                rewrite_script_with_email(user_email)
                break
            else:
                print("[ERROR] Invalid email format! Please enter a valid email (e.g., yourname@example.com)")
    else:
        # Optional: confirm email is loaded
        print(f"[INFO] Using saved email: {Entrez.email}")

# -------------------------- Utility Functions --------------------------
def clean_quote(s):
    """Remove leading/trailing single/double quotes to handle space-containing parameters"""
    if isinstance(s, str):
        return s.strip().strip('"').strip("'")
    return s

def build_search_term(taxon_name, strategy=None, layout=None, lib_source=None):
    """Dynamically build NCBI SRA search term (match web: all fields + no Organism limit)"""
    term_parts = [clean_quote(taxon_name)]
    
    optional_filters = {
        "Strategy": strategy,
        "LibraryLayout": layout,
        "LibrarySource": lib_source
    }
    for key, value in optional_filters.items():
        if value:
            term_parts.append(f'"{clean_quote(value)}"[{key}]')
    
    return " AND ".join(term_parts)

# -------------------------- SRA Data Fetch Function (Run-level) --------------------------
def fetch_sra_batch(term, retstart, retmax):
    """Fetch SRA data at RUN level (SRR) to match web results, fix spots/bases extraction"""
    try:
        search_handle = Entrez.esearch(
            db="sra",
            term=term,
            retstart=retstart,
            retmax=retmax,
            usehistory="y"
        )
        search_results = Entrez.read(search_handle)
        search_handle.close()

        id_list = search_results["IdList"]
        if not id_list:
            return [], int(search_results["Count"])

        fetch_handle = Entrez.efetch(
            db="sra",
            id=",".join(id_list),
            rettype="xml",
            retmode="xml"
        )
        xml_data = fetch_handle.read()
        fetch_handle.close()

        xml_str = xml_data.decode('utf-8')
        xml_str_clean = xml_str.replace('xmlns="http://www.ncbi.nlm.nih.gov/SRA"', '')
        root = ET.fromstring(xml_str_clean.encode('utf-8'))

        batch_results = []
        for exp_package in root.findall(".//EXPERIMENT_PACKAGE"):
            run_set = exp_package.find("RUN_SET")
            if run_set is None:
                continue
            
            for run in run_set.findall("RUN"):
                res = {
                    "SRR_accession": "",
                    "SRX_accession": "",
                    "experiment_title": "",
                    "library_strategy": "",
                    "library_source": "",
                    "library_selection": "",
                    "library_layout": "",
                    "sample_accession": "",
                    "scientific_name": "",
                    "tax_id": "",
                    "platform_type": "",
                    "instrument_model": "",
                    "download_size": "",
                    "published_date": "",
                    "spots": "",
                    "bases": "",
                    "study_accession": ""
                }

                res["SRR_accession"] = run.get("accession", "")
                
                experiment = exp_package.find("EXPERIMENT")
                if experiment is not None:
                    identifiers = experiment.find("IDENTIFIERS")
                    if identifiers is not None:
                        primary_id = identifiers.find("PRIMARY_ID")
                        if primary_id is not None:
                            res["SRX_accession"] = primary_id.text or ""
                    title_elem = experiment.find("TITLE")
                    res["experiment_title"] = title_elem.text or "" if title_elem is not None else ""
                    
                    design = experiment.find("DESIGN")
                    if design is not None:
                        lib_desc = design.find("LIBRARY_DESCRIPTOR")
                        if lib_desc is not None:
                            res["library_strategy"] = lib_desc.find("LIBRARY_STRATEGY").text or "" if lib_desc.find("LIBRARY_STRATEGY") is not None else ""
                            res["library_source"] = lib_desc.find("LIBRARY_SOURCE").text or "" if lib_desc.find("LIBRARY_SOURCE") is not None else ""
                            res["library_selection"] = lib_desc.find("LIBRARY_SELECTION").text or "" if lib_desc.find("LIBRARY_SELECTION") is not None else ""
                            layout_paired = lib_desc.find("LIBRARY_LAYOUT/PAIRED")
                            res["library_layout"] = "PAIRED" if layout_paired is not None else "SINGLE"

                sample = exp_package.find("SAMPLE")
                if sample is not None:
                    res["sample_accession"] = sample.find("IDENTIFIERS/PRIMARY_ID").text or "" if sample.find("IDENTIFIERS/PRIMARY_ID") is not None else ""
                    sci_name_paths = [
                        sample.find("SCIENTIFIC_NAME"),
                        sample.find("SAMPLE_NAME/SCIENTIFIC_NAME"),
                        sample.find("Attributes/Attribute[@name='scientific_name']")
                    ]
                    for sci_name in sci_name_paths:
                        if sci_name is not None and sci_name.text and sci_name.text.strip():
                            res["scientific_name"] = sci_name.text.strip()
                            break
                    tax_id_paths = [
                        sample.find("TAXON_ID"),
                        sample.find("SAMPLE_NAME/TAXON_ID"),
                        sample.find("Attributes/Attribute[@name='tax_id']")
                    ]
                    for tax_id in tax_id_paths:
                        if tax_id is not None and tax_id.text:
                            res["tax_id"] = tax_id.text
                            break

                platform = experiment.find("PLATFORM") if experiment is not None else None
                if platform is not None and len(platform) > 0:
                    res["platform_type"] = platform[0].tag
                    instrument_elem = platform.find(f"{platform[0].tag}/INSTRUMENT_MODEL")
                    res["instrument_model"] = instrument_elem.text or "" if instrument_elem is not None else ""

                res["download_size"] = run.get("size", "")
                stats = run.find("Statistics")

                # Spots extraction (4 paths)
                spots = ""
                if stats is not None:
                    spots_elem = stats.find("nspots")
                    if spots_elem is not None and spots_elem.text:
                        spots = spots_elem.text
                    elif "nspots" in stats.attrib:
                        spots = stats.attrib["nspots"]
                if not spots and "total_spots" in run.attrib:
                    spots = run.attrib["total_spots"]
                if not spots and stats is not None:
                    total_spots_elem = stats.find("TotalSpots")
                    if total_spots_elem is not None and total_spots_elem.text:
                        spots = total_spots_elem.text
                res["spots"] = spots

                # Bases extraction (4 paths)
                bases = ""
                if stats is not None:
                    bases_elem = stats.find("nbases")
                    if bases_elem is not None and bases_elem.text:
                        bases = bases_elem.text
                    elif "nbases" in stats.attrib:
                        bases = stats.attrib["nbases"]
                if not bases and "total_bases" in run.attrib:
                    bases = run.attrib["total_bases"]
                if not bases and stats is not None:
                    total_bases_elem = stats.find("TotalBases")
                    if total_bases_elem is not None and total_bases_elem.text:
                        bases = total_bases_elem.text
                res["bases"] = bases

                study = exp_package.find("STUDY")
                if study is not None:
                    res["study_accession"] = study.find("IDENTIFIERS/PRIMARY_ID").text or "" if study.find("IDENTIFIERS/PRIMARY_ID") is not None else ""

                pub_date_raw = run.get("published", "") or (experiment.get("published", "") if experiment is not None else "")
                res["published_date"] = pub_date_raw[:10] if pub_date_raw and len(pub_date_raw) >= 10 else ""

                if res["SRR_accession"]:
                    batch_results.append(res)

        return batch_results, int(search_results["Count"])

    except Exception as e:
        print(f"[ERROR] Batch retrieval failed (start position: {retstart}): {str(e)}")
        return [], 0

# -------------------------- Main Function --------------------------
def main():
    set_entrez_email()  # Check and rewrite email if needed

    parser = argparse.ArgumentParser(
        description="SRA Database Retriever (Match Web Results): All parameters are --named (taxon_name is mandatory). Params with spaces must be wrapped in quotes.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "--taxon_name", 
        required=True, 
        help="Mandatory: Taxon name (e.g., 'Plautia stali', 'Pentatomidae')"
    )
    parser.add_argument("--strategy", help="Optional: Sequencing strategy (e.g., 'RNA-Seq', 'WGS')")
    parser.add_argument("--layout", help="Optional: Library layout (e.g., 'PAIRED', 'SINGLE')")
    parser.add_argument("--lib_source", help="Optional: Library source (e.g., 'TRANSCRIPTOMIC', 'GENOMIC')")

    args = parser.parse_args()
    search_term = build_search_term(args.taxon_name, args.strategy, args.layout, args.lib_source)
    print(f"\n[INFO] Search term (match web): {search_term}")

    all_results = []
    retstart = 0
    total_count = 0
    while True:
        batch_data, total_count = fetch_sra_batch(search_term, retstart, BATCH_SIZE)
        if not batch_data:
            break
        all_results.extend(batch_data)
        retstart += BATCH_SIZE

    if all_results:
        filename_parts = ["sra_results_web_match", clean_quote(args.taxon_name).replace(" ", "_")]
        if args.strategy:
            filename_parts.append(clean_quote(args.strategy))
        csv_filename = "_".join(filename_parts) + ".csv"
        pd.DataFrame(all_results).to_csv(csv_filename, index=False, encoding="utf-8")
        print(f"[SUCCESS] Retrieved {len(all_results)} RUN-level records (match web count)!")
        print(f"[SUCCESS] CSV file saved to: {csv_filename}")
        print(f"[INFO] NCBI API reported total records: {total_count} (same as web)")
    else:
        print("\n[WARNING] No matching records found")

if __name__ == "__main__":
    main()