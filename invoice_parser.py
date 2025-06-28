# import re
# from typing import Dict, Optional, List, Any
# from datetime import datetime

# class InvoiceParser:
#     """Enhanced invoice parser with robust error handling"""
    
#     @staticmethod
#     def parse_invoice(text: str) -> Dict[str, Any]:
#         """
#         Robust invoice parsing with:
#         - Defensive programming
#         - Better line handling
#         - Comprehensive error recovery
#         """
#         try:
#             # Normalize text and handle empty cases
#             if not text or not isinstance(text, str):
#                 return {"error": "No text provided for parsing"}
                
#             # Clean and prepare text
#             clean_text = re.sub(r'\s+', ' ', text.strip())
#             lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            
#             if not lines:
#                 return {"error": "No content found after text cleaning"}
            
#             # Extract all fields with error handling
#             result = {
#                 "invoice_number": InvoiceParser._safe_extract(lines, r"Invoice Number[:]?\s*([A-Z0-9-]+)"),
#                 "issue_date": InvoiceParser._safe_extract_date(lines, r"Issue Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
#                 "due_date": InvoiceParser._safe_extract_date(lines, r"Due Date[:]?\s*([A-Za-z]+\s\d{1,2},\s\d{4})"),
#                 "status": InvoiceParser._safe_extract(lines, r"Status[:]?\s*([A-Z]+)"),
#                 "vendor": InvoiceParser._extract_vendor_info(lines),
#                 "customer": InvoiceParser._extract_customer_info(lines),
#                 "items": InvoiceParser._safe_extract_items(lines),
#                 "amount_due": InvoiceParser._safe_extract_currency(lines, r"Amount Due[:]?\s*(\$\d+\.\d{2})"),
#                 "subtotal": InvoiceParser._safe_extract_currency(lines, r"Subtotal[:]?\s*(\$\d+\.\d{2})"),
#                 "tax": InvoiceParser._safe_extract_currency(lines, r"Tax[:]?\s*(\$\d+\.\d{2})")
#             }
            
#             # Calculate completeness score
#             filled_fields = sum(1 for v in result.values() if v and not isinstance(v, dict) or 
#                              (isinstance(v, dict) and any(v.values())))
#             result["_completeness"] = f"{(filled_fields/len(result))*100:.1f}%"
            
#             return result
            
#         except Exception as e:
#             return {"error": f"Parsing failed: {str(e)}", "original_text": text[:500] + "..."}

#     @staticmethod
#     def _safe_extract(lines: List[str], pattern: str) -> Optional[str]:
#         """Safe field extraction with error handling"""
#         try:
#             for line in lines:
#                 match = re.search(pattern, line, re.IGNORECASE)
#                 if match:
#                     return match.group(1).strip()
#             return None
#         except:
#             return None

#     @staticmethod
#     def _safe_extract_date(lines: List[str], pattern: str) -> Optional[str]:
#         """Safe date extraction with formatting"""
#         date_str = InvoiceParser._safe_extract(lines, pattern)
#         if not date_str:
#             return None
            
#         try:
#             return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
#         except ValueError:
#             return date_str

#     @staticmethod
#     def _safe_extract_currency(lines: List[str], pattern: str) -> Optional[float]:
#         """Safe currency extraction"""
#         amount = InvoiceParser._safe_extract(lines, pattern)
#         try:
#             return float(amount.replace('$', '')) if amount else None
#         except:
#             return None

#     @staticmethod
#     def _extract_vendor_info(lines: List[str]) -> Dict[str, Optional[str]]:
#         """Robust vendor info extraction"""
#         vendor = {"name": None, "address": None, "email": None, "phone": None}
        
#         try:
#             # Find vendor name (look for LLC/Inc patterns)
#             for line in lines:
#                 if re.search(r"(LLC|Inc|Ltd|Limited|Corp|\,)", line, re.IGNORECASE):
#                     vendor["name"] = line.strip()
#                     break
                
