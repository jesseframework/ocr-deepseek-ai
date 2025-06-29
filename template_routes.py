from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Tuple, Optional
import sqlite3
import json
from datetime import datetime
from parsers.adaptive_invoice_parser import AdaptiveInvoiceParser, InvoiceTemplate
from fastapi import Query

router = APIRouter()

class TemplateCorrection(BaseModel):
    template_id: str
    field_positions: Dict[str, Tuple[int, int]]
    item_pattern: Optional[Dict[str, Any]] = None

@router.post("/api/v2/templates/update", tags=["Templates"])
def update_template(correction: TemplateCorrection):
    parser = AdaptiveInvoiceParser()
    with sqlite3.connect(parser.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates WHERE template_id = ?", (correction.template_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")

        template = InvoiceTemplate(
            template_id=row[0],
            vendor_name=row[1],
            structure_hash=row[2],
            field_positions=correction.field_positions,
            item_pattern=correction.item_pattern or json.loads(row[4]),
            created_at=row[5],
            last_used=datetime.now().isoformat(),
            usage_count=row[7]
        )

        parser._save_template(template)

    return {"status": "success", "message": "Template updated", "template_id": correction.template_id}


@router.get("/api/v2/templates", tags=["Templates"])
def list_templates(template_id: Optional[str] = Query(default=None)):
    parser = AdaptiveInvoiceParser()
    with sqlite3.connect(parser.db_path) as conn:
        cursor = conn.cursor()
        if template_id:
            cursor.execute("SELECT * FROM templates WHERE template_id = ?", (template_id,))
        else:
            cursor.execute("SELECT * FROM templates ORDER BY last_used DESC")

        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No templates found")

        templates = []
        for row in rows:
            templates.append({
                "template_id": row[0],
                "vendor_name": row[1],
                "structure_hash": row[2],
                "field_positions": json.loads(row[3]),
                "item_pattern": json.loads(row[4]),
                "created_at": row[5],
                "last_used": row[6],
                "usage_count": row[7]
            })

    return {
        "status": "success",
        "count": len(templates),
        "templates": templates
    }
