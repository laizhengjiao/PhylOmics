#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
import warnings
import urllib3
import os
import argparse
import re

# -------------------------- Dependency Check & Auto-Install --------------------------
def install_package(package):
    """Install a package via pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])

# Check and install required packages
required_packages = {
    "requests": "requests",
    "bs4": "beautifulsoup4"
}

for module, package in required_packages.items():
    try:
        __import__(module)
    except ImportError:
        print(f"[Installing missing dependency: {package}]")
        try:
            install_package(package)
            __import__(module)
            print(f"[Successfully installed: {package}]")
        except subprocess.CalledProcessError:
            print(f"[ERROR] Failed to install {package}. Please install it manually with:")
            print(f"        pip install {package}")
            sys.exit(1)

# Import modules after ensuring installation
import requests
from bs4 import BeautifulSoup

# -------------------------- Core Configuration --------------------------
warnings.filterwarnings("ignore", category=UserWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

# Define sequencing file suffix patterns (supports _1/_2, fastq/fq, gz compressed)
SEQ_SUFFIX_PATTERN = re.compile(
    r'(_[12])'          # Match _1 or _2 (read end)
    r'(\.fastq|\.fq)'   # Match .fastq or .fq
    r'(\.gz)?$'         # Optional .gz suffix
)

# SRA accession validation pattern
SRA_PATTERN = re.compile(r'^(SRR|DRR|ERR)\d+$')

# -------------------------- Core Functions --------------------------
def extract_organism(sra_id):
    sra_url = f"https://www.ncbi.nlm.nih.gov/sra/{sra_id}[accn]"
    try:
        response = requests.get(
            url=sra_url,
            headers=HEADERS,
            timeout=60,
            allow_redirects=True,
            verify=False
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        organism = ""
        
        organism_dt = soup.find("dt", string=lambda t: t and t.strip() == "Organism")
        if organism_dt:
            organism_dd = organism_dt.find_next_sibling("dd")
            if organism_dd:
                dd_text = organism_dd.text.strip()
                org_match = re.search(r'[A-Z][a-z]+ [a-z]+', dd_text)
                if org_match:
                    organism = org_match.group()
        
        if not organism:
            page_text = soup.get_text()
            if "Organism:" in page_text:
                org_part = page_text.split("Organism:")[1].split("\n")[0].strip()
                org_match = re.search(r'[A-Z][a-z]+ [a-z]+', org_part)
                if org_match:
                    organism = org_match.group()
        
        return organism if organism else None
    except requests.exceptions.Timeout:
        print(f"[Timeout] {sra_id} - Request timed out", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError:
        print(f"[Connection Error] {sra_id} - Network connection failed", file=sys.stderr)
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[HTTP Error] {sra_id} - HTTP {e.response.status_code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Unknown Error] {sra_id} - {str(e)[:30]}", file=sys.stderr)
        return None

def read_sra_file(file_path):
    """
    Read and clean SRA accessions from file:
    - Remove leading/trailing whitespace (including spaces, tabs)
    - Remove empty lines
    - Remove Windows/DOS newlines (\r\n) and convert to Linux newlines (\n)
    - Filter only valid SRA accessions (SRR/DRR/ERR + numbers)
    """
    sra_list = []
    try:
        with open(file_path, "r", encoding="utf-8", newline='') as f:
            # Read all lines and clean format
            for line_num, line in enumerate(f, 1):
                # Step 1: Remove all leading/trailing whitespace (spaces, tabs, newlines)
                cleaned_line = line.strip()
                
                # Step 2: Skip empty lines (after cleaning)
                if not cleaned_line:
                    print(f"[Info] Line {line_num} - Empty line, skipped", file=sys.stderr)
                    continue
                
                # Step 3: Check if cleaned line is a valid SRA accession
                if SRA_PATTERN.match(cleaned_line):
                    sra_list.append(cleaned_line)
                else:
                    print(f"[Warning] Line {line_num} - Invalid SRA accession: '{cleaned_line}' (skipped)", file=sys.stderr)
        
        # Step 4: Deduplicate (preserve order)
        sra_list = list(dict.fromkeys(sra_list))
        print(f"[Info] Successfully parsed {len(sra_list)} valid SRA accessions from {file_path}", file=sys.stderr)
        return sra_list
    
    except FileNotFoundError:
        print(f"[ERROR] File {file_path} does not exist", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"[ERROR] File {file_path} has invalid encoding (only UTF-8 is supported)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read file {file_path}: {str(e)[:50]}", file=sys.stderr)
        sys.exit(1)

def get_unique_name(base_path, name):
    """Generate unique name to avoid overwriting"""
    counter = 1
    new_path = os.path.join(base_path, name)
    while os.path.exists(new_path):
        new_path = os.path.join(base_path, f"{name}_{counter}")
        counter += 1
    return new_path

def process_directory(parent_dir):
    if not os.path.isdir(parent_dir):
        print(f"[ERROR] Directory {parent_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Traverse all items (files/folders) in parent directory
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        
        # -------------------------- Process Folders --------------------------
        if os.path.isdir(item_path):
            # Match pure SRA-named folders (e.g., SRR123456)
            sra_match = SRA_PATTERN.match(item)
            if not sra_match:
                print(f"[Skip Folder] {item} - Not a valid SRA accession folder", file=sys.stderr)
                continue
            
            sra_id = item
            print(f"[Processing Folder] {sra_id} - Querying organism name...")
            
            organism = extract_organism(sra_id)
            if not organism:
                print(f"[Skip Rename] {sra_id} - Failed to get organism name", file=sys.stderr)
                continue
            
            # Generate new folder name (replace space with underscore)
            new_folder_name = organism.replace(" ", "_")
            new_folder_path = get_unique_name(parent_dir, new_folder_name)
            
            # Rename folder
            try:
                os.rename(item_path, new_folder_path)
                print(f"[Success] Folder {sra_id} -> {os.path.basename(new_folder_path)}")
            except PermissionError:
                print(f"[Permission Error] {sra_id} - No permission to rename folder", file=sys.stderr)
            except Exception as e:
                print(f"[Rename Error] {sra_id} - {str(e)[:30]}", file=sys.stderr)
            continue
        
        # -------------------------- Skip non-files --------------------------
        if not os.path.isfile(item_path):
            continue
        
        # -------------------------- Process Sequencing Files (Original Feature) --------------------------
        seq_match = SEQ_SUFFIX_PATTERN.search(item)
        if seq_match:
            # Extract SRA prefix (everything before _1/_2 suffix)
            sra_prefix = SEQ_SUFFIX_PATTERN.sub("", item)
            # Validate SRA prefix
            sra_match = SRA_PATTERN.match(sra_prefix)
            if sra_match:
                sra_id = sra_prefix
                read_end = seq_match.group(1)  # Get _1 or _2
                file_suffix = seq_match.group(2) + (seq_match.group(3) if seq_match.group(3) else "")  # .fastq/.fq(.gz)
                print(f"[Processing Seq File] {item} (SRA: {sra_id}, Read: {read_end}) - Querying organism name...")
                
                # Get organism name
                organism = extract_organism(sra_id)
                if not organism:
                    print(f"[Skip Rename] {item} - Failed to get organism name", file=sys.stderr)
                    continue
                
                # Generate new file name (e.g., Homo_sapiens_1.fastq.gz)
                new_file_name = f"{organism.replace(' ', '_')}{read_end}{file_suffix}"
                new_file_path = get_unique_name(parent_dir, new_file_name)
                
                # Rename file
                try:
                    os.rename(item_path, new_file_path)
                    print(f"[Success] Seq File {item} -> {os.path.basename(new_file_path)}")
                except PermissionError:
                    print(f"[Permission Error] {item} - No permission to rename file", file=sys.stderr)
                except Exception as e:
                    print(f"[Rename Error] {item} - {str(e)[:30]}", file=sys.stderr)
            else:
                print(f"[Skip Seq File] {item} - Prefix {sra_prefix} is not a valid SRA accession", file=sys.stderr)
            continue
        
        # -------------------------- Process General Files (New Feature) --------------------------
        # Split filename into prefix and extension (supports multiple dots, e.g., SRR123456.tar.gz)
        file_name_parts = os.path.splitext(item)
        sra_prefix = file_name_parts[0]  # Part before the last dot
        file_ext = file_name_parts[1]    # Full extension (e.g., .txt, .tar.gz)
        
        # If multiple dots (e.g., SRR123456.tar.gz), recheck prefix (only if first part is SRA)
        if "." in sra_prefix:
            temp_prefix = sra_prefix.split(".")[0]
            if SRA_PATTERN.match(temp_prefix):
                sra_prefix = temp_prefix
                file_ext = item[len(sra_prefix):]  # Full extension including all dots
        
        # Validate SRA prefix
        sra_match = SRA_PATTERN.match(sra_prefix)
        if not sra_match:
            print(f"[Skip General File] {item} - Prefix {sra_prefix} is not a valid SRA accession", file=sys.stderr)
            continue
        
        sra_id = sra_prefix
        print(f"[Processing General File] {item} (SRA: {sra_id}) - Querying organism name...")
        
        # Get organism name
        organism = extract_organism(sra_id)
        if not organism:
            print(f"[Skip Rename] {item} - Failed to get organism name", file=sys.stderr)
            continue
        
        # Generate new file name (e.g., Homo_sapiens.txt, Homo_sapiens.tar.gz)
        new_file_name = f"{organism.replace(' ', '_')}{file_ext}"
        new_file_path = get_unique_name(parent_dir, new_file_name)
        
        # Rename file
        try:
            os.rename(item_path, new_file_path)
            print(f"[Success] General File {item} -> {os.path.basename(new_file_path)}")
        except PermissionError:
            print(f"[Permission Error] {item} - No permission to rename file", file=sys.stderr)
        except Exception as e:
            print(f"[Rename Error] {item} - {str(e)[:30]}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Extract species names for SRA accessions from NCBI SRA database",
        formatter_class=argparse.RawTextHelpFormatter,
        usage="""%(prog)s [options]