#             # Find address (look for street patterns)
#             for i, line in enumerate(lines):
#                 if re.search(r"\d{3,5}\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road)", line, re.IGNORECASE):
#                     vendor["address"] = line.strip()
#                     if i+1 < len(lines) and re.search(r"[A-Z]{2}\s+\d{5}", lines[i+1]):
#                         vendor["address"] += ", " + lines[i+1].strip()
#                     break
                    
#             # Find email and phone
#             for line in lines:
#                 if not vendor["email"]:
#                     email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
#                     if email_match:
#                         vendor["email"] = email_match.group()
                
#                 if not vendor["phone"]:
#                     phone_match = re.search(r"(\(\d{3}\)\s?\d{3}-\d{4}|\d{3}-\d{3}-\d{4})", line)
#                     if phone_match:
#                         vendor["phone"] = phone_match.group()
                        
#         except Exception as e:
#             pass
            
#         return vendor

#     @staticmethod
#     def _extract_customer_info(lines: List[str]) -> Dict[str, Optional[str]]:
#         """Robust customer info extraction"""
#         customer = {"name": None, "email": None}
        
#         try:
#             # Find "Bill To" section
#             for i, line in enumerate(lines):
#                 if "Bill To" in line and i+1 < len(lines):
#                     customer["name"] = lines[i+1].strip()
#                     break
                    
#             # Find customer email
#             for line in lines:
#                 email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
#                 if email_match and "support@" not in line.lower():
#                     customer["email"] = email_match.group()
#                     break
                    
#         except Exception as e:
#             pass
            
#         return customer

#     @staticmethod
#     def _safe_extract_items(lines: List[str]) -> List[Dict[str, Any]]:
#         """Safe item extraction with multiple fallbacks"""
#         items = []
        
#         try:
#             # Try to find items section
#             item_start = None
#             for i, line in enumerate(lines):
#                 if "Item" in line and i+3 < len(lines):
#                     if any(x in lines[i+1] for x in ["Unit Cost", "Price"]):
#                         item_start = i+2
#                         break
            
#             # If found standard item section
#             if item_start:
#                 for i in range(item_start, len(lines), 4):
#                     if i+3 >= len(lines):
#                         break
                        
#                     items.append({
#                         "description": lines[i].strip(),
#                         "unit_price": InvoiceParser._safe_extract_currency([lines[i+1]], r"(\$\d+\.\d{2})"),
#                         "quantity": float(re.search(r"\d+", lines[i+2]).group()) if re.search(r"\d+", lines[i+2]) else 1,
#                         "amount": InvoiceParser._safe_extract_currency([lines[i+3]], r"(\$\d+\.\d{2})")
#                     })
#             else:
#                 # Fallback: look for any price patterns
#                 for i, line in enumerate(lines):
#                     price_match = re.search(r"\$\d+\.\d{2}", line)
#                     if price_match:
#                         items.append({
#                             "description": line[:line.find("$")].strip(),
#                             "unit_price": float(price_match.group().replace("$", "")),
#                             "quantity": 1,
#                             "amount": float(price_match.group().replace("$", ""))
#                         })
                        
#         except Exception as e:
#             pass
            
#         return items

# import re
# from typing import Dict, Optional, List, Any
# from datetime import datetime
# from dateutil.parser import parse as parse_date


# class InvoiceParser:
#     """Improved Invoice Parser for OCR text"""

#     @staticmethod
#     def parse_invoice(text: str) -> Dict[str, Any]:
#         if not text or not isinstance(text, str):
#             return {"error": "No text provided"}

#         lines = [line.strip() for line in text.split('\n') if line.strip()]
#         if not lines:
#             return {"error": "No lines to parse"}

