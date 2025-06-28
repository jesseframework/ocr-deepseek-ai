import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dateutil.parser import parse as parse_date
from dataclasses import dataclass, field
import hashlib
import sqlite3
from datetime import datetime

@dataclass
class InvoiceTemplate:
    template_id: str
    vendor_name: str
    structure_hash: str
    field_positions: Dict[str, Tuple[int, int]]  # field_name: (line_idx, value_offset)
    item_pattern: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 1

class AdaptiveInvoiceParser:
    def __init__(self, db_path: str = "invoice_templates.db"):
        self.db_path = db_path
        self._init_db()
        self.current_template = None

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    template_id TEXT PRIMARY KEY,
                    vendor_name TEXT,
                    structure_hash TEXT,
                    field_positions TEXT,
                    item_pattern TEXT,
                    created_at TEXT,
                    last_used TEXT,
                    usage_count INTEGER
                )
            """)

    def _calculate_structure_hash(self, lines: List[str]) -> str:
        """Create a fingerprint of the invoice structure"""
        structure_features = []
        for line in lines:
            # Extract structural features (not content)
            has_numbers = '1' if re.search(r'\d', line) else '0'
            has_currency = '1' if re.search(r'[\$\£\€]', line) else '0'
            has_date = '1' if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line) else '0'
            line_features = f"{len(line)}|{has_numbers}|{has_currency}|{has_date}"
            structure_features.append(line_features)
        return hashlib.md5('|'.join(structure_features).encode()).hexdigest()

    def _find_matching_template(self, structure_hash: str, vendor_name: str) -> Optional[InvoiceTemplate]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM templates WHERE structure_hash = ? OR vendor_name = ? ORDER BY usage_count DESC LIMIT 1",
                (structure_hash, vendor_name)  # ✅ supply the 2 values here
            )
            row = cursor.fetchone()
            if row:
                return InvoiceTemplate(
                    template_id=row[0],
                    vendor_name=row[1],
                    structure_hash=row[2],
                    field_positions=json.loads(row[3]),
                    item_pattern=json.loads(row[4]),
                    created_at=row[5],
                    last_used=row[6],
                    usage_count=row[7]
                )
        return None


    def _save_template(self, template: InvoiceTemplate):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO templates (
                    template_id,
                    vendor_name,
                    structure_hash,
                    field_positions,
                    item_pattern,
                    created_at,
                    last_used,
                    usage_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template.template_id,
                    template.vendor_name,
                    template.structure_hash,
                    json.dumps(template.field_positions),
                    json.dumps(template.item_pattern),
                    template.created_at,
                    template.last_used,
                    template.usage_count
                )
            )


    def _learn_structure(self, lines: List[str], vendor_name: str) -> InvoiceTemplate:
        """Analyze the invoice structure and create a template"""
        structure_hash = self._calculate_structure_hash(lines)
        field_positions = {}
        
        # Common field patterns to look for
        field_patterns = {
            'invoice_number': r'invoice\s*(?:no|number|#)\s*[:]?\s*([A-Z0-9-]+)',
            'issue_date': r'(?:date|invoice\s*date|date\s*of\s*issue)\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'due_date': r'due\s*date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'amount_due': r'(?:total|amount\s*due|balance\s*due)\s*[:]?\s*([\$\£\€]\s*\d{1,3}(?:,\d{3})*\.\d{2})'
        }
        
        # Find positions of important fields
        for line_idx, line in enumerate(lines):
            for field_name, pattern in field_patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match and field_name not in field_positions:
                    field_positions[field_name] = (line_idx, match.start(1))
        
        # Learn item pattern
        item_pattern = self._learn_item_pattern(lines)
        
        template = InvoiceTemplate(
            template_id=hashlib.md5(f"{vendor_name}_{structure_hash}".encode()).hexdigest(),
            vendor_name=vendor_name,
            structure_hash=structure_hash,
            field_positions=field_positions,
            item_pattern=item_pattern
        )
        
        self._save_template(template)
        return template

    def _learn_item_pattern(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze the invoice to learn how items are structured"""
        item_blocks = []
        current_block = []
        
        # Group lines into potential item blocks
        for line in lines:
            if re.search(r'(?:description|item|service|qty|quantity|rate|amount)', line, re.IGNORECASE):
                if current_block:
                    item_blocks.append(current_block)
                    current_block = []
            elif re.search(r'\$\d+\.?\d*', line):
                current_block.append(line)
        
        if current_block:
            item_blocks.append(current_block)
        
        # Analyze common patterns in item blocks
        pattern = {
            'has_header': False,
            'columns': []
        }
        
        if item_blocks:
            # Simple pattern detection - can be enhanced
            first_item = item_blocks[0]
            if len(first_item) >= 3 and re.search(r'\d+', first_item[-1]):
                pattern['columns'] = ['description', 'rate', 'quantity', 'amount']
            elif len(first_item) >= 2:
                pattern['columns'] = ['description', 'amount']
        
        return pattern

    def _extract_using_template(self, lines: List[str], template: InvoiceTemplate) -> Dict[str, Any]:
        """Extract data from invoice using a learned template"""
        result = {}
        
        # Extract fields using known positions
        for field_name, (line_idx, value_pos) in template.field_positions.items():
            if line_idx < len(lines):
                line = lines[line_idx]
                if field_name == 'invoice_number':
                    result[field_name] = self._extract_invoice_number(line[value_pos:])
                elif field_name in ['issue_date', 'due_date']:
                    result[field_name] = self._extract_date(line[value_pos:])
                elif field_name == 'amount_due':
                    result[field_name] = self._extract_currency(line[value_pos:])
        
        # Extract items using learned pattern
        result['items'] = self._extract_items_using_pattern(lines, template.item_pattern)
        
        # Update template usage
        template.last_used = datetime.now().isoformat()
        template.usage_count += 1
        self._save_template(template)
        
        return result

    def parse(self, ocr_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        
        # Step 1: Extract vendor name (always needed for learning)
        vendor_name = self._extract_vendor_name(lines)
        
        # Step 2: Calculate structure hash and look for matching template
        structure_hash = self._calculate_structure_hash(lines)
        template = self._find_matching_template(structure_hash, vendor_name)
        
        if template:
            # Use existing template
            self.current_template = template
            result = self._extract_using_template(lines, template)
        else:
            # Learn new template
            template = self._learn_structure(lines, vendor_name)
            self.current_template = template
            result = self._extract_using_template(lines, template)
        
        # Add common fields
        result.update({
            'vendor': {
                'name': vendor_name,
                'address': self._extract_vendor_address(lines),
                'phone': self._extract_vendor_phone(lines),
                'email': None
            },
            'currency': self._find_currency(lines),
            '_template_id': template.template_id if template else None
        })
        
        return result

    # Helper extraction methods (similar to previous implementation but refined)
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        match = re.search(r'([A-Z]{2,}\d{3,}|\d{5,})', text)
        return match.group(1) if match else None

    def _extract_date(self, text: str) -> Optional[str]:
        match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        if match:
            try:
                return parse_date(match.group(1)).strftime('%Y-%m-%d')
            except:
                return None
        return None

    def _extract_currency(self, text: str) -> Optional[float]:
        match = re.search(r'[\$\£\€]?\s*([\d,]+\.\d{2})', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                return None
        return None

    def _extract_vendor_name(self, lines: List[str]) -> Optional[str]:
        for line in lines[:5]:
            if re.search(r'(limited|llc|inc|corp|company)\b', line, re.IGNORECASE):
                return line.strip()
        return None

    def _extract_vendor_address(self, lines: List[str]) -> Optional[str]:
        address_lines = []
        for line in lines:
            if re.search(r'\d{1,5}\s+.+(street|ave|road|rd|lane|blvd|drive|st)\b', line, re.IGNORECASE):
                address_lines.append(line.strip())
            elif re.search(r'(kingston|jamaica)\b', line, re.IGNORECASE):
                address_lines.append(line.strip())
        return ' '.join(address_lines) if address_lines else None

    def _extract_vendor_phone(self, lines: List[str]) -> Optional[str]:
        for line in lines:
            match = re.search(r'(?:tel|phone|ph)\s*[:]?\s*([\d\-\(\) ]{7,})', line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _find_currency(self, lines: List[str]) -> Optional[str]:
        for line in lines:
            match = re.search(r'\b(USD|JMD|EUR|GBP)\b', line)
            if match:
                return match.group(1)
        return None

    def _extract_items_using_pattern(self, lines: List[str], pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        in_items_section = False
        
        for line in lines:
            if re.search(r'(?:description|item|service)\b', line, re.IGNORECASE):
                in_items_section = True
                continue
                
            if in_items_section and re.search(r'\$\d+\.?\d*', line):
                parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                
                if len(parts) >= 4 and pattern.get('columns') == ['description', 'rate', 'quantity', 'amount']:
                    items.append({
                        'description': parts[0],
                        'unit_price': self._extract_currency(parts[1]),
                        'quantity': int(parts[2]) if parts[2].isdigit() else 1,
                        'amount': self._extract_currency(parts[3])
                    })
                elif len(parts) >= 2:
                    items.append({
                        'description': parts[0],
                        'unit_price': self._extract_currency(parts[-1]),
                        'quantity': 1,
                        'amount': self._extract_currency(parts[-1])
                    })
        
        return items


# Example usage
if __name__ == "__main__":
    # Initialize parser (creates database if not exists)
    parser = AdaptiveInvoiceParser()
    
    # Example invoice text (would normally come from OCR)
    invoice_text = """WOCOM Limited
The Trade Center Business
30-32 Red Hills Road = Suite #3A
Kingston 10
8769067240
Jermaine Gray
Celebration Brands Limited
214 Spanish Town Rd
Kingston
WOCOM
Complex
Invoice Number
Date of Issue
Due Date
Amount Due (JMD)
0000085
04/29/2025
04/29/2025
$40,250.00
Description
Rate
$10,000.00
+15%
Qty
1
Line Total
$10,000.00
Flexi Sip Trunk - 4 Channels
Sip Trunk - 4 Voice Channels
Flexi- Channels Upgrade
Multiple DID Service
Caller ID
Toll Fraud Detection
Installation
Receive up to 23 simultaneous calls on 1 phone number
$25,000.00
+15%
1
$25,000.00
Onetime Activation and Forwarding Configs
Subtotal
15% (15%)
Total
Amount Paid
Amount Due (JMD)
35,000.00
5,250.00
40,250.00
0.00
$40,250.00"""
    
    # First parse (will learn the structure)
    result = parser.parse(invoice_text)
    print("First parse result:")
    print(json.dumps(result, indent=2))
    
    # Second parse of similar invoice (will use learned template)
    result2 = parser.parse(invoice_text.replace("0000085", "0000086"))
    print("\nSecond parse result (using learned template):")
    print(json.dumps(result2, indent=2))