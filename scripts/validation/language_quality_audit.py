#!/usr/bin/env python3
"""
Language Quality Audit: Redundancy, Repetition, Concision, Precision

Checks for:
1. Redundant phrases and filler words
2. Repetitive sections across documents
3. Unnecessary verbiage
4. Opportunities for concision
5. Precision issues
"""

import re
from pathlib import Path
from collections import defaultdict

findings_dir = Path(__file__).parent.parent.parent / 'findings'

# Common redundant phrases
REDUNDANT_PHRASES = [
    r'\bwhat this means\b',
    r'\bthis means\b',
    r'\bin other words\b',
    r'\bput simply\b',
    r'\bsimply put\b',
    r'\bin summary\b',
    r'\bto summarize\b',
    r'\bit is important to note\b',
    r'\bit should be noted\b',
    r'\bit is worth noting\b',
    r'\bit is worth mentioning\b',
    r'\bas mentioned\b',
    r'\bas stated\b',
    r'\bas previously mentioned\b',
    r'\bas noted above\b',
    r'\bas discussed\b',
    r'\bneedless to say\b',
    r'\bobviously\b',
    r'\bclearly\b',
    r'\bof course\b',
]

# Filler words (context-dependent)
FILLER_WORDS = [
    r'\bvery\b',
    r'\breally\b',
    r'\bquite\b',
    r'\brather\b',
    r'\bextremely\b',
    r'\bincredibly\b',
    r'\bhighly\b',
    r'\bpretty\b',
    r'\bsomewhat\b',
]

# Repetitive patterns
REPETITIVE_PATTERNS = [
    r'\.\.\.',
    r'\b(?:the|a|an)\s+(?:the|a|an)\s+',
    r'\b(?:is|are|was|were)\s+(?:is|are|was|were)\s+',
]

def find_redundant_phrases(content: str, filename: str) -> list:
    """Find redundant phrases in content."""
    issues = []
    
    for pattern in REDUNDANT_PHRASES:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Get context (20 chars before and after)
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            context = content[start:end].replace('\n', ' ')
            issues.append({
                'type': 'redundant_phrase',
                'pattern': pattern,
                'context': context.strip(),
                'file': filename
            })
    
    return issues

def find_filler_words(content: str, filename: str) -> list:
    """Find filler words (context-dependent, may be acceptable)."""
    issues = []
    
    for pattern in FILLER_WORDS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Get context
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context = content[start:end].replace('\n', ' ')
            issues.append({
                'type': 'filler_word',
                'word': match.group(),
                'context': context.strip(),
                'file': filename
            })
    
    return issues