#         result = {
#             "invoice_number": InvoiceParser._safe_extract_next_line(lines, ["Invoice Number", "Invoice No", "Inv No", "#"]),
#             "issue_date": InvoiceParser._safe_extract_date_next_line(lines, ["Issue Date", "Date of Issue", "Invoice Date"]),
#             "due_date": InvoiceParser._safe_extract_date_next_line(lines, ["Due Date", "Payment Due"]),
#             "status": InvoiceParser._safe_extract(lines, r"Status[:]?\s*([A-Z]+)"),
#             "vendor": InvoiceParser._extract_vendor_info(lines),
#             "customer": InvoiceParser._extract_customer_info(lines),
#             "items": InvoiceParser._extract_items(lines),
#             "amount_due": InvoiceParser._safe_extract_currency(lines, r"(?:Amount Due|Balance Due|Total Due|Total Amount)[:\s\$]*([\d,]+\.\d{2})"),
#             "subtotal": InvoiceParser._safe_extract_currency(lines, r"Subtotal[:]?\s*\$?([\d,]+\.\d{2})"),
#             "tax": InvoiceParser._safe_extract_currency(lines, r"(?:Tax|VAT|Sales Tax)[:]?\s*\$?([\d,]+\.\d{2})")
#         }

#         result.update(InvoiceParser._custom_field_hooks(lines))

#         # Scoring
#         total_fields = len(result)
#         filled = sum(1 for v in result.values() if InvoiceParser._is_filled(v))
#         confidence = round(filled / total_fields, 2)
#         result["_completeness"] = f"{confidence * 100:.1f}%"
#         result["_confidence_score"] = confidence
#         result["_fallback_needed"] = confidence < 0.6
#         result["_raw_context"] = InvoiceParser._annotate_raw_context(lines[:15])

#         return result

#     # === Extraction Utilities ===

#     @staticmethod
#     def _safe_extract(lines: List[str], pattern: str) -> Optional[str]:
#         try:
#             for line in lines:
#                 match = re.search(pattern, line, re.IGNORECASE)
#                 if match:
#                     return match.group(1).strip()
#         except:
#             pass
#         return None

#     @staticmethod
#     def _safe_extract_next_line(lines: List[str], keywords: List[str]) -> Optional[str]:
#         for i, line in enumerate(lines):
#             if any(k.lower() in line.lower() for k in keywords):
#                 return lines[i+1].strip() if i+1 < len(lines) else None
#         return None

#     @staticmethod
#     def _safe_extract_date_next_line(lines: List[str], keywords: List[str]) -> Optional[str]:
#         raw = InvoiceParser._safe_extract_next_line(lines, keywords)
#         if not raw:
#             return None
#         try:
#             return parse_date(raw, fuzzy=True).strftime("%Y-%m-%d")
#         except:
#             return raw.strip()

#     @staticmethod
#     def _safe_extract_currency(lines: List[str], pattern: str) -> Optional[float]:
#         raw = InvoiceParser._safe_extract(lines, pattern)
#         if raw:
#             try:
#                 return float(re.sub(r"[^\d.]", "", raw))
#             except:
#                 return None
#         return None

#     # === Vendor / Customer ===

#     @staticmethod
#     def _extract_vendor_info(lines: List[str]) -> Dict[str, Optional[str]]:
#         vendor = {"name": None, "address": None, "email": None, "phone": None}
#         for line in lines[:10]:
#             if re.search(r"(LLC|Inc|Ltd|Limited|Corp|Company|WOCOM)", line, re.IGNORECASE):
#                 vendor["name"] = line
#             if re.search(r"\d{1,5}.+(Street|Ave|Road|Lane|Blvd|Drive|Rd)", line, re.IGNORECASE):
#                 vendor["address"] = line
#         for line in lines:
#             if not vendor["email"]:
#                 email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
#                 if email_match:
#                     vendor["email"] = email_match.group()
#             if not vendor["phone"]:
#                 phone_match = re.search(r"(\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{7,})", line)
#                 if phone_match:
#                     vendor["phone"] = phone_match.group()
#         return vendor

