#!/usr/bin/env python3
import sys
import subprocess

def install_packages():
    required = ['os', 'sys', 'argparse', 'glob', 'subprocess', 'hashlib']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        for pkg in missing:
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', pkg],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                print(f"Successfully installed {pkg}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {pkg}: {e.stderr}", file=sys.stderr)
                sys.exit(1)
    else:
        print("All required packages are already installed")

install_packages()

import os
import argparse
import glob
import hashlib

def run_system_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def validate_gzip_file(file_path):
    if not os.path.isfile(file_path):
        return False, f"File {file_path} does not exist"
    
    cmd = f"gzip -t {file_path}"
    success, msg = run_system_command(cmd)
    if success:
        return True, "Gzip file is valid (no corruption)"
    else:
        return False, f"Gzip file corrupted: {msg}"

def get_fastq_stats(file_path):
    cmd_lines = f"zcat {file_path} | wc -l"
    success, lines_out = run_system_command(cmd_lines)
    line_count = int(lines_out.strip()) if success else 0
    
    cmd_head = f"zcat {file_path} | head -10"
    success, head_out = run_system_command(cmd_head)
    head = head_out if success else ""
    
    cmd_tail = f"zcat {file_path} | tail -10"
    success, tail_out = run_system_command(cmd_tail)
    tail = tail_out if success else ""
    
    return line_count, head, tail

def calculate_fastq_checksum(file_list):
    if not file_list:
        return 0, ""
    
    total_lines = 0
    first_head = ""
    last_tail = ""
    
    for idx, f in enumerate(file_list):
        if not os.path.isfile(f):
            continue
        
        lines, head, tail = get_fastq_stats(f)
        total_lines += lines
        
        if idx == 0 and head:
            first_head = head
        
        if tail:
            last_tail = tail
    
    checksum_data = f"{total_lines}|{first_head}|{last_tail}"
    checksum = hashlib.md5(checksum_data.encode()).hexdigest() if checksum_data else ""
    
    return total_lines, checksum

def validate_merge_integrity(input_files, merged_file):
    print(f"\n=== Validating {merged_file} ===")
    
    gzip_valid, gzip_msg = validate_gzip_file(merged_file)
    print(f"1. Gzip file check: {'PASS' if gzip_valid else 'FAIL'} - {gzip_msg}")
    if not gzip_valid:
        return False
    
    print("2. Calculating stats for original files...")
    orig_lines, orig_checksum = calculate_fastq_checksum(input_files)
    
    print("3. Calculating stats for merged file...")
    merged_lines, merged_checksum = calculate_fastq_checksum([merged_file])
    
    line_check = (orig_lines == merged_lines)
    print(f"4. Line count check: {'PASS' if line_check else 'FAIL'}")
    print(f"   - Original total lines: {orig_lines}")
    print(f"   - Merged total lines: {merged_lines}")
    
    fastq_format_check = (merged_lines % 4 == 0)
    print(f"5. Fastq format check (lines %4 ==0): {'PASS' if fastq_format_check else 'FAIL'}")
    
    checksum_check = (orig_checksum == merged_checksum)
    print(f"6. Content integrity check: {'PASS' if checksum_check else 'FAIL'}")
    print(f"   - Original checksum: {orig_checksum}")
    print(f"   - Merged checksum: {merged_checksum}")
    
    all_checks_passed = gzip_valid and line_check and fastq_format_check and checksum_check
    print(f"\n=== Validation Result: {'ALL PASSED' if all_checks_passed else 'FAILED'} ===")
    
    return all_checks_passed

def get_auto_suffix(output_dir, base_prefix, read_suffix):
    suffix = 0
    while True:
        if suffix == 0:
            file_prefix = base_prefix
        else:
            file_prefix = f"{base_prefix}({suffix})"
        target_file = os.path.join(output_dir, f"{file_prefix}_{read_suffix}.fq.gz")
        if not os.path.exists(target_file):
            return file_prefix
        suffix += 1