def find_repetitive_sections(files: list) -> dict:
    """Find sections that appear in multiple files."""
    section_patterns = defaultdict(list)
    
    # Common section headers
    section_headers = [
        r'##\s+(?:Executive\s+)?Summary',
        r'##\s+Key\s+Findings',
        r'##\s+Methodology',
        r'##\s+Conclusion',
        r'##\s+Overview',
    ]
    
    for filepath in files:
        if 'archive' in str(filepath) or 'validation' in str(filepath).lower():
            continue
        
        try:
            with open(filepath) as f:
                content = f.read()
            
            # Extract sections
            for header_pattern in section_headers:
                matches = re.finditer(header_pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get section content (next 500 chars or until next ##)
                    section_start = match.end()
                    section_end = content.find('\n##', section_start)
                    if section_end == -1:
                        section_end = min(len(content), section_start + 500)
                    section_content = content[section_start:section_end].strip()[:200]  # First 200 chars
                    
                    if len(section_content) > 50:  # Only track substantial sections
                        section_patterns[section_content[:100]].append((filepath.name, match.group()))
        except:
            pass
    
    # Find duplicates
    repetitive = {k: v for k, v in section_patterns.items() if len(v) > 1}
    return repetitive

def check_concision(content: str, filename: str) -> list:
    """Check for opportunities for concision."""
    issues = []
    
    # Long sentences (over 100 words)
    sentences = re.split(r'[.!?]\s+', content)
    for i, sentence in enumerate(sentences):
        words = len(sentence.split())
        if words > 100:
            issues.append({
                'type': 'long_sentence',
                'words': words,
                'sentence': sentence[:150] + '...',
                'file': filename
            })
    
    # Repeated words in close proximity
    words = content.lower().split()
    for i in range(len(words) - 1):
        if words[i] == words[i+1] and len(words[i]) > 3:
            # Check if it's not intentional (like "Bitcoin Bitcoin" would be wrong)
            if i > 0 and words[i-1] != words[i]:
                issues.append({
                    'type': 'repeated_word',
                    'word': words[i],
                    'file': filename
                })
    
    return issues

def check_precision(content: str, filename: str) -> list:
    """Check for precision issues."""
    issues = []
    
    # Vague quantifiers
    vague_patterns = [
        (r'\bmany\b', 'Consider using specific number'),
        (r'\bfew\b', 'Consider using specific number'),
        (r'\bseveral\b', 'Consider using specific number'),
        (r'\bsome\b', 'Consider using specific number or percentage'),
        (r'\ba lot\b', 'Consider using specific number'),
        (r'\ba few\b', 'Consider using specific number'),
    ]
    
    for pattern, suggestion in vague_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Get context
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context = content[start:end].replace('\n', ' ')
            issues.append({
                'type': 'vague_quantifier',
                'word': match.group(),
                'suggestion': suggestion,
                'context': context.strip(),
                'file': filename
            })
    
    return issues

def main():
    """Main audit function."""
    print("="*80)
    print("LANGUAGE QUALITY AUDIT: Redundancy, Repetition, Concision, Precision")
    print("="*80)
    print()
    
    all_issues = []
    all_warnings = []
    
    # Get all markdown files
    md_files = list(findings_dir.glob('*.md'))
    md_files = [f for f in md_files if 'archive' not in str(f) and 'validation' not in str(f).lower()]
    
    print(f"Analyzing {len(md_files)} files...")
    print()
    
    # 1. Redundant phrases
    print("1. REDUNDANT PHRASES")
    print("-"*80)
    redundant_count = 0
    for filepath in md_files:
        with open(filepath) as f:
            content = f.read()
        issues = find_redundant_phrases(content, filepath.name)
        all_issues.extend(issues)
        redundant_count += len(issues)
    
    if redundant_count > 0:
        print(f"   ⚠️  Found {redundant_count} redundant phrases")
        # Show first 5
        for issue in all_issues[:5]:
            if issue['type'] == 'redundant_phrase':
                print(f"      - {issue['file']}: {issue['context'][:60]}...")
    else:
        print("   ✅ No redundant phrases found")
    print()
    
    # 2. Filler words (warnings only)
    print("2. FILLER WORDS (Context-Dependent)")
    print("-"*80)
    filler_count = 0
    for filepath in md_files:
        with open(filepath) as f:
            content = f.read()
        issues = find_filler_words(content, filepath.name)
        all_warnings.extend(issues)
        filler_count += len(issues)
    
    if filler_count > 0:
        print(f"   ⚠️  Found {filler_count} filler words (review context)")
    else:
        print("   ✅ No filler words found")
    print()
    
    # 3. Repetitive sections
    print("3. REPETITIVE SECTIONS")
    print("-"*80)
    repetitive = find_repetitive_sections(md_files)
    if repetitive:
        print(f"   ⚠️  Found {len(repetitive)} potentially repetitive sections")
        for section_start, files in list(repetitive.items())[:3]:
            print(f"      Section appears in {len(files)} files:")
            for filename, header in files[:3]:
                print(f"         - {filename}: {header}")
    else:
        print("   ✅ No obvious repetitive sections")
    print()
    
    # 4. Concision opportunities
    print("4. CONCISION OPPORTUNITIES")
    print("-"*80)
    concision_count = 0
    for filepath in md_files:
        with open(filepath) as f:
            content = f.read()
        issues = check_concision(content, filepath.name)
        all_issues.extend(issues)
        concision_count += len(issues)
    
    if concision_count > 0:
        print(f"   ⚠️  Found {concision_count} concision opportunities")
        for issue in all_issues[:5]:
            if issue['type'] in ['long_sentence', 'repeated_word']:
                if issue['type'] == 'long_sentence':
                    print(f"      - {issue['file']}: {issue['words']}-word sentence")
                else:
                    print(f"      - {issue['file']}: Repeated word '{issue['word']}'")
    else:
        print("   ✅ No major concision issues")
    print()
    
    # 5. Precision issues
    print("5. PRECISION ISSUES")
    print("-"*80)
    precision_count = 0
    for filepath in md_files:
        with open(filepath) as f:
            content = f.read()
        issues = check_precision(content, filepath.name)
        all_warnings.extend(issues)
        precision_count += len(issues)
    
    if precision_count > 0:
        print(f"   ⚠️  Found {precision_count} vague quantifiers (review context)")
    else:
        print("   ✅ No precision issues found")
    print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Redundant phrases: {redundant_count}")
    print(f"Filler words: {filler_count} (context-dependent)")
    print(f"Repetitive sections: {len(repetitive)}")
    print(f"Concision opportunities: {concision_count}")
    print(f"Precision issues: {precision_count}")
    print()
    
    if redundant_count == 0 and concision_count == 0:
        print("✅ No major language quality issues found")
    else:
        print("⚠️  Review recommended for identified issues")
    
    # Save detailed report
    report_file = findings_dir / 'LANGUAGE_QUALITY_AUDIT_REPORT.md'
    with open(report_file, 'w') as f:
        f.write("# Language Quality Audit Report\n\n")
        f.write(f"**Generated**: {Path(__file__).stat().st_mtime}\n\n")
        f.write("---\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Redundant phrases**: {redundant_count}\n")
        f.write(f"- **Filler words**: {filler_count} (context-dependent)\n")
        f.write(f"- **Repetitive sections**: {len(repetitive)}\n")
        f.write(f"- **Concision opportunities**: {concision_count}\n")
        f.write(f"- **Precision issues**: {precision_count}\n\n")
        
        if redundant_count > 0:
            f.write("## Redundant Phrases\n\n")
            redundant_issues = [i for i in all_issues if i['type'] == 'redundant_phrase']
            for issue in redundant_issues[:20]:
                f.write(f"- **{issue['file']}**: `{issue['pattern']}` - {issue['context'][:80]}...\n")
            f.write("\n")
        
        if concision_count > 0:
            f.write("## Concision Opportunities\n\n")
            concision_issues = [i for i in all_issues if i['type'] in ['long_sentence', 'repeated_word']]
            for issue in concision_issues[:20]:
                if issue['type'] == 'long_sentence':
                    f.write(f"- **{issue['file']}**: {issue['words']}-word sentence\n")
                else:
                    f.write(f"- **{issue['file']}**: Repeated word '{issue['word']}'\n")
            f.write("\n")
    
    print(f"\nDetailed report saved to {report_file}")

if __name__ == '__main__':
    main()