#     @staticmethod
#     def _extract_customer_info(lines: List[str]) -> Dict[str, Optional[str]]:
#         customer = {"name": None, "email": None}
#         for i, line in enumerate(lines):
#             if "Bill To" in line and i + 1 < len(lines):
#                 customer["name"] = lines[i + 1].strip()
#         for line in lines:
#             email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
#             if email_match and "support@" not in line.lower():
#                 customer["email"] = email_match.group()
#                 break
#         return customer

#     # === Items ===

#     @staticmethod
#     def _extract_items(lines: List[str]) -> List[Dict[str, Any]]:
#         items = []
#         for i, line in enumerate(lines):
#             price_match = re.search(r"\$[\d,]+\.\d{2}", line)
#             if price_match:
#                 amount = float(re.sub(r"[^\d.]", "", price_match.group()))
#                 description = ""
#                 for offset in range(1, 3):
#                     if i - offset >= 0 and not re.search(r"\$[\d,]+\.\d{2}", lines[i - offset]):
#                         description = lines[i - offset].strip() + " " + description
#                 items.append({
#                     "description": description.strip(),
#                     "unit_price": amount,
#                     "quantity": 1,
#                     "amount": amount
#                 })
#         return items

#     # === Additional Hooks ===

#     @staticmethod
#     def _custom_field_hooks(lines: List[str]) -> Dict[str, Any]:
#         return {
#             "po_number": InvoiceParser._safe_extract(lines, r"PO(?: Number|#)?[:]?\s*([A-Z0-9-]+)"),
#             "currency": InvoiceParser._safe_extract(lines, r"(USD|JMD|EUR|GBP)")
#         }

#     @staticmethod
#     def _is_filled(value: Any) -> bool:
#         if isinstance(value, dict):
#             return any(v for v in value.values())
#         if isinstance(value, list):
#             return len(value) > 0
#         return value not in (None, "", [], {})

#     # === Debug / Explainability ===

#     @staticmethod
#     def _annotate_raw_context(lines: List[str]) -> List[Dict[str, str]]:
#         labeled = []
#         for line in lines:
#             l = line.strip()
#             if re.search(r"(limited|llc|inc|corp)", l, re.IGNORECASE):
#                 label = "vendor_name"
#             elif re.search(r"\d{7,}", l):
#                 label = "vendor_phone"
#             elif re.search(r"(invoice|date|due|amount)", l, re.IGNORECASE):
#                 label = "field_label"
#             elif re.search(r"(spanish town|red hills|road|rd|kingston)", l, re.IGNORECASE):
#                 label = "address"
#             elif re.search(r"jermaine|gray", l, re.IGNORECASE):
#                 label = "contact_person"
#             elif "celebration" in l.lower():
#                 label = "customer_name"
#             elif l.lower().startswith("the "):
#                 label = "business_tagline"
#             else:
#                 label = "unknown"
#             labeled.append({"label": label, "value": l})
#         return labeled


import re
from typing import List, Dict, Any, Optional
from dateutil.parser import parse as parse_date