def merge_specific_files(input_files, output_dir, base_prefix, read_suffix, validate=True):
    if not input_files:
        print(f"Warning: No input files provided for merging", file=sys.stderr)
        return False

    valid_files = [f for f in input_files if os.path.isfile(f)]
    invalid_files = set(input_files) - set(valid_files)
    for f in invalid_files:
        print(f"Warning: File {f} does not exist, skipped", file=sys.stderr)
    
    if not valid_files:
        print(f"Error: No valid input files to merge", file=sys.stderr)
        return False

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    final_prefix = get_auto_suffix(output_dir, base_prefix, read_suffix)
    output_file = os.path.join(output_dir, f"{final_prefix}_{read_suffix}.fq.gz")

    print(f"\n=== Merging read{read_suffix} files ===")
    print(f"Total input files: {len(input_files)}")
    print(f"Valid files to merge: {len(valid_files)}")
    print(f"Merging the following files:")
    for idx, f in enumerate(valid_files, 1):
        print(f"  {idx}. {os.path.abspath(f)}")

    cmd = f"cat {' '.join(valid_files)} > {output_file}"
    print(f"\nRunning merge command: {cmd}")
    success, msg = run_system_command(cmd)
    
    if success:
        print(f"Merged {len(valid_files)} files into {output_file}")
        if validate:
            return validate_merge_integrity(valid_files, output_file)
        return True
    else:
        print(f"Merge failed: {msg}", file=sys.stderr)
        return False

def merge_dir_files(input_dir, output_dir, base_prefix, validate=True):
    pattern_1 = os.path.join(input_dir, "*_1.f*q.gz")
    pattern_2 = os.path.join(input_dir, "*_2.f*q.gz")
    
    files_1 = sorted(glob.glob(pattern_1))
    files_2 = sorted(glob.glob(pattern_2))

    if not files_1 and not files_2:
        print(f"Warning: No _1/_2 ending fastq.gz/fq.gz files found in {input_dir}", file=sys.stderr)
        return False

    merge_success = True
    if files_1:
        if not merge_specific_files(files_1, output_dir, base_prefix, "1", validate):
            merge_success = False
    else:
        print(f"Warning: No _1 ending fastq.gz/fq.gz files found in {input_dir}\n")

    if files_2:
        if not merge_specific_files(files_2, output_dir, base_prefix, "2", validate):
            merge_success = False
    else:
        print(f"Warning: No _2 ending fastq.gz/fq.gz files found in {input_dir}")

    return merge_success

def main():
    parser = argparse.ArgumentParser(
        description='Merge fastq.gz/fq.gz files with integrity validation and auto dependency install',
        epilog='For any questions during use, please contact Laizheng Jiao (jlz0602@163.com)'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--directory', help='Directory path to process all _1/_2 ending fastq.gz/fq.gz files')
    group.add_argument('-1', '--read1', nargs='+', help='List of read1 files to merge')
    parser.add_argument('-2', '--read2', nargs='+', help='List of read2 files to merge')
    parser.add_argument('-o', '--output-dir', required=True, help='Directory for merged output files')
    parser.add_argument('-p', '--prefix', default='merge', help='Prefix for merged files (default: merge)')
    parser.add_argument('--no-validate', action='store_false', dest='validate', 
                        help='Skip integrity validation (faster, no check)')

    args = parser.parse_args()
    output_dir = os.path.abspath(args.output_dir)
    base_prefix = args.prefix

    if args.directory:
        input_dir = os.path.abspath(args.directory)
        if not os.path.isdir(input_dir):
            print(f"Error: Directory {input_dir} does not exist", file=sys.stderr)
            sys.exit(1)
        print(f"=== Scanning directory {input_dir} for fastq.gz files ===")
        success = merge_dir_files(input_dir, output_dir, base_prefix, args.validate)
    else:
        success = True
        if args.read1:
            if not merge_specific_files(args.read1, output_dir, base_prefix, "1", args.validate):
                success = False
        
        if args.read2:
            if not merge_specific_files(args.read2, output_dir, base_prefix, "2", args.validate):
                success = False
        
        if not args.read1 and not args.read2:
            print(f"Error: At least one of -1/--read1 or -2/--read2 must be provided", file=sys.stderr)
            sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()