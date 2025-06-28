import re
from typing import Dict, Optional, List, Any
from datetime import datetime

class InvoiceParser:
    """Enhanced invoice parser with robust error handling"""
    
    @staticmethod
    def parse_invoice(text: str) -> Dict[str, Any]:
        """
        Robust invoice parsing with:
        - Defensive programming
        - Better line handling
        - Comprehensive error recovery
        """
        try:
            # Normalize text and handle empty cases
            if not text or not isinstance(text, str):
                return {"error": "No text provided for parsing"}
                
            # Clean and prepare text
            clean_text = re.sub(r'\s+', ' ', text.strip())
            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            
            if not lines:
                return {"error": "No content found after text cleaning"}
            
            # Extract all fields with error handling
            result = {
                "invoice_number": InvoiceParser._safe_extract(lines, r"Invoice Number[:]?\s*([A-Z0-9-]+)"),
                "issue_date": InvoiceParser._safe_extract_date(lines, r"Issue Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
                "due_date": InvoiceParser._safe_extract_date(lines, r"Due Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
                "status": InvoiceParser._safe_extract(lines, r"Status[:]?\s*([A-Z]+)"),
                "vendor": InvoiceParser._extract_vendor_info(lines),
                "customer": InvoiceParser._extract_customer_info(lines),
                "items": InvoiceParser._safe_extract_items(lines),
                "amount_due": InvoiceParser._safe_extract_currency(lines, r"Amount Due[:]?\s*(\$\d+\.\d{2})"),
                "subtotal": InvoiceParser._safe_extract_currency(lines, r"Subtotal[:]?\s*(\$\d+\.\d{2})"),
                "tax": InvoiceParser._safe_extract_currency(lines, r"Tax[:]?\s*(\$\d+\.\d{2})")
            }
            
            # Calculate completeness score
            filled_fields = sum(1 for v in result.values() if v and not isinstance(v, dict) or 
                             (isinstance(v, dict) and any(v.values())))
            result["_completeness"] = f"{(filled_fields/len(result))*100:.1f}%"
            
            return result
            
        except Exception as e:
            return {"error": f"Parsing failed: {str(e)}", "original_text": text[:500] + "..."}

    @staticmethod
    def _safe_extract(lines: List[str], pattern: str) -> Optional[str]:
        """Safe field extraction with error handling"""
        try:
            for line in lines:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None
        except:
            return None

    @staticmethod
    def _safe_extract_date(lines: List[str], pattern: str) -> Optional[str]:
        """Safe date extraction with formatting"""
        date_str = InvoiceParser._safe_extract(lines, pattern)
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return date_str

    @staticmethod
    def _safe_extract_currency(lines: List[str], pattern: str) -> Optional[float]:
        """Safe currency extraction"""
        amount = InvoiceParser._safe_extract(lines, pattern)
        try:
            return float(amount.replace('$', '')) if amount else None
        except:
            return None

    @staticmethod
    def _extract_vendor_info(lines: List[str]) -> Dict[str, Optional[str]]:
        """Robust vendor info extraction"""
        vendor = {"name": None, "address": None, "email": None, "phone": None}
        
        try:
            # Find vendor name (look for LLC/Inc patterns)
            for line in lines:
                if re.search(r"(LLC|Inc|Ltd|Limited|Corp|\,)", line, re.IGNORECASE):
                    vendor["name"] = line.strip()
                    break
                
            # Find address (look for street patterns)
            for i, line in enumerate(lines):
                if re.search(r"\d{3,5}\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road)", line, re.IGNORECASE):
                    vendor["address"] = line.strip()
                    if i+1 < len(lines) and re.search(r"[A-Z]{2}\s+\d{5}", lines[i+1]):
                        vendor["address"] += ", " + lines[i+1].strip()
                    break
                    
            # Find email and phone
            for line in lines:
                if not vendor["email"]:
                    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
                    if email_match:
                        vendor["email"] = email_match.group()
                
                if not vendor["phone"]:
                    phone_match = re.search(r"(\(\d{3}\)\s?\d{3}-\d{4}|\d{3}-\d{3}-\d{4})", line)
                    if phone_match:
                        vendor["phone"] = phone_match.group()
                        
        except Exception as e:
            pass
            
        return vendor

    @staticmethod
    def _extract_customer_info(lines: List[str]) -> Dict[str, Optional[str]]:
        """Robust customer info extraction"""
        customer = {"name": None, "email": None}
        
        try:
            # Find "Bill To" section
            for i, line in enumerate(lines):
                if "Bill To" in line and i+1 < len(lines):
                    customer["name"] = lines[i+1].strip()
                    break
                    
            # Find customer email
            for line in lines:
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
                if email_match and "support@" not in line.lower():
                    customer["email"] = email_match.group()
                    break
                    
        except Exception as e:
            pass
            
        return customer

    @staticmethod
    def _safe_extract_items(lines: List[str]) -> List[Dict[str, Any]]:
        """Safe item extraction with multiple fallbacks"""
        items = []
        
        try:
            # Try to find items section
            item_start = None
            for i, line in enumerate(lines):
                if "Item" in line and i+3 < len(lines):
                    if any(x in lines[i+1] for x in ["Unit Cost", "Price"]):
                        item_start = i+2
                        break
            
            # If found standard item section
            if item_start:
                for i in range(item_start, len(lines), 4):
                    if i+3 >= len(lines):
                        break
                        
                    items.append({
                        "description": lines[i].strip(),
                        "unit_price": InvoiceParser._safe_extract_currency([lines[i+1]], r"(\$\d+\.\d{2})"),
                        "quantity": float(re.search(r"\d+", lines[i+2]).group()) if re.search(r"\d+", lines[i+2]) else 1,
                        "amount": InvoiceParser._safe_extract_currency([lines[i+3]], r"(\$\d+\.\d{2})")
                    })
            else:
                # Fallback: look for any price patterns
                for i, line in enumerate(lines):
                    price_match = re.search(r"\$\d+\.\d{2}", line)
                    if price_match:
                        items.append({
                            "description": line[:line.find("$")].strip(),
                            "unit_price": float(price_match.group().replace("$", "")),
                            "quantity": 1,
                            "amount": float(price_match.group().replace("$", ""))
                        })
                        
        except Exception as e:
            pass
            
        return items