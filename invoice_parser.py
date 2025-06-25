import re
from typing import Dict, Optional, List
from datetime import datetime

class InvoiceParser:
    """Enhanced invoice parser with better field extraction"""
    
    @staticmethod
    def parse_invoice(text: str) -> Dict[str, any]:
        """
        Improved invoice parsing with:
        - Better regex patterns
        - Multi-line field handling
        - Error-resistant parsing
        """
        # Normalize text first
        clean_text = re.sub(r'\s+', ' ', text.strip())
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        
        return {
            "invoice_number": InvoiceParser._extract_field(lines, r"Invoice Number[:]?\s*([A-Z0-9-]+)"),
            "issue_date": InvoiceParser._extract_date(lines, r"Issue Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
            "due_date": InvoiceParser._extract_date(lines, r"Due Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
            "status": InvoiceParser._extract_field(lines, r"Status[:]?\s*([A-Z]+)"),
            "vendor": {
                "name": InvoiceParser._extract_vendor_name(lines),
                "address": InvoiceParser._extract_vendor_address(lines),
                "email": InvoiceParser._extract_email(lines, r"support@([a-zA-Z0-9.-]+)"),
                "phone": InvoiceParser._extract_phone(lines)
            },
            "customer": {
                "name": InvoiceParser._extract_customer_name(lines),
                "email": InvoiceParser._extract_email(lines, r"cusi?omer@([a-zA-Z0-9.-]+)")
            },
            "items": InvoiceParser._extract_items(lines),
            "amount_due": InvoiceParser._extract_currency(lines, r"Amount Due[:]?\s*(\$\d+\.\d{2})"),
            "subtotal": InvoiceParser._extract_currency(lines, r"Subtotal[:]?\s*(\$\d+\.\d{2})"),
            "tax": InvoiceParser._extract_currency(lines, r"Tax[:]?\s*(\$\d+\.\d{2})")
        }
    
    @staticmethod
    def _extract_field(lines: List[str], pattern: str) -> Optional[str]:
        """Extract single field using regex"""
        for line in lines:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    @staticmethod
    def _extract_date(lines: List[str], pattern: str) -> Optional[str]:
        """Extract and format date"""
        date_str = InvoiceParser._extract_field(lines, pattern)
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return date_str
    
    @staticmethod
    def _extract_currency(lines: List[str], pattern: str) -> Optional[float]:
        """Extract currency value"""
        amount = InvoiceParser._extract_field(lines, pattern)
        return float(amount.replace('$', '')) if amount else None
    
    @staticmethod
    def _extract_vendor_name(lines: List[str]) -> Optional[str]:
        """Special handling for vendor name"""
        for i, line in enumerate(lines):
            if re.search(r"(LLC|Inc|Ltd|Corp)[.]?$", line, re.IGNORECASE):
                return line.strip()
            if "Example," in line:  # Fallback for your specific case
                return line.strip()
        return None
    
    @staticmethod
    def _extract_vendor_address(lines: List[str]) -> Optional[str]:
        """Extract multi-line address"""
        for i, line in enumerate(lines):
            if re.search(r"\d{3}\s\w+\s(Street|St|Avenue|Ave|Road|Rd)", line):
                return f"{line.strip()}, {lines[i+1].strip()}" if i+1 < len(lines) else line.strip()
        return None
    
    @staticmethod
    def _extract_phone(lines: List[str]) -> Optional[str]:
        """Extract phone number with various formats"""
        for line in lines:
            match = re.search(r"(\(\d{3}\)\s?\d{3}-\d{4}|\d{3}-\d{3}-\d{4})", line)
            if match:
                return match.group()
        return None
    
    @staticmethod
    def _extract_customer_name(lines: List[str]) -> Optional[str]:
        """Find customer name after Bill To"""
        for i, line in enumerate(lines):
            if "Bill To" in line and i+1 < len(lines):
                return lines[i+1].strip()
        return None
    
    @staticmethod
    def _extract_email(lines: List[str], pattern: str) -> Optional[str]:
        """Extract email with domain validation"""
        for line in lines:
            match = re.search(r"[\w.-]+@([\w-]+\.)+[\w-]{2,4}", line)
            if match:
                return match.group()
        return None
    
    @staticmethod
    def _extract_items(lines: List[str]) -> List[Dict]:
        """Improved item extraction"""
        items = []
        item_start = None
        
        # Find where items section begins
        for i, line in enumerate(lines):
            if "Item" in line and "Unit Cost" in lines[i+1]:
                item_start = i+2
                break
        
        if item_start:
            # Process in blocks of 4 lines (Item, Unit Cost, Quantity, Amount)
            for i in range(item_start, len(lines), 4):
                if i+3 >= len(lines):
                    break
                    
                items.append({
                    "description": lines[i].strip(),
                    "unit_price": InvoiceParser._extract_currency([lines[i+1]], r"(\$\d+\.\d{2})"),
                    "quantity": float(re.search(r"\d+", lines[i+2]).group()) if re.search(r"\d+", lines[i+2]) else 1,
                    "amount": InvoiceParser._extract_currency([lines[i+3]], r"(\$\d+\.\d{2})")
                })
        
        return items