class InvoiceParser:
    FIELD_LABELS = {
        "invoice_number": ["invoice number", "inv no", "tax invoice", "invoice #", "invoice no"],
        "issue_date": ["invoice date", "issue date", "date of issue", "date"],
        "due_date": ["due date", "payment due"],
        "amount_due": ["balance due", "amount due", "total due", "amount payable"],
        "subtotal": ["subtotal"],
        "tax": ["tax", "vat", "gct"],
        "po_number": ["po number", "purchase order", "order number"],
        "vendor_phone": ["tel", "telephone", "phone"],
        "vendor_email": ["email"],
        "vendor_fax": ["fax"],
        "customer": ["bill to", "ship to"]
    }

    CURRENCY_PATTERN = r"\b(USD|JMD|EUR|GBP)\b"

    def parse(self, ocr_text: str) -> Dict[str, Any]:
        lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
        labeled = self.classify_lines(lines)

        structure = {
            "invoice_number": self.extract_invoice_number(labeled),
            "po_number": self.extract_value_near(labeled, "po_number"),
            "issue_date": self.extract_date(labeled, "issue_date"),
            "due_date": self.extract_date(labeled, "due_date"),
            "amount_due": self.extract_amount_due(labeled),
            "subtotal": self.extract_currency_near(labeled, "subtotal"),
            "tax": self.extract_currency_near(labeled, "tax"),
            "vendor": self.parse_vendor_info(lines),
            "customer": {
                "name": self.extract_value(labeled, "customer"),
                "email": None
            },
            "items": self.extract_items(lines),
            "currency": self.find_currency(lines)
        }

        filled = sum(1 for v in structure.values() if self._is_filled(v))
        total = len(structure)
        score = round(filled / total, 2)

        structure["_completeness"] = f"{score * 100:.1f}%"
        structure["_confidence_score"] = score
        structure["_fallback_needed"] = score < 0.6
        structure["_raw_context"] = labeled

        return structure

    def classify_lines(self, lines: List[str]) -> List[Dict[str, str]]:
        results = []
        for line in lines:
            lower = line.lower()
            label = "unknown"
            for key, keywords in self.FIELD_LABELS.items():
                if any(k in lower for k in keywords):
                    label = key
                    break
            if not label.startswith("vendor") and re.search(r"\d{7,}", line):
                label = "vendor_phone"
            results.append({"label": label, "value": line})
        return results

    def extract_invoice_number(self, lines: List[Dict[str, str]]) -> Optional[str]:
        # Look for numeric patterns near invoice number labels
        for idx, line in enumerate(lines):
            if line["label"] == "invoice_number":
                # Check next few lines for potential invoice numbers
                for offset in range(1, 4):
                    if idx + offset < len(lines):
                        candidate = lines[idx + offset]["value"].strip()
                        if re.match(r"^\d{5,}$", candidate):  # At least 5 digits
                            return candidate
                        if re.match(r"^[A-Z]{2,}\d{3,}$", candidate):  # Mix of letters and numbers
                            return candidate
        
        # Fallback: look for any invoice-like code in the document
        for line in lines:
            if self._is_invoice_code(line["value"]):
                return line["value"].strip()
        
        return None

    def _is_invoice_code(self, text: str) -> bool:
        text = text.strip()
        if len(text) < 5:
            return False
        if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text):
            return False
        if re.search(r"\$\d+", text):
            return False
        if re.match(r"^(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})$", text):
            return False
        if re.match(r"^\d{10}$", text):
            return False
        return bool(re.match(r"^[A-Z0-9\-]{5,}$", text))

    def extract_value(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
        for line in lines:
            if line["label"] == label:
                parts = line["value"].split()
                for p in parts[::-1]:
                    if re.match(r"[A-Z0-9\-]{4,}", p):
                        return p
                return line["value"]
        return None

    def extract_value_near(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
        for idx, line in enumerate(lines):
            if line["label"] == label:
                for offset in range(1, 4):
                    if idx + offset < len(lines):
                        candidate = lines[idx + offset]["value"]
                        match = re.search(r"[A-Z0-9]{5,}", candidate)
                        if match:
                            return match.group()
        return None

    def extract_date(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
        for line in lines:
            if line["label"] == label:
                try:
                    return parse_date(line["value"], fuzzy=True).strftime("%Y-%m-%d")
                except:
                    continue
        for line in lines:
            match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", line["value"])
            if match:
                try:
                    return parse_date(match.group(), fuzzy=True).strftime("%Y-%m-%d")
                except:
                    continue
        return None

    def extract_amount_due(self, lines: List[Dict[str, str]]) -> Optional[float]:
        # Look for amount near "Amount Due" label
        for idx, line in enumerate(lines):
            if line["label"] == "amount_due":
                # Check next few lines for currency amounts
                for offset in range(1, 4):
                    if idx + offset < len(lines):
                        amount_str = lines[idx + offset]["value"]
                        match = re.search(r"[\$JMD]*[\s]*([\d,]+\.\d{2})", amount_str)
                        if match:
                            try:
                                return float(match.group(1).replace(",", ""))
                            except:
                                continue
        return None

    def extract_currency_near(self, lines: List[Dict[str, str]], label: str) -> Optional[float]:
        for idx, line in enumerate(lines):
            if line["label"] == label:
                for lookahead in range(1, 3):
                    if idx + lookahead < len(lines):
                        target = lines[idx + lookahead]["value"]
                        match = re.search(r"[\$JMD]*[\s]*([\d,]+\.\d{2})", target)
                        if match:
                            try:
                                return float(match.group(1).replace(",", ""))
                            except:
                                continue
        return None

    def extract_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        items = []
        item_pattern = re.compile(
            r"(?P<desc>.+?)\s+"  # Description
            r"(?P<rate>\$\d+,\d+\.\d{2})\s+"  # Rate
            r"(?:\+15\%\s+)?"  # Optional tax indicator
            r"(?P<qty>\d+)\s+"  # Quantity
            r"(?P<total>\$\d+,\d+\.\d{2})"  # Total
        )
        
        for line in lines:
            match = item_pattern.search(line)
            if match:
                items.append({
                    "description": match.group("desc").strip(),
                    "unit_price": float(match.group("rate").replace("$", "").replace(",", "")),
                    "quantity": int(match.group("qty")),
                    "amount": float(match.group("total").replace("$", "").replace(",", ""))
                })
        
        # Fallback for simpler item formats
        if not items:
            for idx, line in enumerate(lines):
                if re.search(r"\$\d{1,3}(?:,\d{3})*\.\d{2}", line):
                    amount = float(re.sub(r"[^\d.]", "", line))
                    description = ""
                    qty = 1
                    if idx > 0:
                        description = lines[idx - 1].strip()
                    if idx + 2 < len(lines):
                        if re.match(r"\d+$", lines[idx + 2]):
                            qty = int(lines[idx + 2])
                    items.append({
                        "description": description,
                        "unit_price": amount,
                        "quantity": qty,
                        "amount": amount * qty
                    })
        return items

    def parse_vendor_info(self, lines: List[str]) -> Dict[str, Any]:
        vendor = {
            "name": None,
            "address": None,
            "email": None,
            "phone": None
        }
        
        # Look for vendor name in first few lines
        for line in lines[:5]:
            if re.search(r"(limited|llc|inc|corp|company)", line, re.IGNORECASE):
                vendor["name"] = line.strip()
                break
                
        # Look for address components
        address_lines = []
        for line in lines:
            if re.search(r"\d{1,5}\s+.+(street|ave|road|rd|lane|blvd|drive)", line, re.IGNORECASE):
                address_lines.append(line.strip())
            elif re.search(r"kingston|jamaica", line, re.IGNORECASE):
                address_lines.append(line.strip())
        
        vendor["address"] = " ".join(address_lines) if address_lines else None
        
        # Extract phone number
        for line in lines:
            phone_match = re.search(r"(?:tel|phone):?\s*([\d\-\(\) ]+)", line, re.IGNORECASE)
            if phone_match:
                vendor["phone"] = phone_match.group(1).strip()
                break
                
        return vendor

    def find_currency(self, lines: List[str]) -> Optional[str]:
        for line in lines:
            match = re.search(self.CURRENCY_PATTERN, line)
            if match:
                return match.group()
        return None

    def _is_filled(self, value: Any) -> bool:
        if isinstance(value, dict):
            return any(self._is_filled(v) for v in value.values())
        return bool(value)


# Example usage:
if __name__ == "__main__":
    parser = InvoiceParser()
    with open("invoice.txt", "r") as f:
        ocr_text = f.read()
    result = parser.parse(ocr_text)
    print(result)