# import re
# from typing import List, Dict, Any, Optional
# from dateutil.parser import parse as parse_date


# class DynamicInvoiceParser:
#     FIELD_LABELS = {
#         "invoice_number": ["invoice number", "inv no", "tax invoice", "invoice #", "invoice no"],
#         "issue_date": ["invoice date", "issue date", "date of issue", "date"],
#         "due_date": ["due date", "payment due"],
#         "amount_due": ["balance due", "amount due", "total due", "amount payable"],
#         "subtotal": ["subtotal"],
#         "tax": ["tax", "vat", "gct"],
#         "po_number": ["po number", "purchase order", "order number"],
#         "vendor_phone": ["tel", "telephone", "phone"],
#         "vendor_email": ["email"],
#         "vendor_fax": ["fax"],
#         "customer": ["bill to", "ship to"]
#     }

#     CURRENCY_PATTERN = r"\b(USD|JMD|EUR|GBP)\b"

#     def parse(self, ocr_text: str) -> Dict[str, Any]:
#         lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
#         labeled = self.classify_lines(lines)

#         structure = {
#             "invoice_number": self.extract_invoice_number(labeled),
#             "po_number": self.extract_value_near(labeled, "po_number"),
#             "issue_date": self.extract_date(labeled, "issue_date"),
#             "due_date": self.extract_date(labeled, "due_date"),
#             "amount_due": self.extract_currency_near(labeled, "amount_due"),
#             "subtotal": self.extract_currency_near(labeled, "subtotal"),
#             "tax": self.extract_currency_near(labeled, "tax"),
#             "vendor": {
#                 "name": self.guess_vendor_name(lines),
#                 "address": self.guess_vendor_address(lines),
#                 "email": self.extract_value(labeled, "vendor_email"),
#                 "phone": self.extract_value(labeled, "vendor_phone")
#             },
#             "customer": {
#                 "name": self.extract_value(labeled, "customer"),
#                 "email": None
#             },
#             "items": self.extract_items(lines),
#             "currency": self.find_currency(lines)
#         }

#         filled = sum(1 for v in structure.values() if self._is_filled(v))
#         total = len(structure)
#         score = round(filled / total, 2)

#         structure["_completeness"] = f"{score * 100:.1f}%"
#         structure["_confidence_score"] = score
#         structure["_fallback_needed"] = score < 0.6
#         structure["_raw_context"] = labeled

#         return structure

#     def classify_lines(self, lines: List[str]) -> List[Dict[str, str]]:
#         results = []
#         for line in lines:
#             lower = line.lower()
#             label = "unknown"
#             for key, keywords in self.FIELD_LABELS.items():
#                 if any(k in lower for k in keywords):
#                     label = key
#                     break
#             if not label.startswith("vendor") and re.search(r"\d{7,}", line):
#                 label = "vendor_phone"
#             results.append({"label": label, "value": line})
#         return results

#     def extract_invoice_number(self, lines: List[Dict[str, str]]) -> Optional[str]:
#         import difflib

#         label_keywords = [
#             "invoice number", "inv", "inv#", "inv no", "document number", "tax invoice"
#         ]

#         for idx, line in enumerate(lines):
#             content = line["value"].lower()
#             close_match = difflib.get_close_matches(content, label_keywords, n=1, cutoff=0.7)
#             if close_match:
#                 for offset in range(1, 4):
#                     if idx + offset < len(lines):
#                         candidate = lines[idx + offset]["value"]
#                         if self._is_invoice_code(candidate):
#                             return candidate.strip()

#         for line in lines[:10]:
#             if self._is_invoice_code(line["value"]):
#                 return line["value"].strip()

#         for line in lines:
#             if self._is_invoice_code(line["value"]):
#                 return line["value"].strip()

#         return None


