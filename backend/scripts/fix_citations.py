"""Fix floating citation numbers [1], [2] etc. in advanced content."""
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase


def strip_citations(text: str) -> str:
    """Remove [N] citation markers outside code blocks."""
    lines = text.split('\n')
    result = []
    in_code = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code = not in_code
            result.append(line)
            continue
        if in_code:
            result.append(line)
            continue
        # Keep reference headers like ### [1] Title
        if re.match(r'^#{1,4}\s+\[\d+\]', line):
            result.append(line)
            continue
        # Remove (\[N]) or ([N])
        c = re.sub(r'\s*\(\\?\[\d{1,2}\]\)', '', line)
        # Remove standalone \[N]
        c = re.sub(r'\s*\\\[\d{1,2}\]', '', c)
        # Remove standalone [N] not followed by ( (not a markdown link)
        c = re.sub(r'\s*\[(\d{1,2})\](?!\()', '', c)
        # Remove (see [N]), (per [N])
        c = re.sub(r'\s*\((?:see |per )\[?\d{1,2}\]?\)', '', c)
        result.append(c)
    return '\n'.join(result)


def main():
    sb = get_supabase()
    r = sb.table('handbook_terms').select(
        'id,term,body_advanced_ko,body_advanced_en'
    ).neq('status', 'archived').execute()

    fixed = 0
    total_chars = 0
    for d in r.data:
        updates = {}
        for field in ('body_advanced_ko', 'body_advanced_en'):
            text = d.get(field, '') or ''
            if not text:
                continue
            cleaned = strip_citations(text)
            if cleaned != text:
                updates[field] = cleaned
                total_chars += len(text) - len(cleaned)
        if updates:
            sb.table('handbook_terms').update(updates).eq('id', d['id']).execute()
            fixed += 1
            print(f"  Fixed: {d['term']}")

    print(f"\nTotal: {fixed} terms fixed, ~{total_chars} chars removed")


if __name__ == '__main__':
    main()