Usage modes:
  1. Single/multiple SRA accessions: %(prog)s -S SRR32815856 SRR35420852 DRR814136
  2. Batch query from file: %(prog)s -F srr.txt
  3. Directory mode (rename SRA-named folders/sequencing/general files): %(prog)s -D /path/to/parent_dir"""
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-S", "--sra", nargs="+", help="Single or multiple SRA accessions (SRR/DRR/ERR)")
    group.add_argument("-F", "--file", help="File with SRA accessions (one per line, auto-cleaned)")
    group.add_argument("-D", "--directory", help="Parent directory with SRA-named folders/sequencing/general files")
    
    args = parser.parse_args()
    
    if args.sra:
        sra_list = []
        for sra_id in args.sra:
            cleaned_sra = sra_id.strip()
            if SRA_PATTERN.match(cleaned_sra):
                sra_list.append(cleaned_sra)
            else:
                print(f"[Warning] Skipping invalid accession: {sra_id}", file=sys.stderr)
        
        if not sra_list:
            print("[ERROR] No valid SRA accessions found", file=sys.stderr)
            sys.exit(1)
        
        # Deduplicate
        sra_list = list(dict.fromkeys(sra_list))
        for sra_id in sra_list:
            organism = extract_organism(sra_id) or "Organism field not found"
            print(f"{sra_id}\t{organism}")
    
    elif args.file:
        # Read and clean SRA list from file
        sra_list = read_sra_file(args.file)
        
        if not sra_list:
            print("[ERROR] No valid SRA accessions found in file", file=sys.stderr)
            sys.exit(1)
        
        # Query and output (Linux-compatible format: tab-separated, \n newlines)
        for sra_id in sra_list:
            organism = extract_organism(sra_id) or "Organism field not found"
            # Ensure output uses Linux newlines (\n) instead of Windows (\r\n)
            print(f"{sra_id}\t{organism}", end='\n')
    
    elif args.directory:
        process_directory(args.directory)

if __name__ == "__main__":
    main()