#     def _is_invoice_code(self, text: str) -> bool:
#         text = text.strip()
#         # Too short
#         if len(text) < 5:
#             return False
#         # Is a date
#         if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text):
#             return False
#         # Is a currency amount
#         if re.search(r"\$\d+", text):
#             return False
#         # Is a phone number (e.g., 10-digit or (876) xxx-xxxx)
#         if re.match(r"^(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})$", text):
#             return False
#         if re.match(r"^\d{10}$", text):  # raw 10-digit number
#             return False
#         # Good code pattern (letters + numbers, or digits-only if not phone-like)
#         return bool(re.match(r"^[A-Z0-9\-]{5,}$", text))


#     def extract_value(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
#         for line in lines:
#             if line["label"] == label:
#                 parts = line["value"].split()
#                 for p in parts[::-1]:
#                     if re.match(r"[A-Z0-9\-]{4,}", p):
#                         return p
#                 return line["value"]
#         return None

#     def extract_value_near(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
#         for idx, line in enumerate(lines):
#             if line["label"] == label:
#                 for offset in range(1, 4):
#                     if idx + offset < len(lines):
#                         candidate = lines[idx + offset]["value"]
#                         match = re.search(r"[A-Z0-9]{5,}", candidate)
#                         if match:
#                             return match.group()
#         return None

#     def extract_date(self, lines: List[Dict[str, str]], label: str) -> Optional[str]:
#         for line in lines:
#             if line["label"] == label:
#                 try:
#                     return parse_date(line["value"], fuzzy=True).strftime("%Y-%m-%d")
#                 except:
#                     continue
#         for line in lines:
#             match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", line["value"])
#             if match:
#                 try:
#                     return parse_date(match.group(), fuzzy=True).strftime("%Y-%m-%d")
#                 except:
#                     continue
#         return None

#     def extract_currency_near(self, lines: List[Dict[str, str]], label: str) -> Optional[float]:
#         for idx, line in enumerate(lines):
#             if line["label"] == label:
#                 for lookahead in range(1, 3):
#                     if idx + lookahead < len(lines):
#                         target = lines[idx + lookahead]["value"]
#                         match = re.search(r"[\$JMD]*[\s]*([\d,]+\.\d{2})", target)
#                         if match:
#                             try:
#                                 return float(match.group(1).replace(",", ""))
#                             except:
#                                 continue
#         return None

#     def extract_items(self, lines: List[str]) -> List[Dict[str, Any]]:
#         items = []
#         for idx, line in enumerate(lines):
#             if re.search(r"\$\d{1,3}(?:,\d{3})*\.\d{2}", line):
#                 amount = float(re.sub(r"[^\d.]", "", line))
#                 description = ""
#                 qty = 1
#                 if idx > 0:
#                     description = lines[idx - 1].strip()
#                 if idx + 2 < len(lines):
#                     if re.match(r"\d+$", lines[idx + 2]):
#                         qty = int(lines[idx + 2])
#                 items.append({
#                     "description": description,
#                     "unit_price": amount,
#                     "quantity": qty,
#                     "amount": amount * qty
#                 })
#         return items

#     def guess_vendor_name(self, lines: List[str]) -> Optional[str]:
#         for line in lines[:5]:
#             if re.search(r"(limited|llc|inc|corp|pbs)", line, re.IGNORECASE):
#                 return line.strip()
#         return None

#     def guess_vendor_address(self, lines: List[str]) -> Optional[str]:
#         for line in lines:
#             if re.search(r"\d{1,5}.+(Street|Ave|Road|Lane|Blvd|Drive|Rd)", line, re.IGNORECASE):
#                 return line.strip()
#         return None

#     def find_currency(self, lines: List[str]) -> Optional[str]:
#         for line in lines:
#             match = re.search(self.CURRENCY_PATTERN, line)
#             if match:
#                 return match.group()
#         return None

#     def _is_filled(self, value: Any) -> bool:
#         if isinstance(value, dict):
#             return any(self._is_filled(v) for v in value.values())
#         return bool(value)

import re
from typing import List, Dict, Any, Optional
from dateutil.parser import parse as parse_date


class DynamicInvoiceParser:
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
    parser = ImprovedInvoiceParser()
    with open("invoice.txt", "r") as f:
        ocr_text = f.read()
    result = parser.parse(ocr_text)
    print(result)